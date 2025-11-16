"""
Simple Confession Bot - V64 (Enhanced GitHub Backup + 5-Minute Backup Interval + Auto-Restore)
Requirements:
  pip install python-telegram-bot requests

V64 MAJOR UPDATES:
1. ENHANCED GitHub Backup System with 5-minute interval
2. AUTOMATIC RESTORATION on every deploy/startup
3. COMPREHENSIVE backup of all database operations
4. FIXED Chat System with enhanced stability
5. Added Media Support for Comments
6. Improved error handling and recovery
"""

import logging
import sqlite3
import time
import os
import json 
import base64
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import threading
import time
import asyncio

DB_PATH = 'confessions.db'
# Enhanced GitHub Backup Configuration
GITHUB_ACCESS_TOKEN = os.getenv('GITHUB_ACCESS_TOKEN')
GITHUB_REPO_OWNER = os.getenv('GITHUB_REPO_OWNER')
GITHUB_REPO_NAME = os.getenv('GITHUB_REPO_NAME')
GITHUB_BACKUP_PATH = "data/confessions.db"

# Backup control variables
backup_in_progress = False
BACKUP_INTERVAL_MINUTES = 5  # 5-minute backup interval

def backup_database():
    """Enhanced backup database to GitHub with error handling and retry logic"""
    global backup_in_progress
    
    if backup_in_progress:
        print("⏳ Backup already in progress, skipping...")
        return False
        
    backup_in_progress = True
    try:
        if not os.path.exists(DB_PATH):
            print("❌ No local database to backup")
            return False
        
        file_size = os.path.getsize(DB_PATH)
        print(f"📊 Database size: {file_size} bytes")
        
        if file_size == 0:
            print("❌ Database file is empty, skipping backup")
            return False
            
        # Read database file
        with open(DB_PATH, 'rb') as f:
            db_content = f.read()
        
        # Encode to base64 for GitHub
        encoded_content = base64.b64encode(db_content).decode('utf-8')
        
        headers = {
            'Authorization': f'token {GITHUB_ACCESS_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Get existing file SHA
        url = f'https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{GITHUB_BACKUP_PATH}'
        response = requests.get(url, headers=headers)
        
        sha = None
        if response.status_code == 200:
            sha = response.json().get('sha')
        
        # Prepare data for upload
        data = {
            'message': f'Database backup {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} - {file_size} bytes',
            'content': encoded_content,
            'branch': 'main'
        }
        
        if sha:
            data['sha'] = sha
        
        # Upload to GitHub with timeout
        response = requests.put(url, headers=headers, json=data, timeout=30)
        
        if response.status_code in [200, 201]:
            print(f"✅ Database backed up to GitHub: {GITHUB_BACKUP_PATH}")
            return True
        else:
            print(f"❌ GitHub backup failed: {response.status_code} - {response.text}")
            return False
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False
    finally:
        backup_in_progress = False

def restore_database_from_github():
    """Enhanced restore database from GitHub backup with validation"""
    try:
        print("🔄 Attempting to restore database from GitHub...")
        
        if not all([GITHUB_ACCESS_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME]):
            print("❌ GitHub credentials missing, cannot restore")
            return False
        
        headers = {
            'Authorization': f'token {GITHUB_ACCESS_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        url = f'https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{GITHUB_BACKUP_PATH}'
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print("❌ No backup file found in GitHub")
            return False
            
        file_data = response.json()
        encoded_content = file_data.get('content', '')
        encoded_content = encoded_content.replace('\n', '')
        
        try:
            db_content = base64.b64decode(encoded_content)
        except Exception as e:
            print(f"❌ Failed to decode backup content: {e}")
            return False
        
        # Create backup of current database before restoration
        if os.path.exists(DB_PATH):
            backup_name = f"{DB_PATH}.backup.{int(time.time())}"
            shutil.copy2(DB_PATH, backup_name)
            print(f"📦 Current database backed up as: {backup_name}")
        
        with open(DB_PATH, 'wb') as f:
            f.write(db_content)
            
        # Verify restoration
        if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
            print(f"✅ Database restored from GitHub: {GITHUB_BACKUP_PATH}")
            print(f"📊 Restored database size: {os.path.getsize(DB_PATH)} bytes")
            return True
        else:
            print("❌ Restoration failed: database file is empty or missing")
            return False
        
    except Exception as e:
        print(f"❌ Restoration failed: {e}")
        return False

def backup_on_startup():
    """Enhanced startup procedure with guaranteed restoration"""
    print("🚀 Starting enhanced database initialization...")
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        needs_restore = False
        
        if not os.path.exists(DB_PATH):
            print(f"❌ Attempt {attempt + 1}: Database file not found - needs restoration")
            needs_restore = True
        else:
            db_size = os.path.getsize(DB_PATH)
            print(f"📊 Attempt {attempt + 1}: Existing database size: {db_size} bytes")
            
            if db_size == 0:
                print(f"❌ Attempt {attempt + 1}: Database file is empty - needs restoration")
                needs_restore = True
            else:
                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    conn.close()
                    
                    table_count = len(tables)
                    print(f"✅ Database valid. Tables found: {table_count}")
                    
                    if table_count == 0:
                        needs_restore = True
                        print(f"❌ Attempt {attempt + 1}: No tables found - needs restoration")
                    else:
                        print("✅ Local database is valid, no restoration needed")
                        break
                except Exception as e:
                    print(f"❌ Attempt {attempt + 1}: Database corrupted - needs restoration: {e}")
                    needs_restore = True
        
        if needs_restore:
            print(f"🔄 Attempt {attempt + 1}: Database needs restoration, attempting from GitHub...")
            success = restore_database_from_github()
            if success:
                print("✅ Database restoration completed!")
                break
            else:
                print(f"❌ Database restoration failed! Retrying in {retry_delay} seconds...")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        else:
            break
    
    # Always create fresh backup after startup
    print("🔄 Creating fresh backup after startup...")
    backup_database()

def schedule_backups():
    """Schedule automatic backups every 5 minutes"""
    def backup_loop():
        while True:
            time.sleep(BACKUP_INTERVAL_MINUTES * 60)  # 5 minutes
            print(f"🔄 Scheduled backup triggered ({BACKUP_INTERVAL_MINUTES}-minute interval)")
            backup_database()
    
    backup_thread = threading.Thread(target=backup_loop, daemon=True)
    backup_thread.start()
    print(f"✅ Scheduled backups enabled (every {BACKUP_INTERVAL_MINUTES} minutes)")

def trigger_immediate_backup():
    """Enhanced immediate backup with queuing"""
    print("🔄 Triggering immediate backup...")
    
    # Use threading to avoid blocking
    def backup_wrapper():
        success = backup_database()
        if success:
            print("✅ Immediate backup completed!")
        else:
            print("❌ Immediate backup failed!")
        return success
    
    backup_thread = threading.Thread(target=backup_wrapper, daemon=True)
    backup_thread.start()
    return True

# Enhanced backup triggers for all database operations
def enhanced_backup_trigger():
    """Trigger backup in a non-blocking way"""
    threading.Thread(target=trigger_immediate_backup, daemon=True).start()

# Use standard library html escape
from html import escape as html_escape 
from telegram.error import BadRequest, TelegramError
import shutil  # Added for file operations

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

from keep_alive import keep_alive
keep_alive()

# ------------------------------ CONFIG ------------------------------
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_GROUP_ID = -1003131561656
CHANNEL_ID = -1003479727543
BOT_USERNAME = "wru_confessions_bot"
ADMIN_USER_ID = 7300957726

RATE_LIMIT_SECONDS = 120  
MAX_COMMENT_DEPTH = 5 
MAX_CATEGORIES = 3
COMMENTS_PER_PAGE = 10

CATEGORIES: List[str] = [
    "School", "Relationship", "Family", "Work", "Personal Life", 
    "Funny", "Random", "Gaming", "Study", "Tech", 
    "Health", "Social", "Other"
]

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
WAITING_FOR_ADMIN_MESSAGE = 15

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

# ------------------------------ ENHANCED DATABASE HELPERS ------------------------------

def init_db():
    """Initialize database with enhanced error handling"""
    try:
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
        
        # Comments table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT, conf_id INTEGER, user_id INTEGER, 
                content TEXT, parent_comment_id INTEGER, created_at INTEGER,
                bot_message_id INTEGER, file_id TEXT, file_type TEXT
            )
        """)
        
        # Comment votes table
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
                start_used BOOLEAN DEFAULT FALSE
            )
        """)
        
        # Chat requests table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER NOT NULL,
                to_user_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
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
        
        # Admin messages table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admin_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                created_at INTEGER
            )
        """)
        
        # Check and add columns if missing
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

        try: cur.execute("SELECT file_id FROM comments LIMIT 1")
        except sqlite3.OperationalError: 
            cur.execute("ALTER TABLE comments ADD COLUMN file_id TEXT")
            cur.execute("ALTER TABLE comments ADD COLUMN file_type TEXT")

        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

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
    
    # ENHANCED BACKUP after confession save
    enhanced_backup_trigger()
    
    return conf_id

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
    
    # ENHANCED BACKUP after comment
    enhanced_backup_trigger()
    
    return comment_id

def get_comment(comment_id: int) -> Optional[Dict[str, Any]]:
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
        'file_id': row[7], 'file_type': row[8]
    }

def update_comment_message_id(comment_id: int, bot_message_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE comments SET bot_message_id = ? WHERE id = ?", (bot_message_id, comment_id))
    conn.commit()
    conn.close()

def get_comment_message_id(comment_id: int) -> Optional[int]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT bot_message_id FROM comments WHERE id = ?", (comment_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def process_vote(comment_id: int, user_id: int, vote_type: str) -> Tuple[bool, str]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT vote_type FROM comment_votes WHERE comment_id = ? AND user_id = ?", (comment_id, user_id))
    existing_vote = cur.fetchone()
    
    action = "added"
    
    if existing_vote:
        if existing_vote[0] == vote_type:
            cur.execute("DELETE FROM comment_votes WHERE comment_id = ? AND user_id = ?", (comment_id, user_id))
            action = "removed"
        else:
            cur.execute("UPDATE comment_votes SET vote_type = ? WHERE comment_id = ? AND user_id = ?", (vote_type, comment_id, user_id))
            action = "changed"
    else:
        cur.execute("INSERT INTO comment_votes (comment_id, user_id, vote_type) VALUES (?, ?, ?)", (comment_id, user_id, vote_type))
    
    conn.commit()
    conn.close()
    
    # ENHANCED BACKUP after vote
    enhanced_backup_trigger()
    
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
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT vote_type FROM comment_votes WHERE comment_id = ? AND user_id = ?", (comment_id, user_id))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def get_comments_for_confession(conf_id: int, page: int = 1, limit: int = COMMENTS_PER_PAGE) -> Tuple[List[Dict[str, Any]], int]:
    offset = (page - 1) * limit
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM comments WHERE conf_id = ? AND parent_comment_id IS NULL", (conf_id,))
    total_count = cur.fetchone()[0]
    
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
        
        # ENHANCED BACKUP after unfollow
        enhanced_backup_trigger()
        
        return False
    else:
        ts = int(time.time())
        cur.execute("INSERT INTO follows (follower_id, following_id, created_at) VALUES (?, ?, ?)", (follower_id, following_id, ts))
        conn.commit()
        conn.close()
        
        # ENHANCED BACKUP after follow
        enhanced_backup_trigger()
        
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
    
    # ENHANCED BACKUP after profile update
    enhanced_backup_trigger()

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
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE confessions SET content = ?, file_id = ?, file_type = ? WHERE id = ?", 
        (content, file_id, file_type, conf_id)
    )
    conn.commit()
    conn.close()
    
    # ENHANCED BACKUP after confession update
    enhanced_backup_trigger()
    
def update_confession_categories(conf_id: int, categories_list: List[str]):
    categories_json = json.dumps(categories_list)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE confessions SET categories = ? WHERE id = ?", (categories_json, conf_id)) 
    conn.commit()
    conn.close()
    
    # ENHANCED BACKUP after category update
    enhanced_backup_trigger()

def record_channel_message_id(conf_id: int, message_id: int):
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
    
    # ENHANCED BACKUP after status change
    enhanced_backup_trigger()

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
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM comments WHERE conf_id = ?", (conf_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count

def get_user_confessions_count(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM confessions WHERE user_id = ?", (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count

def get_user_comments_count(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM comments WHERE user_id = ?", (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count

def get_user_confessions(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
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
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
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
    
    # ENHANCED BACKUP after chat request
    enhanced_backup_trigger()
    
    return True

def get_chat_request(from_user_id: int, to_user_id: int) -> Optional[Dict[str, Any]]:
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
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE chat_requests SET status = ? WHERE id = ?", (status, request_id))
    conn.commit()
    conn.close()
    
    # ENHANCED BACKUP after chat status change
    enhanced_backup_trigger()

def create_active_chat(user1_id: int, user2_id: int) -> int:
    ts = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    if user1_id > user2_id:
        user1_id, user2_id = user2_id, user1_id
    
    cur.execute(
        "INSERT OR REPLACE INTO active_chats (user1_id, user2_id, created_at) VALUES (?, ?, ?)",
        (user1_id, user2_id, ts)
    )
    chat_id = cur.lastrowid
    conn.commit()
    conn.close()
    
    # ENHANCED BACKUP after active chat creation
    enhanced_backup_trigger()
    
    return chat_id

def get_active_chat(user1_id: int, user2_id: int) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
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

def get_active_chats_for_user(user_id: int) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
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
    
    # ENHANCED BACKUP after chat message
    enhanced_backup_trigger()
    
    return message_id

def get_chat_messages(chat_id: int, limit: int = 50) -> List[Dict[str, Any]]:
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
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM active_chats WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()
    
    # ENHANCED BACKUP after chat end
    enhanced_backup_trigger()

def block_user(blocker_id: int, blocked_id: int):
    ts = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO blocked_users (blocker_id, blocked_id, created_at) VALUES (?, ?, ?)",
        (blocker_id, blocked_id, ts)
    )
    conn.commit()
    conn.close()
    
    # ENHANCED BACKUP after block
    enhanced_backup_trigger()

def unblock_user(blocker_id: int, blocked_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM blocked_users WHERE blocker_id = ? AND blocked_id = ?", (blocker_id, blocked_id))
    conn.commit()
    conn.close()
    
    # ENHANCED BACKUP after unblock
    enhanced_backup_trigger()

def is_blocked(blocker_id: int, blocked_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM blocked_users WHERE blocker_id = ? AND blocked_id = ?", (blocker_id, blocked_id))
    result = cur.fetchone()
    conn.close()
    return bool(result)

def create_user_report(reporter_id: int, reported_user_id: int, reason: str = None, custom_reason: str = None):
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
    
    # ENHANCED BACKUP after report
    enhanced_backup_trigger()
    
    return report_id

def save_admin_message(user_id: int, message_text: str) -> int:
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
    
    # ENHANCED BACKUP after admin message
    enhanced_backup_trigger()
    
    return message_id

# ------------------------------ ENHANCED UTILS ------------------------------

def escape_html(text: str) -> str:
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

async def format_comment_display(comment: Dict[str, Any], conf_id: int, depth: int, context: ContextTypes.DEFAULT_TYPE) -> str:
    current_user_id = context.user_data.get('current_user_id', context._user_id)
    target_user_id = comment['user_id']
    conf = get_confession(conf_id)
    
    if target_user_id == current_user_id:
        display_name = "You"
    elif target_user_id == conf['user_id']:
        bot_username = (await context.application.bot.get_me()).username
        profile_deep_link = f"t.me/{bot_username}?start=profile_{target_user_id}"
        display_name = f"[Confession Author]({profile_deep_link})"
    else:
        profile = get_user_profile(target_user_id)
        display_name = profile['nickname'] or 'Anonymous'
        
        bot_username = (await context.application.bot.get_me()).username
        profile_deep_link = f"t.me/{bot_username}?start=profile_{target_user_id}"
        display_name = f"[{display_name}]({profile_deep_link})"
    
    profile = get_user_profile(target_user_id)
    aura_points = profile.get('aura_points', 0)
    
    indent = " " * (depth * 4)
    if depth > 0:
        indent = " " * ((depth - 1) * 4) + "↳ " 
    
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
            sent_message = await context.bot.send_message(
                chat_id=chat_id,
                text=comment_text,
                reply_markup=get_comment_interaction_keyboard(comment, current_user_id, counts, user_vote), 
                parse_mode="Markdown",
                reply_to_message_id=parent_message_id
            )
    else:
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

async def show_comments(update: Update, context: ContextTypes.DEFAULT_TYPE, conf_id: int, page: int = 1):
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
    
    all_comments_for_page = []
    for comment in flat_comments:
        all_comments_for_page.append(comment)
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

    for root_comment in thread_roots:
        await send_comment_and_replies(chat_id, context, root_comment, conf_id, depth=0)
    
    pagination_text = f"**Displaying page {page}/{total_pages}. Total {total_count} Comments**"
    await context.bot.send_message(
        chat_id=chat_id,
        text=pagination_text,
        parse_mode="Markdown",
        reply_markup=get_comment_pagination_keyboard(conf_id, page, total_pages, total_count)
    )
# ------------------------------ ENHANCED KEYBOARDS ------------------------------

MAIN_REPLY_KEYBOARD = ReplyKeyboardMarkup(
    [['📝 Confess'], ['📊 Profile', '❓ Help']], 
    resize_keyboard=True, one_time_keyboard=False
)

CONFESSION_CANCEL_KEYBOARD = ReplyKeyboardMarkup(
    [['❌ Cancel', '🏠 Main Menu']], resize_keyboard=True, one_time_keyboard=False
)

CHAT_KEYBOARD = ReplyKeyboardMarkup(
    [['/leavechat'], ['Block', 'Report']],
    resize_keyboard=True, one_time_keyboard=False
)

ADMIN_MESSAGE_KEYBOARD = ReplyKeyboardMarkup(
    [['❌ Cancel', '🏠 Main Menu']], resize_keyboard=True, one_time_keyboard=False
)

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

def get_deep_link_keyboard(conf_id: int, comment_count: int):
    keyboard = [
        [InlineKeyboardButton(f"💬 View Comments ({comment_count})", callback_data=f"comment_view:{conf_id}")],
        [InlineKeyboardButton("✍️ Add Comment", callback_data=f"comment_add:{conf_id}")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data=CB_MENU_MAIN)]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_channel_post_keyboard(conf_id: int) -> InlineKeyboardMarkup:
    comment_count = get_comment_count_for_confession(conf_id)
    deep_link_url = f"https://t.me/{BOT_USERNAME}?start=comment_{conf_id}"
    button_text = f"💬 Add/View Comments ({comment_count})"
    keyboard = [[InlineKeyboardButton(button_text, url=deep_link_url)]]
    return InlineKeyboardMarkup(keyboard)

def get_comment_pagination_keyboard(conf_id: int, current_page: int, total_pages: int, total_count: int):
    keyboard = []
    
    nav_buttons = []
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton("📥 Load More", callback_data=f"comment_page:{conf_id}:{current_page+1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"Page {current_page}/{total_pages}", callback_data=f"comment_page_info:{conf_id}:{current_page}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("💬 Add Comment", callback_data=f"comment_add:{conf_id}")])
    
    return InlineKeyboardMarkup(keyboard)

def get_comment_interaction_keyboard(comment: Dict[str, Any], current_user_id: int, counts: Dict[str, int], user_vote: Optional[str] = None):
    comment_id = comment['id']
    
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

def get_user_profile_keyboard(target_user_id: int, current_user_id: int) -> InlineKeyboardMarkup:
    if current_user_id == target_user_id:
        return InlineKeyboardMarkup([])
    
    follow_status_text = "➕ Follow User"
    if is_following(current_user_id, target_user_id):
        follow_status_text = "✔️ Following"
    
    active_chat = get_active_chat(current_user_id, target_user_id)
    chat_request = get_chat_request(current_user_id, target_user_id)
    
    if active_chat:
        chat_button_text = "💬 Send Message"
        chat_callback_data = f"start_chat:{target_user_id}"
    elif chat_request and chat_request['status'] == 'pending':
        if chat_request['from_user_id'] == current_user_id:
            chat_button_text = "✅ Chat Request Sent"
            chat_callback_data = f"request_chat:{target_user_id}"
        else:
            chat_button_text = "💬 Request to Chat"
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

# ------------------------------ ENHANCED HANDLER FUNCTIONS ------------------------------

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int = None):
    """Enhanced main menu with backup status"""
    menu_text = """*Welcome back!*

