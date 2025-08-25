# core/database.py
import sqlite3
import uuid
import json

DB_NAME = 'chat_history.db'

# === BƯỚC 1: TẠO DEPENDENCY QUẢN LÝ KẾT NỐI ===
def get_db():
    """
    Dependency của FastAPI để quản lý kết nối DB.
    Mỗi request sẽ dùng chung kết nối này.
    """
    conn = sqlite3.connect(DB_NAME, timeout=10) 
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_db_connection():
    """Tạo và trả về một kết nối đến DB."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            sources TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        );
    ''')
    conn.commit()
    conn.close()


# === BƯỚC 2: SỬA LẠI TẤT CẢ CÁC HÀM ĐỂ NHẬN `conn` LÀM THAM SỐ ===
# Chúng sẽ không tự mở/đóng kết nối nữa

def get_user_id(conn: sqlite3.Connection, username: str) -> int | None:
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    return user['id'] if user else None

def get_user_conversations(conn: sqlite3.Connection, user_id: int) -> list:
    convos = conn.execute(
        'SELECT id, title FROM conversations WHERE user_id = ? ORDER BY created_at DESC', 
        (user_id,)
    ).fetchall()
    return convos

def get_conversation_messages(conn: sqlite3.Connection, conversation_id: str) -> list:
    messages = conn.execute(
        'SELECT role, content, sources FROM messages WHERE conversation_id = ? ORDER BY created_at ASC',
        (conversation_id,)
    ).fetchall()
    
    results = []
    for msg in messages:
        results.append({
            "role": msg["role"],
            "content": msg["content"],
            "sources": json.loads(msg["sources"]) if msg["sources"] else None
        })
    return results

def add_conversation(conn: sqlite3.Connection, user_id: int, title: str) -> str:
    new_convo_id = str(uuid.uuid4())
    conn.execute(
        'INSERT INTO conversations (id, user_id, title) VALUES (?, ?, ?)',
        (new_convo_id, user_id, title)
    )
    conn.commit()
    return new_convo_id

def add_message(conn: sqlite3.Connection, conversation_id: str, role: str, content: str, sources: list | None = None):
    sources_json = json.dumps(sources) if sources else None
    conn.execute(
        'INSERT INTO messages (conversation_id, role, content, sources) VALUES (?, ?, ?, ?)',
        (conversation_id, role, content, sources_json)
    )
    conn.commit()

def delete_conversation(conn: sqlite3.Connection, conversation_id: str, user_id: int):
    delete_messages_sql = 'DELETE FROM messages WHERE conversation_id = ?'
    delete_conversation_sql = 'DELETE FROM conversations WHERE id = ? AND user_id = ?'
    
    try:
        with conn: # Dùng transaction
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute(delete_messages_sql, (conversation_id,))
            cursor = conn.execute(delete_conversation_sql, (conversation_id, user_id))
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Lỗi database khi xóa: {e}")
        return False
        
def register_user_in_db(conn: sqlite3.Connection, username: str, hashed_password: str):
    """Hàm riêng để đăng ký user, nhận conn"""
    conn.execute(
        "INSERT INTO users (username, hashed_password) VALUES (?, ?)",
        (username, hashed_password)
    )
    conn.commit()