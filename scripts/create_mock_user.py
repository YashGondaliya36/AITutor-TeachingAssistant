"""
Create mock development user
This allows testing the app without Google OAuth setup
"""
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db
from managers.user_manager import UserManager, User
from datetime import datetime

def create_mock_user():
    """Create dev_user_123 for development testing"""
    
    user_manager = UserManager()
    user_id = "dev_user_123"
    
    # Check if user already exists
    existing_user = user_manager.load_user(user_id)
    if existing_user:
        print(f"✓ Mock user '{user_id}' already exists")
        return
    
    # Create user in MongoDB users collection
    user_doc = {
        "user_id": user_id,
        "google_id": "mock_google_id",
        "google_email": "dev@example.com",
        "google_name": "Dev User",
        "current_grade": 8,
        "age": 13,
        "picture": "",
        "subjects": ["math", "science"],
        "learning_goals": ["improve problem solving"],
        "interests": ["coding", "games"],
        "learning_style": "visual",
        "user_type": "student",
        "created_at": datetime.utcnow()
    }
    
    mongo_db.users.insert_one(user_doc)
    print(f"✓ Created MongoDB user document for '{user_id}'")
    
    # Create User object for user_manager
    user = User(
        user_id=user_id,
        age=13,
        current_grade=8
    )
    
    user_manager.save_user(user)
    print(f"✓ Created User object in user_manager for '{user_id}'")
    
    # Initialize skill states
    skill_state_doc = {
        "user_id": user_id,
        "skillData": {}
    }
    mongo_db.skill_states.update_one(
        {"user_id": user_id},
        {"$set": skill_state_doc},
        upsert=True
    )
    print(f"✓ Created skill_states document for '{user_id}'")
    
    print(f"\n✅ Mock user '{user_id}' created successfully!")
    print(f"   Email: dev@example.com")
    print(f"   Grade: 8")
    print(f"   Age: 13")


if __name__ == "__main__":
    create_mock_user()
