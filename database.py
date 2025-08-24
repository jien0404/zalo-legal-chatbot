# database.py
import sqlite3

def init_db():
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    
    # Bảng người dùng
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL
        );
    ''')
    
    # Bảng các cuộc trò chuyện
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY, -- Dùng UUID từ Python
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    ''')

    # Bảng các tin nhắn
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL, -- 'user' or 'assistant'
            content TEXT NOT NULL,
            sources TEXT, -- Lưu sources dưới dạng JSON string
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        );
    ''')
    
    conn.commit()
    conn.close()

# Chạy lần đầu để tạo file DB
if __name__ == "__main__":
    init_db()
    print("Cơ sở dữ liệu đã được khởi tạo.")