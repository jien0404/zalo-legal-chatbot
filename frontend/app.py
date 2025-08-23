# frontend/app.py
import streamlit as st

from utils.state import initialize_session_state
from services.api_client import get_answer_from_api
from components.sidebar import render_sidebar
from components.chat_elements import display_chat_message
from style import inject_custom_css

# --- Cấu hình trang và UI ---
st.set_page_config(
    page_title="Hỏi Đáp Pháp Luật", 
    layout="wide", 
    initial_sidebar_state="expanded"
)
inject_custom_css()
render_sidebar()
st.header("⚖️ Trò chuyện cùng Trợ lý Pháp luật")
st.caption("Được hỗ trợ bởi các mô hình AI tiên tiến")

# --- Khởi tạo trạng thái session ---
initialize_session_state()

# --- Hiển thị lịch sử chat ---
# Vòng lặp này sẽ vẽ lại toàn bộ cuộc trò chuyện mỗi khi có thay đổi
for message in st.session_state.messages:
    display_chat_message(message)

# 1. Xử lý input của người dùng và thêm vào state ngay lập tức
if prompt := st.chat_input("Nhập câu hỏi của bạn ở đây..."):
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)
    # Ngay sau khi thêm, chạy lại script để tin nhắn của người dùng
    # được hiển thị ngay lập tức mà không cần chờ bot.
    st.rerun()

# 2. Kiểm tra xem bot có cần trả lời hay không
# Logic này sẽ chạy sau khi st.rerun() ở trên được thực thi
# Nó kiểm tra xem tin nhắn cuối cùng có phải của người dùng không
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_user_prompt = st.session_state.messages[-1]["content"]
    
    # Hiển thị spinner và gọi API
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Bot đang suy nghĩ..."):
            api_response = get_answer_from_api(last_user_prompt)
            
            if "error" in api_response:
                bot_response_content = api_response["error"]
                bot_response_sources = None
            else:
                bot_response_content = api_response.get("answer", "Xin lỗi, đã có lỗi xảy ra.")
                bot_response_sources = api_response.get("sources")

            # Tạo tin nhắn đầy đủ của bot
            bot_message = {
                "role": "assistant",
                "content": bot_response_content,
                "sources": bot_response_sources
            }
            # Thêm tin nhắn của bot vào lịch sử
            st.session_state.messages.append(bot_message)
            
            # Chạy lại script một lần nữa để vẽ tin nhắn của bot lên màn hình
            st.rerun()