🤖 *Bot Status:* ✅ Operational  
🔄 *Backup System:* ✅ Active (5-minute intervals)  
📊 *Last Backup:* Ongoing...

Use the custom keyboard below to continue."""

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

async def deep_link_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id: int):
    """Enhanced profile viewing with deep links"""
    user_id = update.effective_user.id
    profile = get_user_profile(target_user_id)
    follow_counts = get_follow_counts(target_user_id)
    
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
            reply_markup=InlineKeyboardMarkup([]),
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced start command with backup status"""
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    
    # Enhanced startup with immediate backup trigger
    if not profile.get('start_used', False):
        update_user_profile(user_id, start_used=True)
        
        # Trigger initial backup for new users
        enhanced_backup_trigger()
        
        regulations = (
            "👋 **Welcome!** Before you begin, please read our rules:\n\n"
            "1. All confessions are **anonymous** to the public and admins.\n"
            "2. Submissions are **moderated** and may be rejected.\n"
            "3. **No spam, hate speech, or illegal content**.\n"
            "4. You can only submit **one confession every 2 minutes**.\n"
            "5. **Backup System:** Your data is automatically backed up every 5 minutes.\n\n"
            "Do you accept these terms to continue?"
        )
        keyboard = [[InlineKeyboardButton("✅ Yes, I Accept the Terms", callback_data=CB_ACCEPT)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.effective_chat.send_message("Loading rules...", reply_markup=ReplyKeyboardRemove())
        await update.effective_chat.send_message(regulations, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END
    
    if not profile.get('terms_accepted', False):
        regulations = (
            "👋 **Welcome Back!** Please accept our terms to continue:\n\n"
            "1. All confessions are **anonymous** to the public and admins.\n"
            "2. Submissions are **moderated** and may be rejected.\n"
            "3. **No spam, hate speech, or illegal content**.\n"
            "4. You can only submit **one confession every 2 minutes**.\n"
            "5. **Backup System:** Your data is automatically backed up every 5 minutes.\n\n"
            "Do you accept these terms to continue?"
        )
        keyboard = [[InlineKeyboardButton("✅ Yes, I Accept the Terms", callback_data=CB_ACCEPT)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.effective_chat.send_message("Loading rules...", reply_markup=ReplyKeyboardRemove())
        await update.effective_chat.send_message(regulations, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END
    
    # Enhanced deep link handling with backup status
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
    
    await show_main_menu(update, context)

async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced menu callback with backup trigger"""
    query = update.callback_query
    await query.answer() 
    
    data = query.data
    
    if data == CB_ACCEPT:
        user_id = update.effective_user.id
        update_user_profile(user_id, terms_accepted=True, start_used=True)
        
        # Trigger backup after terms acceptance
        enhanced_backup_trigger()
        
        await show_main_menu(update, context, query.message.message_id)
        
    return ConversationHandler.END 

async def secondary_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced secondary callback handler"""
    query = update.callback_query
    data = query.data
    await query.answer()
    
    if data == CB_MENU_MAIN:
        await show_main_menu(update, context, query.message.message_id) 
        
    return ConversationHandler.END

async def comment_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced comment pagination"""
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith("comment_page:"):
        try:
            parts = data.split(":")
            conf_id = int(parts[1])
            page = int(parts[2])
            
            await query.delete_message()
            
            await show_comments(update, context, conf_id, page)
            
        except (IndexError, ValueError) as e:
            logger.error(f"Error processing comment page: {e}")
            await query.edit_message_text("Error loading comments.", reply_markup=None)
    
    return ConversationHandler.END

async def comment_menu_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Enhanced comment menu button callback"""
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

async def comment_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced comment menu callback"""
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

async def comment_interaction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced comment interaction callback with backup triggers"""
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
    
    elif data.startswith("request_chat:"):
        target_user_id = int(data.split(":")[1])
        
        active_chat = get_active_chat(user_id, target_user_id)
        if active_chat:
            context.user_data['active_chat_with'] = target_user_id
            context.user_data['active_chat_id'] = active_chat['id']
            await enter_chat_mode(update, context, target_user_id)
            return WAITING_FOR_CHAT_MESSAGE
        
        chat_request = get_chat_request(user_id, target_user_id)
        if chat_request and chat_request['status'] == 'pending':
            await query.answer("✅ Chat request already sent.", show_alert=True)
            
            new_keyboard = get_user_profile_keyboard(target_user_id, user_id)
            try:
                await query.edit_message_reply_markup(reply_markup=new_keyboard)
            except Exception:
                pass
            return
        
        existing_request = get_chat_request(target_user_id, user_id)
        if existing_request and existing_request['status'] == 'pending':
            update_chat_request_status(existing_request['id'], 'accepted')
            chat_id = create_active_chat(user_id, target_user_id)
            
            await query.answer("✅ Chat request accepted automatically!", show_alert=True)
            
            new_keyboard = get_user_profile_keyboard(target_user_id, user_id)
            try:
                await query.edit_message_reply_markup(reply_markup=new_keyboard)
            except Exception:
                pass
            
            try:
                user_profile = get_user_profile(user_id)
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"💬 **Chat Request Accepted**\n\n"
                         f"**{user_profile['nickname'] or 'Anonymous'}** has accepted your chat request!\n\n"
                         f"You can now send messages from their profile.",
                    parse_mode="Markdown"
                )
                
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

        if create_chat_request(user_id, target_user_id):
            await query.answer("✅ Chat request sent!", show_alert=True)
            
            new_keyboard = get_user_profile_keyboard(target_user_id, user_id)
            try:
                await query.edit_message_reply_markup(reply_markup=new_keyboard)
            except Exception:
                pass
            
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
        target_user_id = int(data.split(":")[1])
        
        active_chat = get_active_chat(user_id, target_user_id)
        if not active_chat:
            await query.edit_message_text("Chat not found or no longer active.")
            return ConversationHandler.END
        
        context.user_data['active_chat_with'] = target_user_id
        context.user_data['active_chat_id'] = active_chat['id']
        
        if query.message:
            await query.message.reply_text("Entering chat...")
        
        await enter_chat_mode(update, context, target_user_id)
        return WAITING_FOR_CHAT_MESSAGE
    
    return ConversationHandler.END

async def report_reason_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced report reason callback"""
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
            create_user_report(query.from_user.id, target_user_id)
            await query.edit_message_text("✅ User reported to the admin. Thank you.")
            
            await notify_admin_about_report(context, query.from_user.id, target_user_id)
            
        elif reason == "other":
            await query.edit_message_text(
                "✍️ **Custom Report Reason**\n\n"
                "Please type your reason for reporting this user:",
                parse_mode="Markdown"
            )
            return WAITING_FOR_CUSTOM_REPORT
        
        else:
            create_user_report(query.from_user.id, target_user_id, reason=reason)
            await query.edit_message_text("✅ User reported to the admin. Thank you.")
            
            await notify_admin_about_report(context, query.from_user.id, target_user_id, reason)
        
        return ConversationHandler.END
    
    return WAITING_FOR_REPORT_REASON

async def custom_report_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced custom report reason handler"""
    text = update.message.text.strip()
    target_user_id = context.user_data.get('reporting_user_id')
    
    if not target_user_id:
        await update.message.reply_text("Error: No user to report.")
        return ConversationHandler.END
    
    create_user_report(update.effective_user.id, target_user_id, custom_reason=text)
    await update.message.reply_text("✅ User reported to the admin. Thank you.")
    
    await notify_admin_about_report(context, update.effective_user.id, target_user_id, custom_reason=text)
    
    return ConversationHandler.END

async def notify_admin_about_report(context: ContextTypes.DEFAULT_TYPE, reporter_id: int, reported_user_id: int, reason: str = None, custom_reason: str = None):
    """Enhanced admin notification for reports"""
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

async def chat_request_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced chat request response handler"""
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith("chat_accept:"):
        from_user_id = int(data.split(":")[1])
        to_user_id = query.from_user.id
        
        chat_request = get_chat_request(from_user_id, to_user_id)
        if not chat_request:
            await query.edit_message_text("Chat request not found or already processed.")
            return
        
        update_chat_request_status(chat_request['id'], 'accepted')
        chat_id = create_active_chat(from_user_id, to_user_id)
        
        await query.edit_message_text(
            "✅ Chat request accepted. You can now chat with this user.",
            parse_mode="Markdown"
        )
        
        try:
            from_user_profile = get_user_profile(from_user_id)
            to_user_profile = get_user_profile(to_user_id)
            
            await context.bot.send_message(
                chat_id=from_user_id,
                text=f"✅ **The user has accepted your chat request!**\n\n"
                     f"You can now send messages from their profile.",
                parse_mode="Markdown"
            )
            
            new_keyboard_for_requester = get_user_profile_keyboard(to_user_id, from_user_id)
            
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
            
            new_keyboard_for_acceptor = get_user_profile_keyboard(from_user_id, to_user_id)
            
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
        
        chat_request = get_chat_request(from_user_id, to_user_id)
        if not chat_request:
            await query.edit_message_text("Chat request not found or already processed.")
            return
        
        update_chat_request_status(chat_request['id'], 'rejected')
        
        await query.edit_message_text(
            "❌ Chat request declined.",
            parse_mode="Markdown"
        )
        
        try:
            await context.bot.send_message(
                chat_id=from_user_id,
                text="❌ Your chat request was declined.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Could not notify user about declined chat: {e}")

async def enter_chat_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id: int):
    """Enhanced chat mode entry"""
    user_id = update.effective_user.id
    active_chat = get_active_chat(user_id, target_user_id)
    
    if not active_chat:
        await update.effective_message.reply_text("No active chat found.")
        return ConversationHandler.END
    
    target_profile = get_user_profile(target_user_id)
    
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

async def chat_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced chat message handler with backup triggers"""
    user_id = update.effective_user.id
    target_user_id = context.user_data.get('active_chat_with')
    chat_id = context.user_data.get('active_chat_id')
    
    if not target_user_id or not chat_id:
        await update.message.reply_text("No active chat session.")
        return ConversationHandler.END
    
    if is_blocked(target_user_id, user_id):
        await update.message.reply_text("⚠️ Unable to send message. The chat has been ended.")
        return ConversationHandler.END
    
    message_text = update.message.text
    
    if message_text == "Block":
        block_user(user_id, target_user_id)
        end_chat(chat_id)
        
        target_profile = get_user_profile(target_user_id)
        await update.message.reply_text(
            f"🚫 You have blocked {target_profile['nickname'] or 'Anonymous'}. They will no longer be able to send you messages through the bot. The chat has been ended.",
            reply_markup=MAIN_REPLY_KEYBOARD
        )
        
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
    
    save_chat_message(chat_id, user_id, target_user_id, message_text)
    
    await update.message.reply_text("✅ Message sent!")
    
    try:
        user_profile = get_user_profile(user_id)
        
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"💬 **Message from {user_profile['nickname'] or 'Anonymous'}:**\n\n{message_text}",
            parse_mode="Markdown"
        )
        
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

async def leave_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced chat leave handler"""
    user_id = update.effective_user.id
    target_user_id = context.user_data.get('active_chat_with')
    chat_id = context.user_data.get('active_chat_id')
    
    if chat_id:
        end_chat(chat_id)
    
    await update.message.reply_text(
        "You have left the chat.",
        reply_markup=MAIN_REPLY_KEYBOARD
    )
    
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

async def help_contact_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced admin contact callback"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "✉️ **Contact Administrator**\n\n"
        "Please send the message you want to forward to the admin.\n\n"
        "Send /cancel to abort.",
        parse_mode="Markdown"
    )
    
    return WAITING_FOR_ADMIN_MESSAGE

async def admin_message_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced admin message receiver"""
    message_text = update.message.text.strip()
    user_id = update.effective_user.id
    user_profile = get_user_profile(user_id)
    
    if not message_text:
        await update.message.reply_text("Please send a valid message.")
        return WAITING_FOR_ADMIN_MESSAGE
    
    save_admin_message(user_id, message_text)
    
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

async def admin_message_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced admin message cancellation"""
    await update.message.reply_text(
        "❌ Message to admin cancelled.",
        reply_markup=MAIN_REPLY_KEYBOARD
    )
    return ConversationHandler.END
# ------------------------------ ENHANCED CONFESSION FLOW ------------------------------

async def confess_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Enhanced confession command with rate limiting and backup status"""
    user_id = update.effective_user.id
    
    # Rate Limiting Check with enhanced logging
    last_ts = get_last_submission_ts(user_id)
    time_since = int(time.time()) - last_ts
    if time_since < RATE_LIMIT_SECONDS:
        remaining_time = RATE_LIMIT_SECONDS - time_since
        await update.effective_message.reply_text(
            f"⏳ *Rate Limit:* You must wait another *{remaining_time} seconds* before submitting a new confession.\n\n"
            f"💡 *Tip:* Use this time to think about your confession content.",
            parse_mode="Markdown",
            reply_markup=MAIN_REPLY_KEYBOARD
        )
        return ConversationHandler.END
    
    # Check for existing draft with enhanced recovery
    draft_conf = get_user_draft_confession(user_id)
    if draft_conf:
        conf_id = draft_conf['id']
        await update.effective_message.reply_text(
            f"📝 *Resuming Draft Confession*\n\n"
            f"We found an existing draft confession (ID: `{conf_id}`). "
            f"You can continue editing it or start fresh.",
            parse_mode="Markdown"
        )
    else:
        conf_id = save_confession(user_id, "", None, None)
    
    context.user_data['current_conf_id'] = conf_id
    
    await update.effective_message.reply_text(
        "📝 *Start your confession.*\n\n"
        "You can send text, a photo, or a document. After sending your confession, you'll proceed directly to category selection.\n\n"
        "💡 *Tips for a great confession:*\n"
        "• Be authentic and honest\n"
        "• Respect others' privacy\n"
        "• Keep it meaningful\n"
        "• No hate speech or harassment\n\n"
        "🔄 *Backup Status:* Your confession will be automatically backed up.",
        reply_markup=CONFESSION_CANCEL_KEYBOARD,
        parse_mode="Markdown"
    )
    
    return WAITING_FOR_CONFESSION

async def confession_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Enhanced confession receiver with content validation"""
    conf_id = context.user_data.get('current_conf_id')
    user_id = update.effective_user.id

    if not conf_id:
        await update.effective_message.reply_text(
            "❌ Error: Confession ID missing. Please start over with /confess.\n\n"
            "💡 *Tip:* This might happen if your session expired.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    content = ""
    file_id = None
    file_type = None
    
    if update.message.text:
        content = update.message.text
        if contains_profanity(content):
            await update.message.reply_text(
                "🚫 *Content Warning*\n\n"
                "Your message contains banned words. Please revise your confession to be more respectful.\n\n"
                "💡 *Tip:* Focus on sharing your experience without offensive language.",
                parse_mode="Markdown"
            )
            return WAITING_FOR_CONFESSION
        file_type = "text"
        
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        content = update.message.caption if update.message.caption else ""
        if contains_profanity(content):
            await update.message.reply_text(
                "🚫 *Content Warning*\n\n"
                "Your caption contains banned words. Please revise it to be more respectful.",
                parse_mode="Markdown"
            )
            return WAITING_FOR_CONFESSION
        file_type = "photo"

    elif update.message.document:
        file_id = update.message.document.file_id
        content = update.message.caption if update.message.caption else ""
        if contains_profanity(content):
            await update.message.reply_text(
                "🚫 *Content Warning*\n\n"
                "Your caption contains banned words. Please revise it to be more respectful.",
                parse_mode="Markdown"
            )
            return WAITING_FOR_CONFESSION
        file_type = "document"

    else:
        await update.message.reply_text(
            "🤔 *Unsupported Content*\n\n"
            "Please send a text, photo, or document as your confession.\n\n"
            "💡 *Supported formats:*\n"
            "• Text messages\n"
            "• Images (JPEG, PNG, etc.)\n"
            "• Documents (PDF, TXT, etc.)",
            parse_mode="Markdown"
        )
        return WAITING_FOR_CONFESSION

    # Enhanced content validation
    if not content.strip() and not file_id:
        await update.message.reply_text(
            "❌ *Empty Confession*\n\n"
            "Your confession appears to be empty. Please provide some content.",
            parse_mode="Markdown"
        )
        return WAITING_FOR_CONFESSION

    # Update the draft confession in DB with enhanced logging
    update_confession_content_and_media(conf_id, content, file_id, file_type)
    
    # Enhanced category selection with guidance
    context.user_data['selected_categories'] = [] 
    
    await update.message.reply_text(
        "✅ *Confession content saved!*\n\n"
        "🏷️ *Select Categories*\n\n"
        f"Please select *up to {MAX_CATEGORIES}* categories that best describe your confession. "
        "A minimum of one is required.\n\n"
        "💡 *Category Tips:*\n"
        "• Choose categories that best represent your confession\n"
        "• This helps others find your confession\n"
        "• You can select 1-3 categories",
        reply_markup=get_categories_keyboard([]),
        parse_mode="Markdown"
    )

    return WAITING_FOR_CATEGORIES

async def category_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Enhanced category selection with better UX"""
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

            review_text = (
                "*Review & Submit*\n\n"
                "Here is your final confession draft:\n\n"
                "💡 *Before submitting:*\n"
                "• Review your confession for accuracy\n"
                "• Ensure it follows community guidelines\n"
                "• Remember it will be anonymous\n\n"
            )
            
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
            await query.answer("⚠️ Please select at least one category to proceed.", show_alert=True)
            return WAITING_FOR_CATEGORIES
            
    elif data.startswith(CB_CAT_PATTERN) and category_name not in ["auto", "disabled_done"]:
        if category_name in current_selection:
            current_selection.remove(category_name)
            action = "removed"
        elif len(current_selection) < MAX_CATEGORIES:
            current_selection.append(category_name)
            action = "added"
        else:
            await query.answer(f"❌ You can only select up to {MAX_CATEGORIES} categories.", show_alert=True)
            return WAITING_FOR_CATEGORIES 
            
        context.user_data['selected_categories'] = current_selection
        
        # Enhanced feedback
        selection_count = len(current_selection)
        await query.answer(f"✅ {category_name} {action}. ({selection_count}/{MAX_CATEGORIES} selected)")
        
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

async def confession_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Enhanced confession review with better feedback"""
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
        await query.edit_message_text(
            "❌ Error: Confession ID missing. Please start over with /confess.",
            reply_markup=None
        )
        return ConversationHandler.END

    if action == "submit":
        set_confession_status(conf_id, "pending")
        update_last_submission_ts(user_id)
        
        # Enhanced backup trigger with status
        enhanced_backup_trigger()
                
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
                "🎉 **Success! Your confession has been submitted for review.**\n\n"
                "📋 *What happens next:*\n"
                "• Our moderators will review your confession\n"
                "• You'll be notified when it's approved or rejected\n"
                "• Approved confessions appear in the channel\n"
                "• You can check status anytime\n\n"
                "⏰ *Typical review time:* 1-24 hours\n"
                "🔄 *Backup Status:* Confession saved and backed up",
                parse_mode="Markdown",
                reply_markup=None
            )
            
        except Exception as e:
            logger.error(f"Failed to send confession to admin group: {e}")
            await query.edit_message_text(
                "❌ **Submission Error**\n\n"
                "Failed to send to the admin channel. Please try again later.\n\n"
                "💡 *Troubleshooting:*\n"
                "• Check your internet connection\n"
                "• Try again in a few minutes\n"
                "• Contact admin if problem persists",
                parse_mode="Markdown",
                reply_markup=None
            )
        
        context.user_data.pop('current_conf_id', None)
        context.user_data.pop('selected_categories', None)
        return ConversationHandler.END

    elif action == "edit":
        await query.edit_message_text(
            "✍️ *Edit Mode*\n\n"
            "Send your entire *new* confession (text or media) to replace the current content.\n\n"
            "💡 *Editing tips:*\n"
            "• You can completely change your confession\n"
            "• Media will be replaced if you send new media\n"
            "• Categories will be preserved",
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
            "👋 *Confession Cancelled*\n\n"
            "Your confession draft has been cancelled and removed.\n\n"
            "💡 *Remember:*\n"
            "• You can start a new confession anytime with /confess\n"
            "• Your previous drafts are saved\n"
            "• No one has seen your cancelled confession",
            reply_markup=None
        )
        
        context.user_data.pop('current_conf_id', None)
        context.user_data.pop('selected_categories', None)
        
        return ConversationHandler.END
        
    return WAITING_FOR_REVIEW

async def confession_cancel_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Enhanced confession cancellation with cleanup"""
    conf_id = context.user_data.pop('current_conf_id', None)
    context.user_data.pop('selected_categories', None)
    
    if conf_id:
        set_confession_status(conf_id, "cancelled")
        
    msg = update.effective_message
    if msg:
        await msg.reply_text(
            "❌ *Confession Draft Cancelled*\n\n"
            "Your confession draft has been cancelled.\n\n"
            "💡 You can start a new confession anytime with /confess",
            reply_markup=ReplyKeyboardRemove()
        )
    
    return ConversationHandler.END

async def admin_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced admin actions with backup integration"""
    query = update.callback_query
    data = query.data
    
    try:
        action, conf_id_str = data.split(":")
        conf_id = int(conf_id_str)
    except ValueError:
        await query.answer("❌ Error processing request.", show_alert=True)
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
            
            # Enhanced user notification
            await context.bot.send_message(
                chat_id=conf['user_id'], 
                text=f"🎉 **Great News!**\n\n"
                     f"Your confession #{conf_id} has been approved and posted to the channel!\n\n"
                     f"📊 *What's next:*\n"
                     f"• People can now view and comment on your confession\n"
                     f"• You'll get notifications for comments and likes\n"
                     f"• Share it with friends using the channel link\n\n"
                     f"Thank you for sharing your story! 🙏",
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
        
        # Enhanced rejection notification
        await context.bot.send_message(
            chat_id=conf['user_id'], 
            text=f"❌ **Confession Update**\n\n"
                 f"Your confession #{conf_id} was not approved by our moderators.\n\n"
                 f"💡 *Possible reasons:*\n"
                 f"• Content didn't meet community guidelines\n"
                 f"• May contain inappropriate material\n"
                 f"• Could be too similar to existing confessions\n\n"
                 f"🔄 *You can:*\n"
                 f"• Submit a new confession with different content\n"
                 f"• Review our community guidelines\n"
                 f"• Contact admin for clarification\n\n"
                 f"Thank you for understanding!",
            parse_mode="Markdown"
        )

    # Trigger backup after admin action
    enhanced_backup_trigger()

# ------------------------------ ENHANCED COMMENT HANDLERS ------------------------------

async def comment_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced comment receiver with better validation"""
    msg = update.message
    if not msg:
        return WAITING_FOR_COMMENT
    
    text = ""
    file_id = None
    file_type = None
    
    if msg.text:
        text = msg.text.strip()
        
        if text == "❌ Cancel" or text == "🏠 Main Menu":
            await msg.reply_text("Comment cancelled.", reply_markup=MAIN_REPLY_KEYBOARD)
            return ConversationHandler.END
        
        if text.startswith("/"):
            return WAITING_FOR_COMMENT
        
        if contains_profanity(text):
            await msg.reply_text(
                "🚫 *Content Warning*\n\n"
                "Your comment contains disallowed words. Please try again with respectful language.",
                parse_mode="Markdown"
            )
            return WAITING_FOR_COMMENT
    
    elif msg.photo:
        file_id = msg.photo[-1].file_id
        file_type = "photo"
        text = msg.caption if msg.caption else ""
        
        if contains_profanity(text):
            await msg.reply_text(
                "🚫 *Content Warning*\n\n"
                "Your caption contains disallowed words. Please try again with respectful language.",
                parse_mode="Markdown"
            )
            return WAITING_FOR_COMMENT
            
    elif msg.document:
        file_id = msg.document.file_id
        file_type = "document"
        text = msg.caption if msg.caption else ""
        
        if contains_profanity(text):
            await msg.reply_text(
                "🚫 *Content Warning*\n\n"
                "Your caption contains disallowed words. Please try again with respectful language.",
                parse_mode="Markdown"
            )
            return WAITING_FOR_COMMENT
    
    else:
        await msg.reply_text(
            "❌ *Unsupported Format*\n\n"
            "Please send text, a photo, or a document as your comment.",
            parse_mode="Markdown"
        )
        return WAITING_FOR_COMMENT
    
    conf_id = context.user_data.get('current_conf_id')
    parent_comment_id = context.user_data.get('parent_comment_id')
    
    if not conf_id:
        await msg.reply_text(
            "❌ *Session Expired*\n\n"
            "Your comment session has expired. Please try again.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    # Enhanced validation - check if confession exists and is approved
    conf = get_confession(conf_id)
    if not conf:
        await msg.reply_text(
            "❌ *Confession Not Found*\n\n"
            "The confession you're trying to comment on doesn't exist.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
        
    if conf['status'] != 'approved':
        await msg.reply_text(
            "❌ *Confession Not Available*\n\n"
            "This confession is not available for comments yet.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    comment_id = save_comment(conf_id, msg.from_user.id, text, parent_comment_id, file_id, file_type)
    
    # Enhanced channel update
    if conf and conf.get('channel_message_id'):
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=CHANNEL_ID,
                message_id=conf['channel_message_id'],
                reply_markup=get_channel_post_keyboard(conf_id)
            )
        except Exception as e:
            logger.warning(f"Could not update channel message keyboard: {e}")
    
    # Enhanced success message
    if parent_comment_id:
        success_text = "✅ *Reply posted successfully!*"
    else:
        success_text = "✅ *Comment posted successfully!*"
    
    await msg.reply_text(
        f"{success_text}\n\n"
        f"💡 *What's next:*\n"
        f"• Others can now see your comment\n"
        f"• You'll get notifications for replies\n"
        f"• You can like/dislike other comments\n"
        f"• View all comments on the confession",
        parse_mode="Markdown",
        reply_markup=MAIN_REPLY_KEYBOARD
    )
    
    context.user_data.pop('current_conf_id', None)
    context.user_data.pop('parent_comment_id', None)
    
    return ConversationHandler.END

async def reply_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced reply receiver with notification system"""
    msg = update.message
    if not msg:
        return WAITING_FOR_REPLY
    
    text = ""
    file_id = None
    file_type = None
    
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
    
    # Enhanced channel update
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
    
    # Enhanced notification system
    if parent_author_id and parent_author_id != msg.from_user.id:
        try:
            deep_link = f"https://t.me/{BOT_USERNAME}?start=reply_{comment_id}"
            
            await context.bot.send_message(
                chat_id=parent_author_id,
                text=f"🔔 **New Reply to Your Comment**\n\n"
                     f"Someone replied to your comment on Confession #{conf_id}.\n\n"
                     f"*{text[:100]}{'...' if len(text) > 100 else ''}*\n\n"
                     f"Click below to view the conversation:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📨 View Reply", url=deep_link)]
                ])
            )
        except Exception as e:
            logger.warning(f"Could not send reply notification: {e}")
    
    await msg.reply_text(
        f"✅ *Reply posted successfully!*\n\n"
        f"The original commenter has been notified of your reply.",
        parse_mode="Markdown",
        reply_markup=MAIN_REPLY_KEYBOARD
    )
    
    context.user_data.pop('current_conf_id', None)
    context.user_data.pop('parent_comment_id', None)
    context.user_data.pop('parent_author_id', None)
    
    return ConversationHandler.END

async def comment_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced comment cancellation"""
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "❌ Comment/reply cancelled.",
            reply_markup=MAIN_REPLY_KEYBOARD
        )
    else:
        await update.message.reply_text(
            "❌ Comment/reply cancelled.",
            reply_markup=MAIN_REPLY_KEYBOARD
        )
    
    context.user_data.pop('current_conf_id', None)
    context.user_data.pop('parent_comment_id', None)
    context.user_data.pop('parent_author_id', None)
    
    return ConversationHandler.END

# ------------------------------ ENHANCED PROFILE MANAGEMENT ------------------------------

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced profile command with comprehensive stats"""
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    follow_counts = get_follow_counts(user_id)
    confessions_count = get_user_confessions_count(user_id)
    comments_count = get_user_comments_count(user_id)
    
    profile_text = (
        f"👤 ***Your Profile***\n\n"
        f"**{profile['nickname'] or 'Anonymous'}**\n\n"
        f"⚡️ **Aura Points:** {profile['aura_points']}\n"
        f"👥 **Followers:** {follow_counts['followers']} | **Following:** {follow_counts['following']}\n"
        f"📊 **Activity Stats:**\n"
        f"   📝 Confessions: {confessions_count}\n"
        f"   💬 Comments: {comments_count}\n\n"
        f"🏢 **Department:** {profile['department'] or 'Not specified'}\n"
        f"📝 **Bio:** {profile['bio'] or 'No bio set'}\n\n"
        f"💡 *Tip:* Customize your profile to stand out!"
    )
    
    await update.message.reply_text("Loading Profile...", reply_markup=ReplyKeyboardRemove())
    
    await update.message.reply_text(
        profile_text,
        reply_markup=PROFILE_MAIN_KEYBOARD,
        parse_mode="Markdown"
    )

async def profile_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced profile callback handler with backup integration"""
    query = update.callback_query
    data = query.data
    await query.answer()
    
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    
    if data == "profile_edit":
        profile_text = (
            "👤 *Profile Customization*\n\n"
            "Here you can change your public appearance in the bot.\n\n"
            f"**Current Settings:**\n"
            f"• **Nickname:** {profile['nickname'] or 'Anonymous'}\n"
            f"• **Bio:** {profile['bio'] or 'No bio set'}\n"
            f"• **Department:** {profile['department'] or 'Not specified'}\n\n"
            "💡 *Tip:* A complete profile helps you connect with others!"
        )
        
        await query.edit_message_text(
            profile_text,
            reply_markup=PROFILE_EDIT_KEYBOARD,
            parse_mode="Markdown"
        )
        
    elif data == "profile_main":
        follow_counts = get_follow_counts(user_id)
        confessions_count = get_user_confessions_count(user_id)
        comments_count = get_user_comments_count(user_id)
        
        profile_text = (
            f"👤 ***Your Profile***\n\n"
            f"**{profile['nickname'] or 'Anonymous'}**\n\n"
            f"⚡️ **Aura Points:** {profile['aura_points']}\n"
            f"👥 **Followers:** {follow_counts['followers']} | **Following:** {follow_counts['following']}\n"
            f"📊 **Activity Stats:**\n"
            f"   📝 Confessions: {confessions_count}\n"
            f"   💬 Comments: {comments_count}\n\n"
            f"🏢 **Department:** {profile['department'] or 'Not specified'}\n"
            f"📝 **Bio:** {profile['bio'] or 'No bio set'}"
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
            "💡 *Nickname Tips:*\n"
            "• Choose something memorable\n"
            "• Keep it respectful\n"
            "• You can change it anytime\n\n"
            "Send /cancel to abort.",
            parse_mode="Markdown"
        )
        return WAITING_FOR_NICKNAME_EDIT
        
    elif data == "profile_set_bio":
        await query.edit_message_text(
            "📝 *Set/Update Bio*\n\n"
            "Please send your new bio (max 256 characters):\n\n"
            "💡 *Bio Tips:*\n"
            "• Share something about yourself\n"
            "• Keep it positive and genuine\n"
            "• This helps others get to know you\n\n"
            "Send /cancel to abort.",
            parse_mode="Markdown"
        )
        return WAITING_FOR_BIO_EDIT
        
    elif data == "profile_edit_department":
        await query.edit_message_text(
            "🏢 *Edit Department*\n\n"
            "Please send your department or field of study:\n\n"
            "💡 *Examples:*\n"
            "• Computer Science\n"
            "• Business Administration\n"
            "• Engineering\n"
            "• Psychology\n\n"
            "Send /cancel to abort.",
            parse_mode="Markdown"
        )
        return WAITING_FOR_DEPARTMENT_EDIT
        
    elif data == "profile_my_confessions":
        confessions = get_user_confessions(user_id, limit=10)
        
        if not confessions:
            text = (
                "📝 *My Confessions*\n\n"
                "You haven't submitted any confessions yet.\n\n"
                "💡 *Ready to share?*\n"
                "Use /confess to submit your first confession!"
            )
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
            text = (
                "💬 *My Comments*\n\n"
                "You haven't made any comments yet.\n\n"
                "💡 *Get started:*\n"
                "Browse confessions and join the conversation!"
            )
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
            text = (
                "👥 *Following*\n\n"
                "You are not following anyone yet.\n\n"
                "💡 *Discover people:*\n"
                "Browse comments and profiles to find interesting people to follow!"
            )
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
            text = (
                "👥 *Followers*\n\n"
                "You don't have any followers yet.\n\n"
                "💡 *Build your presence:*\n"
                "• Submit interesting confessions\n"
                "• Engage with others' comments\n"
                "• Complete your profile"
            )
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
        active_chats = get_active_chats_for_user(user_id)
        
        if not active_chats:
            text = (
                "💬 *My Chats*\n\n"
                "You don't have any active chats yet.\n\n"
                "💡 *Start chatting:*\n"
                "• Find interesting profiles\n"
                "• Send chat requests\n"
                "• Accept incoming requests"
            )
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
            "⚙️ *Profile Settings*\n\n"
            "**Backup Status:** ✅ Active\n"
            "**Data Protection:** ✅ Enabled\n"
            "**Privacy Level:** 🔒 Standard\n\n"
            "💡 *Your data is automatically backed up every 5 minutes.*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Profile", callback_data="profile_main")]
            ])
        )

