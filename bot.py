"""
Simple Confession Bot - V61 (Fixed Chat System + Media Comments + Comment Order Fix)
Requirements:
  pip install python-telegram-bot

V61 MAJOR UPDATES:
1. COMPLETELY FIXED Chat System - buttons now properly update to "Send Message" after acceptance
2. Added Media Support for Comments (text, photos, GIFs, documents)
3. Fixed comment display order and ensured ALL comments show
4. Fixed confession #40 comment display issue
5. Enhanced Dropbox backup to include all data
"""

import logging
import sqlite3
import time
import os
import json 
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import dropbox
import sqlite3
import dropbox
import os
from datetime import datetime
import threading
import time

DB_PATH = 'confession_bot.db'
DROPBOX_ACCESS_TOKEN = os.getenv('DROPBOX_ACCESS_TOKEN')
dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

def backup_database():
    """Backup database to Dropbox"""
    try:
        if not os.path.exists(DB_PATH):
            print("❌ No local database to backup")
            return
            
        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"confession_bot_backup_{timestamp}.db"
        
        # Upload to Dropbox
        with open(DB_PATH, 'rb') as f:
            dbx.files_upload(f.read(), f'/{backup_name}', mode=dropbox.files.WriteMode.overwrite)
        
        print(f"✅ Database backed up to Dropbox: {backup_name}")
        
        # Keep only last 5 backups
        clean_old_backups()
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")

def restore_database_from_dropbox():
    """Restore database from latest Dropbox backup"""
    try:
        print("🔄 Attempting to restore database from Dropbox...")
        
        # Get list of backup files
        result = dbx.files_list_folder('')
        backup_files = []
        
        for entry in result.entries:
            if 'confession_bot_backup' in entry.name:
                backup_files.append(entry.name)
        
        if not backup_files:
            print("❌ No backup files found in Dropbox")
            return False
            
        # Sort by name (which includes timestamp) and get latest
        backup_files.sort(reverse=True)
        latest_backup = backup_files[0]
        print(f"📦 Found backup: {latest_backup}")
        
        # Download the backup
        metadata, response = dbx.files_download(f'/{latest_backup}')
        
        # Save to local database file
        with open(DB_PATH, 'wb') as f:
            f.write(response.content)
            
        print(f"✅ Database restored from: {latest_backup}")
        print(f"📊 Restored database size: {os.path.getsize(DB_PATH)} bytes")
        return True
        
    except Exception as e:
        print(f"❌ Restoration failed: {e}")
        return False

def clean_old_backups():
    """Keep only the 5 most recent backups"""
    try:
        result = dbx.files_list_folder('')
        backup_files = []
        
        for entry in result.entries:
            if 'confession_bot_backup' in entry.name:
                backup_files.append(entry.name)
        
        # Sort by name (newest first)
        backup_files.sort(reverse=True)
        
        # Delete all but the 5 most recent
        for old_backup in backup_files[5:]:
            dbx.files_delete_v2(f'/{old_backup}')
            print(f"🗑️ Deleted old backup: {old_backup}")
            
    except Exception as e:
        print(f"Error cleaning backups: {e}")

def backup_on_startup():
    """Check and restore database on startup"""
    print("🚀 Starting database initialization...")
    print(f"📁 Current directory: {os.getcwd()}")
    print(f"🗃️ Database path: {DB_PATH}")
    
    # Check if database exists and has data
    needs_restore = False
    
    if not os.path.exists(DB_PATH):
        print("❌ Database file not found - needs restoration")
        needs_restore = True
    else:
        db_size = os.path.getsize(DB_PATH)
        print(f"📊 Existing database size: {db_size} bytes")
        
        if db_size == 0:
            print("❌ Database file is empty - needs restoration")
            needs_restore = True
        else:
            # Test if database is valid
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                conn.close()
                print(f"✅ Database valid. Tables found: {len(tables)}")
                if len(tables) == 0:
                    needs_restore = True
                    print("❌ No tables found - needs restoration")
            except Exception as e:
                print(f"❌ Database corrupted - needs restoration: {e}")
                needs_restore = True
    
    if needs_restore:
        print("🔄 Database needs restoration, attempting from Dropbox...")
        success = restore_database_from_dropbox()
        if success:
            print("✅ Database restoration completed!")
        else:
            print("❌ Database restoration failed!")
    else:
        print("✅ Local database is valid, no restoration needed")
    
    # Always create a fresh backup on startup
    print("🔄 Creating fresh backup...")
    backup_database()

def schedule_backups():
    """Schedule automatic backups every 6 hours"""
    def backup_loop():
        while True:
            time.sleep(6 * 60 * 60)  # 6 hours
            backup_database()
    
    backup_thread = threading.Thread(target=backup_loop, daemon=True)
    backup_thread.start()
    print("✅ Scheduled backups enabled (every 6 hours)")
# Use standard library html escape
from html import escape as html_escape 

# Import Telegram error for catching specific API exceptions
from telegram.error import BadRequest, TelegramError

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ===== ADD THESE 2 LINES =====
from keep_alive import keep_alive
import os

# ===== ADD THIS LINE =====
keep_alive()

# ------------------------------ CONFIG ------------------------------
BOT_TOKEN = os.environ.get('BOT_TOKEN')  # CHANGED THIS LINE
ADMIN_GROUP_ID = -1003131561656  # Admin group ID
CHANNEL_ID = -1003479727543     # Destination channel ID
BOT_USERNAME = "wru_confessions_bot"
ADMIN_USER_ID = 7300957726  # Admin ID for reports

DB_PATH = "confessions.db"
RATE_LIMIT_SECONDS = 120  
MAX_COMMENT_DEPTH = 5 
MAX_CATEGORIES = 3
COMMENTS_PER_PAGE = 10  # For pagination

# Categories List
CATEGORIES: List[str] = [
    "School", "Relationship", "Family", "Work", "Personal Life", 
    "Funny", "Random", "Gaming", "Study", "Tech", 
    "Health", "Social", "Other"
]

# Basic profanity list
BANNED_WORDS = {"badword1", "badword2", "idiot", "stupid"}

# Conversation states
WAITING_FOR_CONFESSION = 1
WAITING_FOR_COMMENT = 2
WAITING_FOR_REPLY = 3 
WAITING_FOR_CATEGORIES = 6 
WAITING_FOR_REVIEW = 7 
WAITING_FOR_BIO_EDIT = 9
WAITING_FOR_NICKNAME_EDIT = 10
WAITING_FOR_DEPARTMENT_EDIT = 11
WAITING_FOR_REPORT_REASON = 12
WAITING_FOR_CUSTOM_REPORT = 13
WAITING_FOR_CHAT_MESSAGE = 14
WAITING_FOR_ADMIN_MESSAGE = 15  # For admin messages

# Callback Data keys
CB_ACCEPT = "accept_terms"
CB_APPROVE_PATTERN = "approve:"
CB_REJECT_PATTERN = "reject:"
CB_CAT_PATTERN = "cat:"
CB_CAT_DONE = "cat_done" 
CB_START_COMMENT = "start_comment"
CB_MENU_MAIN = "menu_main"

# ------------------------------ LOGGING ------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s - Line %(lineno)d", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------------------ DATABASE HELPERS ------------------------------

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Confessions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS confessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, content TEXT, 
            file_id TEXT, file_type TEXT, created_at INTEGER, status TEXT, 
            admin_message_id INTEGER, channel_message_id INTEGER, 
            categories TEXT 
        )
    """)
    
    # Rate limit table
    cur.execute("CREATE TABLE IF NOT EXISTS rate_limit (user_id INTEGER PRIMARY KEY, last_ts INTEGER)")
    
    # Comments table - UPDATED: Added file_id and file_type for media comments
    cur.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, conf_id INTEGER, user_id INTEGER, 
            content TEXT, parent_comment_id INTEGER, created_at INTEGER,
            bot_message_id INTEGER, file_id TEXT, file_type TEXT
        )
    """)
    
    # Comment votes table - UPDATED for toggle functionality
    cur.execute("""
        CREATE TABLE IF NOT EXISTS comment_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, comment_id INTEGER, user_id INTEGER, 
            vote_type TEXT, UNIQUE(comment_id, user_id), 
            FOREIGN KEY(comment_id) REFERENCES comments(id)
        )
    """)
    
    # Follows table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS follows (
            follower_id INTEGER NOT NULL, following_id INTEGER NOT NULL, 
            created_at INTEGER, PRIMARY KEY (follower_id, following_id)
        )
    """)
    
    # User profiles table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY, aura_points INTEGER DEFAULT 0,
            bio TEXT, department TEXT, created_at INTEGER,
            nickname TEXT, terms_accepted BOOLEAN DEFAULT FALSE,
            start_used BOOLEAN DEFAULT FALSE  -- Track if user has used /start
        )
    """)
    
    # Chat requests table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id INTEGER NOT NULL,
            to_user_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending', -- pending, accepted, rejected
            created_at INTEGER,
            UNIQUE(from_user_id, to_user_id)
        )
    """)
    
    # Active chats table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS active_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            created_at INTEGER,
            UNIQUE(user1_id, user2_id)
        )
    """)
    
    # Chat messages table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            from_user_id INTEGER NOT NULL,
            to_user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at INTEGER,
            FOREIGN KEY(chat_id) REFERENCES active_chats(id)
        )
    """)
    
    # Blocked users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS blocked_users (
            blocker_id INTEGER NOT NULL,
            blocked_id INTEGER NOT NULL,
            created_at INTEGER,
            PRIMARY KEY (blocker_id, blocked_id)
        )
    """)
    
    # User reports table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER NOT NULL,
            reported_user_id INTEGER NOT NULL,
            reason TEXT,
            custom_reason TEXT,
            created_at INTEGER
        )
    """)
    
    # Admin messages table (NEW)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message_text TEXT NOT NULL,
            created_at INTEGER
        )
    """)
    
    # Check and add columns if they are missing
    try: cur.execute("SELECT bot_message_id FROM comments LIMIT 1")
    except sqlite3.OperationalError: cur.execute("ALTER TABLE comments ADD COLUMN bot_message_id INTEGER")
        
    try: cur.execute("SELECT channel_message_id FROM confessions LIMIT 1")
    except sqlite3.OperationalError: cur.execute("ALTER TABLE confessions ADD COLUMN channel_message_id INTEGER")
        
    try: cur.execute("SELECT categories FROM confessions LIMIT 1")
    except sqlite3.OperationalError: cur.execute("ALTER TABLE confessions ADD COLUMN categories TEXT")
    
    try: cur.execute("SELECT nickname FROM user_profiles LIMIT 1")
    except sqlite3.OperationalError: cur.execute("ALTER TABLE user_profiles ADD COLUMN nickname TEXT")
        
    try: cur.execute("SELECT terms_accepted FROM user_profiles LIMIT 1")
    except sqlite3.OperationalError: cur.execute("ALTER TABLE user_profiles ADD COLUMN terms_accepted BOOLEAN DEFAULT FALSE")
    
    try: cur.execute("SELECT start_used FROM user_profiles LIMIT 1")
    except sqlite3.OperationalError: cur.execute("ALTER TABLE user_profiles ADD COLUMN start_used BOOLEAN DEFAULT FALSE")

    # NEW: Check for comment media columns
    try: cur.execute("SELECT file_id FROM comments LIMIT 1")
    except sqlite3.OperationalError: 
        cur.execute("ALTER TABLE comments ADD COLUMN file_id TEXT")
        cur.execute("ALTER TABLE comments ADD COLUMN file_type TEXT")

    conn.commit()
    conn.close()

def save_confession(user_id: int, content: str, file_id: str, file_type: str) -> int:
    ts = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO confessions (user_id, content, file_id, file_type, created_at, status, categories) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, content, file_id, file_type, ts, "draft", None),
    )
    conf_id = cur.lastrowid
    conn.commit()
    conn.close()
    return conf_id

# UPDATED: Added file_id and file_type support for comments
def save_comment(conf_id: int, user_id: int, content: str, parent_comment_id: Optional[int] = None, file_id: str = None, file_type: str = None) -> int:
    ts = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO comments (conf_id, user_id, content, parent_comment_id, created_at, file_id, file_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (conf_id, user_id, content, parent_comment_id, ts, file_id, file_type),
    )
    comment_id = cur.lastrowid
    conn.commit()
    conn.close()
    return comment_id

def get_comment(comment_id: int) -> Optional[Dict[str, Any]]:
    """Get comment by ID"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, conf_id, user_id, content, parent_comment_id, created_at, bot_message_id, file_id, file_type FROM comments WHERE id = ?",
        (comment_id,)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'id': row[0], 'conf_id': row[1], 'user_id': row[2], 'content': row[3],
        'parent_comment_id': row[4], 'created_at': row[5], 'bot_message_id': row[6],
        'file_id': row[7], 'file_type': row[8]  # NEW: Added file info
    }

def update_comment_message_id(comment_id: int, bot_message_id: int):
    """Store the Telegram message ID for a comment"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE comments SET bot_message_id = ? WHERE id = ?", (bot_message_id, comment_id))
    conn.commit()
    conn.close()

def get_comment_message_id(comment_id: int) -> Optional[int]:
    """Retrieve the Telegram message ID for a comment"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT bot_message_id FROM comments WHERE id = ?", (comment_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def process_vote(comment_id: int, user_id: int, vote_type: str) -> Tuple[bool, str]:
    """Process vote and return (success, action) where action is 'added', 'removed', or 'changed'"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT vote_type FROM comment_votes WHERE comment_id = ? AND user_id = ?", (comment_id, user_id))
    existing_vote = cur.fetchone()
    
    action = "added"
    
    if existing_vote:
        if existing_vote[0] == vote_type:
            # Same vote - remove it (toggle off)
            cur.execute("DELETE FROM comment_votes WHERE comment_id = ? AND user_id = ?", (comment_id, user_id))
            action = "removed"
        else:
            # Different vote - change it
            cur.execute("UPDATE comment_votes SET vote_type = ? WHERE comment_id = ? AND user_id = ?", (vote_type, comment_id, user_id))
            action = "changed"
    else:
        # New vote
        cur.execute("INSERT INTO comment_votes (comment_id, user_id, vote_type) VALUES (?, ?, ?)", (comment_id, user_id, vote_type))
    
    conn.commit()
    conn.close()
    return True, action

def get_comment_vote_counts(comment_id: int) -> Dict[str, int]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT vote_type, COUNT(*) FROM comment_votes WHERE comment_id = ? GROUP BY vote_type", (comment_id,))
    rows = cur.fetchall()
    conn.close()
    counts = {row[0]: row[1] for row in rows}
    return {'likes': counts.get('like', 0), 'dislikes': counts.get('dislike', 0)}

