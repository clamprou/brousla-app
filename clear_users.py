"""Script to clear all users from the database and delete all their associated workflows."""
import sqlite3
import os
import shutil
from pathlib import Path

# Get the script directory
SCRIPT_DIR = Path(__file__).parent

# Database paths
API_SERVER_DIR = SCRIPT_DIR / "api-server"
DB_FILE = API_SERVER_DIR / "users_db.sqlite"

# Workflow server paths
WORKFLOW_SERVER_DIR = SCRIPT_DIR / "workflow-server"
DATA_DIR = WORKFLOW_SERVER_DIR / "data"
STORED_WORKFLOWS_USERS_DIR = DATA_DIR / "stored_workflows" / "users"


def get_all_user_ids():
    """Get all user IDs from the database."""
    if not DB_FILE.exists():
        print("Database file not found. Nothing to clear.")
        return []
    
    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM users")
        user_ids = [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()
    
    return user_ids


def delete_user_workflows(user_id):
    """Delete all workflows associated with a user."""
    deleted_items = []
    
    # Delete stored workflow files directory
    user_workflows_dir = STORED_WORKFLOWS_USERS_DIR / user_id
    if user_workflows_dir.exists() and user_workflows_dir.is_dir():
        try:
            shutil.rmtree(user_workflows_dir)
            deleted_items.append(f"Stored workflows directory: {user_workflows_dir}")
        except Exception as e:
            print(f"  Warning: Failed to delete stored workflows directory: {e}")
    
    # Delete workflow state file
    workflow_state_file = DATA_DIR / f"workflow_state_{user_id}.json"
    if workflow_state_file.exists():
        try:
            os.remove(workflow_state_file)
            deleted_items.append(f"Workflow state file: {workflow_state_file}")
        except Exception as e:
            print(f"  Warning: Failed to delete workflow state file: {e}")
    
    return deleted_items


def clear_all_users():
    """Clear all users and their associated workflows."""
    print("=" * 60)
    print("Clearing all users and their workflows")
    print("=" * 60)
    
    # Check if database exists
    if not DB_FILE.exists():
        print("Database file not found. Nothing to clear.")
        return
    
    # Get all user IDs before deletion
    user_ids = get_all_user_ids()
    
    if not user_ids:
        print("No users found in database.")
        return
    
    print(f"\nFound {len(user_ids)} user(s) in database.")
    print("\nDeleting associated workflows...")
    
    # Delete workflows for each user
    total_deleted_items = 0
    for user_id in user_ids:
        print(f"\nProcessing user: {user_id}")
        deleted_items = delete_user_workflows(user_id)
        if deleted_items:
            for item in deleted_items:
                print(f"  ✓ Deleted: {item}")
                total_deleted_items += 1
        else:
            print(f"  No workflows found for this user")
    
    print(f"\nDeleted {total_deleted_items} workflow item(s) for {len(user_ids)} user(s).")
    
    # Now delete all users from database
    print("\nDeleting users from database...")
    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()
    
    try:
        # Get count before deletion
        cursor.execute("SELECT COUNT(*) FROM users")
        count_before = cursor.fetchone()[0]
        
        # Delete all users
        cursor.execute("DELETE FROM users")
        conn.commit()
        
        # Get count after deletion
        cursor.execute("SELECT COUNT(*) FROM users")
        count_after = cursor.fetchone()[0]
        
        print(f"✓ Deleted {count_before} user(s) from the database.")
        print(f"✓ Remaining users: {count_after}")
    finally:
        conn.close()
    
    print("\n" + "=" * 60)
    print("Cleanup complete!")
    print("=" * 60)
    print("\nNote: AI Workflows stored in browser localStorage are not deleted.")
    print("      Users will need to clear their browser data manually if needed.")


if __name__ == "__main__":
    try:
        clear_all_users()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()










