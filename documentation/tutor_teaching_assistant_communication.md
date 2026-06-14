# Tutor ↔ TeachingAssistant Communication Architecture

## Overview

This document outlines the plan to upgrade communication between the Frontend Tutor service and Backend TeachingAssistant service, including proper session state management for production readiness.

**Goals:**
1. **Channel 1:** Replace POST `/webhook/feed` with WebSocket for streaming audio/video/transcript
2. **Channel 2:** Add SSE endpoint for TeachingAssistant to push instructions to Tutor
3. **Session Management:** Persist session state to MongoDB for multi-instance Cloud Run support

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CURRENT STATE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Frontend                          Backend (Cloud Run)                      │
│  ┌─────────────┐                   ┌─────────────────────┐                  │
│  │   Tutor     │  POST /webhook/   │  TeachingAssistant  │                  │
│  │   Service   │ ────────────────► │  (Singleton)        │                  │
│  │             │  feed             │                     │                  │
│  │             │                   │  ⚠️ In-memory state  │                  │
│  │             │  POST /send_      │  ⚠️ Single user only │                  │
│  │             │ ────────────────► │  ⚠️ Lost on restart  │                  │
│  │             │  instruction      │                     │                  │
│  └─────────────┘                   └─────────────────────┘                  │
│                                                                             │
│  Problems:                                                                  │
│  - Multiple users overwrite each other's session state                     │
│  - Session state lost when Cloud Run instance restarts                     │
│  - No way for backend to proactively push instructions                     │
│  - High overhead from repeated POST requests                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              TARGET STATE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Frontend                          Backend (Cloud Run)                      │
│  ┌─────────────┐                   ┌─────────────────────┐                  │
│  │   Tutor     │  WebSocket        │  TeachingAssistant  │                  │
│  │   Service   │ ═══════════════►  │  (Stateless)        │                  │
│  │             │  /ws/feed         │                     │                  │
│  │             │  (audio/video/    │  ┌───────────────┐  │                  │
│  │             │   transcript)     │  │   MongoDB     │  │                  │
│  │             │                   │  │   sessions    │  │                  │
│  │             │ ◄═══════════════  │  │   collection  │  │                  │
│  │             │  SSE              │  └───────────────┘  │                  │
│  │             │  /sse/instructions│                     │                  │
│  │             │  (text prompts)   │  ✅ Per-user state   │                  │
│  └─────────────┘                   │  ✅ Survives restart │                  │
│                                    │  ✅ Multi-instance   │                  │
│                                    └─────────────────────┘                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Session State Management (MongoDB)

### 1.1 Problem Statement

Current session state is stored in-memory in a singleton:

```python
# Current: services/TeachingAssistant/teaching_assistant.py
class TeachingAssistant:
    def __init__(self):
        self.current_user_id = None      # ⚠️ Only ONE user
        self.session_active = False       # ⚠️ Only ONE session
        self.greeting_handler = GreetingHandler()  # ⚠️ In-memory
        self.inactivity_handler = InactivityHandler()  # ⚠️ In-memory
```

**Issues:**
- User A starts session → `current_user_id = "user_A"`
- User B starts session → `current_user_id = "user_B"` (overwrites A!)
- Cloud Run restarts → ALL session state lost

### 1.2 Solution: MongoDB `sessions` Collection

Create a new collection to store active session state:

```javascript
// MongoDB: sessions collection
{
  "_id": ObjectId("..."),
  "session_id": "sess_abc123def456",           // Unique session identifier
  "user_id": "user_85818357f902",              // Links to users collection

  // Session lifecycle
  "started_at": ISODate("2024-01-15T14:30:00Z"),
  "last_activity": ISODate("2024-01-15T14:35:22Z"),
  "ended_at": null,                            // Set when session ends
  "is_active": true,

  // Session metrics
  "questions_answered_this_session": 3,
  "questions_correct_this_session": 2,

  // For inactivity tracking
  "last_conversation_turn": ISODate("2024-01-15T14:35:22Z"),
  "last_question_submission": ISODate("2024-01-15T14:33:10Z"),

  // For SSE instruction delivery
  "pending_instructions": [
    {
      "instruction_id": "instr_001",
      "text": "Ask the student about fractions",
      "created_at": ISODate("2024-01-15T14:36:00Z"),
      "delivered": false
    }
  ],

  // Connection tracking
  "websocket_connected": true,
  "sse_connected": true,

  // TTL for automatic cleanup (24 hours after last activity)
  "expires_at": ISODate("2024-01-16T14:35:22Z")
}
```

### 1.3 Session Manager Implementation

**New File:** `services/TeachingAssistant/session_manager.py`

