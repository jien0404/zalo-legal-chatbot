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


# Pydantic models (giữ nguyên)
class QueryRequest(BaseModel):
    question: str
    top_k_rerank: int = 5

class AnswerResponse(BaseModel):
    answer: str
    sources: list[dict]

# Hàm format_prompt (giữ nguyên)
def format_prompt(question: str, context_chunks: list[dict]) -> str:
    """Tạo prompt cho LLM với chỉ thị rõ ràng."""
    context = ""
    for i, chunk in enumerate(context_chunks):
        # Chỉ lấy 250 từ đầu của mỗi chunk để prompt gọn hơn
        shortened_text = " ".join(chunk['text'].split()[:250])
        context += f"Nguồn {i+1} (từ văn bản {chunk['doc_id']}):\n\"\"\"\n{shortened_text}...\n\"\"\"\n\n"
    
    prompt = f"""Bạn là một trợ lý chuyên về pháp luật Việt Nam. Nhiệm vụ của bạn là trả lời câu hỏi của người dùng DỰA VÀ CHỈ DỰA VÀO các nguồn thông tin được cung cấp dưới đây.

**Quy tắc bắt buộc:**
1.  Đọc kỹ câu hỏi và tất cả các nguồn.
2.  **Trước tiên, hãy tự xác định xem các nguồn này có chứa đủ thông tin để trả lời câu hỏi không.**
3.  **Nếu các nguồn KHÔNG chứa thông tin liên quan để trả lời, HÃY TRẢ LỜI CHÍNH XÁC LÀ:** "Tôi không tìm thấy thông tin để trả lời câu hỏi này trong các tài liệu được cung cấp."
4.  Nếu thông tin có trong các nguồn, hãy tổng hợp lại và trả lời một cách súc tích, chuyên nghiệp. Trích dẫn nguồn tin liên quan nhất bằng cách ghi `[Nguồn X]` ở cuối câu trả lời.

**Thông tin các nguồn:**
{context}
**Câu hỏi của người dùng:** {question}

**Câu trả lời của bạn:**
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
    # if not is_legal_question(request.question):
    #     return AnswerResponse(
    #         answer="Tôi là trợ lý pháp lý và chỉ có thể trả lời các câu hỏi liên quan đến pháp luật.",
    #         sources=[]
    #     )
    
    retrieved_chunks = retriever.retrieve_chunks(request.question, top_k_rerank=request.top_k_rerank)

    if not retrieved_chunks:
        return AnswerResponse(answer="Không tìm thấy tài liệu liên quan.", sources=[])
    
    best_chunk_score = retrieved_chunks[0]['score']
    if best_chunk_score < RERANKER_SCORE_THRESHOLD:
        return AnswerResponse(
            answer="Tôi xin lỗi, tôi không tìm thấy thông tin đủ liên quan trong cơ sở dữ liệu để trả lời câu hỏi này.",
            sources=retrieved_chunks 
        )

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