# api/main.py
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

import json
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

from core.database import (
    get_user_id, get_user_conversations, get_conversation_messages,
    add_conversation, add_message, get_db_connection, delete_conversation
)
from retriever.retrieval_system import RetrievalSystem
from api.dependencies import get_retriever
import logging
logging.basicConfig(level=logging.INFO)

load_dotenv()

app = FastAPI(title="Zalo Legal RAG API")
RERANKER_SCORE_THRESHOLD = 0.5

try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    print(f"Lỗi cấu hình Gemini API: {e}")

# --- Pydantic Models ---
class ChatMessage(BaseModel):
    role: str
    content: str

class QueryRequest(BaseModel):
    chat_history: list[ChatMessage]
    conversation_id: str | None
    username: str
    top_k_rerank: int = 5

class RegisterRequest(BaseModel):
    username: str
    hashed_password: str
    
class NewConversationRequest(BaseModel):
    username: str
    title: str

# --- Helper Functions ---
def rewrite_query_with_history(chat_history: list[ChatMessage]) -> str:
    if len(chat_history) < 2:
        return chat_history[-1].content
    history_str = "\n".join([f"{'Người dùng' if msg.role == 'user' else 'Trợ lý'}: {msg.content}" for msg in chat_history[:-1]])
    current_question = chat_history[-1].content
    prompt = f"Dựa vào lịch sử trò chuyện, viết lại câu hỏi cuối cùng thành một câu hỏi độc lập, đầy đủ ngữ nghĩa để tìm kiếm. Nếu câu hỏi đã đủ nghĩa, trả về chính nó.\n\nLịch sử trò chuyện:\n{history_str}\n\nCâu hỏi cuối cùng: {current_question}\n\nCâu hỏi độc lập:"
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return current_question

def create_final_prompt(chat_history: list[ChatMessage], source_context: str) -> str:
    current_question = chat_history[-1].content
    history_context = "\n".join([f"{'Người dùng' if msg.role == 'user' else 'Trợ lý'}: {msg.content}" for msg in chat_history[:-1]])
    return f"""**LỊCH SỬ TRÒ CHUYỆN:**\n---\n{history_context}\n---\n**KIẾN THỨC NỀN (Dùng để trả lời câu hỏi cuối cùng):**\n---\n{source_context}\n---\n**CÂU HỎI CUỐI CÙNG CỦA NGƯỜI DÙNG:** {current_question}\n---\n**HƯỚNG DẪN:**\nBạn là một trợ lý pháp lý chuyên nghiệp. Dựa vào KIẾN THỨC NỀN và LỊCH SỬ TRÒ CHUYỆN ở trên để trả lời câu hỏi cuối cùng của người dùng.\n- **Quan trọng:** Nhập vai một chuyên gia, trả lời trực tiếp, **không được nhắc đến "kiến thức nền" hay "nguồn được cung cấp"**.\n- Trích dẫn các nguồn liên quan bằng cách ghi `[Nguồn X]` ở cuối câu.\n- Nếu không có thông tin để trả lời, hãy nói rằng bạn không có thông tin về vấn đề này.\n\n**Câu trả lời của bạn:**"""