def get_user_vote_on_comment(comment_id: int, user_id: int) -> Optional[str]:
    """Get how a user voted on a comment"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT vote_type FROM comment_votes WHERE comment_id = ? AND user_id = ?", (comment_id, user_id))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

# UPDATED: Fixed comment fetching to ensure ALL comments are retrieved in correct order
def get_comments_for_confession(conf_id: int, page: int = 1, limit: int = COMMENTS_PER_PAGE) -> Tuple[List[Dict[str, Any]], int]:
    """Get paginated root comments for confession and total count - FIXED to ensure all comments are retrieved"""
    offset = (page - 1) * limit
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Get total count of root comments
    cur.execute("SELECT COUNT(*) FROM comments WHERE conf_id = ? AND parent_comment_id IS NULL", (conf_id,))
    total_count = cur.fetchone()[0]
    
    # Get paginated root comments - FIXED: Proper ordering
    cur.execute(
        """
        SELECT id, user_id, content, created_at, parent_comment_id, bot_message_id, file_id, file_type
        FROM comments 
        WHERE conf_id = ? AND parent_comment_id IS NULL
        ORDER BY created_at ASC
        LIMIT ? OFFSET ?
        """, 
        (conf_id, limit, offset)
    )
    rows = cur.fetchall()
    conn.close()
    
    comments = []
    for r in rows:
        comments.append({
            'id': r[0], 'user_id': r[1], 'content': r[2], 'created_at': r[3],
            'parent_comment_id': r[4], 'bot_message_id': r[5], 'file_id': r[6], 'file_type': r[7]
        })
    return comments, total_count

def get_replies_for_comment(comment_id: int) -> List[Dict[str, Any]]:
    """Get all replies for a comment - FIXED: Added file info"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, user_id, content, created_at, parent_comment_id, bot_message_id, file_id, file_type
        FROM comments 
        WHERE parent_comment_id = ?
        ORDER BY created_at ASC
        """, 
        (comment_id,)
    )
    rows = cur.fetchall()
    conn.close()
    
    replies = []
    for r in rows:
        replies.append({
            'id': r[0], 'user_id': r[1], 'content': r[2], 'created_at': r[3],
            'parent_comment_id': r[4], 'bot_message_id': r[5], 'file_id': r[6], 'file_type': r[7]
        })
    return replies

def get_comment_author_id(comment_id: int) -> Optional[int]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM comments WHERE id = ?", (comment_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def toggle_follow(follower_id: int, following_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM follows WHERE follower_id = ? AND following_id = ?", (follower_id, following_id))
    exists = cur.fetchone()
    
    if exists:
        cur.execute("DELETE FROM follows WHERE follower_id = ? AND following_id = ?", (follower_id, following_id))
        conn.commit()
        conn.close()
        return False
    else:
        ts = int(time.time())
        cur.execute("INSERT INTO follows (follower_id, following_id, created_at) VALUES (?, ?, ?)", (follower_id, following_id, ts))
        conn.commit()
        conn.close()
        return True

def get_follow_counts(user_id: int) -> Dict[str, int]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM follows WHERE following_id = ?", (user_id,))
    followers = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM follows WHERE follower_id = ?", (user_id,))
    following = cur.fetchone()[0]
    conn.close()
    return {'followers': followers, 'following': following}

def is_following(follower_id: int, following_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM follows WHERE follower_id = ? AND following_id = ?", (follower_id, following_id))
    exists = cur.fetchone()
    conn.close()
    return bool(exists)

def get_user_profile(user_id: int) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, aura_points, bio, department, nickname, terms_accepted, start_used FROM user_profiles WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            'user_id': row[0], 'aura_points': row[1], 'bio': row[2], 'department': row[3],
            'nickname': row[4], 'terms_accepted': bool(row[5]), 'start_used': bool(row[6])
        }
    else:
        # Create default profile
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        ts = int(time.time())
        cur.execute("INSERT INTO user_profiles (user_id, aura_points, bio, department, created_at, nickname, terms_accepted, start_used) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (user_id, 0, "No bio set", "Not specified", ts, "Anonymous", False, False))
        conn.commit()
        conn.close()
        return {
            'user_id': user_id, 'aura_points': 0, 'bio': "No bio set", 'department': "Not specified",
            'nickname': "Anonymous", 'terms_accepted': False, 'start_used': False
        }

def update_user_profile(user_id: int, bio: str = None, department: str = None, nickname: str = None, terms_accepted: bool = None, start_used: bool = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Build update query dynamically based on provided fields
    updates = []
    params = []
    
    if bio is not None:
        updates.append("bio = ?")
        params.append(bio)
    if department is not None:
        updates.append("department = ?")
        params.append(department)
    if nickname is not None:
        updates.append("nickname = ?")
        params.append(nickname)
    if terms_accepted is not None:
        updates.append("terms_accepted = ?")
        params.append(terms_accepted)
    if start_used is not None:
        updates.append("start_used = ?")
        params.append(start_used)
        
    if updates:
        params.append(user_id)
        query = f"UPDATE user_profiles SET {', '.join(updates)} WHERE user_id = ?"
        cur.execute(query, params)
    
    conn.commit()
    conn.close()

def get_confession(conf_id: int) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user_id, content, file_id, file_type, created_at, status, admin_message_id, channel_message_id, categories "
        "FROM confessions WHERE id = ?", 
        (conf_id,)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return {}
    return {
        "id": row[0], "user_id": row[1], "content": row[2], "file_id": row[3], 
        "file_type": row[4], "created_at": row[5], "status": row[6], "admin_message_id": row[7],
        "channel_message_id": row[8], "categories": row[9] 
    }

def update_confession_content_and_media(conf_id: int, content: str, file_id: Optional[str], file_type: Optional[str]):
    """Update confession content, and optionally media, for the current draft."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE confessions SET content = ?, file_id = ?, file_type = ? WHERE id = ?", 
        (content, file_id, file_type, conf_id)
    )
    conn.commit()
    conn.close()
    
def update_confession_categories(conf_id: int, categories_list: List[str]):
    """Updates the categories for a confession draft."""
    categories_json = json.dumps(categories_list)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE confessions SET categories = ? WHERE id = ?", (categories_json, conf_id)) 
    conn.commit()
    conn.close()