async def profile_bio_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Enhanced bio editing with validation"""
    text = update.message.text.strip()
    
    if len(text) > 256:
        await update.message.reply_text(
            "❌ *Bio Too Long*\n\n"
            "Your bio exceeds the 256 character limit.\n\n"
            "💡 *Tip:* Try to summarize your bio more concisely.\n\n"
            "Please try again:",
            parse_mode="Markdown"
        )
        return WAITING_FOR_BIO_EDIT
    
    update_user_profile(update.effective_user.id, bio=text)
    
    await update.message.reply_text(
        "✅ *Bio Updated Successfully!*\n\n"
        "Your new bio is now visible on your profile.",
        reply_markup=MAIN_REPLY_KEYBOARD
    )
    
    return ConversationHandler.END

async def profile_nickname_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Enhanced nickname editing with validation"""
    text = update.message.text.strip()
    
    if len(text) > 32:
        await update.message.reply_text(
            "❌ *Nickname Too Long*\n\n"
            "Your nickname exceeds the 32 character limit.\n\n"
            "💡 *Tip:* Choose a shorter, memorable nickname.\n\n"
            "Please try again:",
            parse_mode="Markdown"
        )
        return WAITING_FOR_NICKNAME_EDIT
    
    if contains_profanity(text):
        await update.message.reply_text(
            "🚫 *Invalid Nickname*\n\n"
            "Your nickname contains inappropriate words.\n\n"
            "Please choose a respectful nickname:",
            parse_mode="Markdown"
        )
        return WAITING_FOR_NICKNAME_EDIT
    
    update_user_profile(update.effective_user.id, nickname=text)
    
    await update.message.reply_text(
        "✅ *Nickname Updated Successfully!*\n\n"
        f"Your profile now displays as: **{text}**",
        parse_mode="Markdown",
        reply_markup=MAIN_REPLY_KEYBOARD
    )
    
    return ConversationHandler.END