```python
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from bson import ObjectId
import uuid

class SessionManager:
    """
    Manages session state in MongoDB instead of in-memory.
    Enables multi-user support and survives Cloud Run restarts.
    """

    def __init__(self, mongo_client):
        self.db = mongo_client.db
        self.sessions = self.db.sessions
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create indexes for efficient queries"""
        self.sessions.create_index("user_id")
        self.sessions.create_index("session_id", unique=True)
        self.sessions.create_index([("is_active", 1), ("user_id", 1)])
        self.sessions.create_index("expires_at", expireAfterSeconds=0)  # TTL index

    def create_session(self, user_id: str) -> Dict[str, Any]:
        """Start a new session for a user"""
        # End any existing active session for this user
        self.end_active_sessions(user_id)

        now = datetime.utcnow()
        session = {
            "session_id": f"sess_{uuid.uuid4().hex[:16]}",
            "user_id": user_id,
            "started_at": now,
            "last_activity": now,
            "ended_at": None,
            "is_active": True,
            "questions_answered_this_session": 0,
            "questions_correct_this_session": 0,
            "last_conversation_turn": now,
            "last_question_submission": None,
            "pending_instructions": [],
            "websocket_connected": False,
            "sse_connected": False,
            "expires_at": now + timedelta(hours=24)
        }
        self.sessions.insert_one(session)
        return session

    def get_active_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the active session for a user"""
        return self.sessions.find_one({
            "user_id": user_id,
            "is_active": True
        })

    def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by its ID"""
        return self.sessions.find_one({"session_id": session_id})

    def update_activity(self, session_id: str) -> None:
        """Update last activity timestamp"""
        now = datetime.utcnow()
        self.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "last_activity": now,
                    "expires_at": now + timedelta(hours=24)
                }
            }
        )

    def record_conversation_turn(self, session_id: str) -> None:
        """Record a conversation turn for inactivity tracking"""
        now = datetime.utcnow()
        self.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "last_conversation_turn": now,
                    "last_activity": now,
                    "expires_at": now + timedelta(hours=24)
                }
            }
        )

    def record_question_answered(
        self,
        session_id: str,
        is_correct: bool
    ) -> None:
        """Record a question answer"""
        now = datetime.utcnow()
        update = {
            "$set": {
                "last_question_submission": now,
                "last_activity": now,
                "expires_at": now + timedelta(hours=24)
            },
            "$inc": {
                "questions_answered_this_session": 1
            }
        }
        if is_correct:
            update["$inc"]["questions_correct_this_session"] = 1

        self.sessions.update_one({"session_id": session_id}, update)

    def push_instruction(self, session_id: str, instruction_text: str) -> str:
        """Add an instruction to the pending queue"""
        instruction = {
            "instruction_id": f"instr_{uuid.uuid4().hex[:8]}",
            "text": instruction_text,
            "created_at": datetime.utcnow(),
            "delivered": False
        }
        self.sessions.update_one(
            {"session_id": session_id},
            {"$push": {"pending_instructions": instruction}}
        )
        return instruction["instruction_id"]

    def get_pending_instructions(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all undelivered instructions"""
        session = self.sessions.find_one(
            {"session_id": session_id},
            {"pending_instructions": 1}
        )
        if not session:
            return []
        return [
            inst for inst in session.get("pending_instructions", [])
            if not inst.get("delivered", False)
        ]

    def mark_instruction_delivered(
        self,
        session_id: str,
        instruction_id: str
    ) -> None:
        """Mark an instruction as delivered"""
        self.sessions.update_one(
            {
                "session_id": session_id,
                "pending_instructions.instruction_id": instruction_id
            },
            {"$set": {"pending_instructions.$.delivered": True}}
        )

    def set_connection_status(
        self,
        session_id: str,
        websocket: bool = None,
        sse: bool = None
    ) -> None:
        """Update connection status"""
        update = {}
        if websocket is not None:
            update["websocket_connected"] = websocket
        if sse is not None:
            update["sse_connected"] = sse
        if update:
            self.sessions.update_one(
                {"session_id": session_id},
                {"$set": update}
            )

    def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a session and return summary"""
        session = self.sessions.find_one({"session_id": session_id})
        if not session:
            return {}

        now = datetime.utcnow()
        duration_minutes = (now - session["started_at"]).total_seconds() / 60

        self.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "is_active": False,
                    "ended_at": now,
                    "websocket_connected": False,
                    "sse_connected": False
                }
            }
        )

        return {
            "session_id": session_id,
            "duration_minutes": round(duration_minutes, 2),
            "questions_answered": session["questions_answered_this_session"],
            "questions_correct": session["questions_correct_this_session"]
        }

    def end_active_sessions(self, user_id: str) -> int:
        """End all active sessions for a user (cleanup)"""
        result = self.sessions.update_many(
            {"user_id": user_id, "is_active": True},
            {
                "$set": {
                    "is_active": False,
                    "ended_at": datetime.utcnow(),
                    "websocket_connected": False,
                    "sse_connected": False
                }
            }
        )
        return result.modified_count

    def check_inactivity(self, session_id: str, threshold_seconds: int = 60) -> bool:
        """Check if session has been inactive beyond threshold"""
        session = self.sessions.find_one({"session_id": session_id})
        if not session or not session["is_active"]:
            return False

        now = datetime.utcnow()
        last_activity = max(
            session.get("last_conversation_turn") or session["started_at"],
            session.get("last_question_submission") or session["started_at"]
        )

        inactive_seconds = (now - last_activity).total_seconds()
        return inactive_seconds >= threshold_seconds

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get session info for API response"""
        session = self.sessions.find_one({"session_id": session_id})
        if not session:
            return {"session_active": False}

        now = datetime.utcnow()
        duration_minutes = (now - session["started_at"]).total_seconds() / 60

        return {
            "session_id": session["session_id"],
            "user_id": session["user_id"],
            "session_active": session["is_active"],
            "duration_minutes": round(duration_minutes, 2),
            "questions_answered": session["questions_answered_this_session"],
            "questions_correct": session["questions_correct_this_session"],
            "websocket_connected": session["websocket_connected"],
            "sse_connected": session["sse_connected"]
        }
```