def record_channel_message_id(conf_id: int, message_id: int):
    """Store the channel message ID for a confession."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE confessions SET channel_message_id = ? WHERE id = ?", (message_id, conf_id))
    conn.commit()
    conn.close()

def set_confession_status(conf_id: int, status: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE confessions SET status = ? WHERE id = ?", (status, conf_id))
    conn.commit()
    conn.close()

def record_admin_message_id(conf_id: int, message_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE confessions SET admin_message_id = ? WHERE id = ?", (message_id, conf_id))
    conn.commit()
    conn.close()

def get_last_submission_ts(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT last_ts FROM rate_limit WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0

def update_last_submission_ts(user_id: int):
    ts = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO rate_limit (user_id, last_ts) VALUES (?, ?)",
        (user_id, ts),
    )
    conn.commit()
    conn.close()

def get_user_draft_confession(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves the latest 'draft' confession for a user."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user_id, content, file_id, file_type, status, categories "
        "FROM confessions WHERE user_id = ? AND status = 'draft' ORDER BY created_at DESC LIMIT 1",
        (user_id,)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0], "user_id": row[1], "content": row[2], "file_id": row[3], 
        "file_type": row[4], "status": row[5], "categories": row[6]
    }

def get_comment_count_for_confession(conf_id: int) -> int:
    """Returns the total number of comments for a given confession."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM comments WHERE conf_id = ?", (conf_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count

def get_user_confessions_count(user_id: int) -> int:
    """Returns the number of confessions submitted by a user."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM confessions WHERE user_id = ?", (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count

def get_user_comments_count(user_id: int) -> int:
    """Returns the number of comments made by a user."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM comments WHERE user_id = ?", (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count

def get_user_confessions(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get user's confessions with pagination"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, content, status, created_at FROM confessions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    
    confessions = []
    for row in rows:
        confessions.append({
            'id': row[0], 'content': row[1], 'status': row[2], 'created_at': row[3]
        })
    return confessions

def get_user_comments(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get user's comments with pagination"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """SELECT c.id, c.content, c.created_at, conf.id as conf_id, conf.content as conf_content, c.file_id, c.file_type
        FROM comments c 
        JOIN confessions conf ON c.conf_id = conf.id 
        WHERE c.user_id = ? 
        ORDER BY c.created_at DESC LIMIT ?""",
        (user_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    
    comments = []
    for row in rows:
        comments.append({
            'id': row[0], 'content': row[1], 'created_at': row[2],
            'conf_id': row[3], 'conf_content': row[4], 'file_id': row[5], 'file_type': row[6]
        })
    return comments

def get_following_users(user_id: int) -> List[Dict[str, Any]]:
    """Get users that the current user is following"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """SELECT u.user_id, u.nickname 
        FROM user_profiles u 
        JOIN follows f ON u.user_id = f.following_id 
        WHERE f.follower_id = ?""",
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    
    users = []
    for row in rows:
        users.append({
            'user_id': row[0], 'nickname': row[1]
        })
    return users

def get_follower_users(user_id: int) -> List[Dict[str, Any]]:
    """Get users that are following the current user"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """SELECT u.user_id, u.nickname 
        FROM user_profiles u 
        JOIN follows f ON u.user_id = f.follower_id 
        WHERE f.following_id = ?""",
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    
    users = []
    for row in rows:
        users.append({
            'user_id': row[0], 'nickname': row[1]
        })
    return users

def create_chat_request(from_user_id: int, to_user_id: int) -> bool:
    """Create a chat request. Returns True if created, False if already exists."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if request already exists
    cur.execute("SELECT id FROM chat_requests WHERE from_user_id = ? AND to_user_id = ?", (from_user_id, to_user_id))
    if cur.fetchone():
        conn.close()
        return False
    
    ts = int(time.time())
    cur.execute(
        "INSERT INTO chat_requests (from_user_id, to_user_id, status, created_at) VALUES (?, ?, ?, ?)",
        (from_user_id, to_user_id, "pending", ts)
    )
    conn.commit()
    conn.close()
    return True

def get_chat_request(from_user_id: int, to_user_id: int) -> Optional[Dict[str, Any]]:
    """Get chat request between two users"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, from_user_id, to_user_id, status, created_at FROM chat_requests WHERE from_user_id = ? AND to_user_id = ?",
        (from_user_id, to_user_id)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'id': row[0], 'from_user_id': row[1], 'to_user_id': row[2], 'status': row[3], 'created_at': row[4]
    }

def update_chat_request_status(request_id: int, status: str):
    """Update chat request status"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE chat_requests SET status = ? WHERE id = ?", (status, request_id))
    conn.commit()
    conn.close()

def create_active_chat(user1_id: int, user2_id: int) -> int:
    """Create an active chat session and return chat ID"""
    ts = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Ensure consistent ordering of user IDs to avoid duplicates
    if user1_id > user2_id:
        user1_id, user2_id = user2_id, user1_id
    
    cur.execute(
        "INSERT OR REPLACE INTO active_chats (user1_id, user2_id, created_at) VALUES (?, ?, ?)",
        (user1_id, user2_id, ts)
    )
    chat_id = cur.lastrowid
    conn.commit()
    conn.close()
    return chat_id

def get_active_chat(user1_id: int, user2_id: int) -> Optional[Dict[str, Any]]:
    """Get active chat between two users"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Ensure consistent ordering
    if user1_id > user2_id:
        user1_id, user2_id = user2_id, user1_id
    
    cur.execute(
        "SELECT id, user1_id, user2_id, created_at FROM active_chats WHERE user1_id = ? AND user2_id = ?",
        (user1_id, user2_id)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'id': row[0], 'user1_id': row[1], 'user2_id': row[2], 'created_at': row[3]
    }

# NEW: Get active chats for a user
def get_active_chats_for_user(user_id: int) -> List[Dict[str, Any]]:
    """Get all active chats for a user"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Get chats where user is either user1 or user2
    cur.execute(
        """SELECT id, user1_id, user2_id, created_at 
        FROM active_chats 
        WHERE user1_id = ? OR user2_id = ?""",
        (user_id, user_id)
    )
    rows = cur.fetchall()
    conn.close()
    
    chats = []
    for row in rows:
        chat_id, user1_id, user2_id, created_at = row
        # Determine the other user in the chat
        other_user_id = user2_id if user1_id == user_id else user1_id
        other_user_profile = get_user_profile(other_user_id)
        
        chats.append({
            'chat_id': chat_id,
            'other_user_id': other_user_id,
            'other_user_nickname': other_user_profile['nickname'] or 'Anonymous',
            'created_at': created_at
        })
    
    return chats

def save_chat_message(chat_id: int, from_user_id: int, to_user_id: int, content: str) -> int:
    """Save a chat message and return message ID"""
    ts = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO chat_messages (chat_id, from_user_id, to_user_id, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (chat_id, from_user_id, to_user_id, content, ts)
    )
    message_id = cur.lastrowid
    conn.commit()
    conn.close()
    return message_id

def get_chat_messages(chat_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Get chat messages for a chat session"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, from_user_id, to_user_id, content, created_at FROM chat_messages WHERE chat_id = ? ORDER BY created_at ASC LIMIT ?",
        (chat_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    
    messages = []
    for row in rows:
        messages.append({
            'id': row[0], 'from_user_id': row[1], 'to_user_id': row[2], 'content': row[3], 'created_at': row[4]
        })
    return messages

def end_chat(chat_id: int):
    """End a chat session"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM active_chats WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()

def block_user(blocker_id: int, blocked_id: int):
    """Block a user"""
    ts = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO blocked_users (blocker_id, blocked_id, created_at) VALUES (?, ?, ?)",
        (blocker_id, blocked_id, ts)
    )
    conn.commit()
    conn.close()

def unblock_user(blocker_id: int, blocked_id: int):
    """Unblock a user"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM blocked_users WHERE blocker_id = ? AND blocked_id = ?", (blocker_id, blocked_id))
    conn.commit()
    conn.close()

def is_blocked(blocker_id: int, blocked_id: int) -> bool:
    """Check if a user is blocked by another"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM blocked_users WHERE blocker_id = ? AND blocked_id = ?", (blocker_id, blocked_id))
    result = cur.fetchone()
    conn.close()
    return bool(result)

def create_user_report(reporter_id: int, reported_user_id: int, reason: str = None, custom_reason: str = None):
    """Create a user report"""
    ts = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO user_reports (reporter_id, reported_user_id, reason, custom_reason, created_at) VALUES (?, ?, ?, ?, ?)",
        (reporter_id, reported_user_id, reason, custom_reason, ts)
    )
    report_id = cur.lastrowid
    conn.commit()
    conn.close()
    return report_id

# NEW: Save admin message
def save_admin_message(user_id: int, message_text: str) -> int:
    """Save a message to admin and return message ID"""
    ts = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO admin_messages (user_id, message_text, created_at) VALUES (?, ?, ?)",
        (user_id, message_text, ts)
    )
    message_id = cur.lastrowid
    conn.commit()
    conn.close()
    return message_id

# ------------------------------ UTILS ------------------------------

def escape_html(text: str) -> str:
    """Escapes HTML special characters in the text."""
    if text is None:
        return ""
    return html_escape(text)

def contains_profanity(text: str) -> bool:
    if not text: return False
    tx = text.lower()
    for bad in BANNED_WORDS:
        if bad in tx: return True
    return False

def format_categories_for_display(categories_json: Optional[str]) -> str:
    """Converts the JSON list of categories into a string of #hashtags."""
    if not categories_json:
        return ""
    try:
        categories: List[str] = json.loads(categories_json)
        return "\n" + " ".join([f"#{c.replace(' ', '_').capitalize()}" for c in categories])
    except:
        return ""

def format_confession_for_admin(conf: Dict[str, Any]) -> str:
    created = datetime.utcfromtimestamp(conf["created_at"]).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    categories_hashtags = format_categories_for_display(conf.get("categories"))
    
    text = f"📩 <b>Confession ID:</b> <code>{conf['id']}</code>\n\n" 
    if conf["content"]: 
        text += f"{escape_html(conf['content'])}\n"
    
    text += f"{categories_hashtags}\n\n"
    text += f"<i>Submitted:</i> {created}\n\n"
    text += "Use the buttons below to <b>Approve</b> or <b>Reject</b>."
    return text

def format_confession_for_channel(conf: Dict[str, Any]) -> str:
    categories_hashtags = format_categories_for_display(conf.get("categories"))
    
    text = f"💬 <b>Confession #{conf['id']}</b>\n\n"
    if conf["content"]: 
        text += f"{escape_html(conf['content'])}\n\n"
        
    text += categories_hashtags
    
    return text.strip()

# UPDATED: Improved comment display with media support
async def format_comment_display(comment: Dict[str, Any], conf_id: int, depth: int, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Formats an individual comment for display with media support."""
    
    current_user_id = context.user_data.get('current_user_id', context._user_id)
    target_user_id = comment['user_id']
    conf = get_confession(conf_id)
    
    # Determine display name with PROFILE LINKS
    if target_user_id == current_user_id:
        display_name = "You"
    elif target_user_id == conf['user_id']:
        # Confession Author with profile link
        bot_username = (await context.application.bot.get_me()).username
        profile_deep_link = f"t.me/{bot_username}?start=profile_{target_user_id}"
        display_name = f"[Confession Author]({profile_deep_link})"
    else:
        profile = get_user_profile(target_user_id)
        display_name = profile['nickname'] or 'Anonymous'
        
        # Create profile link for others
        bot_username = (await context.application.bot.get_me()).username
        profile_deep_link = f"t.me/{bot_username}?start=profile_{target_user_id}"
        display_name = f"[{display_name}]({profile_deep_link})"
    
    profile = get_user_profile(target_user_id)
    aura_points = profile.get('aura_points', 0)
    
    indent = " " * (depth * 4)
    if depth > 0:
        indent = " " * ((depth - 1) * 4) + "↳ " 
    
    # Handle media comments
    if comment.get('file_id'):
        file_type = comment.get('file_type', '')
        if file_type == 'photo':
            media_indicator = "🖼️ "
        elif file_type == 'document':
            media_indicator = "📎 "
        else:
            media_indicator = "📁 "
    else:
        media_indicator = ""
    
    text = f"{indent}{media_indicator}💬 {comment['content']}\n\n"
    text += f"{indent}👤 {display_name} ⚡︎{aura_points} Aura\n"
    
    return text

def build_comment_thread(flat_comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Transforms a flat list of comments into a nested tree structure."""
    
    comment_map = {c['id']: {**c, 'replies': []} for c in flat_comments}
    thread_roots = []
    for comment in comment_map.values():
        parent_id = comment.get('parent_comment_id')
        if parent_id in comment_map:
            comment_map[parent_id]['replies'].append(comment)
        else:
            thread_roots.append(comment)
            
    for comment in comment_map.values():
        comment['replies'].sort(key=lambda x: x['created_at'])
            
    return thread_roots

# UPDATED: Send comments with media support
async def send_comment_and_replies(
    chat_id: int, 
    context: ContextTypes.DEFAULT_TYPE, 
    comment: Dict[str, Any], 
    conf_id: int,
    depth: int = 0
):
    current_user_id = context.user_data.get('current_user_id', chat_id)
    
    counts = get_comment_vote_counts(comment['id'])
    user_vote = get_user_vote_on_comment(comment['id'], current_user_id)
    comment_text = await format_comment_display(comment, conf_id, depth, context) 

    parent_message_id = None
    if comment.get('parent_comment_id'):
        parent_message_id = get_comment_message_id(comment['parent_comment_id'])
    
    # Handle media comments
    if comment.get('file_id'):
        file_id = comment['file_id']
        file_type = comment.get('file_type', '')
        
        if file_type == 'photo':
            sent_message = await context.bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                caption=comment_text,
                reply_markup=get_comment_interaction_keyboard(comment, current_user_id, counts, user_vote), 
                parse_mode="Markdown",
                reply_to_message_id=parent_message_id
            )
        elif file_type == 'document':
            sent_message = await context.bot.send_document(
                chat_id=chat_id,
                document=file_id,
                caption=comment_text,
                reply_markup=get_comment_interaction_keyboard(comment, current_user_id, counts, user_vote), 
                parse_mode="Markdown",
                reply_to_message_id=parent_message_id
            )
        else:
            # Fallback to text for unknown file types
            sent_message = await context.bot.send_message(
                chat_id=chat_id,
                text=comment_text,
                reply_markup=get_comment_interaction_keyboard(comment, current_user_id, counts, user_vote), 
                parse_mode="Markdown",
                reply_to_message_id=parent_message_id
            )
    else:
        # Text-only comment
        sent_message = await context.bot.send_message(
            chat_id=chat_id,
            text=comment_text,
            reply_markup=get_comment_interaction_keyboard(comment, current_user_id, counts, user_vote), 
            parse_mode="Markdown",
            reply_to_message_id=parent_message_id
        )
    
    update_comment_message_id(comment['id'], sent_message.message_id)
    
    if depth < MAX_COMMENT_DEPTH and comment.get('replies'):
        for reply in comment['replies']:
            await send_comment_and_replies(chat_id, context, reply, conf_id, depth + 1)

# UPDATED: Show comments with improved pagination and FIXED comment retrieval
async def show_comments(update: Update, context: ContextTypes.DEFAULT_TYPE, conf_id: int, page: int = 1):
    # FIXED: Check if confession exists and is approved
    conf = get_confession(conf_id)
    if not conf:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ Confession #{conf_id} not found."
        )
        return
        
    if conf['status'] != 'approved':
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ Confession #{conf_id} is not approved yet or has been removed."
        )
        return
    
    flat_comments, total_count = get_comments_for_confession(conf_id, page)
    
    # Build full thread structure for the current page
    all_comments_for_page = []
    for comment in flat_comments:
        all_comments_for_page.append(comment)
        # Get replies for this comment
        replies = get_replies_for_comment(comment['id'])
        all_comments_for_page.extend(replies)
    
    thread_roots = build_comment_thread(all_comments_for_page)
    
    chat_id = update.effective_chat.id
    
    context.user_data['current_user_id'] = update.effective_user.id
    context.user_data['last_viewed_conf_id'] = conf_id
    context.user_data['comment_page'] = page
    
    total_pages = (total_count + COMMENTS_PER_PAGE - 1) // COMMENTS_PER_PAGE
    
    if not flat_comments: 
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"No comments found for Confession #{conf_id}. Be the first to add one!",
            reply_markup=get_deep_link_keyboard(conf_id, 0),
        )
        return

    # Send comments first
    for root_comment in thread_roots:
        await send_comment_and_replies(chat_id, context, root_comment, conf_id, depth=0)
    
    # Send pagination footer at the bottom (UPDATED)
    pagination_text = f"**Displaying page {page}/{total_pages}. Total {total_count} Comments**"
    await context.bot.send_message(
        chat_id=chat_id,
        text=pagination_text,
        parse_mode="Markdown",
        reply_markup=get_comment_pagination_keyboard(conf_id, page, total_pages, total_count)
    )

# ------------------------------ KEYBOARDS ------------------------------

MAIN_REPLY_KEYBOARD = ReplyKeyboardMarkup(
    [['📝 Confess'], ['📊 Profile', '❓ Help']], 
    resize_keyboard=True, one_time_keyboard=False
)

CONFESSION_CANCEL_KEYBOARD = ReplyKeyboardMarkup(
    [['❌ Cancel', '🏠 Main Menu']], resize_keyboard=True, one_time_keyboard=False
)

# Chat keyboard
CHAT_KEYBOARD = ReplyKeyboardMarkup(
    [['/leavechat'], ['Block', 'Report']],
    resize_keyboard=True, one_time_keyboard=False
)

# Admin message keyboard (NEW)
ADMIN_MESSAGE_KEYBOARD = ReplyKeyboardMarkup(
    [['❌ Cancel', '🏠 Main Menu']], resize_keyboard=True, one_time_keyboard=False
)

# Profile keyboard
PROFILE_MAIN_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("Edit Profile", callback_data="profile_edit")],
    [
        InlineKeyboardButton("My Confessions", callback_data="profile_my_confessions"),
        InlineKeyboardButton("My Comments", callback_data="profile_my_comments"),
    ],
    [
        InlineKeyboardButton("Following", callback_data="profile_following"),
        InlineKeyboardButton("Followers", callback_data="profile_followers"), 
    ],
    [
        InlineKeyboardButton("Settings", callback_data="profile_settings"),
        InlineKeyboardButton("My Chats", callback_data="profile_my_chats"),
    ],
])

# Edit profile keyboard
PROFILE_EDIT_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("Change Nickname", callback_data="profile_change_nickname")],
    [InlineKeyboardButton("Set/Update Bio", callback_data="profile_set_bio")],
    [InlineKeyboardButton("Edit Department", callback_data="profile_edit_department")],
    [InlineKeyboardButton("Back to Profile", callback_data="profile_main")]
])

HELP_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("📜 Rules & Regulations", callback_data="help_rules")],
    [InlineKeyboardButton("🔒 Privacy Information", callback_data="help_privacy")],
    [InlineKeyboardButton("✉️ Contact Admin", callback_data="help_contact_admin")],
    [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")]
])

def get_review_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Submit", callback_data="confess_action:submit")],
        [InlineKeyboardButton("✍️ Edit", callback_data="confess_action:edit")],
        [InlineKeyboardButton("❌ Cancel", callback_data="confess_action:cancel")],
    ])

# UPDATED: New deep link keyboard with View Comments, Add Comment, Main Menu
def get_deep_link_keyboard(conf_id: int, comment_count: int):
    """Generate keyboard for deep link with View Comments, Add Comment, Main Menu"""
    keyboard = [
        [InlineKeyboardButton(f"💬 View Comments ({comment_count})", callback_data=f"comment_view:{conf_id}")],
        [InlineKeyboardButton("✍️ Add Comment", callback_data=f"comment_add:{conf_id}")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data=CB_MENU_MAIN)]
    ]
    return InlineKeyboardMarkup(keyboard)

# UPDATED: Channel post button with LIVE comment count
def get_channel_post_keyboard(conf_id: int) -> InlineKeyboardMarkup:
    comment_count = get_comment_count_for_confession(conf_id)
    deep_link_url = f"https://t.me/{BOT_USERNAME}?start=comment_{conf_id}"
    button_text = f"💬 Add/View Comments ({comment_count})"  # UPDATED: Shows LIVE count
    keyboard = [[InlineKeyboardButton(button_text, url=deep_link_url)]]
    return InlineKeyboardMarkup(keyboard)

# UPDATED: Comment pagination with Load More button
def get_comment_pagination_keyboard(conf_id: int, current_page: int, total_pages: int, total_count: int):
    """Generate pagination keyboard for comments with Load More"""
    keyboard = []
    
    # Page navigation with Load More
    nav_buttons = []
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton("📥 Load More", callback_data=f"comment_page:{conf_id}:{current_page+1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"Page {current_page}/{total_pages}", callback_data=f"comment_page_info:{conf_id}:{current_page}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Add comment button
    keyboard.append([InlineKeyboardButton("💬 Add Comment", callback_data=f"comment_add:{conf_id}")])
    
    return InlineKeyboardMarkup(keyboard)

def get_comment_interaction_keyboard(comment: Dict[str, Any], current_user_id: int, counts: Dict[str, int], user_vote: Optional[str] = None):
    comment_id = comment['id']
    
    # Determine button texts based on user's current vote
    like_text = f"👍 {counts['likes']}"
    dislike_text = f"👎 {counts['dislikes']}"
    
    if user_vote == 'like':
        like_text = f"✅ {counts['likes']}"
    elif user_vote == 'dislike':
        dislike_text = f"✅ {counts['dislikes']}"
    
    buttons = [
        InlineKeyboardButton(like_text, callback_data=f"vote:like:{comment_id}"),
        InlineKeyboardButton(dislike_text, callback_data=f"vote:dislike:{comment_id}"),
        InlineKeyboardButton("↩️ Reply", callback_data=f"reply:{comment_id}")
    ]
    
    return InlineKeyboardMarkup([buttons])

# COMPLETELY FIXED: Profile keyboard with proper chat button states
def get_user_profile_keyboard(target_user_id: int, current_user_id: int) -> InlineKeyboardMarkup:
    if current_user_id == target_user_id:
        # No buttons for own profile
        return InlineKeyboardMarkup([])
    
    # Follow status
    follow_status_text = "➕ Follow User"
    if is_following(current_user_id, target_user_id):
        follow_status_text = "✔️ Following"
    
    # FIXED: Chat button logic - ALWAYS show "Send Message" if active chat exists
    active_chat = get_active_chat(current_user_id, target_user_id)
    chat_request = get_chat_request(current_user_id, target_user_id)
    
    # FIXED: This is the critical fix - always prioritize active chat
    if active_chat:
        chat_button_text = "💬 Send Message"
        chat_callback_data = f"start_chat:{target_user_id}"
    elif chat_request and chat_request['status'] == 'pending':
        if chat_request['from_user_id'] == current_user_id:
            chat_button_text = "✅ Chat Request Sent"
            chat_callback_data = f"request_chat:{target_user_id}"  # Keep same callback to show status
        else:
            # This user received a request from the target user
            chat_button_text = "💬 Request to Chat"  # They can still send a request
            chat_callback_data = f"request_chat:{target_user_id}"
    else:
        chat_button_text = "💬 Request to Chat"
        chat_callback_data = f"request_chat:{target_user_id}"
    
    profile_buttons = []
    profile_buttons.append(
        InlineKeyboardButton(follow_status_text, callback_data=f"follow_user:{target_user_id}")
    )
    profile_buttons.append(
        InlineKeyboardButton("⚠️ Report User", callback_data=f"report_user:{target_user_id}")
    )
    profile_buttons.append(
        InlineKeyboardButton(chat_button_text, callback_data=chat_callback_data)
    )
        
    return InlineKeyboardMarkup([profile_buttons])

def get_report_reason_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Spam", callback_data="report_reason:spam")],
        [InlineKeyboardButton("Harassment", callback_data="report_reason:harassment")],
        [InlineKeyboardButton("Inappropriate Profile", callback_data="report_reason:inappropriate")],
        [InlineKeyboardButton("Other (Custom Reason)", callback_data="report_reason:other")],
        [InlineKeyboardButton("Skip Reason", callback_data="report_reason:skip")],
        [InlineKeyboardButton("Cancel", callback_data="report_reason:cancel")]
    ])

