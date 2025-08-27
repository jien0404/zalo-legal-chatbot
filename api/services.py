import json
import os
import logging
import google.generativeai as genai

from api.schemas import QueryRequest 
from core.database import (
    get_db_connection, add_message, get_user_id, add_conversation
)
from retriever.retrieval_system import RetrievalSystem

RERANKER_SCORE_THRESHOLD = 0.5

try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    print(f"Lỗi cấu hình Gemini API: {e}")

# --- Helper Functions ---
GREETING_KEYWORDS = ["chào", "hello", "hi", "xin chào"]
FAREWELL_KEYWORDS = ["tạm biệt", "bye", "bai bai"]
HELP_KEYWORDS = ["giúp", "cứu", "bạn làm được gì", "chức năng"]

def pre_filter_intent(query: str) -> str | None:
    """Bộ lọc siêu nhanh dựa trên từ khóa, chạy trước cả LLM."""
    lower_query = query.lower().strip()
    
    # Kiểm tra xem câu có BẮT ĐẦU bằng từ khóa không
    if any(lower_query.startswith(key) for key in GREETING_KEYWORDS):
        return "Greeting"
    if any(lower_query.startswith(key) for key in FAREWELL_KEYWORDS):
        return "Farewell"
    if any(lower_query.startswith(key) for key in HELP_KEYWORDS):
        return "Help Request"
        
    return None


def get_structured_input_analysis(query: str, is_first_message: bool) -> dict:
    """
    Một lệnh gọi LLM duy nhất để sửa chính tả, phân loại ý định,
    VÀ TẠO TIÊU ĐỀ cho tin nhắn đầu tiên. (Đã tối ưu cho Zalo Legal Dataset)
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        title_instruction = ""
        if is_first_message:
            title_instruction = """4. `conversation_title`: Dựa vào `corrected_query`, tạo một tiêu đề ngắn gọn (3-5 từ) cho cuộc trò chuyện. Nếu ý định không phải là "Legal Question", trả về null."""

        # === PROMPT MỚI ĐÃ ĐƯỢC TỐI ƯU HÓA ===
        prompt = f"""Bạn là một bộ xử lý ngôn ngữ đầu vào thông minh cho một trợ lý chuyên về pháp luật Việt Nam. 
Cơ sở dữ liệu của trợ lý này chứa các điều khoản, luật, và nghị định của Việt Nam.

Nhiệm vụ của bạn là phân tích câu hỏi của người dùng và trả về một đối tượng JSON duy nhất để quyết định xem câu hỏi đó có thể được trả lời bằng cách tra cứu trong cơ sở dữ liệu pháp luật hay không.

JSON trả về phải có các trường sau:
1.  `corrected_query`: Câu đã được sửa lỗi chính tả và ngữ pháp.
2.  `intent`: Phân loại ý định của câu. Quan trọng nhất là "Legal Question".
    - "Legal Question": Bất kỳ câu hỏi nào, dù là hỏi trực tiếp hay mô tả một tình huống, mà câu trả lời có thể nằm trong một văn bản pháp luật.
    - Các loại khác: "Greeting", "Farewell", "Help Request", "Other".
3.  `is_rag_required`: Luôn là `true` nếu intent là "Legal Question", ngược lại là `false`.
{title_instruction}

Ví dụ:
- Câu gốc: "Công ty nợ lương 2 tháng thì phải làm sao?"
- JSON trả về: {{"corrected_query": "Công ty nợ lương 2 tháng thì phải làm sao?", "intent": "Legal Question", "is_rag_required": true, "conversation_title": "Xử lý nợ lương"}}
- Câu gốc: "được nghỉ bao nhiêu ngày phép 1 năm"
- JSON trả về: {{"corrected_query": "Được nghỉ bao nhiêu ngày phép 1 năm?", "intent": "Legal Question", "is_rag_required": true, "conversation_title": "Quy định ngày phép"}}
- Câu gốc: "chao ban"
- JSON trả về: {{"corrected_query": "Chào bạn.", "intent": "Greeting", "is_rag_required": false, "conversation_title": null}}