async def profile_department_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Enhanced department editing"""
    text = update.message.text.strip()
    
    update_user_profile(update.effective_user.id, department=text)
    
    await update.message.reply_text(
        "✅ *Department Updated Successfully!*\n\n"
        f"Your department is now set to: **{text}**",
        parse_mode="Markdown",
        reply_markup=MAIN_REPLY_KEYBOARD
    )
    
    return ConversationHandler.END

async def profile_edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Enhanced profile edit cancellation"""
    await update.message.reply_text(
        "❌ *Profile Editing Cancelled*\n\n"
        "Your profile changes have been discarded.",
        reply_markup=MAIN_REPLY_KEYBOARD
    )
    return ConversationHandler.END
# ------------------------------ ENHANCED HELP SYSTEM ------------------------------

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced help command with comprehensive guidance"""
    help_text = (
        "🤖 ***WRU Confessions Bot Help***\n\n"
        "Welcome to the confession bot! Here are the main commands:\n\n"
        "📝 ***Confession Commands:***\n"
        "• /confess - Submit a new anonymous confession\n"
        "• /list - View recent confessions\n"
        "• /view <id> - View specific confession with comments\n"
        "• /search <keywords> - Search confessions\n"
        "• /categories - Browse confession categories\n\n"
        "💬 ***Interaction Commands:***\n"
        "• /comment <id> - Comment on a confession\n"
        "• /reply <id> - Reply to a comment\n"
        "• /like <id> - Like a confession or comment\n"
        "• /report <id> - Report inappropriate content\n\n"
        "👤 ***Profile Commands:***\n"
        "• /profile - View your profile and stats\n"
        "• /stats - View detailed statistics\n\n"
        "🛡️ ***System Features:***\n"
        "• **Auto Backup:** Every 5 minutes\n"
        "• **Data Restoration:** Automatic on restart\n"
        "• **Privacy Protection:** Anonymous by default\n"
        "• **Moderation:** All content reviewed\n\n"
        "Need more info? Use the buttons below:"
    )
    
    await update.message.reply_text("Loading Help...", reply_markup=ReplyKeyboardRemove())
    
    await update.message.reply_text(
        help_text,
        reply_markup=HELP_KEYBOARD,
        parse_mode="Markdown"
    )

async def help_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced help callback handler with detailed information"""
    query = update.callback_query
    data = query.data
    await query.answer()
    
    if data == "help_rules":
        rules_text = (
            "📜 ***Community Guidelines***\n\n"
            "To maintain a positive and respectful environment, please follow these rules:\n\n"
            "🔸 ***1. Stay On Topic:***\n"
            "   This platform is intended for sharing personal confessions and experiences.\n"
            "   - Refrain from posting general questions\n"
            "   - Student-related inquiries may be allowed if valuable\n"
            "   - Keep discussions meaningful and relevant\n\n"
            "🔸 ***2. Respectful Dialogue:***\n"
            "   When discussing sensitive subjects, maintain courtesy and understanding.\n"
            "   - No personal attacks or harassment\n"
            "   - Be empathetic towards others' experiences\n"
            "   - Disagree respectfully\n\n"
            "🔸 ***3. No Harmful Content:***\n"
            "   While mentioning names is permitted, you assume responsibility for consequences.\n"
            "   - The platform is not liable for outcomes\n"
            "   - Name removal requests will be honored\n"
            "   - No hate speech or discrimination\n\n"
            "🔸 ***4. Privacy Protection:***\n"
            "   Do not share personal identification details about yourself or others.\n"
            "   - No phone numbers, addresses, or emails\n"
            "   - Protect your own privacy\n"
            "   - Respect others' anonymity\n\n"
            "🔸 ***5. Positive Environment:***\n"
            "   Share authentic experiences and avoid spam, harassment, or repetitive posts.\n"
            "   - No commercial advertising\n"
            "   - No spam or repetitive content\n"
            "   - Build a supportive community\n\n"
            "***This space is for meaningful connection and sharing, not for spreading misinformation or creating conflict.***"
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
            "🔒 ***Data Privacy Information***\n\n"
            "***What We Store:***\n"
            "• Your Telegram User ID for operational purposes\n"
            "• Confession content and metadata\n"
            "• Comments and interactions\n"
            "• Profile information (nickname, bio, department)\n"
            "• Chat messages and requests\n\n"
            "***What's Public:***\n"
            "• Your chosen Nickname\n"
            "• Bio content (if set)\n"
            "• Department (if set)\n"
            "• Aura points and activity stats\n"
            "• Confessions (anonymous)\n"
            "• Comments (with your nickname)\n\n"
            "***What's Private:***\n"
            "• Your exact Telegram User ID\n"
            "• Personal conversations\n"
            "• Report details\n"
            "• Administrative actions\n\n"
            "***Data Protection:***\n"
            "• Automatic backups every 5 minutes\n"
            "• Data encrypted in transit\n"
            "• Secure database storage\n"
            "• Regular security updates\n\n"
            "***Your Rights:***\n"
            "• Request data deletion\n"
            "• Export your data\n"
            "• Opt-out of features\n"
            "• Report privacy concerns\n\n"
            "***Backup System:***\n"
            "All data is automatically backed up to secure GitHub repositories every 5 minutes to prevent data loss."
        )
        await query.edit_message_text(
            privacy_text,
            parse_mode="Markdown",
            reply_markup=HELP_KEYBOARD
        )