def get_chat_request_keyboard(from_user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Accept", callback_data=f"chat_accept:{from_user_id}"),
            InlineKeyboardButton("Decline", callback_data=f"chat_decline:{from_user_id}")
        ]
    ])

def get_categories_keyboard(selected_categories: List[str]):
    keyboard = []
    keyboard.append([InlineKeyboardButton("🤖 Auto-select Categories", callback_data=f"{CB_CAT_PATTERN}auto")])
    
    row = []
    for category in CATEGORIES:
        text = f"✅ {category}" if category in selected_categories else category
        row.append(InlineKeyboardButton(text, callback_data=f"{CB_CAT_PATTERN}{category}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    current_count = len(selected_categories)
    done_text = f"➡️ Done Selecting ({current_count}/{MAX_CATEGORIES})"
    
    if current_count >= 1:
        done_callback_data = CB_CAT_DONE
    else:
        done_callback_data = f"{CB_CAT_PATTERN}disabled_done" 
        
    keyboard.append([InlineKeyboardButton(done_text, callback_data=done_callback_data)])
    keyboard.append([InlineKeyboardButton("❌ Cancel Confession", callback_data="confess_action:cancel")])
    
    return InlineKeyboardMarkup(keyboard)

# ------------------------------ DROPBOX BACKUP ------------------------------

def get_dropbox_client():
    """Get Dropbox client with access token"""
    access_token = os.environ.get('DROPBOX_ACCESS_TOKEN')
    if not access_token:
        logger.warning("Dropbox access token not found in environment variables")
        return None
    return dropbox.Dropbox(access_token)

def backup_database_to_dropbox():
    """Backup SQLite database to Dropbox - ENHANCED for data preservation"""
    try:
        dbx = get_dropbox_client()
        if not dbx:
            return False
            
        # Read database file
        with open(DB_PATH, 'rb') as db_file:
            db_content = db_file.read()
        
        # Upload to Dropbox with timestamp for multiple backups
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"/confessions_backup_{timestamp}.db"
        
        dbx.files_upload(
            db_content, 
            backup_path,
            mode=dropbox.files.WriteMode.overwrite
        )
        
        logger.info(f"Database backed up successfully to Dropbox: {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to backup database to Dropbox: {e}")
        return False

def restore_database_from_dropbox():
    """Restore SQLite database from Dropbox backup - ENHANCED for data preservation"""
    try:
        dbx = get_dropbox_client()
        if not dbx:
            return False
            
        # List all backup files and get the latest one
        result = dbx.files_list_folder("")
        backup_files = [entry for entry in result.entries if entry.name.startswith("confessions_backup_")]
        
        if not backup_files:
            logger.info("No backup files found in Dropbox")
            return False
            
        # Sort by name (which includes timestamp) to get the latest
        backup_files.sort(key=lambda x: x.name, reverse=True)
        latest_backup = backup_files[0].name
        
        # Download the latest backup file
        metadata, response = dbx.files_download(f"/{latest_backup}")
        
        # Write to database file
        with open(DB_PATH, 'wb') as db_file:
            db_file.write(response.content)
        
        logger.info(f"Successfully restored database from Dropbox backup: {latest_backup}")
        return True
        
    except dropbox.exceptions.ApiError as e:
        if e.error.is_path() and e.error.get_path().is_not_found():
            logger.info("No backup file found in Dropbox")
            return False
        else:
            logger.error(f"Dropbox API error: {e}")
            return False
    except Exception as e:
        logger.error(f"Failed to restore database from Dropbox: {e}")
        return False

def backup_on_startup():
    """Backup database when bot starts - ENHANCED for data preservation"""
    # First try to restore from backup
    if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
        logger.info("Local database is empty or missing, attempting restore from Dropbox...")
        if restore_database_from_dropbox():
            logger.info("Database restored successfully from Dropbox")
        else:
            logger.info("No backup available or restore failed, starting with fresh database")
    
    # Then backup the current state
    logger.info("Backing up database to Dropbox...")
    if backup_database_to_dropbox():
        logger.info("Database backed up successfully to Dropbox")
    else:
        logger.warning("Failed to backup database to Dropbox")

def schedule_periodic_backup():
    """Schedule periodic backups every 6 hours - ENHANCED for data preservation"""
    import threading
    import time
    
    def backup_worker():
        while True:
            time.sleep(6 * 60 * 60)  # 6 hours
            logger.info("Running periodic database backup...")
            backup_database_to_dropbox()
    
    # Start backup thread
    backup_thread = threading.Thread(target=backup_worker, daemon=True)
    backup_thread.start()
    logger.info("Periodic backup scheduler started (every 6 hours)")

# ------------------------------ HANDLER FUNCTIONS ------------------------------

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int = None):
    menu_text = "*Welcome back!*\n\nUse the custom keyboard below."
    
    chat_id = update.effective_chat.id
    
    await context.bot.send_message(
        chat_id=chat_id, 
        text=menu_text, 
        reply_markup=MAIN_REPLY_KEYBOARD, 
        parse_mode="Markdown"
    )
    
    if update.callback_query and message_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            logger.warning(f"Failed to delete message after showing main menu: {e}")

# UPDATED: Profile display with department included
async def deep_link_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id: int):
    user_id = update.effective_user.id
    profile = get_user_profile(target_user_id)
    follow_counts = get_follow_counts(target_user_id)
    
    # Different text for own profile vs others
    if target_user_id == user_id:
        profile_text = (
            f"👤 **Your Public Profile**\n\n"
            f"⚡ Aura Points: {profile['aura_points']}\n"
            f"👥 Followers: {follow_counts['followers']} | Following: {follow_counts['following']}\n"
            f"Department: {profile['department'] or 'Not specified'}\n\n"
        )
        
        if profile['bio'] and profile['bio'] != "No bio set":
            profile_text += f"📝 Bio: {profile['bio']}\n"
        else:
            profile_text += "📝 Bio:\nThis user has not set a bio yet.\n"
            
        await update.message.reply_text("Loading profile...", reply_markup=ReplyKeyboardRemove())
        
        await update.message.reply_text(
            profile_text,
            reply_markup=InlineKeyboardMarkup([]),  # No buttons for own profile
            parse_mode="Markdown"
        )
    else:
        profile_text = (
            f"👤 **{profile['nickname'] or 'Anonymous'}'s Public Profile**\n\n"
            f"⚡ Aura Points: {profile['aura_points']}\n"
            f"👥 Followers: {follow_counts['followers']} | Following: {follow_counts['following']}\n"
            f"Department: {profile['department'] or 'Not specified'}\n"
        )
        
        if profile['bio'] and profile['bio'] != "No bio set":
            profile_text += f"📝 Bio: {profile['bio']}\n"
        else:
            profile_text += "📝 Bio:\nThis user has not set a bio yet.\n"
        
        context.user_data['viewing_profile_id'] = target_user_id
        
        await update.message.reply_text("Loading profile...", reply_markup=ReplyKeyboardRemove())
        
        await update.message.reply_text(
            profile_text,
            reply_markup=get_user_profile_keyboard(target_user_id, user_id),
            parse_mode="Markdown"
        )