---
Bây giờ, hãy xử lý câu sau đây. Chỉ trả về đối tượng JSON.
Câu gốc: "{query}"
"""
        
        response = model.generate_content(prompt)
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        analysis = json.loads(json_text)
        
        # Đảm bảo trường title luôn tồn tại, kể cả khi LLM quên
        if is_first_message and 'conversation_title' not in analysis:
            analysis['conversation_title'] = None
            
        return analysis

    except Exception as e:
        logging.error(f"Lỗi khi phân tích có cấu trúc: {e}")
        # Mặc định an toàn
        default_response = {
            "corrected_query": query,
            "intent": "Legal Question",
            "is_rag_required": True
        }
        if is_first_message:
            default_response['conversation_title'] = query[:30] + "..." # Tiêu đề tạm
        return default_response

def rewrite_query_with_history(chat_history: list) -> str:
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

def create_final_prompt(chat_history: list, source_context: str) -> str:
    current_question = chat_history[-1].content
    history_context = "\n".join([f"{'Người dùng' if msg.role == 'user' else 'Trợ lý'}: {msg.content}" for msg in chat_history[:-1]])
    return f"""**LỊCH SỬ TRÒ CHUYỆN:**\n---\n{history_context}\n---\n**KIẾN THỨC NỀN (Dùng để trả lời câu hỏi cuối cùng):**\n---\n{source_context}\n---\n**CÂU HỎI CUỐI CÙNG CỦA NGƯỜI DÙNG:** {current_question}\n---\n**HƯỚNG DẪN:**\nBạn là một trợ lý pháp lý chuyên nghiệp. Dựa vào KIẾN THỨC NỀN và LỊCH SỬ TRÒ CHUYỆN ở trên để trả lời câu hỏi cuối cùng của người dùng.\n- **Quan trọng:** Nhập vai một chuyên gia, trả lời trực tiếp, **không được nhắc đến "kiến thức nền" hay "nguồn được cung cấp"**.\n- Trích dẫn các nguồn liên quan bằng cách ghi `[Nguồn X]` ở cuối câu.\n- Nếu không có thông tin để trả lời, hãy nói rằng bạn không có thông tin về vấn đề này.\n\n**Câu trả lời của bạn:**"""

def stream_response_generator(request: QueryRequest, retriever: RetrievalSystem):
    conn = get_db_connection()
    try:
        # --- BƯỚC 1: LƯU TIN NHẮN CỦA NGƯỜI DÙNG NGAY LẬP TỨC ---
        user_message_content = request.chat_history[-1].content
        # === LỚP 1: BỘ LỌC NHANH ===
        fast_intent = pre_filter_intent(user_message_content)
        if fast_intent:
            logging.info(f"Phát hiện ý định nhanh: {fast_intent}")
            intent_responses = {
                "Greeting": "Chào bạn. Tôi là trợ lý pháp lý ảo. Bạn cần tôi giúp gì về pháp luật Việt Nam?",
                "Farewell": "Tạm biệt bạn. Nếu cần hỗ trợ, hãy liên hệ lại nhé!",
                "Help Request": "Tôi có thể trả lời các câu hỏi liên quan đến dữ liệu pháp luật được cung cấp. Bạn hãy đặt một câu hỏi cụ thể về một vấn đề pháp lý nhé."
            }
            response_text = intent_responses.get(fast_intent)
            yield f"data: {json.dumps({'text': response_text})}\n\n"
            return

        # === LỚP 2: LỆNH GỌI LLM THÔNG MINH ===
        is_new_conversation_thread = request.conversation_id is None
        analysis = get_structured_input_analysis(user_message_content, is_new_conversation_thread)
        corrected_query = analysis['corrected_query']

        # Cập nhật chat history với câu đã sửa
        request.chat_history[-1].content = corrected_query
        if corrected_query != user_message_content:
            logging.info(f"Sửa chính tả: '{user_message_content}' -> '{corrected_query}'")
        
        # === LOGIC "KHAI SINH" CUỘC TRÒ CHUYỆN MỚI ===
        if is_new_conversation_thread and analysis.get("conversation_title"):
            # Thời điểm để tạo và lưu trữ!
            title = analysis["conversation_title"]
            logging.info(f"Tạo cuộc trò chuyện mới với tiêu đề: '{title}'")
            
            # 1. Tạo cuộc trò chuyện trong DB
            user_id = get_user_id(conn, request.username)
            if not user_id: 
                # Xử lý trường hợp user không tồn tại, mặc dù hiếm
                raise Exception(f"User {request.username} không tìm thấy khi đang tạo convo.")
            created_convo_id = add_conversation(conn, user_id, title)

            # 2. Lưu TOÀN BỘ lịch sử chat "lơ lửng" vào DB
            for message in request.chat_history:
                add_message(conn, created_convo_id, message.role, message.content)
            
            # 3. Gửi thông tin về cho frontend để cập nhật state
            yield f"data: {json.dumps({'new_conversation': {'id': created_convo_id, 'title': title}})}\n\n"

            request.conversation_id = created_convo_id

        elif not is_new_conversation_thread:
            add_message(conn, request.conversation_id, "user", corrected_query)

        # === ĐỊNH TUYẾN DỰA TRÊN KẾT QUẢ PHÂN TÍCH ===
        if not analysis['is_rag_required']:
            # Xử lý các trường hợp small-talk khác mà bộ lọc nhanh bỏ lỡ
            intent = analysis['intent']
            response_text = "Tôi là trợ lý pháp luật và chỉ có thể giúp bạn các kiến thức trong lĩnh vực luật pháp mà thôi." 
            if intent == "Greeting":
                 response_text = "Chào bạn. Tôi có thể giúp gì cho bạn về pháp luật?"
            elif intent == "Farewell":
                 response_text = "Tạm biệt!"
            elif intent == "Help Request":
                 response_text = "Hãy đặt câu hỏi về pháp luật và tôi sẽ cố gắng trả lời dựa trên dữ liệu của mình."

            if request.conversation_id:
                add_message(conn, request.conversation_id, "assistant", response_text)
            yield f"data: {json.dumps({'text': response_text})}\n\n"
            return
        
        # --- BƯỚC 2: BIẾN ĐỔI CÂU HỎI VÀ RETRIEVAL (như cũ) ---
        standalone_question = rewrite_query_with_history(request.chat_history)
        retrieved_chunks = retriever.retrieve_chunks(standalone_question, top_k_rerank=request.top_k_rerank)

        # --- BƯỚC 3: KIỂM TRA "GÁC CỔNG" ---
        if not retrieved_chunks or retrieved_chunks[0]['score'] < RERANKER_SCORE_THRESHOLD:
            bot_response_content = "Tôi xin lỗi, tôi không tìm thấy thông tin đủ liên quan trong cơ sở dữ liệu để trả lời câu hỏi này."
            # Lưu lại câu trả lời "từ chối" của bot
            add_message(conn, request.conversation_id, "assistant", bot_response_content)
            # Stream câu trả lời này về và kết thúc
            yield f"data: {json.dumps({'text': bot_response_content})}\n\n"
            return

        high_quality_chunks = [chunk for chunk in retrieved_chunks if chunk['score'] >= RERANKER_SCORE_THRESHOLD]
        if not high_quality_chunks:
            bot_response_content = "Mặc dù đã tìm thấy một vài thông tin, nhưng chúng không đủ độ tin cậy để đưa ra câu trả lời chính xác."
            # Lưu lại câu trả lời "từ chối" của bot
            add_message(conn, request.conversation_id, "assistant", bot_response_content)
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
            add_message(conn, request.conversation_id, "assistant", full_bot_response, sources_data)

        except Exception as e:
            error_message = f"Lỗi khi gọi Gemini API: {e}"
            # Lưu lại thông báo lỗi
            add_message(conn, request.conversation_id, "assistant", error_message)
            yield f"data: {json.dumps({'text': error_message})}\n\n"
    finally:
        if conn:
            conn.close()