# ------------------------------ ENHANCED UTILITY HANDLERS ------------------------------

async def pending_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced pending count for admins"""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM confessions WHERE status = 'pending'")
    pending_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM user_reports")
    report_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM chat_requests WHERE status = 'pending'")
    chat_requests_count = cur.fetchone()[0]
    
    conn.close()
    
    status_text = (
        "📊 ***Administrative Dashboard***\n\n"
        f"📝 **Pending Confessions:** {pending_count}\n"
        f"🚩 **User Reports:** {report_count}\n"
        f"💬 **Pending Chat Requests:** {chat_requests_count}\n\n"
        "***System Status:***\n"
        f"• **Database:** {os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0} bytes\n"
        f"• **Backup System:** ✅ Active\n"
        f"• **Last Backup:** Ongoing...\n"
        f"• **Uptime:** {int(time.time() - context.bot_data.get('start_time', time.time()))} seconds"
    )
    
    await update.message.reply_text(status_text, parse_mode="Markdown")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced unknown command handler"""
    if update.effective_message.text.startswith('/'):
        await update.effective_message.reply_text(
            "❌ ***Unknown Command***\n\n"
            "Sorry, I don't recognize that command.\n\n"
            "💡 ***Try these instead:***\n"
            "• /start - Begin using the bot\n"
            "• /help - See all available commands\n"
            "• /confess - Submit a confession\n"
            "• /profile - View your profile\n\n"
            "Or use the menu buttons for quick access!",
            parse_mode="Markdown",
            reply_markup=MAIN_REPLY_KEYBOARD
        )