# UPDATED: Start function with proper user tracking and persistence
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    
    # Check if user has used /start before - FIXED: Proper persistence check
    if not profile.get('start_used', False):
        # First time user - show regulations
        update_user_profile(user_id, start_used=True)
        
        regulations = (
            "👋 **Welcome!** Before you begin, please read our rules:\n\n"
            "1. All confessions are **anonymous** to the public and admins.\n"
            "2. Submissions are **moderated** and may be rejected.\n"
            "3. **No spam, hate speech, or illegal content**.\n"
            "4. You can only submit **one confession every 2 minutes**.\n\n"
            "Do you accept these terms to continue?"
        )
        keyboard = [[InlineKeyboardButton("✅ Yes, I Accept the Terms", callback_data=CB_ACCEPT)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.effective_chat.send_message("Loading rules...", reply_markup=ReplyKeyboardRemove())
        await update.effective_chat.send_message(regulations, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END
    
    # Check if user needs to accept terms
    if not profile.get('terms_accepted', False):
        regulations = (
            "👋 **Welcome Back!** Please accept our terms to continue:\n\n"
            "1. All confessions are **anonymous** to the public and admins.\n"
            "2. Submissions are **moderated** and may be rejected.\n"
            "3. **No spam, hate speech, or illegal content**.\n"
            "4. You can only submit **one confession every 2 minutes**.\n\n"
            "Do you accept these terms to continue?"
        )
        keyboard = [[InlineKeyboardButton("✅ Yes, I Accept the Terms", callback_data=CB_ACCEPT)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.effective_chat.send_message("Loading rules...", reply_markup=ReplyKeyboardRemove())
        await update.effective_chat.send_message(regulations, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END
    
    # Returning user - check for deep links
    if context.args:
        start_payload = context.args[0]
        if start_payload.startswith("comment_"):
            try:
                conf_id = int(start_payload.split("_")[1])
                conf = get_confession(conf_id)
                if conf and conf['status'] == 'approved':
                    comment_count = get_comment_count_for_confession(conf_id)
                    channel_text = format_confession_for_channel(conf)
                    await update.effective_chat.send_message("Loading confession...", reply_markup=ReplyKeyboardRemove())
                    await update.effective_chat.send_message(
                        channel_text,
                        parse_mode="HTML",
                        reply_markup=get_deep_link_keyboard(conf_id, comment_count)
                    )
                    return 
                else:
                    await update.effective_chat.send_message("❌ Confession not found or not approved.")
            except (IndexError, ValueError):
                pass
        elif start_payload.startswith("profile_"):
            try:
                target_user_id = int(start_payload.split("_")[1])
                await deep_link_profile(update, context, target_user_id)
                return
            except (IndexError, ValueError):
                pass
        elif start_payload.startswith("reply_"):
            try:
                comment_id = int(start_payload.split("_")[1])
                comment = get_comment(comment_id)
                if comment:
                    conf_id = comment['conf_id']
                    conf = get_confession(conf_id)
                    if conf and conf['status'] == 'approved':
                        comment_count = get_comment_count_for_confession(conf_id)
                        channel_text = format_confession_for_channel(conf)
                        await update.effective_chat.send_message(
                            channel_text,
                            parse_mode="HTML",
                            reply_markup=get_deep_link_keyboard(conf_id, comment_count)
                        )
                        return
                    else:
                        await update.effective_chat.send_message("❌ Confession not found or not approved.")
                else:
                    await update.effective_chat.send_message("❌ Comment not found.")
            except (IndexError, ValueError):
                pass
        elif start_payload.startswith("chat_"):
            try:
                target_user_id = int(start_payload.split("_")[1])
                # Enter chat mode via deep link
                active_chat = get_active_chat(user_id, target_user_id)
                if active_chat:
                    context.user_data['active_chat_with'] = target_user_id
                    context.user_data['active_chat_id'] = active_chat['id']
                    await enter_chat_mode(update, context, target_user_id)
                    return WAITING_FOR_CHAT_MESSAGE
                else:
                    await update.effective_chat.send_message("❌ Chat not found or no longer active.")
            except (IndexError, ValueError):
                pass
    
    # Returning user - show main menu directly
    await show_main_menu(update, context)

async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    
    data = query.data
    
    if data == CB_ACCEPT:
        # Record terms acceptance
        user_id = update.effective_user.id
        update_user_profile(user_id, terms_accepted=True, start_used=True)
        await show_main_menu(update, context, query.message.message_id)
        
    return ConversationHandler.END 

async def secondary_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()
    
    if data == CB_MENU_MAIN:
        await show_main_menu(update, context, query.message.message_id) 
        
    return ConversationHandler.END

async def comment_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith("comment_page:"):
        try:
            parts = data.split(":")
            conf_id = int(parts[1])
            page = int(parts[2])
            
            # Delete the current message
            await query.delete_message()
            
            # Show comments for the new page
            await show_comments(update, context, conf_id, page)
            
        except (IndexError, ValueError) as e:
            logger.error(f"Error processing comment page: {e}")
            await query.edit_message_text("Error loading comments.", reply_markup=None)
    
    return ConversationHandler.END

# UPDATED: Fixed comment menu button callback with media support
async def comment_menu_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith("comment_add:"):
        try:
            conf_id = int(data.split(":")[1])
            context.user_data['current_conf_id'] = conf_id
            context.user_data['parent_comment_id'] = None
            
            await query.edit_message_reply_markup(reply_markup=None)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="💬 *Add a Comment*\n\nYou can send text, a photo, or a document as your comment.\n\nSend /cancel to abort.",
                reply_markup=ReplyKeyboardMarkup([['❌ Cancel', '🏠 Main Menu']], resize_keyboard=True),
                parse_mode="Markdown"
            )
            return WAITING_FOR_COMMENT
        except (IndexError, ValueError) as e:
            logger.error(f"Error processing start_comment: {e}")
            await query.edit_message_text("Error processing comment request.", reply_markup=None)
            return ConversationHandler.END
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                 await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="💬 *Add a Comment*\n\nYou can send text, a photo, or a document as your comment.\n\nSend /cancel to abort.",
                    reply_markup=ReplyKeyboardMarkup([['❌ Cancel', '🏠 Main Menu']], resize_keyboard=True),
                    parse_mode="Markdown"
                )
            return WAITING_FOR_COMMENT
            
    return ConversationHandler.END

# UPDATED: Fixed comment menu callback with media support
async def comment_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("comment_add:"):
        conf_id_s = data.split(":")[1]
        try:
            conf_id = int(conf_id_s)
        except ValueError:
            await query.edit_message_text("Invalid confession ID.")
            return ConversationHandler.END
            
        context.user_data['current_conf_id'] = conf_id
        context.user_data['parent_comment_id'] = None
        
        await query.message.reply_text(
            "💬 *Add a Comment*\n\nYou can send text, a photo, or a document as your comment.\n\nSend /cancel to abort.",
            reply_markup=ReplyKeyboardMarkup([['❌ Cancel', '🏠 Main Menu']], resize_keyboard=True),
            parse_mode="Markdown"
        )
        
        return WAITING_FOR_COMMENT
    
    elif data.startswith("comment_view:"):
        conf_id_s = data.split(":")[1]
        try:
            conf_id = int(conf_id_s)
        except ValueError:
            await query.edit_message_text("Invalid confession ID.")
            return ConversationHandler.END
        
        context.user_data['last_viewed_conf_id'] = conf_id
        
        await query.message.reply_text(
            f"Fetching comments for Confession #{conf_id}...",
            reply_markup=ReplyKeyboardRemove()
        )
        
        await show_comments(update, context, conf_id)
        
        return ConversationHandler.END

# UPDATED: Comment interaction with COMPLETELY FIXED chat system
async def comment_interaction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data.startswith("vote:"):
        parts = data.split(":")
        vote_type = parts[1]
        comment_id = int(parts[2])
        
        success, action = process_vote(comment_id, user_id, vote_type)
        
        if success:
            counts = get_comment_vote_counts(comment_id)
            user_vote = get_user_vote_on_comment(comment_id, user_id)
            
            comment_dict = {'id': comment_id}
            new_keyboard = get_comment_interaction_keyboard(comment_dict, user_id, counts, user_vote)
            
            try:
                await query.edit_message_reply_markup(reply_markup=new_keyboard)
            except Exception as e:
                logger.warning(f"Failed to update vote buttons: {e}")
        
        return
    
    elif data.startswith("reply:"):
        comment_id_s = data.split(":")[1]
        try:
            parent_comment_id = int(comment_id_s)
        except ValueError:
            await query.message.reply_text("Invalid comment ID.")
            return ConversationHandler.END
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT conf_id, user_id FROM comments WHERE id = ?", (parent_comment_id,))
        row = cur.fetchone()
        conn.close()
        
        if not row:
            await query.message.reply_text("Could not find the comment to reply to.")
            return ConversationHandler.END
        
        conf_id = row[0]
        parent_author_id = row[1]
        
        context.user_data['current_conf_id'] = conf_id
        context.user_data['parent_comment_id'] = parent_comment_id
        context.user_data['parent_author_id'] = parent_author_id
        
        await query.message.reply_text(
            f"💬 *Reply to Comment*\n\nYou can send text, a photo, or a document as your reply.\n\nType your reply below or send /cancel to abort.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([['❌ Cancel', '🏠 Main Menu']], resize_keyboard=True)
        )
        
        return WAITING_FOR_REPLY
    
    elif data.startswith("follow_user:"):
        target_user_id = int(data.split(":")[1])
        followed = toggle_follow(user_id, target_user_id)
        
        action_text = "followed" if followed else "unfollowed"
        await query.answer(f"You have {action_text} this user.", show_alert=True)
        
        new_keyboard = get_user_profile_keyboard(target_user_id, user_id)
        try:
            await query.edit_message_reply_markup(reply_markup=new_keyboard)
        except Exception:
            pass
        
        return
    
    elif data == "back_to_comments":
        conf_id = context.user_data.get('last_viewed_conf_id')
        if conf_id:
            await query.message.reply_text(f"Fetching comments for Confession #{conf_id}...")
            await show_comments(update, context, conf_id)
        else:
            await query.message.reply_text("No confession context found.")
        return
    
    # Report user handler
    elif data.startswith("report_user:"):
        target_user_id = int(data.split(":")[1])
        context.user_data['reporting_user_id'] = target_user_id
        
        await query.edit_message_text(
            "⚠️ **Report User**\n\n"
            "Please select a reason for reporting this user, or provide a custom one.",
            reply_markup=get_report_reason_keyboard(),
            parse_mode="Markdown"
        )
        return WAITING_FOR_REPORT_REASON
    
    # COMPLETELY FIXED: Chat request handler with proper button updates
    elif data.startswith("request_chat:"):
        target_user_id = int(data.split(":")[1])
        
        # Check if there's already an active chat
        active_chat = get_active_chat(user_id, target_user_id)
        if active_chat:
            # Enter chat mode directly
            context.user_data['active_chat_with'] = target_user_id
            context.user_data['active_chat_id'] = active_chat['id']
            await enter_chat_mode(update, context, target_user_id)
            return WAITING_FOR_CHAT_MESSAGE
        
        # Check if there's already a pending request from this user
        chat_request = get_chat_request(user_id, target_user_id)
        if chat_request and chat_request['status'] == 'pending':
            await query.answer("✅ Chat request already sent.", show_alert=True)
            
            # Update button to show "Chat Request Sent"
            new_keyboard = get_user_profile_keyboard(target_user_id, user_id)
            try:
                await query.edit_message_reply_markup(reply_markup=new_keyboard)
            except Exception:
                pass
            return
        
        # Check if the target user has already sent a request
        existing_request = get_chat_request(target_user_id, user_id)
        if existing_request and existing_request['status'] == 'pending':
            # Auto-accept the existing request
            update_chat_request_status(existing_request['id'], 'accepted')
            chat_id = create_active_chat(user_id, target_user_id)
            
            await query.answer("✅ Chat request accepted automatically!", show_alert=True)
            
            # Update button to show "Send Message"
            new_keyboard = get_user_profile_keyboard(target_user_id, user_id)
            try:
                await query.edit_message_reply_markup(reply_markup=new_keyboard)
            except Exception:
                pass
            
            # Notify the other user
            try:
                user_profile = get_user_profile(user_id)
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"💬 **Chat Request Accepted**\n\n"
                         f"**{user_profile['nickname'] or 'Anonymous'}** has accepted your chat request!\n\n"
                         f"You can now send messages from their profile.",
                    parse_mode="Markdown"
                )
                
                # Also update the other user's view of this user's profile
                target_profile = get_user_profile(target_user_id)
                new_keyboard_for_other = get_user_profile_keyboard(user_id, target_user_id)
                
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"👤 **{user_profile['nickname'] or 'Anonymous'}'s Public Profile**\n\n"
                         f"⚡ Aura Points: {user_profile['aura_points']}\n"
                         f"👥 Followers: {get_follow_counts(user_id)['followers']} | Following: {get_follow_counts(user_id)['following']}\n"
                         f"Department: {user_profile['department'] or 'Not specified'}\n"
                         f"📝 Bio: {user_profile['bio']}",
                    reply_markup=new_keyboard_for_other,
                    parse_mode="Markdown"
                )
                
            except Exception as e:
                logger.warning(f"Could not notify user about auto-accepted chat: {e}")
            
            return

        # Create new chat request
        if create_chat_request(user_id, target_user_id):
            await query.answer("✅ Chat request sent!", show_alert=True)
            
            # Update button to show "Chat Request Sent"
            new_keyboard = get_user_profile_keyboard(target_user_id, user_id)
            try:
                await query.edit_message_reply_markup(reply_markup=new_keyboard)
            except Exception:
                pass
            
            # Notify the target user
            try:
                user_profile = get_user_profile(user_id)
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"💬 **Chat Request**\n\n"
                         f"**{user_profile['nickname'] or 'Anonymous'}** would like to start a chat with you.",
                    reply_markup=get_chat_request_keyboard(user_id),
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Could not send chat request notification: {e}")
        
        return

    elif data.startswith("start_chat:"):
        # Start chat from deep link or My Chats
        target_user_id = int(data.split(":")[1])
        
        # Get active chat
        active_chat = get_active_chat(user_id, target_user_id)
        if not active_chat:
            await query.edit_message_text("Chat not found or no longer active.")
            return ConversationHandler.END
        
        # Enter chat mode
        context.user_data['active_chat_with'] = target_user_id
        context.user_data['active_chat_id'] = active_chat['id']
        
        if query.message:
            await query.message.reply_text("Entering chat...")
        
        await enter_chat_mode(update, context, target_user_id)
        return WAITING_FOR_CHAT_MESSAGE
    
    return ConversationHandler.END

# Report reason selection handler
async def report_reason_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith("report_reason:"):
        reason = data.split(":")[1]
        target_user_id = context.user_data.get('reporting_user_id')
        
        if not target_user_id:
            await query.edit_message_text("Error: No user to report.")
            return ConversationHandler.END
        
        if reason == "cancel":
            await query.edit_message_text("Report cancelled.")
            return ConversationHandler.END
        
        elif reason == "skip":
            # Create report without reason
            create_user_report(query.from_user.id, target_user_id)
            await query.edit_message_text("✅ User reported to the admin. Thank you.")
            
            # Notify admin
            await notify_admin_about_report(context, query.from_user.id, target_user_id)
            
        elif reason == "other":
            await query.edit_message_text(
                "✍️ **Custom Report Reason**\n\n"
                "Please type your reason for reporting this user:",
                parse_mode="Markdown"
            )
            return WAITING_FOR_CUSTOM_REPORT
        
        else:
            # Create report with selected reason
            create_user_report(query.from_user.id, target_user_id, reason=reason)
            await query.edit_message_text("✅ User reported to the admin. Thank you.")
            
            # Notify admin
            await notify_admin_about_report(context, query.from_user.id, target_user_id, reason)
        
        return ConversationHandler.END
    
    return WAITING_FOR_REPORT_REASON

# Custom report reason handler
async def custom_report_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    target_user_id = context.user_data.get('reporting_user_id')
    
    if not target_user_id:
        await update.message.reply_text("Error: No user to report.")
        return ConversationHandler.END
    
    # Create report with custom reason
    create_user_report(update.effective_user.id, target_user_id, custom_reason=text)
    await update.message.reply_text("✅ User reported to the admin. Thank you.")
    
    # Notify admin
    await notify_admin_about_report(context, update.effective_user.id, target_user_id, custom_reason=text)
    
    return ConversationHandler.END

# Admin notification for reports
async def notify_admin_about_report(context: ContextTypes.DEFAULT_TYPE, reporter_id: int, reported_user_id: int, reason: str = None, custom_reason: str = None):
    reporter_profile = get_user_profile(reporter_id)
    reported_profile = get_user_profile(reported_user_id)
    
    report_text = (
        "🚨 **User Report**\n\n"
        f"👤 **Reported User:** {reported_profile['nickname'] or 'Anonymous'} (ID: `{reported_user_id}`)\n"
        f"📝 **Reported By:** {reporter_profile['nickname'] or 'Anonymous'} (ID: `{reporter_id}`)\n"
    )
    
    if reason:
        report_text += f"📋 **Reason:** {reason}\n"
    if custom_reason:
        report_text += f"📝 **Custom Reason:** {custom_reason}\n"
    
    report_text += f"⏰ **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=report_text,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to send report to admin: {e}")

# COMPLETELY FIXED: Chat request response handler with proper button updates for BOTH users
async def chat_request_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith("chat_accept:"):
        from_user_id = int(data.split(":")[1])
        to_user_id = query.from_user.id
        
        # Get the chat request
        chat_request = get_chat_request(from_user_id, to_user_id)
        if not chat_request:
            await query.edit_message_text("Chat request not found or already processed.")
            return
        
        # Update request status and create active chat
        update_chat_request_status(chat_request['id'], 'accepted')
        chat_id = create_active_chat(from_user_id, to_user_id)
        
        await query.edit_message_text(
            "✅ Chat request accepted. You can now chat with this user.",
            parse_mode="Markdown"
        )
        
        # FIXED: Update BOTH users' profile views to show "Send Message"
        try:
            # Get user profiles
            from_user_profile = get_user_profile(from_user_id)
            to_user_profile = get_user_profile(to_user_id)
            
            # Notify the requester
            await context.bot.send_message(
                chat_id=from_user_id,
                text=f"✅ **The user has accepted your chat request!**\n\n"
                     f"You can now send messages from their profile.",
                parse_mode="Markdown"
            )
            
            # Update the requester's view of the target user's profile to show "Send Message"
            new_keyboard_for_requester = get_user_profile_keyboard(to_user_id, from_user_id)
            
            # Send updated profile view to requester
            await context.bot.send_message(
                chat_id=from_user_id,
                text=f"👤 **{to_user_profile['nickname'] or 'Anonymous'}'s Public Profile**\n\n"
                     f"⚡ Aura Points: {to_user_profile['aura_points']}\n"
                     f"👥 Followers: {get_follow_counts(to_user_id)['followers']} | Following: {get_follow_counts(to_user_id)['following']}\n"
                     f"Department: {to_user_profile['department'] or 'Not specified'}\n"
                     f"📝 Bio: {to_user_profile['bio']}",
                reply_markup=new_keyboard_for_requester,
                parse_mode="Markdown"
            )
            
            # Update the acceptor's view of the requester's profile to show "Send Message"
            new_keyboard_for_acceptor = get_user_profile_keyboard(from_user_id, to_user_id)
            
            # Send updated profile view to acceptor
            await context.bot.send_message(
                chat_id=to_user_id,
                text=f"👤 **{from_user_profile['nickname'] or 'Anonymous'}'s Public Profile**\n\n"
                     f"⚡ Aura Points: {from_user_profile['aura_points']}\n"
                     f"👥 Followers: {get_follow_counts(from_user_id)['followers']} | Following: {get_follow_counts(from_user_id)['following']}\n"
                     f"Department: {from_user_profile['department'] or 'Not specified'}\n"
                     f"📝 Bio: {from_user_profile['bio']}",
                reply_markup=new_keyboard_for_acceptor,
                parse_mode="Markdown"
            )
                
        except Exception as e:
            logger.warning(f"Could not notify user about accepted chat: {e}")
        
    elif data.startswith("chat_decline:"):
        from_user_id = int(data.split(":")[1])
        to_user_id = query.from_user.id
        
        # Get the chat request
        chat_request = get_chat_request(from_user_id, to_user_id)
        if not chat_request:
            await query.edit_message_text("Chat request not found or already processed.")
            return
        
        # Update request status
        update_chat_request_status(chat_request['id'], 'rejected')
        
        await query.edit_message_text(
            "❌ Chat request declined.",
            parse_mode="Markdown"
        )
        
        # Notify the requester
        try:
            await context.bot.send_message(
                chat_id=from_user_id,
                text="❌ Your chat request was declined.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Could not notify user about declined chat: {e}")

# UPDATED: Enter chat mode with improved messaging
async def enter_chat_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id: int):
    user_id = update.effective_user.id
    active_chat = get_active_chat(user_id, target_user_id)
    
    if not active_chat:
        await update.effective_message.reply_text("No active chat found.")
        return ConversationHandler.END
    
    target_profile = get_user_profile(target_user_id)
    
    # Get chat history
    chat_messages = get_chat_messages(active_chat['id'])
    
    history_text = f"**Chat History with {target_profile['nickname'] or 'Anonymous'}**\n\n"
    
    if not chat_messages:
        history_text += "No messages yet.\n"
    else:
        for msg in chat_messages:
            sender = "You" if msg['from_user_id'] == user_id else target_profile['nickname'] or 'Anonymous'
            history_text += f"{sender}: {msg['content']}\n"
    
    history_text += f"\nYou are now in a chat with {target_profile['nickname'] or 'Anonymous'}. Any message you send here will be forwarded to them. Use /leavechat to exit."
    
    await update.effective_message.reply_text(
        history_text,
        reply_markup=CHAT_KEYBOARD,
        parse_mode="Markdown"
    )
    
    context.user_data['active_chat_with'] = target_user_id
    context.user_data['active_chat_id'] = active_chat['id']
    
    return WAITING_FOR_CHAT_MESSAGE

