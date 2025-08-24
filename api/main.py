# api/main.py
import os
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from dotenv import load_dotenv

# === THAY ĐỔI 1: Import thư viện Gemini ===
import google.generativeai as genai

from .dependencies import get_retriever
from retriever.retrieval_system import RetrievalSystem

load_dotenv()

app = FastAPI(
    title="Zalo Legal RAG API",
    description="API for a Retrieval-Augmented Generation system on legal documents"
)

RERANKER_SCORE_THRESHOLD = 0.3 

# === THAY ĐỔI 2: Cấu hình API Key cho Gemini ===
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    print(f"Lỗi cấu hình Gemini API: {e}")


# === SỬA ĐỔI: Pydantic models để nhận lịch sử chat ===
class ChatMessage(BaseModel):
    role: str
    content: str

class QueryRequest(BaseModel):
    # Thêm trường chat_history
    chat_history: list[ChatMessage]
    # Câu hỏi mới nhất sẽ là tin nhắn cuối cùng trong history
    top_k_rerank: int = 5

class AnswerResponse(BaseModel):
    answer: str
    sources: list[dict]

def format_prompt(chat_history: list[ChatMessage]) -> str:
    """Tạo prompt cho LLM từ toàn bộ lịch sử chat."""
    
    # Lấy câu hỏi mới nhất của người dùng
    current_question = chat_history[-1].content
    
    # Xây dựng context từ các tin nhắn trước đó (trừ câu hỏi hiện tại)
    history_context = ""
    # Chỉ lấy 10 tin nhắn gần nhất để tránh vượt token limit
    for message in chat_history[-11:-1]: 
        role = "Người dùng" if message.role == "user" else "Trợ lý"
        history_context += f"{role}: {message.content}\n"
    
    prompt = f"""Bạn là một trợ lý chuyên về pháp luật Việt Nam. Dựa vào lịch sử cuộc trò chuyện và các nguồn thông tin được cung cấp để trả lời câu hỏi MỚI NHẤT của người dùng.

**Lịch sử cuộc trò chuyện gần đây:**
---
{history_context}---

**Câu hỏi MỚI NHẤT của người dùng:** {current_question}

**Nhiệm vụ:**
1.  Hiểu câu hỏi MỚI NHẤT trong ngữ cảnh của cuộc trò chuyện.
2.  Dựa vào các NGUỒN THÔNG TIN TÌM KIẾM được (sẽ được thêm vào sau) để trả lời.
3.  Nếu lịch sử hoặc các nguồn không đủ thông tin, hãy nói bạn không biết.

Đây là các nguồn thông tin tìm kiếm được liên quan đến câu hỏi mới nhất:
"""
    return prompt


def is_legal_question(question: str) -> bool:
    """Sử dụng LLM để phân loại câu hỏi."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = f"""Câu hỏi sau đây có liên quan đến pháp luật Việt Nam không? Chỉ trả lời "Có" hoặc "Không".
Câu hỏi: "{question}"
Trả lời:"""
        response = model.generate_content(prompt)
        # Chuẩn hóa output: loại bỏ khoảng trắng, viết thường
        answer = response.text.strip().lower()
        return "có" in answer
    except Exception:
        return True # Mặc định là có nếu API lỗi để không chặn nhầm

@app.post("/generate_answer", response_model=AnswerResponse)
def generate_answer(request: QueryRequest, retriever: RetrievalSystem = Depends(get_retriever)):
    current_question = request.chat_history[-1].content

    # if not is_legal_question(current_question): 
    #     return AnswerResponse(
    #         answer="Tôi là trợ lý pháp lý và chỉ có thể trả lời các câu hỏi liên quan đến pháp luật.",
    #         sources=[]
    #     )
    
    retrieved_chunks = retriever.retrieve_chunks(current_question, top_k_rerank=request.top_k_rerank)

    if not retrieved_chunks:
        return AnswerResponse(answer="Không tìm thấy tài liệu liên quan.", sources=[])
    
    best_chunk_score = retrieved_chunks[0]['score']
    if best_chunk_score < RERANKER_SCORE_THRESHOLD:
        return AnswerResponse(
            answer="Tôi xin lỗi, tôi không tìm thấy thông tin đủ liên quan trong cơ sở dữ liệu để trả lời câu hỏi này.",
            sources=retrieved_chunks 
        )
    
    source_context = ""
    for i, chunk in enumerate(retrieved_chunks):
        source_context += f"Nguồn {i+1} (từ văn bản {chunk['doc_id']}):\n\"\"\"\n{chunk['text']}\n\"\"\"\n\n"

    final_prompt = format_prompt(request.chat_history) + source_context
    
    # === THAY ĐỔI 3: Gọi API Gemini thay vì OpenAI ===
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(final_prompt)
        answer = response.text
    except Exception as e:
        return AnswerResponse(answer=f"Lỗi khi gọi Gemini API: {e}", sources=retrieved_chunks)

    return AnswerResponse(answer=answer, sources=retrieved_chunks)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Zalo Legal RAG API (Gemini Edition)"}