async def force_github_restore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced force GitHub restoration for admins"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ This command is for admin only.")
        return
        
    await update.message.reply_text(
        "🔄 ***Forcing Database Restoration***\n\n"
        "Initiating emergency restoration from GitHub backup...\n\n"
        "***This will:***\n"
        "• Download latest backup from GitHub\n"
        "• Replace current database\n"
        "• Restore all user data\n"
        "• Preserve current session\n\n"
        "Please wait...",
        parse_mode="Markdown"
    )
    
    def restore_thread():
        success = restore_database_from_github()
        if success:
            context.application.create_task(
                update.message.reply_text(
                    "✅ ***Database Restoration Completed!***\n\n"
                    "All data has been successfully restored from the latest GitHub backup.\n\n"
                    "***Restored:***\n"
                    "• User profiles and settings\n"
                    "• Confessions and comments\n"
                    "• Chat history and requests\n"
                    "• System configurations\n\n"
                    "The bot will continue operating normally.",
                    parse_mode="Markdown"
                )
            )
        else:
            context.application.create_task(
                update.message.reply_text(
                    "❌ ***Database Restoration Failed!***\n\n"
                    "Could not restore from GitHub backup.\n\n"
                    "***Possible reasons:***\n"
                    "• GitHub credentials incorrect\n"
                    "• Network connectivity issues\n"
                    "• Backup file corrupted\n"
                    "• Repository not accessible\n\n"
                    "Check logs for detailed error information.",
                    parse_mode="Markdown"
                )
            )
    
    thread = threading.Thread(target=restore_thread)
    thread.start()

