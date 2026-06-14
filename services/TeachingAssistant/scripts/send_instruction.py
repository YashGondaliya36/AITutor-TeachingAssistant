#!/usr/bin/env python3
"""
Channel 2 Test Script - Send instruction to a user's active session via SSE

Usage:
    python send_instruction.py <user_id> "Your instruction text here"
    python send_instruction.py <user_id>  # Interactive mode

Examples:
    python send_instruction.py user_123 "Ask the student about quadratic equations"
    python send_instruction.py user_123  # Will prompt for instruction
"""

import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from managers.mongodb_manager import MongoDBManager


def get_active_session(user_id: str):
    """Get active session for a user"""
    mongo = MongoDBManager()
    session = mongo.sessions.find_one({
        "user_id": user_id,
        "is_active": True
    })
    return session


def list_active_sessions():
    """List all active sessions"""
    mongo = MongoDBManager()
    sessions = mongo.sessions.find({"is_active": True})
    return list(sessions)


def push_instruction(session_id: str, instruction: str):
    """Push an instruction to a session"""
    from services.TeachingAssistant.session_manager import SessionManager
    mongo = MongoDBManager()
    session_manager = SessionManager(mongo)
    instruction_id = session_manager.push_instruction(session_id, instruction)
    return instruction_id


def main():
    print("\n" + "="*60)
    print("  CHANNEL 2 TEST - Send Instruction via SSE")
    print("="*60 + "\n")

    # List active sessions first
    sessions = list_active_sessions()

    if not sessions:
        print("No active sessions found!")
        print("\nTo test this script:")
        print("1. Start a tutoring session from the frontend")
        print("2. Run this script again")
        sys.exit(1)

    print(f"Found {len(sessions)} active session(s):\n")
    for i, session in enumerate(sessions):
        print(f"  [{i+1}] User: {session['user_id']}")
        print(f"      Session ID: {session['session_id']}")
        print(f"      Started: {session['started_at']}")
        print(f"      Questions: {session.get('questions_answered_this_session', 0)}")
        print(f"      WebSocket: {'Connected' if session.get('websocket_connected') else 'Disconnected'}")
        print(f"      SSE: {'Connected' if session.get('sse_connected') else 'Disconnected'}")
        print()

    # Get user_id from args or prompt
    if len(sys.argv) >= 2:
        user_id = sys.argv[1]
    else:
        user_id = input("Enter user_id (or session number from above): ").strip()

        # Check if they entered a number
        if user_id.isdigit():
            idx = int(user_id) - 1
            if 0 <= idx < len(sessions):
                user_id = sessions[idx]['user_id']
            else:
                print(f"Invalid session number: {user_id}")
                sys.exit(1)

    # Find session for user
    session = get_active_session(user_id)
    if not session:
        print(f"\nNo active session for user: {user_id}")
        sys.exit(1)

    print(f"\nTarget session: {session['session_id']}")
    print(f"SSE Connected: {'Yes' if session.get('sse_connected') else 'No'}")

    if not session.get('sse_connected'):
        print("\nWARNING: SSE is not connected for this session.")
        print("The instruction will be queued but won't be delivered until SSE connects.\n")

    # Get instruction from args or prompt
    if len(sys.argv) >= 3:
        instruction = " ".join(sys.argv[2:])
    else:
        print("\n" + "-"*40)
        print("Enter your instruction (this will be sent to the Gemini tutor):")
        print("(Press Enter twice to send, or Ctrl+C to cancel)")
        print("-"*40 + "\n")

        lines = []
        try:
            while True:
                line = input()
                if line == "" and lines:
                    break
                lines.append(line)
        except KeyboardInterrupt:
            print("\nCancelled.")
            sys.exit(0)

        instruction = "\n".join(lines)

    if not instruction.strip():
        print("No instruction provided. Exiting.")
        sys.exit(1)

    # Add system prompt prefix
    SYSTEM_PROMPT_PREFIX = "[SYSTEM PROMPT FOR ADAM]"
    full_instruction = f"{SYSTEM_PROMPT_PREFIX}\n{instruction}"

    print("\n" + "="*40)
    print("Sending instruction:")
    print("="*40)
    print(full_instruction[:200] + ("..." if len(full_instruction) > 200 else ""))
    print("="*40 + "\n")

    # Push the instruction
    instruction_id = push_instruction(session['session_id'], full_instruction)

    print(f"SUCCESS! Instruction queued.")
    print(f"Instruction ID: {instruction_id}")
    print(f"\nThe instruction will be delivered via SSE within 5 seconds.")
    print("Check the frontend - the tutor should respond to this instruction.\n")


if __name__ == "__main__":
    main()