### 1.4 Refactor TeachingAssistant Class

**File:** `services/TeachingAssistant/teaching_assistant.py`

Remove singleton state, use SessionManager:

```python
from .session_manager import SessionManager
from managers.mongodb_manager import MongoDBManager

class TeachingAssistant:
    """
    Refactored to be stateless - all state stored in MongoDB.
    Each method takes session_id or user_id as parameter.
    """

    def __init__(self):
        mongo = MongoDBManager()
        self.session_manager = SessionManager(mongo)
        self.greeting_handler = GreetingHandler()
        # Note: InactivityHandler refactored to use session_manager

    def start_session(self, user_id: str) -> dict:
        """Start a new session, returns greeting prompt"""
        session = self.session_manager.create_session(user_id)
        greeting = self.greeting_handler.get_greeting(user_id)
        return {
            "session_id": session["session_id"],
            "prompt": greeting,
            "session_info": self.session_manager.get_session_info(session["session_id"])
        }

    def end_session(self, session_id: str) -> dict:
        """End session, returns closing prompt with stats"""
        session_summary = self.session_manager.end_session(session_id)
        closing = self.greeting_handler.get_closing(
            duration_minutes=session_summary.get("duration_minutes", 0),
            questions_answered=session_summary.get("questions_answered", 0)
        )
        return {
            "prompt": closing,
            "session_info": session_summary
        }

    def record_question_answered(
        self,
        session_id: str,
        question_id: str,
        is_correct: bool
    ) -> None:
        """Record a question answer"""
        self.session_manager.record_question_answered(session_id, is_correct)

    def record_conversation_turn(self, session_id: str) -> None:
        """Record a conversation turn"""
        self.session_manager.record_conversation_turn(session_id)

    def check_inactivity(self, session_id: str) -> Optional[str]:
        """Check inactivity and return prompt if needed"""
        if self.session_manager.check_inactivity(session_id, threshold_seconds=60):
            prompt = "Check with the student if they're there..."
            self.session_manager.push_instruction(session_id, prompt)
            return prompt
        return None

    def get_session_info(self, session_id: str) -> dict:
        """Get current session info"""
        return self.session_manager.get_session_info(session_id)

    def get_active_session(self, user_id: str) -> Optional[dict]:
        """Get active session for user"""
        return self.session_manager.get_active_session(user_id)
```

### 1.5 Refactor GreetingHandler

**File:** `services/TeachingAssistant/greeting_handler.py`