def stream_response_generator(request: QueryRequest, retriever: RetrievalSystem):
    # --- BƯỚC 1: LƯU TIN NHẮN CỦA NGƯỜI DÙNG NGAY LẬP TỨC ---
    user_message_content = request.chat_history[-1].content
    add_message(request.conversation_id, "user", user_message_content)

    # --- BƯỚC 2: BIẾN ĐỔI CÂU HỎI VÀ RETRIEVAL (như cũ) ---
    standalone_question = rewrite_query_with_history(request.chat_history)
    retrieved_chunks = retriever.retrieve_chunks(standalone_question, top_k_rerank=request.top_k_rerank)

    # --- BƯỚC 3: KIỂM TRA "GÁC CỔNG" ---
    if not retrieved_chunks or retrieved_chunks[0]['score'] < RERANKER_SCORE_THRESHOLD:
        bot_response_content = "Tôi xin lỗi, tôi không tìm thấy thông tin đủ liên quan trong cơ sở dữ liệu để trả lời câu hỏi này."
        # Lưu lại câu trả lời "từ chối" của bot
        add_message(request.conversation_id, "assistant", bot_response_content)
        # Stream câu trả lời này về và kết thúc
        yield f"data: {json.dumps({'text': bot_response_content})}\n\n"
        return

    high_quality_chunks = [chunk for chunk in retrieved_chunks if chunk['score'] >= RERANKER_SCORE_THRESHOLD]
    if not high_quality_chunks:
        bot_response_content = "Mặc dù đã tìm thấy một vài thông tin, nhưng chúng không đủ độ tin cậy để đưa ra câu trả lời chính xác."
        # Lưu lại câu trả lời "từ chối" của bot
        add_message(request.conversation_id, "assistant", bot_response_content)
        # Stream câu trả lời này về và kết thúc
        yield f"data: {json.dumps({'text': bot_response_content})}\n\n"
        return
    
    # --- BƯỚC 4: GỬI SOURCES VÀ STREAM CÂU TRẢ LỜI TỪ LLM ---
    sources_data = [{"doc_id": c["doc_id"], "text": c["text"], "score": c["score"]} for c in high_quality_chunks]
    yield f"data: {json.dumps({'sources': sources_data})}\n\n"

    source_context = "\n\n".join([f"Nguồn {i+1} (từ văn bản {c['doc_id']}):\n\"\"\"\n{c['text']}\n\"\"\"" for i, c in enumerate(high_quality_chunks)])
    final_prompt = create_final_prompt(request.chat_history, source_context)
    
    full_bot_response = ""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        stream = model.generate_content(final_prompt, stream=True)
        for chunk in stream:
            if chunk.text:
                full_bot_response += chunk.text
                yield f"data: {json.dumps({'text': chunk.text})}\n\n"
        
        # Sau khi stream xong, chỉ cần lưu câu trả lời thành công của bot
        add_message(request.conversation_id, "assistant", full_bot_response, sources_data)

    except Exception as e:
        error_message = f"Lỗi khi gọi Gemini API: {e}"
        # Lưu lại thông báo lỗi
        add_message(request.conversation_id, "assistant", error_message)
        yield f"data: {json.dumps({'text': error_message})}\n\n"
        
# --- API Endpoints ---
@app.post("/generate_answer")
def generate_answer(request: QueryRequest, retriever: RetrievalSystem = Depends(get_retriever)):
    return StreamingResponse(stream_response_generator(request, retriever), media_type="text/event-stream")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Zalo Legal RAG API"}

@app.get("/conversations/{username}")
def get_conversations(username: str):
    user_id = get_user_id(username)
    if not user_id: return []
    conversations = get_user_conversations(user_id)
    return [{"id": convo["id"], "title": convo["title"]} for convo in conversations]

@app.get("/messages/{conversation_id}")
def get_messages(conversation_id: str):
    return get_conversation_messages(conversation_id)

@app.post("/conversations")
def create_conversation(request: NewConversationRequest):
    user_id = get_user_id(request.username)
    if not user_id:
        # Log lại để biết tại sao trả về 404
        logging.warning(f"User '{request.username}' not found in DB. Returning 404.")
        return JSONResponse(status_code=404, content={"error": "User not found"})
    try:
        new_convo_id = add_conversation(user_id, request.title)
        return JSONResponse(status_code=200, content={"conversation_id": new_convo_id})
    except Exception as e:
        logging.error(f"Error creating conversation for user '{request.username}': {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/register")
def register_user(request: RegisterRequest):
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", (request.username, request.hashed_password))
        conn.commit()
        conn.close()
        logging.info(f"User '{request.username}' registered successfully in DB.")
        return {"message": "User registered successfully in DB"}
    except Exception as e:
        # Log lại lỗi cụ thể
        logging.error(f"Failed to register user '{request.username}' in DB: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
    
class DeleteConversationRequest(BaseModel):
    username: str
    conversation_id: str

@app.post("/conversations/delete") # Sử dụng POST thay vì DELETE để dễ gọi từ HTML form/JS
def delete_conversation_endpoint(request: DeleteConversationRequest):
    """Xóa một cuộc trò chuyện."""
    user_id = get_user_id(request.username)
    if not user_id:
        return JSONResponse(status_code=404, content={"error": "User not found"})
    
    success = delete_conversation(request.conversation_id, user_id)
    
    if success:
        return JSONResponse(status_code=200, content={"message": "Conversation deleted successfully"})
    else:
        return JSONResponse(status_code=403, content={"error": "Forbidden or conversation not found"})