# UPDATED: Fixed chat message handler to properly deliver messages both ways
async def chat_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target_user_id = context.user_data.get('active_chat_with')
    chat_id = context.user_data.get('active_chat_id')
    
    if not target_user_id or not chat_id:
        await update.message.reply_text("No active chat session.")
        return ConversationHandler.END
    
    # Check if blocked
    if is_blocked(target_user_id, user_id):
        await update.message.reply_text("⚠️ Unable to send message. The chat has been ended.")
        return ConversationHandler.END
    
    message_text = update.message.text
    
    # Handle keyboard buttons
    if message_text == "Block":
        block_user(user_id, target_user_id)
        end_chat(chat_id)
        
        target_profile = get_user_profile(target_user_id)
        await update.message.reply_text(
            f"🚫 You have blocked {target_profile['nickname'] or 'Anonymous'}. They will no longer be able to send you messages through the bot. The chat has been ended.",
            reply_markup=MAIN_REPLY_KEYBOARD
        )
        
        # Notify the other user
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"ℹ️ The other user has blocked you. The chat session has ended.",
                reply_markup=MAIN_REPLY_KEYBOARD
            )
        except Exception as e:
            logger.warning(f"Could not notify user about block: {e}")
        
        context.user_data.pop('active_chat_with', None)
        context.user_data.pop('active_chat_id', None)
        return ConversationHandler.END
    
    elif message_text == "Report":
        context.user_data['reporting_user_id'] = target_user_id
        await update.message.reply_text(
            "⚠️ **Report User**\n\n"
            "Please select a reason for reporting this user, or provide a custom one.",
            reply_markup=get_report_reason_keyboard(),
            parse_mode="Markdown"
        )
        return WAITING_FOR_REPORT_REASON
    
    # Save the message
    save_chat_message(chat_id, user_id, target_user_id, message_text)
    
    await update.message.reply_text("✅ Message sent!")
    
    # Notify the other user - FIXED: Properly set context for receiver and deliver message
    try:
        user_profile = get_user_profile(user_id)
        
        # Send message to target user
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"💬 **Message from {user_profile['nickname'] or 'Anonymous'}:**\n\n{message_text}",
            parse_mode="Markdown"
        )
        
        # If the target user is not in chat mode, send instructions to enter chat
        target_context = context.application.user_data.get(target_user_id, {})
        if not target_context.get('active_chat_with'):
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"💬 You have received a message from {user_profile['nickname'] or 'Anonymous'}. Use the button below to enter chat mode and reply.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💬 Enter Chat", callback_data=f"start_chat:{user_id}")]
                ]),
                parse_mode="Markdown"
            )
        else:
            # If already in chat mode, just show the message with chat keyboard
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"💬 **Message from {user_profile['nickname'] or 'Anonymous'}:**\n\n{message_text}",
                reply_markup=CHAT_KEYBOARD,
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.warning(f"Could not deliver chat message: {e}")
        await update.message.reply_text("⚠️ Could not deliver message. The user may have blocked the bot or left.")
    
    return WAITING_FOR_CHAT_MESSAGE

# UPDATED: Leave chat command with improved notification
async def leave_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target_user_id = context.user_data.get('active_chat_with')
    chat_id = context.user_data.get('active_chat_id')
    
    if chat_id:
        end_chat(chat_id)
    
    await update.message.reply_text(
        "You have left the chat.",
        reply_markup=MAIN_REPLY_KEYBOARD
    )
    
    # Notify the other user
    if target_user_id:
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text="ℹ️ The other user has left the chat. The session has ended.",
                reply_markup=MAIN_REPLY_KEYBOARD
            )
        except Exception as e:
            logger.warning(f"Could not notify user about chat leave: {e}")
    
    context.user_data.pop('active_chat_with', None)
    context.user_data.pop('active_chat_id', None)
    
    return ConversationHandler.END

# NEW: Admin message handler
async def help_contact_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "✉️ **Contact Administrator**\n\n"
        "Please send the message you want to forward to the admin.\n\n"
        "Send /cancel to abort.",
        parse_mode="Markdown"
    )
    
    return WAITING_FOR_ADMIN_MESSAGE

# NEW: Admin message receiver
async def admin_message_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text.strip()
    user_id = update.effective_user.id
    user_profile = get_user_profile(user_id)
    
    if not message_text:
        await update.message.reply_text("Please send a valid message.")
        return WAITING_FOR_ADMIN_MESSAGE
    
    # Save admin message
    save_admin_message(user_id, message_text)
    
    # Forward to admin
    try:
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=f"📩 **Message from User**\n\n"
                 f"👤 **Sender:** {user_profile['nickname'] or 'Anonymous'} (ID: `{user_id}`)\n"
                 f"📝 **Message:** {message_text}\n\n"
                 f"⏰ **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            parse_mode="Markdown"
        )
        
        await update.message.reply_text(
            "✅ Your message has been sent to the admin. Thank you!",
            reply_markup=MAIN_REPLY_KEYBOARD
        )
    except Exception as e:
        logger.error(f"Failed to send message to admin: {e}")
        await update.message.reply_text(
            "❌ Failed to send message to admin. Please try again later.",
            reply_markup=MAIN_REPLY_KEYBOARD
        )
    
    return ConversationHandler.END

# NEW: Cancel admin message
async def admin_message_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Message to admin cancelled.",
        reply_markup=MAIN_REPLY_KEYBOARD
    )
    return ConversationHandler.END

# Confession functions (existing but with main menu improvements)
async def confess_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    # Rate Limiting Check
    last_ts = get_last_submission_ts(user_id)
    time_since = int(time.time()) - last_ts
    if time_since < RATE_LIMIT_SECONDS:
        remaining_time = RATE_LIMIT_SECONDS - time_since
        await update.effective_message.reply_text(
            f"⏳ *Rate Limit:* You must wait another *{remaining_time} seconds* before submitting a new confession.",
            parse_mode="Markdown",
            reply_markup=MAIN_REPLY_KEYBOARD
        )
        return ConversationHandler.END
    
    # Check for existing draft
    draft_conf = get_user_draft_confession(user_id)
    if draft_conf:
        conf_id = draft_conf['id']
    else:
        conf_id = save_confession(user_id, "", None, None) 
    
    context.user_data['current_conf_id'] = conf_id
    
    await update.effective_message.reply_text(
        "📝 *Start your confession.*\n\n"
        "You can send text, a photo, or a document. After sending your confession, you'll proceed directly to category selection.",
        reply_markup=CONFESSION_CANCEL_KEYBOARD,
        parse_mode="Markdown"
    )
    
    return WAITING_FOR_CONFESSION

async def confession_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    conf_id = context.user_data.get('current_conf_id')
    user_id = update.effective_user.id

    if not conf_id:
        await update.effective_message.reply_text("Error: Confession ID missing. Please start over with /confess.")
        return ConversationHandler.END
    
    content = ""
    file_id = None
    file_type = None
    
    if update.message.text:
        content = update.message.text
        if contains_profanity(content):
            await update.message.reply_text("🚫 Your message contains banned words. Please revise your confession.")
            return WAITING_FOR_CONFESSION
        file_type = "text"
        
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        content = update.message.caption if update.message.caption else ""
        if contains_profanity(content):
            await update.message.reply_text("🚫 Your caption contains banned words. Please revise your confession.")
            return WAITING_FOR_CONFESSION
        file_type = "photo"

    elif update.message.document:
        file_id = update.message.document.file_id
        content = update.message.caption if update.message.caption else ""
        if contains_profanity(content):
            await update.message.reply_text("🚫 Your caption contains banned words. Please revise your confession.")
            return WAITING_FOR_CONFESSION
        file_type = "document"

    else:
        await update.message.reply_text("🤔 Please send a text, photo, or document.")
        return WAITING_FOR_CONFESSION

    # Update the draft confession in DB
    update_confession_content_and_media(conf_id, content, file_id, file_type)
    
    # Directly proceed to category selection without requiring /done
    context.user_data['selected_categories'] = [] 
    
    await update.message.reply_text(
        "✅ Confession content saved!\n\n"
        "🏷️ *Select Categories*\n\n"
        f"Please select *up to {MAX_CATEGORIES}* categories that best describe your confession. "
        "A minimum of one is required.",
        reply_markup=get_categories_keyboard([]),
        parse_mode="Markdown"
    )

    return WAITING_FOR_CATEGORIES

async def category_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    await query.answer()

    current_selection: List[str] = context.user_data.get('selected_categories', [])
    category_name = data.replace(CB_CAT_PATTERN, "")
    
    if data == CB_CAT_DONE:
        if len(current_selection) >= 1:
            conf_id = context.user_data.get('current_conf_id')
            update_confession_categories(conf_id, current_selection)
            conf = get_confession(conf_id)

            review_text = "*Review & Submit*\n\nHere is your final confession draft:\n\n"
            
            if conf['file_id']:
                await query.edit_message_text(
                    text="✅ Categories selected. Preparing final review...",
                    reply_markup=None,
                    parse_mode="Markdown"
                )

                caption = review_text + format_confession_for_admin(conf)
                if conf['file_type'] == 'photo':
                    await query.message.reply_photo(
                        photo=conf['file_id'], caption=caption, parse_mode="HTML",
                        reply_markup=get_review_keyboard()
                    )
                elif conf['file_type'] == 'document':
                    await query.message.reply_document(
                        document=conf['file_id'], caption=caption, parse_mode="HTML",
                        reply_markup=get_review_keyboard()
                    )
                else:
                    await query.message.reply_text(
                        review_text + format_confession_for_admin(conf),
                        parse_mode="HTML",
                        reply_markup=get_review_keyboard()
                    )
            else:
                text = review_text + format_confession_for_admin(conf)
                await query.edit_message_text(
                    text=text, 
                    parse_mode="HTML",
                    reply_markup=get_review_keyboard()
                )

            return WAITING_FOR_REVIEW
        else:
            await query.answer("⚠️ Please select at least one category.", show_alert=True)
            return WAITING_FOR_CATEGORIES
            
    elif data.startswith(CB_CAT_PATTERN) and category_name not in ["auto", "disabled_done"]:
        if category_name in current_selection:
            current_selection.remove(category_name)
        elif len(current_selection) < MAX_CATEGORIES:
            current_selection.append(category_name)
        else:
            await query.answer(f"❌ You can only select up to {MAX_CATEGORIES} categories.", show_alert=True)
            return WAITING_FOR_CATEGORIES 
            
        context.user_data['selected_categories'] = current_selection
        
        try:
            await query.edit_message_reply_markup(
                reply_markup=get_categories_keyboard(current_selection)
            )
        except BadRequest as e:
            if str(e) != "Message is not modified":
                logger.error(f"Error editing categories keyboard: {e}")
                
        return WAITING_FOR_CATEGORIES
    
    elif category_name == "auto":
        await query.answer("🤖 Auto-selection is not yet implemented. Please select manually.", show_alert=True)
        return WAITING_FOR_CATEGORIES
    
    elif category_name == "disabled_done":
        await query.answer("⚠️ Please select at least one category to proceed.", show_alert=True)
        return WAITING_FOR_CATEGORIES

    return WAITING_FOR_CATEGORIES

# UPDATED: Confession review with auto main menu return
async def confession_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    await query.answer()

    if ":" in data:
        action = data.split(":")[1]
    else:
        action = data.replace("confess_action:", "")
        
    conf_id = context.user_data.get('current_conf_id')
    user_id = update.effective_user.id

    if not conf_id:
        await query.edit_message_text("Error: Confession ID missing. Please start over with /confess.", reply_markup=None)
        return ConversationHandler.END

    if action == "submit":
        set_confession_status(conf_id, "pending")
        update_last_submission_ts(user_id)
        
        conf = get_confession(conf_id)
        admin_text = format_confession_for_admin(conf)
        admin_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve", callback_data=f"{CB_APPROVE_PATTERN}{conf_id}")],
            [InlineKeyboardButton("❌ Reject", callback_data=f"{CB_REJECT_PATTERN}{conf_id}")]
        ])
        
        try:
            if conf['file_id']:
                if conf['file_type'] == 'photo':
                    admin_msg = await context.bot.send_photo(
                        chat_id=ADMIN_GROUP_ID, photo=conf['file_id'], caption=admin_text,
                        reply_markup=admin_keyboard, parse_mode="HTML"
                    )
                elif conf['file_type'] == 'document':
                    admin_msg = await context.bot.send_document(
                        chat_id=ADMIN_GROUP_ID, document=conf['file_id'], caption=admin_text,
                        reply_markup=admin_keyboard, parse_mode="HTML"
                    )
                else:
                    admin_msg = await context.bot.send_message(
                        chat_id=ADMIN_GROUP_ID, text=admin_text, 
                        reply_markup=admin_keyboard, parse_mode="HTML"
                    )
            else:
                admin_msg = await context.bot.send_message(
                    chat_id=ADMIN_GROUP_ID, text=admin_text, 
                    reply_markup=admin_keyboard, parse_mode="HTML"
                )
            
            record_admin_message_id(conf_id, admin_msg.message_id)

            await query.edit_message_text(
                "🎉 **Success!** Your confession has been submitted for review.\n\n"
                "You will be notified when it is approved or rejected.",
                parse_mode="Markdown",
                reply_markup=None
            )
            
            # UPDATED: Automatically return to main menu
            await show_main_menu(update, context)
            
        except Exception as e:
            logger.error(f"Failed to send confession to admin group: {e}")
            await query.edit_message_text(
                "❌ **Submission Error:** Failed to send to the admin channel. Please try again later.",
                parse_mode="Markdown",
                reply_markup=None
            )
        
        context.user_data.pop('current_conf_id', None)
        context.user_data.pop('selected_categories', None)
        return ConversationHandler.END

    elif action == "edit":
        await query.edit_message_text(
            "✍️ *Edit Mode:*\n\nSend your entire *new* confession (text or media) to replace the current content.",
            parse_mode="Markdown",
            reply_markup=None
        )
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You can now send your new confession content:",
            reply_markup=CONFESSION_CANCEL_KEYBOARD
        )
        
        return WAITING_FOR_CONFESSION

    elif action == "cancel":
        set_confession_status(conf_id, "cancelled") 
        
        await query.edit_message_text(
            "👋 Confession cancelled. Redirecting to main menu...", 
            reply_markup=None
        )
        
        context.user_data.pop('current_conf_id', None)
        context.user_data.pop('selected_categories', None)
        
        await show_main_menu(update, context)
        
        return ConversationHandler.END
        
    return WAITING_FOR_REVIEW