Simplify to only generate prompts (no longer tracks session time - that's now in MongoDB):

```python
class GreetingHandler:
    """
    Simplified: Only generates greeting/closing prompts.
    Session timing is now handled by SessionManager in MongoDB.
    """
    SYSTEM_PROMPT_PREFIX = "[SYSTEM PROMPT FOR ADAM]"

    def get_greeting(self, user_id: str) -> str:
        """Generate greeting prompt for session start"""
        return f"""{self.SYSTEM_PROMPT_PREFIX}
You are starting a tutoring session.
Please greet the student warmly and ask how they're doing today.
Make them feel welcome and excited to learn."""

    def get_closing(self, duration_minutes: float, questions_answered: int) -> str:
        """Generate closing prompt with session stats (passed in from SessionManager)"""
        return f"""{self.SYSTEM_PROMPT_PREFIX}
The tutoring session is ending now.
Session stats: {duration_minutes:.1f} minutes, {questions_answered} questions attempted.
Please give the student a warm closing message, acknowledge their hard work,
and encourage them for next session."""
```

**What was removed:**
- `session_start_time` instance variable → Now in MongoDB session
- `questions_log` instance variable → Now in MongoDB session
- `start_session()` method → Replaced by `get_greeting()`
- `end_session()` method → Replaced by `get_closing()` (stats passed in)
- `record_question()` method → Now handled by SessionManager
- `get_session_stats()` method → Now handled by SessionManager

### 1.6 Refactor InactivityHandler

**File:** `services/TeachingAssistant/inactivity_handler.py`

The current InactivityHandler uses a background thread to monitor inactivity. With MongoDB-backed sessions, we have two options:

**Option A: Remove threading, use polling from SSE endpoint (Recommended)**

Since the SSE endpoint already polls every 5 seconds, inactivity checking can be done there:

```python
# In api.py SSE endpoint
async def event_generator():
    while True:
        # ... existing code ...

        # Check for inactivity (replaces background thread)
        if ta.session_manager.check_inactivity(session_id, threshold_seconds=60):
            prompt = "Check with the student if they're there..."
            ta.session_manager.push_instruction(session_id, prompt)

        await asyncio.sleep(5)
```

**Option B: Keep threading, but read/write from MongoDB**

If you prefer to keep the background thread pattern:

```python
class InactivityHandler:
    """
    Refactored to use SessionManager for state.
    Still uses background thread for monitoring.
    """
    SYSTEM_PROMPT_PREFIX = "[SYSTEM PROMPT FOR ADAM]"
    INACTIVITY_THRESHOLD_SECONDS = 60
    CHECK_INTERVAL_SECONDS = 5
    GRACE_PERIOD_SECONDS = 60

    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.monitoring_sessions: Dict[str, threading.Thread] = {}
        self.lock = threading.Lock()

    def start_monitoring(self, session_id: str):
        """Start monitoring a specific session"""
        with self.lock:
            if session_id in self.monitoring_sessions:
                return

            thread = threading.Thread(
                target=self._monitor_loop,
                args=(session_id,),
                daemon=True
            )
            self.monitoring_sessions[session_id] = thread
            thread.start()

    def stop_monitoring(self, session_id: str):
        """Stop monitoring a specific session"""
        with self.lock:
            if session_id in self.monitoring_sessions:
                del self.monitoring_sessions[session_id]

    def _monitor_loop(self, session_id: str):
        """Monitor a specific session for inactivity"""
        while session_id in self.monitoring_sessions:
            try:
                if self.session_manager.check_inactivity(
                    session_id,
                    self.INACTIVITY_THRESHOLD_SECONDS
                ):
                    prompt = f"""{self.SYSTEM_PROMPT_PREFIX}
Check with the student if they're there, and if they want to continue..."""
                    self.session_manager.push_instruction(session_id, prompt)

                time.sleep(self.CHECK_INTERVAL_SECONDS)
            except Exception as e:
                logger.error(f"Error in inactivity monitor for {session_id}: {e}")
                time.sleep(self.CHECK_INTERVAL_SECONDS)
```

**Recommendation:** Use Option A (SSE-based polling) because:
- Simpler architecture (no threads)
- State is already in MongoDB
- SSE endpoint already polls every 5 seconds
- Easier to debug and monitor

### 1.7 Update API Endpoints

**File:** `services/TeachingAssistant/api.py`

Update endpoints to use session_id:

```python
# Create TeachingAssistant (no longer singleton with state)
ta = TeachingAssistant()

@app.post("/session/start")
def start_session(request: Request):
    user_id = get_current_user(request)
    result = ta.start_session(user_id)
    return PromptResponse(
        prompt=result["prompt"],
        session_info=result["session_info"]
    )

@app.post("/session/end")
def end_session(request: Request, body: EndSessionRequest):
    user_id = get_current_user(request)
    session = ta.get_active_session(user_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session")

    result = ta.end_session(session["session_id"])
    return PromptResponse(
        prompt=result["prompt"],
        session_info=result["session_info"]
    )

@app.post("/question/answered")
def question_answered(request: Request, body: QuestionAnsweredRequest):
    user_id = get_current_user(request)
    session = ta.get_active_session(user_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session")

    ta.record_question_answered(
        session["session_id"],
        body.question_id,
        body.is_correct
    )
    return {"status": "recorded"}

@app.get("/session/info")
def get_session_info(request: Request):
    user_id = get_current_user(request)
    session = ta.get_active_session(user_id)
    if not session:
        return {"session_active": False}
    return ta.get_session_info(session["session_id"])
```

---

## Part 2: WebSocket (Frontend → Backend)

### 2.1 Backend WebSocket Endpoint

**File:** `services/TeachingAssistant/api.py`

```python
from fastapi import WebSocket, WebSocketDisconnect
from urllib.parse import parse_qs

@app.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket):
    # 1. Extract and validate JWT from query parameter
    query_params = parse_qs(websocket.scope["query_string"].decode())
    token = query_params.get("token", [None])[0]

    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    user_info = get_user_from_token(token)
    if not user_info:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = user_info["user_id"]

    # 2. Get or create session
    session = ta.get_active_session(user_id)
    if not session:
        await websocket.close(code=4002, reason="No active session")
        return

    session_id = session["session_id"]

    # 3. Accept connection and update status
    await websocket.accept()
    ta.session_manager.set_connection_status(session_id, websocket=True)

    try:
        # 4. Message handling loop
        while True:
            data = await websocket.receive_json()

            # Update activity timestamp
            ta.session_manager.update_activity(session_id)

            # Process message based on type
            msg_type = data.get("type")
            timestamp = data.get("timestamp")
            payload = data.get("data", {})

            if msg_type == "audio":
                await process_audio(session_id, payload.get("audio"), timestamp)
            elif msg_type == "media":
                await process_media(session_id, payload.get("media"), timestamp)
            elif msg_type == "transcript":
                await process_transcript(session_id, payload.get("transcript"), timestamp)
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        ta.session_manager.set_connection_status(session_id, websocket=False)
    except Exception as e:
        print(f"WebSocket error: {e}")
        ta.session_manager.set_connection_status(session_id, websocket=False)


async def process_audio(session_id: str, audio_base64: str, timestamp: str):
    """Process incoming audio data"""
    # TODO: Implement audio analysis
    print(f"[AUDIO] Session {session_id}: received audio at {timestamp}")


async def process_media(session_id: str, media_base64: str, timestamp: str):
    """Process incoming media (video frames)"""
    # TODO: Implement media analysis
    print(f"[MEDIA] Session {session_id}: received frame at {timestamp}")


async def process_transcript(session_id: str, transcript: str, timestamp: str):
    """Process incoming transcript"""
    # Record conversation turn
    ta.record_conversation_turn(session_id)

    # TODO: Analyze transcript for instruction generation
    print(f"[TRANSCRIPT] Session {session_id}: {transcript[:100]}...")
```

### 2.2 Frontend WebSocket Service

**New File:** `frontend/src/services/feed-websocket-service.ts`

```typescript
import { jwtUtils } from '../lib/jwt-utils';

const TEACHING_ASSISTANT_WS_URL =
  import.meta.env.VITE_TEACHING_ASSISTANT_WS_URL || 'ws://localhost:8002';

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';
type StatusCallback = (status: ConnectionStatus) => void;

class FeedWebSocketService {
  private socket: WebSocket | null = null;
  private audioBuffer: string[] = [];
  private batchInterval: number | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private statusCallbacks: Set<StatusCallback> = new Set();
  private _status: ConnectionStatus = 'disconnected';

  private set status(value: ConnectionStatus) {
    this._status = value;
    this.statusCallbacks.forEach(cb => cb(value));
  }

  get connectionStatus(): ConnectionStatus {
    return this._status;
  }

  onStatusChange(callback: StatusCallback): () => void {
    this.statusCallbacks.add(callback);
    return () => this.statusCallbacks.delete(callback);
  }

  async connect(): Promise<void> {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return;
    }

    this.status = 'connecting';
    const token = jwtUtils.getToken();

    if (!token) {
      this.status = 'error';
      throw new Error('No authentication token available');
    }

    return new Promise((resolve, reject) => {
      const url = `${TEACHING_ASSISTANT_WS_URL}/ws/feed?token=${encodeURIComponent(token)}`;
      this.socket = new WebSocket(url);

      this.socket.onopen = () => {
        console.log('[FeedWebSocket] Connected');
        this.status = 'connected';
        this.reconnectAttempts = 0;
        this.startAudioBatching();
        resolve();
      };

      this.socket.onclose = (event) => {
        console.log(`[FeedWebSocket] Closed: ${event.code} ${event.reason}`);
        this.status = 'disconnected';
        this.stopAudioBatching();
        this.attemptReconnect();
      };

      this.socket.onerror = (error) => {
        console.error('[FeedWebSocket] Error:', error);
        this.status = 'error';
        reject(error);
      };

      this.socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'pong') {
          // Keepalive response
        }
      };
    });
  }

  disconnect(): void {
    this.stopAudioBatching();
    if (this.socket) {
      this.socket.close(1000, 'Client disconnect');
      this.socket = null;
    }
    this.status = 'disconnected';
    this.reconnectAttempts = 0;
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[FeedWebSocket] Max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

    console.log(`[FeedWebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    setTimeout(() => this.connect().catch(console.error), delay);
  }

  private startAudioBatching(): void {
    if (this.batchInterval) return;

    this.batchInterval = window.setInterval(() => {
      this.flushAudioBuffer();
    }, 2000); // 2 second batching
  }

  private stopAudioBatching(): void {
    if (this.batchInterval) {
      clearInterval(this.batchInterval);
      this.batchInterval = null;
    }
    this.flushAudioBuffer(); // Send any remaining audio
  }

  private flushAudioBuffer(): void {
    if (this.audioBuffer.length === 0) return;
    if (this.socket?.readyState !== WebSocket.OPEN) return;

    const combinedAudio = this.audioBuffer.join('');
    this.audioBuffer = [];

    this.sendMessage({
      type: 'audio',
      timestamp: new Date().toISOString(),
      data: { audio: combinedAudio }
    });
  }

  private sendMessage(message: object): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    }
  }

  sendAudio(base64: string): void {
    this.audioBuffer.push(base64);
  }

  sendMedia(base64: string): void {
    this.sendMessage({
      type: 'media',
      timestamp: new Date().toISOString(),
      data: { media: base64 }
    });
  }

  sendTranscript(transcript: string): void {
    this.sendMessage({
      type: 'transcript',
      timestamp: new Date().toISOString(),
      data: { transcript }
    });
  }

  // Cleanup method
  cleanup(): void {
    this.disconnect();
    this.statusCallbacks.clear();
  }
}

