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

# === THAY ĐỔI 2: Cấu hình API Key cho Gemini ===
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    print(f"Lỗi cấu hình Gemini API: {e}")


# Pydantic models (giữ nguyên)
class QueryRequest(BaseModel):
    question: str
    top_k_rerank: int = 5

class AnswerResponse(BaseModel):
    answer: str
    sources: list[dict]

# Hàm format_prompt (giữ nguyên)
def format_prompt(question: str, context_chunks: list[dict]) -> str:
    context = ""
    for i, chunk in enumerate(context_chunks):
        context += f"Nguồn {i+1} (từ văn bản {chunk['doc_id']}):\n\"\"\"\n{chunk['text']}\n\"\"\"\n\n"
    
    prompt = f"""Dựa vào các nguồn thông tin được cung cấp dưới đây để trả lời câu hỏi của người dùng một cách chính xác và súc tích.
Chỉ sử dụng thông tin từ các nguồn đã cho, không được bịa đặt hay thêm thông tin ngoài lề.
Nếu thông tin không có trong các nguồn, hãy trả lời là "Tôi không tìm thấy thông tin để trả lời câu hỏi này trong các tài liệu được cung cấp."

{context}
Câu hỏi của người dùng: {question}
Câu trả lời của bạn:
"""
    return prompt

@app.post("/generate_answer", response_model=AnswerResponse)
def generate_answer(request: QueryRequest, retriever: RetrievalSystem = Depends(get_retriever)):
    retrieved_chunks = retriever.retrieve_chunks(request.question, top_k_rerank=request.top_k_rerank)

    if not retrieved_chunks:
        return AnswerResponse(answer="Không tìm thấy tài liệu liên quan.", sources=[])

    prompt = format_prompt(request.question, retrieved_chunks)
    
    # === THAY ĐỔI 3: Gọi API Gemini thay vì OpenAI ===
    try:
        # 1. Khởi tạo model
        model = genai.GenerativeModel('gemini-1.5-flash-latest') # Hoặc 'gemini-pro'
        
        # 2. Sinh câu trả lời
        response = model.generate_content(prompt)
        
        # 3. Lấy text từ response
        answer = response.text

    except Exception as e:
        return AnswerResponse(answer=f"Lỗi khi gọi Gemini API: {e}", sources=retrieved_chunks)
    # === KẾT THÚC THAY ĐỔI ===

    return AnswerResponse(answer=answer, sources=retrieved_chunks)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Zalo Legal RAG API (Gemini Edition)"}