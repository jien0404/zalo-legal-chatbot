# api/main.py
import os
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

from .dependencies import get_retriever
from retriever.retrieval_system import RetrievalSystem

load_dotenv()

app = FastAPI(
    title="Zalo Legal RAG API",
    description="API for a Retrieval-Augmented Generation system on legal documents"
)

RERANKER_SCORE_THRESHOLD = 0.7
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    print(f"Lỗi cấu hình Gemini API: {e}")

class ChatMessage(BaseModel):
    role: str
    content: str

class QueryRequest(BaseModel):
    chat_history: list[ChatMessage]
    top_k_rerank: int = 5

class AnswerResponse(BaseModel):
    answer: str
    sources: list[dict]

def rewrite_query_with_history(chat_history: list[ChatMessage]) -> str:
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
    # Lấy câu hỏi mới nhất để nhấn mạnh
    current_question = chat_history[-1].content
    
    # Xây dựng lịch sử chat (không bao gồm câu hỏi hiện tại để tránh lặp lại)
    history_context = "\n".join(
        [f"{'Người dùng' if msg.role == 'user' else 'Trợ lý'}: {msg.content}" 
         for msg in chat_history[:-1]]
    )

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

@app.post("/generate_answer", response_model=AnswerResponse)
def generate_answer(request: QueryRequest, retriever: RetrievalSystem = Depends(get_retriever)):
    
    standalone_question = rewrite_query_with_history(request.chat_history)
    
    retrieved_chunks = retriever.retrieve_chunks(standalone_question, top_k_rerank=request.top_k_rerank)

    if not retrieved_chunks:
        return AnswerResponse(answer="Không tìm thấy tài liệu liên quan.", sources=[])
    
    if retrieved_chunks[0]['score'] < RERANKER_SCORE_THRESHOLD:
        return AnswerResponse(
            answer="Tôi xin lỗi, tôi không tìm thấy thông tin đủ liên quan trong cơ sở dữ liệu để trả lời câu hỏi này.",
            sources=retrieved_chunks 
        )
    
    high_quality_chunks = [chunk for chunk in retrieved_chunks if chunk['score'] >= RERANKER_SCORE_THRESHOLD]

    if not high_quality_chunks:
        return AnswerResponse(
            answer="Mặc dù đã tìm thấy một vài thông tin, nhưng chúng không đủ độ tin cậy để đưa ra câu trả lời chính xác.",
            sources=retrieved_chunks
        )

    source_context = "\n\n".join(
        [f"Nguồn {i+1} (từ văn bản {chunk['doc_id']}):\n\"\"\"\n{chunk['text']}\n\"\"\"" 
         for i, chunk in enumerate(high_quality_chunks)]
    )

    final_prompt = create_final_prompt(request.chat_history, source_context)
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(final_prompt)
        answer = response.text
    except Exception as e:
        return AnswerResponse(answer=f"Lỗi khi gọi Gemini API: {e}", sources=high_quality_chunks)

    return AnswerResponse(answer=answer, sources=high_quality_chunks)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Zalo Legal RAG API"}