export const feedWebSocketService = new FeedWebSocketService();
```

---

## Part 3: SSE (Backend → Frontend)

### 3.1 Backend SSE Endpoint

**File:** `services/TeachingAssistant/api.py`

```python
from sse_starlette.sse import EventSourceResponse
import asyncio

@app.get("/sse/instructions")
async def sse_instructions(request: Request, token: str = None):
    """SSE endpoint for pushing instructions to frontend"""

    # Validate token (passed as query param for SSE)
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    user_info = get_user_from_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = user_info["user_id"]

    # Get active session
    session = ta.get_active_session(user_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session")

    session_id = session["session_id"]
    ta.session_manager.set_connection_status(session_id, sse=True)

    async def event_generator():
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                # Check for pending instructions in MongoDB
                instructions = ta.session_manager.get_pending_instructions(session_id)

                for instruction in instructions:
                    yield {
                        "event": "instruction",
                        "id": instruction["instruction_id"],
                        "data": instruction["text"]
                    }
                    # Mark as delivered
                    ta.session_manager.mark_instruction_delivered(
                        session_id,
                        instruction["instruction_id"]
                    )

                # Check for inactivity and generate prompt if needed
                inactivity_prompt = ta.check_inactivity(session_id)
                # Note: check_inactivity already pushes to MongoDB if needed

                # Send keepalive every 30 seconds
                yield {"event": "keepalive", "data": ""}

                # Poll interval
                await asyncio.sleep(5)

        finally:
            ta.session_manager.set_connection_status(session_id, sse=False)

    return EventSourceResponse(event_generator())
```

### 3.2 Frontend SSE Service

**New File:** `frontend/src/services/instruction-sse-service.ts`

```typescript
import { jwtUtils } from '../lib/jwt-utils';

const TEACHING_ASSISTANT_API_URL =
  import.meta.env.VITE_TEACHING_ASSISTANT_API_URL || 'http://localhost:8002';

type InstructionCallback = (instruction: string) => void;
type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';
type StatusCallback = (status: ConnectionStatus) => void;

class InstructionSSEService {
  private eventSource: EventSource | null = null;
  private instructionCallbacks: Set<InstructionCallback> = new Set();
  private statusCallbacks: Set<StatusCallback> = new Set();
  private _status: ConnectionStatus = 'disconnected';
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  private set status(value: ConnectionStatus) {
    this._status = value;
    this.statusCallbacks.forEach(cb => cb(value));
  }

  get connectionStatus(): ConnectionStatus {
    return this._status;
  }

  onStatusChange(callback: StatusCallback): () => void {
    this.statusCallbacks.add(callback);
    return () => this.statusCallbacks.delete(callback);
  }

  connect(): void {
    if (this.eventSource) {
      return;
    }

    this.status = 'connecting';
    const token = jwtUtils.getToken();

    if (!token) {
      this.status = 'error';
      console.error('[InstructionSSE] No authentication token available');
      return;
    }

    const url = `${TEACHING_ASSISTANT_API_URL}/sse/instructions?token=${encodeURIComponent(token)}`;
    this.eventSource = new EventSource(url);

    this.eventSource.onopen = () => {
      console.log('[InstructionSSE] Connected');
      this.status = 'connected';
      this.reconnectAttempts = 0;
    };

    this.eventSource.onerror = (error) => {
      console.error('[InstructionSSE] Error:', error);
      this.status = 'error';
      this.eventSource?.close();
      this.eventSource = null;
      this.attemptReconnect();
    };

    // Listen for instruction events
    this.eventSource.addEventListener('instruction', (event: MessageEvent) => {
      const instruction = event.data;
      console.log('[InstructionSSE] Received instruction:', instruction);
      this.instructionCallbacks.forEach(cb => cb(instruction));
    });

    // Listen for keepalive (just to confirm connection is alive)
    this.eventSource.addEventListener('keepalive', () => {
      // Connection is alive
    });
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.status = 'disconnected';
    this.reconnectAttempts = 0;
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[InstructionSSE] Max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

    console.log(`[InstructionSSE] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    setTimeout(() => this.connect(), delay);
  }

  onInstruction(callback: InstructionCallback): () => void {
    this.instructionCallbacks.add(callback);
    return () => this.instructionCallbacks.delete(callback);
  }

  cleanup(): void {
    this.disconnect();
    this.instructionCallbacks.clear();
    this.statusCallbacks.clear();
  }
}

export const instructionSSEService = new InstructionSSEService();
```

---

## Part 4: Frontend Integration

### 4.1 Update Control Components

**Files to modify:**
- `frontend/src/components/control-tray/ControlTray.tsx`
- `frontend/src/components/floating-control-panel/FloatingControlPanel.tsx`

**Changes:**

```typescript
// Replace imports
// OLD:
import { feedWebhookService } from "../../services/feed-webhook-service";
// NEW:
import { feedWebSocketService } from "../../services/feed-websocket-service";
import { instructionSSEService } from "../../services/instruction-sse-service";

// In component initialization (useEffect on mount):
useEffect(() => {
  // Subscribe to instructions from TeachingAssistant
  const unsubscribe = instructionSSEService.onInstruction((instruction) => {
    if (client && client.status === "connected") {
      // Send instruction to Gemini tutor
      client.send({ text: instruction });
    }
  });

  return () => {
    unsubscribe();
  };
}, [client]);

// When session starts (connect handler):
const handleConnect = async () => {
  try {
    // Start session first (creates MongoDB session)
    const response = await apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/session/start`);
    const data = await response.json();

    // Connect WebSocket for feed
    await feedWebSocketService.connect();

    // Connect SSE for instructions
    instructionSSEService.connect();

    // Connect to Gemini
    await client.connect(config);

    // Send greeting if available
    if (data.prompt) {
      client.send({ text: data.prompt });
    }
  } catch (error) {
    console.error('Failed to start session:', error);
  }
};

// When session ends (disconnect handler):
const handleDisconnect = async () => {
  try {
    // Disconnect services
    feedWebSocketService.disconnect();
    instructionSSEService.disconnect();

    // End session
    await apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/session/end`);

    // Disconnect from Gemini
    client.disconnect();
  } catch (error) {
    console.error('Failed to end session:', error);
  }
};

// Replace feed webhook calls:
// OLD:
feedWebhookService.sendAudio(base64);
feedWebhookService.sendMedia(data);
feedWebhookService.sendTranscript(transcript);

// NEW:
feedWebSocketService.sendAudio(base64);
feedWebSocketService.sendMedia(data);
feedWebSocketService.sendTranscript(transcript);

// REMOVE these lines (no longer needed with SSE):
// const response = await apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/send_instruction_to_tutor`);
// if (response.ok) { ... }
```

### 4.2 Update MongoDBManager

**File:** `managers/mongodb_manager.py`

Add the `sessions` collection property:

```python
class MongoDBManager:
    # ... existing code ...

    @property
    def sessions(self):
        """Sessions collection for active session state"""
        return self.db.sessions
```

This allows the SessionManager to access the sessions collection via:
```python
mongo = MongoDBManager()
mongo.sessions.find_one({"user_id": user_id})
```

---

## Part 5: Files Summary

### New Files to Create

| File | Purpose |
|------|---------|
| `services/TeachingAssistant/session_manager.py` | MongoDB-backed session state management |
| `frontend/src/services/feed-websocket-service.ts` | WebSocket client for feed streaming |
| `frontend/src/services/instruction-sse-service.ts` | SSE client for receiving instructions |

### Files to Modify

| File | Changes |
|------|---------|
| `services/TeachingAssistant/api.py` | Add `/ws/feed`, `/sse/instructions`; update existing endpoints |
| `services/TeachingAssistant/teaching_assistant.py` | Refactor to use SessionManager |
| `services/TeachingAssistant/greeting_handler.py` | Simplify (no longer tracks session time) |
| `services/TeachingAssistant/inactivity_handler.py` | Refactor to use SessionManager |
| `managers/mongodb_manager.py` | Add `sessions` collection property |
| `frontend/src/components/control-tray/ControlTray.tsx` | Use new services |
| `frontend/src/components/floating-control-panel/FloatingControlPanel.tsx` | Use new services |

### Files to Delete (After Migration)

| File | Reason |
|------|--------|
| `frontend/src/services/feed-webhook-service.ts` | Replaced by WebSocket service |

### Legacy Endpoints to Remove

| Endpoint | Reason |
|----------|--------|
| `POST /webhook/feed` | Replaced by `WS /ws/feed` |
| `POST /send_instruction_to_tutor` | Replaced by `GET /sse/instructions` |

---

## Part 6: Dependencies

### Backend (Python)

Add to `services/TeachingAssistant/requirements.txt`:
```
sse-starlette>=1.6.0    # For SSE support
```

Note: `websockets` is included with FastAPI by default.

### Frontend (npm)

No new dependencies needed:
- `WebSocket`: Native browser API
- `EventSource` (SSE): Native browser API

---

## Part 7: Environment Variables

### Backend

Add to `.env` and Cloud Run deployment:
```
# No new variables needed - uses existing MONGODB_URI
```

### Frontend

Add to `frontend/.env`:
```
VITE_TEACHING_ASSISTANT_WS_URL=ws://localhost:8002
# For production: wss://teaching-assistant-xxxxx.run.app
```

---

## Part 8: Testing Plan

### Unit Tests

1. **SessionManager**
   - Create/end session
   - Update activity timestamps
   - Push/get/mark instructions
   - Inactivity detection
   - TTL expiration

2. **WebSocket endpoint**
   - Authentication validation
   - Message parsing
   - Connection status updates

3. **SSE endpoint**
   - Authentication validation
   - Instruction delivery
   - Keepalive messages

### Integration Tests

1. **Full session flow**
   - Start session → WebSocket connects → SSE connects
   - Send audio/video/transcript
   - Receive instruction via SSE
   - End session → connections close

2. **Multi-user isolation**
   - Two users with concurrent sessions
   - Verify no state leakage

3. **Reconnection**
   - WebSocket disconnect → auto-reconnect
   - SSE disconnect → auto-reconnect
   - Session persists across reconnects

### Manual Testing Checklist

- [ ] Start session → MongoDB session created
- [ ] WebSocket connects → `websocket_connected: true` in MongoDB
- [ ] SSE connects → `sse_connected: true` in MongoDB
- [ ] Send audio → backend logs receipt
- [ ] Send transcript → `last_conversation_turn` updated
- [ ] Wait 60s inactive → instruction pushed via SSE
- [ ] End session → session marked inactive
- [ ] Refresh page → can reconnect to existing session
- [ ] Kill Cloud Run instance → reconnect works, session intact

---

## Part 9: Rollout Strategy

### Phase 1: Backend Foundation (No breaking changes)
1. Add `sessions` collection and indexes to MongoDB
2. Deploy `SessionManager`
3. Add new endpoints (`/ws/feed`, `/sse/instructions`)
4. Keep legacy endpoints working

### Phase 2: Backend Migration
1. Update existing endpoints to use `SessionManager`
2. Verify existing functionality still works
3. Monitor for issues

### Phase 3: Frontend Migration
1. Deploy new WebSocket and SSE services
2. Update control components to use new services
3. Test thoroughly

### Phase 4: Cleanup
1. Remove legacy `feed-webhook-service.ts`
2. Remove legacy endpoints from backend
3. Update documentation

---

## Part 10: Monitoring & Observability

### Metrics to Track

1. **Session metrics**
   - Active sessions count
   - Session duration distribution
   - Questions per session

2. **Connection metrics**
   - WebSocket connection count
   - SSE connection count
   - Reconnection frequency

3. **Performance metrics**
   - WebSocket message latency
   - SSE delivery latency
   - MongoDB query times

### Logging

Add structured logging for:
- Session lifecycle events
- Connection state changes
- Instruction delivery
- Errors and reconnections

---

## Appendix: MongoDB Index Recommendations

```javascript
// Run in MongoDB shell or via migration script
db.sessions.createIndex({ "user_id": 1 });
db.sessions.createIndex({ "session_id": 1 }, { unique: true });
db.sessions.createIndex({ "is_active": 1, "user_id": 1 });
db.sessions.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 });
```

The TTL index on `expires_at` will automatically delete sessions 24 hours after their last activity, keeping the collection clean.