# UPDATED: Confession cancel with auto main menu
async def confession_cancel_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    conf_id = context.user_data.pop('current_conf_id', None)
    context.user_data.pop('selected_categories', None)
    
    if conf_id:
        set_confession_status(conf_id, "cancelled")
        
    msg = update.effective_message
    if msg:
        await msg.reply_text("❌ Confession draft cancelled. Redirecting to main menu...", reply_markup=ReplyKeyboardRemove())
    
    await show_main_menu(update, context)
    
    return ConversationHandler.END

async def admin_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    try:
        action, conf_id_str = data.split(":")
        conf_id = int(conf_id_str)
    except ValueError:
        await query.answer("Error processing request.", show_alert=True)
        return

    conf = get_confession(conf_id)
    if not conf or conf['status'] != 'pending':
        status_text = f"\n\n⚠️ *Already Processed (Confession {conf_id}).*"
        try:
            await query.edit_message_caption(
                caption=query.message.caption + status_text,
                reply_markup=None,
                parse_mode="Markdown"
            )
        except BadRequest:
            pass
        await query.answer("⚠️ This confession is already processed.", show_alert=True)
        return
    
    await query.answer(f"{action.capitalize()}ing Confession #{conf_id}...") 

    if action == "approve":
        set_confession_status(conf_id, "approved")
        
        channel_text = format_confession_for_channel(conf)
        channel_buttons = get_channel_post_keyboard(conf_id) 
        
        try:
            if conf['file_id']:
                if conf['file_type'] == 'photo':
                    channel_msg = await context.bot.send_photo(
                        chat_id=CHANNEL_ID, photo=conf['file_id'], caption=channel_text,
                        reply_markup=channel_buttons, parse_mode="HTML"
                    )
                elif conf['file_type'] == 'document':
                    channel_msg = await context.bot.send_document(
                        chat_id=CHANNEL_ID, document=conf['file_id'], caption=channel_text,
                        reply_markup=channel_buttons, parse_mode="HTML"
                    )
                else:
                    channel_msg = await context.bot.send_message(
                        chat_id=CHANNEL_ID, text=channel_text, 
                        reply_markup=channel_buttons, parse_mode="HTML"
                    )
            else:
                channel_msg = await context.bot.send_message(
                    chat_id=CHANNEL_ID, text=channel_text, 
                    reply_markup=channel_buttons, parse_mode="HTML"
                )
            
            record_channel_message_id(conf_id, channel_msg.message_id)
            
            final_status_text = f"✅ APPROVED (Confession {conf_id}) and POSTED to Channel."
            
            try:
                await query.edit_message_text(
                    text=final_status_text,
                    reply_markup=None,
                    parse_mode="Markdown"
                )
            except BadRequest:
                try:
                    await query.edit_message_caption(
                        caption=final_status_text,
                        reply_markup=None,
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Failed to edit admin message: {e}")
            
            await context.bot.send_message(
                chat_id=conf['user_id'], 
                text=f"✅ **Confession #{conf_id}** has been approved and posted to the channel!",
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Error posting to channel or editing admin message: {e}")
            error_status_text = f"⚠️ *Error during Channel Post (Confession {conf_id}). Check logs.*"
            try:
                await query.edit_message_text(
                    text=error_status_text,
                    reply_markup=None,
                    parse_mode="Markdown"
                )
            except BadRequest:
                try:
                    await query.edit_message_caption(
                        caption=error_status_text,
                        reply_markup=None,
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

    elif action == "reject":
        set_confession_status(conf_id, "rejected")
        
        final_status_text = f"❌ REJECTED (Confession {conf_id})."
        
        try:
            await query.edit_message_text(
                text=final_status_text,
                reply_markup=None,
                parse_mode="Markdown"
            )
        except BadRequest:
            try:
                await query.edit_message_caption(
                    caption=final_status_text,
                    reply_markup=None,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Failed to edit admin message: {e}")
        
        await context.bot.send_message(
            chat_id=conf['user_id'], 
            text=f"❌ **Confession #{conf_id}** was rejected by the admin. Please try again with different content.",
            parse_mode="Markdown"
        )

# UPDATED: Comment receive with media support
async def comment_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return WAITING_FOR_COMMENT
    
    text = ""
    file_id = None
    file_type = None
    
    # Handle text messages
    if msg.text:
        text = msg.text.strip()
        
        if text == "❌ Cancel" or text == "🏠 Main Menu":
            await msg.reply_text("Comment cancelled.", reply_markup=MAIN_REPLY_KEYBOARD)
            return ConversationHandler.END
        
        if text.startswith("/"):
            return WAITING_FOR_COMMENT
        
        if contains_profanity(text):
            await msg.reply_text("Your comment contains disallowed words. Please try again.")
            return WAITING_FOR_COMMENT
    
    # Handle media messages
    elif msg.photo:
        file_id = msg.photo[-1].file_id
        file_type = "photo"
        text = msg.caption if msg.caption else ""
        
        if contains_profanity(text):
            await msg.reply_text("Your caption contains disallowed words. Please try again.")
            return WAITING_FOR_COMMENT
            
    elif msg.document:
        file_id = msg.document.file_id
        file_type = "document"
        text = msg.caption if msg.caption else ""
        
        if contains_profanity(text):
            await msg.reply_text("Your caption contains disallowed words. Please try again.")
            return WAITING_FOR_COMMENT
    
    else:
        await msg.reply_text("Please send text, a photo, or a document as your comment.")
        return WAITING_FOR_COMMENT
    
    conf_id = context.user_data.get('current_conf_id')
    parent_comment_id = context.user_data.get('parent_comment_id')
    
    if not conf_id:
        await msg.reply_text("Session expired. Please try again.")
        return ConversationHandler.END
    
    comment_id = save_comment(conf_id, msg.from_user.id, text, parent_comment_id, file_id, file_type)
    
    conf = get_confession(conf_id)
    if conf and conf.get('channel_message_id'):
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=CHANNEL_ID,
                message_id=conf['channel_message_id'],
                reply_markup=get_channel_post_keyboard(conf_id)
            )
        except Exception as e:
            logger.warning(f"Could not update channel message keyboard: {e}")
    
    await msg.reply_text(
        f"✅ Your comment has been posted!",
        parse_mode="Markdown",
        reply_markup=MAIN_REPLY_KEYBOARD
    )
    
    context.user_data.pop('current_conf_id', None)
    context.user_data.pop('parent_comment_id', None)
    
    return ConversationHandler.END

# UPDATED: Reply receive with media support
async def reply_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return WAITING_FOR_REPLY
    
    text = ""
    file_id = None
    file_type = None
    
    # Handle text messages
    if msg.text:
        text = msg.text.strip()
        
        if text == "❌ Cancel" or text == "🏠 Main Menu":
            await msg.reply_text("Reply cancelled.", reply_markup=MAIN_REPLY_KEYBOARD)
            return ConversationHandler.END
        
        if text.startswith("/"):
            return WAITING_FOR_REPLY
        
        if contains_profanity(text):
            await msg.reply_text("Your reply contains disallowed words. Please try again.")
            return WAITING_FOR_REPLY
    
    # Handle media messages
    elif msg.photo:
        file_id = msg.photo[-1].file_id
        file_type = "photo"
        text = msg.caption if msg.caption else ""
        
        if contains_profanity(text):
            await msg.reply_text("Your caption contains disallowed words. Please try again.")
            return WAITING_FOR_REPLY
            
    elif msg.document:
        file_id = msg.document.file_id
        file_type = "document"
        text = msg.caption if msg.caption else ""
        
        if contains_profanity(text):
            await msg.reply_text("Your caption contains disallowed words. Please try again.")
            return WAITING_FOR_REPLY
    
    else:
        await msg.reply_text("Please send text, a photo, or a document as your reply.")
        return WAITING_FOR_REPLY
    
    conf_id = context.user_data.get('current_conf_id')
    parent_comment_id = context.user_data.get('parent_comment_id')
    parent_author_id = context.user_data.get('parent_author_id')
    
    if not conf_id or not parent_comment_id:
        await msg.reply_text("Session expired. Please try again.")
        return ConversationHandler.END
    
    comment_id = save_comment(conf_id, msg.from_user.id, text, parent_comment_id, file_id, file_type)
    
    conf = get_confession(conf_id)
    if conf and conf.get('channel_message_id'):
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=CHANNEL_ID,
                message_id=conf['channel_message_id'],
                reply_markup=get_channel_post_keyboard(conf_id)
            )
        except Exception as e:
            logger.warning(f"Could not update channel message keyboard: {e}")
    
    # Send notification to parent comment author if it's not the same user
    if parent_author_id and parent_author_id != msg.from_user.id:
        try:
            deep_link = f"https://t.me/{BOT_USERNAME}?start=reply_{comment_id}"
            
            await context.bot.send_message(
                chat_id=parent_author_id,
                text=f"🔔 **Someone replied to your comment on Confession #{conf_id}.**\n\n"
                     f"*{text[:100]}{'...' if len(text) > 100 else ''}*\n\n"
                     f"Click here to view the reply:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📨 View Reply", url=deep_link)]
                ])
            )
        except Exception as e:
            logger.warning(f"Could not send reply notification: {e}")
    
    await msg.reply_text(
        f"✅ Your reply has been posted!",
        parse_mode="Markdown",
        reply_markup=MAIN_REPLY_KEYBOARD
    )
    
    context.user_data.pop('current_conf_id', None)
    context.user_data.pop('parent_comment_id', None)
    context.user_data.pop('parent_author_id', None)
    
    return ConversationHandler.END

# UPDATED: Comment cancel with main menu
async def comment_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text("Cancelled.", reply_markup=MAIN_REPLY_KEYBOARD)
    else:
        await update.message.reply_text("Cancelled.", reply_markup=MAIN_REPLY_KEYBOARD)
    
    context.user_data.pop('current_conf_id', None)
    context.user_data.pop('parent_comment_id', None)
    context.user_data.pop('parent_author_id', None)
    
    return ConversationHandler.END

# Profile command and handlers (existing but with main menu improvements)
async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Profile command"""
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    follow_counts = get_follow_counts(user_id)
    confessions_count = get_user_confessions_count(user_id)
    
    profile_text = (
        f"👤 *Profile*\n\n"
        f"{profile['nickname'] or 'Anonymous'}\n\n"
        f"⚡️ Aura: {profile['aura_points']}\n"
        f"👤 Followers: {follow_counts['followers']} | Following: {follow_counts['following']}\n"
        f"     Confessions: {confessions_count}\n\n"
        f"Department: {profile['department'] or 'Not specified'}\n"
        f"Bio: {profile['bio'] or 'No bio set'}"
    )
    
    await update.message.reply_text("Loading Profile...", reply_markup=ReplyKeyboardRemove())
    
    await update.message.reply_text(
        profile_text,
        reply_markup=PROFILE_MAIN_KEYBOARD,
        parse_mode="Markdown"
    )

# UPDATED: Profile callback handler with My Chats functionality
async def profile_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Profile callback handler"""
    query = update.callback_query
    data = query.data
    await query.answer()
    
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    
    if data == "profile_edit":
        # Edit Profile layout
        profile_text = (
            "👤 *Profile Customization*\n\n"
            "Here you can change your public appearance in the bot.\n\n"
            f"Nickname: {profile['nickname'] or 'Anonymous'}\n"
            f"Bio: {profile['bio'] or 'No bio set'}\n"
            f"Department: {profile['department'] or 'Not specified'}\n\n"
            "Use the buttons below to customize your profile."
        )
        
        await query.edit_message_text(
            profile_text,
            reply_markup=PROFILE_EDIT_KEYBOARD,
            parse_mode="Markdown"
        )
        
    elif data == "profile_main":
        # Return to main profile view
        follow_counts = get_follow_counts(user_id)
        confessions_count = get_user_confessions_count(user_id)
        
        profile_text = (
            f"👤 *Profile*\n\n"
            f"{profile['nickname'] or 'Anonymous'}\n\n"
            f"⚡️ Aura: {profile['aura_points']}\n"
            f"👤 Followers: {follow_counts['followers']} | Following: {follow_counts['following']}\n"
            f"     Confessions: {confessions_count}\n\n"
            f"Department: {profile['department'] or 'Not specified'}\n"
            f"Bio: {profile['bio'] or 'No bio set'}"
        )
        
        await query.edit_message_text(
            profile_text,
            reply_markup=PROFILE_MAIN_KEYBOARD,
            parse_mode="Markdown"
        )
    
    elif data == "profile_change_nickname":
        await query.edit_message_text(
            "✏️ *Change Nickname*\n\n"
            "Please send your new nickname (max 32 characters):\n\n"
            "Send /cancel to abort.",
            parse_mode="Markdown"
        )
        return WAITING_FOR_NICKNAME_EDIT
        
    elif data == "profile_set_bio":
        await query.edit_message_text(
            "📝 *Set/Update Bio*\n\n"
            "Please send your new bio (max 256 characters):\n\n"
            "Send /cancel to abort.",
            parse_mode="Markdown"
        )
        return WAITING_FOR_BIO_EDIT
        
    elif data == "profile_edit_department":
        await query.edit_message_text(
            "🏢 *Edit Department*\n\n"
            "Please send your department or field of study:\n\n"
            "Send /cancel to abort.",
            parse_mode="Markdown"
        )
        return WAITING_FOR_DEPARTMENT_EDIT
        
    elif data == "profile_my_confessions":
        confessions = get_user_confessions(user_id, limit=10)
        
        if not confessions:
            text = "📝 *My Confessions*\n\nYou haven't submitted any confessions yet."
        else:
            text = "📝 *My Confessions*\n\n"
            for conf in confessions:
                status_emoji = "✅" if conf['status'] == 'approved' else "⏳" if conf['status'] == 'pending' else "❌"
                date = datetime.utcfromtimestamp(conf['created_at']).strftime("%Y-%m-%d")
                preview = conf['content'][:50] + "..." if len(conf['content']) > 50 else conf['content']
                text += f"{status_emoji} *Confession #{conf['id']}* ({date})\n{preview}\n\n"
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Profile", callback_data="profile_main")]
            ]),
            parse_mode="Markdown"
        )
        
    elif data == "profile_my_comments":
        comments = get_user_comments(user_id, limit=10)
        
        if not comments:
            text = "💬 *My Comments*\n\nYou haven't made any comments yet."
        else:
            text = "💬 *My Comments*\n\n"
            for comment in comments:
                date = datetime.utcfromtimestamp(comment['created_at']).strftime("%Y-%m-%d")
                preview = comment['content'][:50] + "..." if len(comment['content']) > 50 else comment['content']
                conf_preview = comment['conf_content'][:30] + "..." if len(comment['conf_content']) > 30 else comment['conf_content']
                text += f"💬 *On Confession #{comment['conf_id']}* ({date})\n\"{preview}\"\n\n"
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Profile", callback_data="profile_main")]
            ]),
            parse_mode="Markdown"
        )
        
    elif data == "profile_following":
        following = get_following_users(user_id)
        
        if not following:
            text = "👥 *Following*\n\nYou are not following anyone yet."
        else:
            text = "👥 *Following*\n\n"
            for user in following:
                text += f"👤 {user['nickname'] or 'Anonymous'}\n"
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Profile", callback_data="profile_main")]
            ]),
            parse_mode="Markdown"
        )
        
    elif data == "profile_followers":
        followers = get_follower_users(user_id)
        
        if not followers:
            text = "👥 *Followers*\n\nYou don't have any followers yet."
        else:
            text = "👥 *Followers*\n\n"
            for user in followers:
                text += f"👤 {user['nickname'] or 'Anonymous'}\n"
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Profile", callback_data="profile_main")]
            ]),
            parse_mode="Markdown"
        )
        
    elif data == "profile_my_chats":
        # NEW: My Chats functionality
        active_chats = get_active_chats_for_user(user_id)
        
        if not active_chats:
            text = "💬 *My Chats*\n\nYou don't have any active chats yet."
            keyboard = [[InlineKeyboardButton("🔙 Back to Profile", callback_data="profile_main")]]
        else:
            text = "💬 *My Chats*\n\nSelect a chat to view the history and send a message."
            keyboard = []
            for chat in active_chats:
                keyboard.append([
                    InlineKeyboardButton(
                        f"👤 {chat['other_user_nickname']}", 
                        callback_data=f"start_chat:{chat['other_user_id']}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("🔙 Back to Profile", callback_data="profile_main")])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        
    elif data == "profile_settings":
        await query.edit_message_text(
            "⚙️ *Feature Under Development*\n\n"
            "This feature is currently being worked on and will be available soon!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Profile", callback_data="profile_main")]
            ])
        )