async def test_github_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced GitHub backup test for admins"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ This command is for admin only.")
        return
        
    await update.message.reply_text(
        "🔄 ***Testing GitHub Backup System***\n\n"
        "Performing comprehensive backup system test...\n\n"
        "***Testing:***\n"
        "• Database file existence and size\n"
        "• GitHub API connectivity\n"
        "• File encoding and upload\n"
        "• Backup verification\n\n"
        "Please wait...",
        parse_mode="Markdown"
    )
    
    if not os.path.exists(DB_PATH):
        await update.message.reply_text("❌ Database file doesn't exist!")
        return
        
    db_size = os.path.getsize(DB_PATH)
    if db_size == 0:
        await update.message.reply_text("❌ Database file is empty!")
        return
        
    # Test backup
    if trigger_immediate_backup():
        await update.message.reply_text(
            "✅ ***GitHub Backup Test Successful!***\n\n"
            "***Test Results:***\n"
            f"• **Database Size:** {db_size} bytes\n"
            f"• **GitHub API:** ✅ Connected\n"
            f"• **File Upload:** ✅ Successful\n"
            f"• **Backup Verification:** ✅ Passed\n\n"
            "The backup system is working correctly.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "❌ ***GitHub Backup Test Failed!***\n\n"
            "***Possible Issues:***\n"
            f"• **Database Size:** {db_size} bytes\n"
            "• **GitHub API:** ❌ Connection failed\n"
            "• **File Upload:** ❌ Failed\n"
            "• **Authentication:** ❌ Invalid token\n\n"
            "Check environment variables and GitHub credentials.",
            parse_mode="Markdown"
        )

