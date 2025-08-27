import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

import sqlite3
import logging
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from dotenv import load_dotenv

# Import từ các file đã tách ra
from api import services, schemas
from api.dependencies import get_retriever
from core.database import (
    get_db, get_user_id, get_user_conversations, get_conversation_messages,
    delete_conversation, update_conversation_title, register_user_in_db, add_conversation
)
from retriever.retrieval_system import RetrievalSystem

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Zalo Legal RAG API")
        
# --- API Endpoints ---
@app.post("/generate_answer")
def generate_answer(request: schemas.QueryRequest, retriever: RetrievalSystem = Depends(get_retriever)):
    return StreamingResponse(services.stream_response_generator(request, retriever), media_type="text/event-stream")

@app.get("/conversations/{username}")
def get_conversations(username: str, conn: sqlite3.Connection = Depends(get_db)):
    user_id = get_user_id(conn, username) # Truyền conn
    if not user_id: return []
    conversations = get_user_conversations(conn, user_id) # Truyền conn
    return [{"id": convo["id"], "title": convo["title"]} for convo in conversations]

@app.get("/messages/{conversation_id}")
def get_messages(conversation_id: str, conn: sqlite3.Connection = Depends(get_db)):
    return get_conversation_messages(conn, conversation_id) # Truyền conn

@app.post("/register")
def register_user(request: schemas.RegisterRequest, conn: sqlite3.Connection = Depends(get_db)):
    try:
        # Gọi hàm mới đã sửa
        register_user_in_db(conn, request.username, request.hashed_password)
        logging.info(f"User '{request.username}' registered successfully in DB.")
        return {"message": "User registered successfully in DB"}
    except sqlite3.Error as e: # Bắt lỗi cụ thể của sqlite
        logging.error(f"Failed to register user '{request.username}' in DB: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/conversations/delete")
def delete_conversation_endpoint(request: schemas.DeleteConversationRequest, conn: sqlite3.Connection = Depends(get_db)):
    user_id = get_user_id(conn, request.username) # Truyền conn
    if not user_id:
        return JSONResponse(status_code=404, content={"error": "User not found"})
    
    success = delete_conversation(conn, request.conversation_id, user_id) # Truyền conn
    
    if success:
        return JSONResponse(status_code=200, content={"message": "Conversation deleted successfully"})
    else:
        return JSONResponse(status_code=403, content={"error": "Forbidden or conversation not found"})
    
@app.post("/conversations/update_title")
def update_title_endpoint(request: schemas.UpdateTitleRequest, conn: sqlite3.Connection = Depends(get_db)):
    """Cập nhật tiêu đề của một cuộc trò chuyện."""
    user_id = get_user_id(conn, request.username)
    if not user_id:
        return JSONResponse(status_code=404, content={"error": "User not found"})
    
    # Giới hạn độ dài tiêu đề để tránh dữ liệu quá lớn
    if len(request.new_title) > 100:
        return JSONResponse(status_code=400, content={"error": "Title is too long"})

    success = update_conversation_title(conn, request.conversation_id, user_id, request.new_title)
    
    if success:
        return JSONResponse(status_code=200, content={"message": "Title updated successfully"})
    else:
        # Lỗi có thể do conversation_id không tồn tại hoặc không thuộc về user này
        return JSONResponse(status_code=403, content={"error": "Forbidden or conversation not found"})