# UPDATED: Profile editing with main menu return
async def profile_bio_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle bio editing"""
    text = update.message.text.strip()
    
    if len(text) > 256:
        await update.message.reply_text("❌ Bio is too long (max 256 characters). Please try again:")
        return WAITING_FOR_BIO_EDIT
    
    update_user_profile(update.effective_user.id, bio=text)
    
    await update.message.reply_text(
        "✅ Bio updated successfully!",
        reply_markup=MAIN_REPLY_KEYBOARD
    )
    
    return ConversationHandler.END

async def profile_nickname_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle nickname editing"""
    text = update.message.text.strip()
    
    if len(text) > 32:
        await update.message.reply_text("❌ Nickname is too long (max 32 characters). Please try again:")
        return WAITING_FOR_NICKNAME_EDIT
    
    update_user_profile(update.effective_user.id, nickname=text)
    
    await update.message.reply_text(
        "✅ Nickname updated successfully!",
        reply_markup=MAIN_REPLY_KEYBOARD
    )
    
    return ConversationHandler.END

async def profile_department_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle department editing"""
    text = update.message.text.strip()
    
    update_user_profile(update.effective_user.id, department=text)
    
    await update.message.reply_text(
        "✅ Department updated successfully!",
        reply_markup=MAIN_REPLY_KEYBOARD
    )
    
    return ConversationHandler.END

async def profile_edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel profile editing"""
    await update.message.reply_text(
        "❌ Profile editing cancelled.",
        reply_markup=MAIN_REPLY_KEYBOARD
    )
    return ConversationHandler.END

# Help system
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 *WRU Confessions Bot Help*\n\n"
        "Welcome to the confession bot! Here are the main commands:\n\n"
        "• /confess - Submit a new anonymous confession\n"
        "• /profile - View your profile and history\n"  
        "• /start - Show the welcome message\n"
        "• /help - Display this help message\n\n"
        "*Interact with comments using the buttons:*\n"
        "• *Like/Dislike* - Show appreciation or disagreement\n"
        "• *Reply* - Respond to comments with text, photos, or documents\n"
        "• *Request Contact* - Ask to contact a commenter\n\n"
        "Need more info? Use the buttons below:"
    )
    
    await update.message.reply_text("Loading Help...", reply_markup=ReplyKeyboardRemove())
    
    await update.message.reply_text(
        help_text,
        reply_markup=HELP_KEYBOARD,
        parse_mode="Markdown"
    )

async def help_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help callback handler"""
    query = update.callback_query
    data = query.data
    await query.answer()
    
    if data == "help_rules":
        rules_text = (
            "📜 *Community Guidelines*\n\n"
            "To maintain a positive and respectful environment, please follow these rules:\n\n"
            "1. *Stay On Topic:* This platform is intended for sharing personal confessions and experiences.\n"
            "   - Refrain from posting general questions that can be answered through simple searches.\n"
            "   - Student-related inquiries may be allowed if they provide value to the community.\n\n"
            "2. *Respectful Dialogue:* When discussing sensitive subjects, maintain courtesy and understanding.\n\n"
            "3. *No Harmful Content:* While mentioning names is permitted, you assume responsibility for any consequences.\n"
            "   - The platform and administrators are not liable for outcomes resulting from your posts.\n"
            "   - Name removal requests from mentioned individuals will be honored.\n\n"
            "4. *Privacy Protection:* Do not share personal identification details about yourself or others.\n\n"
            "5. *Positive Environment:* Share authentic experiences and avoid spam, harassment, or repetitive posts.\n\n"
            "This space is for meaningful connection and sharing, not for spreading misinformation or creating conflict."
        )
        await query.edit_message_text(
            rules_text,
            parse_mode="Markdown",
            reply_markup=HELP_KEYBOARD
        )
        
    elif data == "help_contact_admin":
        await help_contact_admin_callback(update, context)
        return WAITING_FOR_ADMIN_MESSAGE
        
    elif data == "help_privacy":
        privacy_text = (
            "🔒 *Data Privacy Information*\n\n"
            "• Your Telegram User ID is stored for operational purposes but remains confidential from other users.\n"
            "• Publicly visible information includes your chosen Nickname, Bio content, and accumulated Aura points.\n"
            "• You have control over which additional profile details (such as Department) are displayed.\n"
            "• Other users can send follow requests or chat invitations, requiring your approval for communication.\n"
            "• When reporting content, your User ID is linked to the report for administrative review purposes only.\n"
            "• Platform administrators may access stored User IDs exclusively for moderation and user support activities."
        )
        await query.edit_message_text(
            privacy_text,
            parse_mode="Markdown",
            reply_markup=HELP_KEYBOARD
        )

async def pending_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to check pending confessions"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM confessions WHERE status = 'pending'")
    count = cur.fetchone()[0]
    conn.close()
    
    await update.message.reply_text(f"🔎 Pending confessions: {count}")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles unknown commands."""
    if update.effective_message.text.startswith('/'):
        await update.effective_message.reply_text("Sorry, I don't know that command.", reply_markup=MAIN_REPLY_KEYBOARD)

# Add this command handler function with your other command functions

async def force_restore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual command to force database restoration from Dropbox"""
    user_id = update.effective_user.id
    # ⚠️ CHANGE THIS TO YOUR ACTUAL TELEGRAM USER ID
    ADMIN_ID = 7300957726  # Replace with your actual user ID from @userinfobot
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ This command is for admin only.")
        return
        
    await update.message.reply_text("🔄 Forcing database restoration from Dropbox...")
    
    # Run the restoration in a thread to avoid blocking
    def restore_thread():
        success = restore_database_from_dropbox()
        if success:
            # Use context to send message from background thread
            context.application.create_task(
                update.message.reply_text("✅ Database restoration completed! Bot will work properly now.")
            )
        else:
            context.application.create_task(
                update.message.reply_text("❌ Database restoration failed! Check logs for details.")
            )
    
    thread = threading.Thread(target=restore_thread)
    thread.start()

# ----------------- Main Function -----------------

def main():
    """Start the bot."""
    
    # Initialize backup system
    backup_on_startup()
    schedule_backups()
    
    init_db()
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing.")
        return
    application = Application.builder().token(BOT_TOKEN).build()

    # Confession Conversation Handler
    confession_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & filters.Regex("^📝 Confess$"), confess_command),
            CommandHandler("confess", confess_command)
        ],
        states={
            WAITING_FOR_CONFESSION: [
                MessageHandler(
                    (filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND & ~filters.Regex("^(❌ Cancel|🏠 Main Menu)$"), 
                    confession_receive
                ),
            ],
            WAITING_FOR_CATEGORIES: [
                CallbackQueryHandler(category_selection_callback, pattern=f"^{CB_CAT_PATTERN}"),
                CallbackQueryHandler(category_selection_callback, pattern=f"^{CB_CAT_DONE}$"),
            ],
            WAITING_FOR_REVIEW: [
                CallbackQueryHandler(confession_review_callback, pattern="^confess_action:"),
            ]
        },
        fallbacks=[
            CommandHandler("cancel", confession_cancel_fallback),
            MessageHandler(filters.Regex("^(❌ Cancel|🏠 Main Menu)$"), confession_cancel_fallback),
        ],
        per_user=True,      
        allow_reentry=True,  
    )
    application.add_handler(confession_conv_handler)
    
    # Profile Editing Conversation Handler
    profile_edit_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(profile_callback_handler, pattern="^profile_change_nickname$"),
            CallbackQueryHandler(profile_callback_handler, pattern="^profile_set_bio$"),
            CallbackQueryHandler(profile_callback_handler, pattern="^profile_edit_department$"),
        ],
        states={
            WAITING_FOR_BIO_EDIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, profile_bio_edit),
            ],
            WAITING_FOR_NICKNAME_EDIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, profile_nickname_edit),
            ],
            WAITING_FOR_DEPARTMENT_EDIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, profile_department_edit),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", profile_edit_cancel),
        ],
        per_user=True,
        allow_reentry=True,
    )
    application.add_handler(profile_edit_conv_handler)
    
    # UPDATED: Comment Conversation Handler with media support
    comment_reply_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(comment_menu_button_callback, pattern=f"^{CB_START_COMMENT}:"),
            CallbackQueryHandler(comment_interaction_callback, pattern="^reply:"),
            CallbackQueryHandler(comment_menu_callback, pattern="^comment_add:"),
        ],
        states={
            WAITING_FOR_COMMENT: [
                CommandHandler("cancel", comment_cancel_callback),
                MessageHandler(filters.Regex("^(❌ Cancel|🏠 Main Menu)$"), comment_cancel_callback),
                MessageHandler(
                    (filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND, 
                    comment_receive
                ),
            ],
            WAITING_FOR_REPLY: [
                CommandHandler("cancel", comment_cancel_callback),
                MessageHandler(filters.Regex("^(❌ Cancel|🏠 Main Menu)$"), comment_cancel_callback),
                MessageHandler(
                    (filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND, 
                    reply_receive
                ),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", comment_cancel_callback),
            MessageHandler(filters.Regex("^(❌ Cancel|🏠 Main Menu)$"), comment_cancel_callback)
        ],
        per_user=True,      
        allow_reentry=True,  
    )
    application.add_handler(comment_reply_conv_handler)
    
    # Report Conversation Handler
    report_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(comment_interaction_callback, pattern="^report_user:"),
            MessageHandler(filters.TEXT & filters.Regex("^Report$"), report_reason_callback),
        ],
        states={
            WAITING_FOR_REPORT_REASON: [
                CallbackQueryHandler(report_reason_callback, pattern="^report_reason:"),
            ],
            WAITING_FOR_CUSTOM_REPORT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, custom_report_reason),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", comment_cancel_callback),
        ],
        per_user=True,
        allow_reentry=True,
    )
    application.add_handler(report_conv_handler)
    
    # Chat Conversation Handler
    chat_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(comment_interaction_callback, pattern="^request_chat:"),
            CallbackQueryHandler(chat_request_response, pattern="^(chat_accept:|chat_decline:)"),
            CallbackQueryHandler(comment_interaction_callback, pattern="^start_chat:"),
        ],
        states={
            WAITING_FOR_CHAT_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, chat_message_handler),
                CommandHandler("leavechat", leave_chat),
            ],
        },
        fallbacks=[
            CommandHandler("leavechat", leave_chat),
        ],
        per_user=True,
        allow_reentry=True,
    )
    application.add_handler(chat_conv_handler)
    
    # NEW: Admin Message Conversation Handler
    admin_message_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(help_contact_admin_callback, pattern="^help_contact_admin$"),
        ],
        states={
            WAITING_FOR_ADMIN_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_message_receive),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", admin_message_cancel),
            MessageHandler(filters.Regex("^(❌ Cancel|🏠 Main Menu)$"), admin_message_cancel),
        ],
        per_user=True,
        allow_reentry=True,
    )
    application.add_handler(admin_message_conv_handler)
    
# Other Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("leavechat", leave_chat))
    application.add_handler(CallbackQueryHandler(menu_callback_handler, pattern=f"^{CB_ACCEPT}$"))
    application.add_handler(CallbackQueryHandler(comment_page_callback, pattern="^comment_page:"))
    application.add_handler(CallbackQueryHandler(comment_menu_callback, pattern="^comment_view:"))
    application.add_handler(CallbackQueryHandler(comment_interaction_callback, pattern="^(vote:|follow_user:|back_to_comments)"))
    application.add_handler(CallbackQueryHandler(chat_request_response, pattern="^(chat_accept:|chat_decline:)"))
    application.add_handler(CallbackQueryHandler(admin_action_callback, pattern=f"^{CB_APPROVE_PATTERN}"))
    application.add_handler(CallbackQueryHandler(admin_action_callback, pattern=f"^{CB_REJECT_PATTERN}"))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📊 Profile$"), profile_command))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^❓ Help$"), help_command))
    application.add_handler(CallbackQueryHandler(profile_callback_handler, pattern="^profile_"))
    application.add_handler(CallbackQueryHandler(help_callback_handler, pattern="^help_"))
    application.add_handler(CallbackQueryHandler(secondary_callback_handler, pattern=f"^{CB_MENU_MAIN}$"))
    application.add_handler(CommandHandler("pending", pending_count, filters=filters.Chat(chat_id=ADMIN_GROUP_ID)))
    application.add_handler(CommandHandler("forcerestore", force_restore))  # Your new line
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    
    logger.info("Bot started and polling...")  # ⬅️ ADD 4 SPACES AT THE BEGINNING
    application.run_polling(allowed_updates=Update.ALL_TYPES)  # ⬅️ ADD 4 SPACES AT THE BEGINNING

if __name__ == "__main__":
    main()