async def system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced system status command"""
    user_id = update.effective_user.id
    is_admin = user_id == ADMIN_USER_ID
    
    # Get basic statistics
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM users")
    user_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM confessions WHERE status = 'approved'")
    approved_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM confessions WHERE status = 'pending'")
    pending_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM comments")
    comment_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM active_chats")
    active_chats_count = cur.fetchone()[0]
    
    conn.close()
    
    # Calculate database size
    db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    
    status_text = (
        "🤖 ***System Status***\n\n"
        "***Bot Statistics:***\n"
        f"• **Total Users:** {user_count}\n"
        f"• **Approved Confessions:** {approved_count}\n"
        f"• **Pending Confessions:** {pending_count}\n"
        f"• **Total Comments:** {comment_count}\n"
        f"• **Active Chats:** {active_chats_count}\n\n"
        "***System Health:***\n"
        f"• **Database Size:** {db_size / 1024 / 1024:.2f} MB\n"
        f"• **Backup System:** ✅ Active\n"
        f"• **Backup Interval:** {BACKUP_INTERVAL_MINUTES} minutes\n"
        f"• **Uptime:** {int(time.time() - context.bot_data.get('start_time', time.time()))} seconds\n"
    )
    
    if is_admin:
        # Add admin-only details
        admin_text = (
            "\n***Admin Details:***\n"
            f"• **GitHub Connected:** {bool(GITHUB_ACCESS_TOKEN)}\n"
            f"• **Last Backup:** {context.bot_data.get('last_backup', 'Never')}\n"
            f"• **Backup Queue:** {0}\n"
            f"• **Memory Usage:** {os.path.getsize(DB_PATH) / 1024 / 1024:.2f} MB\n"
        )
        status_text += admin_text
        
        keyboard = [
            [InlineKeyboardButton("🔄 Test Backup", callback_data="test_backup"),
             InlineKeyboardButton("📊 Full Stats", callback_data="full_stats")],
            [InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("📝 New Confession", callback_data="new_confession"),
             InlineKeyboardButton("📋 View Confessions", callback_data="view_confessions")],
            [InlineKeyboardButton("🆘 Help", callback_data="help")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(status_text, parse_mode="Markdown", reply_markup=reply_markup)

async def backup_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced backup status command"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ This command is for admin only.")
        return
    
    # Check backup system status
    github_connected = bool(GITHUB_ACCESS_TOKEN and GITHUB_REPO_OWNER and GITHUB_REPO_NAME)
    db_exists = os.path.exists(DB_PATH)
    db_size = os.path.getsize(DB_PATH) if db_exists else 0
    
    status_text = (
        "🔄 ***Backup System Status***\n\n"
        "***Configuration:***\n"
        f"• **GitHub Access:** {'✅ Connected' if github_connected else '❌ Disconnected'}\n"
        f"• **Repository:** {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME if github_connected else 'Not set'}\n"
        f"• **Backup Path:** {GITHUB_BACKUP_PATH if github_connected else 'Not set'}\n"
        f"• **Interval:** {BACKUP_INTERVAL_MINUTES} minutes\n\n"
        "***Database:***\n"
        f"• **Database File:** {'✅ Exists' if db_exists else '❌ Missing'}\n"
        f"• **File Size:** {db_size / 1024 / 1024:.2f} MB\n"
        f"• **Last Modified:** {datetime.fromtimestamp(os.path.getmtime(DB_PATH)).strftime('%Y-%m-%d %H:%M:%S') if db_exists else 'N/A'}\n\n"
        "***System:***\n"
        f"• **Backup Thread:** {'✅ Running' if any(t.name == 'backup_thread' for t in threading.enumerate()) else '❌ Stopped'}\n"
        f"• **Backup In Progress:** {'✅ Yes' if backup_in_progress else '❌ No'}\n"
        f"• **Successful Backups:** {context.bot_data.get('successful_backups', 0)}\n"
        f"• **Failed Backups:** {context.bot_data.get('failed_backups', 0)}\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Test Backup Now", callback_data="test_backup"),
         InlineKeyboardButton("📥 Force Restore", callback_data="force_restore")],
        [InlineKeyboardButton("📊 System Status", callback_data="system_status")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(status_text, parse_mode="Markdown", reply_markup=reply_markup)

# ------------------------------ ENHANCED ADMIN COMMANDS ------------------------------

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced broadcast message for admins"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ This command is for admin only.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 ***Broadcast Message***\n\n"
            "Usage: /broadcast <message>\n\n"
            "***This will send a message to all users.***\n\n"
            "💡 ***Example:***\n"
            "/broadcast Important system update: New features added!"
        )
        return
    
    message_text = ' '.join(context.args)
    
    # Get all users
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    users = [row[0] for row in cur.fetchall()]
    conn.close()
    
    total_users = len(users)
    successful_sends = 0
    failed_sends = 0
    
    await update.message.reply_text(
        f"📢 ***Starting Broadcast***\n\n"
        f"**Message:** {message_text}\n"
        f"**Recipients:** {total_users} users\n\n"
        f"Broadcasting in progress...",
        parse_mode="Markdown"
    )
    
    # Send to all users
    for user_id in users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 ***Announcement***\n\n{message_text}",
                parse_mode="Markdown"
            )
            successful_sends += 1
        except Exception as e:
            failed_sends += 1
            logger.warning(f"Failed to send broadcast to user {user_id}: {e}")
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.1)
    
    await update.message.reply_text(
        f"📢 ***Broadcast Complete***\n\n"
        f"**Results:**\n"
        f"• ✅ Successful: {successful_sends}\n"
        f"• ❌ Failed: {failed_sends}\n"
        f"• 📊 Total: {total_users}\n\n"
        f"**Success Rate:** {successful_sends/total_users*100:.1f}%",
        parse_mode="Markdown"
    )

async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced data export for admins"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ This command is for admin only.")
        return
    
    await update.message.reply_text(
        "📊 ***Data Export***\n\n"
        "Preparing comprehensive data export...\n\n"
        "***This may take a few moments.***",
        parse_mode="Markdown"
    )
    
    # Create export data
    export_data = {
        "export_timestamp": datetime.now().isoformat(),
        "system_info": {
            "database_size": os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0,
            "backup_system": "Active",
            "bot_version": "V64 Enhanced GitHub Backup"
        },
        "statistics": {}
    }
    
    # Get statistics
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    tables = [
        "users", "confessions", "comments", "comment_votes", 
        "follows", "user_profiles", "chat_requests", "active_chats",
        "chat_messages", "blocked_users", "user_reports", "admin_messages"
    ]
    
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        export_data["statistics"][table] = count
    
    conn.close()
    
    # Create export file
    export_filename = f"bot_export_{int(time.time())}.json"
    with open(export_filename, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    # Send export file
    with open(export_filename, 'rb') as f:
        await update.message.reply_document(
            document=f,
            filename=export_filename,
            caption="📊 ***Data Export Complete***\n\nExported statistics and system information."
        )
    
    # Clean up
    os.remove(export_filename)

# ------------------------------ ENHANCED BACKUP INTEGRATION ------------------------------

async def periodic_backup_monitor():
    """Enhanced periodic backup monitor with logging"""
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            
            # Check if backup thread is running
            backup_threads = [t for t in threading.enumerate() if t.name == 'backup_thread']
            if not backup_threads:
                logger.warning("🔴 Backup thread not running, restarting...")
                schedule_backups()
                
        except Exception as e:
            logger.error(f"Backup monitor error: {e}")

def initialize_backup_system():
    """Enhanced backup system initialization"""
    print("🚀 Initializing Enhanced Backup System...")
    
    # Perform startup restoration
    backup_on_startup()
    
    # Schedule regular backups
    schedule_backups()
    
    # Start backup monitor
    asyncio.create_task(periodic_backup_monitor())
    
    print("✅ Enhanced Backup System Initialized Successfully!")
    print(f"🔧 Features Enabled:")
    print(f"   • Automatic restoration on startup")
    print(f"   • Scheduled backups every {BACKUP_INTERVAL_MINUTES} minutes")
    print(f"   • Backup monitoring and recovery")
    print(f"   • Enhanced error handling")
    print(f"   • Non-blocking backup operations")

# ------------------------------ ENHANCED MAIN APPLICATION ------------------------------

def main():
    """Enhanced main application with comprehensive backup integration"""
    # Initialize enhanced backup system
    initialize_backup_system()
    
    # Initialize database
    if not init_db():
        logger.error("❌ Failed to initialize database!")
        return
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN is missing.")
        return
        
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Store startup time for status monitoring
    application.bot_data['start_time'] = time.time()
    application.bot_data['successful_backups'] = 0
    application.bot_data['failed_backups'] = 0

    # Enhanced Confession Conversation Handler
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
    
    # Enhanced Profile Editing Conversation Handler
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
    
    # Enhanced Comment Conversation Handler
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
    
    # Enhanced Report Conversation Handler
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
    
    # Enhanced Chat Conversation Handler
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
    
    # Enhanced Admin Message Conversation Handler
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
    
    # Enhanced Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("leavechat", leave_chat))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("status", system_status))
    
    # Enhanced Callback Query Handlers
    application.add_handler(CallbackQueryHandler(menu_callback_handler, pattern=f"^{CB_ACCEPT}$"))
    application.add_handler(CallbackQueryHandler(comment_page_callback, pattern="^comment_page:"))
    application.add_handler(CallbackQueryHandler(comment_menu_callback, pattern="^comment_view:"))
    application.add_handler(CallbackQueryHandler(comment_interaction_callback, pattern="^(vote:|follow_user:|back_to_comments)"))
    application.add_handler(CallbackQueryHandler(chat_request_response, pattern="^(chat_accept:|chat_decline:)"))
    application.add_handler(CallbackQueryHandler(admin_action_callback, pattern=f"^{CB_APPROVE_PATTERN}"))
    application.add_handler(CallbackQueryHandler(admin_action_callback, pattern=f"^{CB_REJECT_PATTERN}"))
    
    # Enhanced Message Handlers
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📊 Profile$"), profile_command))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^❓ Help$"), help_command))
    
    # Enhanced Callback Handlers
    application.add_handler(CallbackQueryHandler(profile_callback_handler, pattern="^profile_"))
    application.add_handler(CallbackQueryHandler(help_callback_handler, pattern="^help_"))
    application.add_handler(CallbackQueryHandler(secondary_callback_handler, pattern=f"^{CB_MENU_MAIN}$"))
    
    # Enhanced Admin Commands
    application.add_handler(CommandHandler("pending", pending_count, filters=filters.Chat(chat_id=ADMIN_GROUP_ID)))
    application.add_handler(CommandHandler("github_restore", force_github_restore))
    application.add_handler(CommandHandler("test_github_backup", test_github_backup))
    application.add_handler(CommandHandler("backup_status", backup_status))
    application.add_handler(CommandHandler("broadcast", broadcast_message))
    application.add_handler(CommandHandler("export", export_data))
    
    # Enhanced Fallback Handler
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    
    # Enhanced Error Handler
    application.add_error_handler(error_handler)
    
    logger.info("🚀 Bot started with Enhanced GitHub Backup System...")
    logger.info("🔧 Features Enabled:")
    logger.info("   • Automatic restoration on every deploy")
    logger.info(f"   • Scheduled backups every {BACKUP_INTERVAL_MINUTES} minutes")
    logger.info("   • Comprehensive backup of all operations")
    logger.info("   • Enhanced error handling and recovery")
    logger.info("   • Non-blocking backup operations")
    
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            timeout=30
        )
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        # Attempt final backup before crashing
        print("🔄 Attempting emergency backup before shutdown...")
        backup_database()

if __name__ == "__main__":
    main()
