# api/main.py
import os
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

from .dependencies import get_retriever
from retriever.retrieval_system import RetrievalSystem

load_dotenv()

app = FastAPI(
    title="Zalo Legal RAG API",
    description="API for a Retrieval-Augmented Generation system on legal documents"
)

# Khởi tạo OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Pydantic models để validate request và response
class QueryRequest(BaseModel):
    question: str
    top_k_rerank: int = 5

class AnswerResponse(BaseModel):
    answer: str
    sources: list[dict]

def format_prompt(question: str, context_chunks: list[dict]) -> str:
    """Tạo prompt cho LLM."""
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
    """
    Endpoint chính: Nhận câu hỏi, retrieve context, và sinh câu trả lời.
    """
    # 1. Retrieve relevant chunks
    retrieved_chunks = retriever.retrieve_chunks(request.question, top_k_rerank=request.top_k_rerank)

    if not retrieved_chunks:
        return AnswerResponse(answer="Không tìm thấy tài liệu liên quan.", sources=[])

    # 2. Tạo prompt và gọi LLM
    prompt = format_prompt(request.question, retrieved_chunks)
    
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo", # Hoặc "gpt-4"
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý pháp lý hữu ích."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        answer = completion.choices[0].message.content
    except Exception as e:
        return AnswerResponse(answer=f"Lỗi khi gọi LLM: {e}", sources=retrieved_chunks)

    # 3. Trả về câu trả lời và nguồn
    return AnswerResponse(answer=answer, sources=retrieved_chunks)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Zalo Legal RAG API"}