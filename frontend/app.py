# frontend/app.py
import streamlit as st
import time

from utils.state import initialize_session_state
from services.api_client import get_answer_stream_from_api
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

# --- Khởi tạo và hiển thị lịch sử ---
initialize_session_state()
for message in st.session_state.messages:
    display_chat_message(message)

# --- Xử lý input ---
if prompt := st.chat_input("Nhập câu hỏi của bạn ở đây..."):
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)
    st.rerun()

# --- Logic stream đã được cải tiến ---
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    
    with st.chat_message("assistant", avatar="🤖"):
        placeholder = st.empty()
        
        # === THAY ĐỔI 1: Hiển thị trạng thái "đang suy nghĩ" ban đầu ===
        thinking_message = "🤔 Bot đang suy nghĩ..."
        placeholder.markdown(thinking_message)
        
        full_response = ""
        sources = None
        
        # Lấy stream từ API
        stream = get_answer_stream_from_api(st.session_state.messages)
        
        # === THAY ĐỔI 2: Xử lý chunk đầu tiên một cách đặc biệt ===
        is_first_chunk = True
        
        for chunk in stream:
            if "error" in chunk:
                full_response = chunk["error"]
                placeholder.error(full_response)
                break
            
            if "sources" in chunk:
                sources = chunk["sources"]
                continue
            
            if "text" in chunk:
                # Nếu là chunk đầu tiên, xóa thông báo "đang suy nghĩ"
                if is_first_chunk:
                    full_response = chunk["text"]
                    is_first_chunk = False
                else:
                    full_response += chunk["text"]
                
                # Cập nhật placeholder với hiệu ứng typing mượt mà hơn
                placeholder.markdown(full_response + "▌")
        
        # Cập nhật lần cuối không có con trỏ
        placeholder.markdown(full_response)

        # Lưu tin nhắn hoàn chỉnh vào session state
        bot_message = {
            "role": "assistant",
            "content": full_response,
            "sources": sources
        }
        # Chỉ thêm vào nếu nó chưa tồn tại (tránh trùng lặp khi rerun)
        if st.session_state.messages[-1] != bot_message:
            st.session_state.messages.append(bot_message)
            # Chạy lại lần cuối để ổn định giao diện và hiển thị sources đúng cách
            st.rerun()