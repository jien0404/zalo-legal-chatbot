# api/main.py
import os
import json
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

from .dependencies import get_retriever
from retriever.retrieval_system import RetrievalSystem

load_dotenv()

app = FastAPI(title="Zalo Legal RAG API")
RERANKER_SCORE_THRESHOLD = 0.5

try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    print(f"Lỗi cấu hình Gemini API: {e}")

# Pydantic models (giữ nguyên)
class ChatMessage(BaseModel):
    role: str
    content: str

class QueryRequest(BaseModel):
    chat_history: list[ChatMessage]
    top_k_rerank: int = 5

# --- Các hàm Helper (giữ nguyên) ---
def rewrite_query_with_history(chat_history: list[ChatMessage]) -> str:
    # ... (code của hàm này giữ nguyên, không cần thay đổi)
    if len(chat_history) == 1:
        return chat_history[0].content
    history_str = "\n".join([f"{'Người dùng' if msg.role == 'user' else 'Trợ lý'}: {msg.content}" for msg in chat_history[:-1]])
    current_question = chat_history[-1].content
    prompt = f"""Dựa vào lịch sử trò chuyện, viết lại câu hỏi cuối cùng thành một câu hỏi độc lập, đầy đủ ngữ nghĩa để tìm kiếm. Nếu câu hỏi đã đủ nghĩa, trả về chính nó.
Lịch sử trò chuyện:
{history_str}
Câu hỏi cuối cùng: {current_question}
Câu hỏi độc lập:"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Lỗi khi biến đổi câu hỏi: {e}")
        return current_question

def create_final_prompt(chat_history: list[ChatMessage], source_context: str) -> str:
    # ... (code của hàm này giữ nguyên, không cần thay đổi)
    current_question = chat_history[-1].content
    history_context = "\n".join([f"{'Người dùng' if msg.role == 'user' else 'Trợ lý'}: {msg.content}" for msg in chat_history[:-1]])
    prompt = f"""
**LỊCH SỬ TRÒ CHUYỆN:**
---
{history_context}
---
**KIẾN THỨC NỀN (Dùng để trả lời câu hỏi cuối cùng):**
---
{source_context}
---
**CÂU HỎI CUỐI CÙNG CỦA NGƯỜI DÙNG:** {current_question}
---
**HƯỚNG DẪN:**
Bạn là một trợ lý pháp lý chuyên nghiệp. Dựa vào KIẾN THỨC NỀN và LỊCH SỬ TRÒ CHUYỆN ở trên để trả lời câu hỏi cuối cùng của người dùng.
- **Quan trọng:** Nhập vai một chuyên gia, trả lời trực tiếp, **không được nhắc đến "kiến thức nền" hay "nguồn được cung cấp"**.
- Trích dẫn các nguồn liên quan bằng cách ghi `[Nguồn X]` ở cuối câu.
- Nếu không có thông tin để trả lời, hãy nói rằng bạn không có thông tin về vấn đề này.
**Câu trả lời của bạn:**
"""
    return prompt


# === THAY ĐỔI LỚN: TẠO MỘT GENERATOR ĐỂ STREAM DỮ LIỆU ===
def stream_response_generator(request: QueryRequest, retriever: RetrievalSystem):
    # Bước 1: Biến đổi câu hỏi (giữ nguyên)
    standalone_question = rewrite_query_with_history(request.chat_history)
    
    # Bước 2: Retrieval (giữ nguyên)
    retrieved_chunks = retriever.retrieve_chunks(standalone_question, top_k_rerank=request.top_k_rerank)

    # Bước 3: Lọc và kiểm tra ngưỡng (giữ nguyên)
    if not retrieved_chunks or retrieved_chunks[0]['score'] < RERANKER_SCORE_THRESHOLD:
        error_message = "Tôi xin lỗi, tôi không tìm thấy thông tin đủ liên quan trong cơ sở dữ liệu để trả lời câu hỏi này."
        yield f"data: {json.dumps({'text': error_message})}\n\n"
        return

    high_quality_chunks = [chunk for chunk in retrieved_chunks if chunk['score'] >= RERANKER_SCORE_THRESHOLD]
    if not high_quality_chunks:
        error_message = "Mặc dù đã tìm thấy một vài thông tin, nhưng chúng không đủ độ tin cậy để đưa ra câu trả lời chính xác."
        yield f"data: {json.dumps({'text': error_message})}\n\n"
        return

    # Bước 4: Gửi các nguồn (sources) về trước
    # Chúng ta gửi sources như một chunk dữ liệu đặc biệt
    sources_data = [
        {"doc_id": chunk["doc_id"], "text": chunk["text"], "score": chunk["score"]} 
        for chunk in high_quality_chunks
    ]
    yield f"data: {json.dumps({'sources': sources_data})}\n\n"

    # Bước 5: Tạo prompt và gọi Gemini ở chế độ stream
    source_context = "\n\n".join(
        [f"Nguồn {i+1} (từ văn bản {chunk['doc_id']}):\n\"\"\"\n{chunk['text']}\n\"\"\"" 
         for i, chunk in enumerate(high_quality_chunks)]
    )
    final_prompt = create_final_prompt(request.chat_history, source_context)
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        # Gọi API với stream=True
        stream = model.generate_content(final_prompt, stream=True)
        
        # Lặp qua từng chunk text từ stream và gửi về frontend
        for chunk in stream:
            if chunk.text:
                yield f"data: {json.dumps({'text': chunk.text})}\n\n"
    except Exception as e:
        error_message = f"Lỗi khi gọi Gemini API: {e}"
        yield f"data: {json.dumps({'text': error_message})}\n\n"

@app.post("/generate_answer") # Bỏ response_model vì chúng ta đang stream
def generate_answer(request: QueryRequest, retriever: RetrievalSystem = Depends(get_retriever)):
    return StreamingResponse(
        stream_response_generator(request, retriever),
        media_type="text/event-stream"
    )

@app.get("/")
def read_root():
    return {"message": "Welcome to the Zalo Legal RAG API"}