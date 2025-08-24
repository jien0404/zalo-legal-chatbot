# database.py
import sqlite3
import uuid
import json
from datetime import datetime

DB_NAME = 'chat_history.db'

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

# === CÁC HÀM MỚI ĐỂ TƯƠNG TÁC VỚI DB ===

def get_user_id(username: str) -> int | None:
    """Lấy user_id từ username."""
    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user['id'] if user else None

def get_user_conversations(user_id: int) -> list:
    """Lấy tất cả các cuộc trò chuyện của một người dùng."""
    conn = get_db_connection()
    convos = conn.execute(
        'SELECT id, title FROM conversations WHERE user_id = ? ORDER BY created_at DESC', 
        (user_id,)
    ).fetchall()
    conn.close()
    return convos

def get_conversation_messages(conversation_id: str) -> list:
    """Lấy tất cả tin nhắn của một cuộc trò chuyện."""
    conn = get_db_connection()
    messages = conn.execute(
        'SELECT role, content, sources FROM messages WHERE conversation_id = ? ORDER BY created_at ASC',
        (conversation_id,)
    ).fetchall()
    conn.close()
    
    # Chuyển đổi sources từ JSON string về lại dict
    results = []
    for msg in messages:
        results.append({
            "role": msg["role"],
            "content": msg["content"],
            "sources": json.loads(msg["sources"]) if msg["sources"] else None
        })
    return results

def add_conversation(user_id: int, title: str) -> str:
    """Tạo một cuộc trò chuyện mới và trả về ID của nó."""
    conn = get_db_connection()
    new_convo_id = str(uuid.uuid4())
    conn.execute(
        'INSERT INTO conversations (id, user_id, title) VALUES (?, ?, ?)',
        (new_convo_id, user_id, title)
    )
    conn.commit()
    conn.close()
    return new_convo_id

def add_message(conversation_id: str, role: str, content: str, sources: list | None = None):
    """Thêm một tin nhắn mới vào cuộc trò chuyện."""
    conn = get_db_connection()
    # Chuyển sources sang dạng JSON string để lưu trữ
    sources_json = json.dumps(sources) if sources else None
    conn.execute(
        'INSERT INTO messages (conversation_id, role, content, sources) VALUES (?, ?, ?, ?)',
        (conversation_id, role, content, sources_json)
    )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Cơ sở dữ liệu đã được khởi tạo.")