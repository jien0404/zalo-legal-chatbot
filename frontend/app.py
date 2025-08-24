# frontend/app.py
import streamlit as st
import time

from utils.state import initialize_session_state
from services.api_client import get_answer_stream_from_api
from components.sidebar import render_sidebar
from components.chat_elements import display_chat_message
from style import inject_custom_css
from auth_manager import initialize_authenticator

# --- Cấu hình trang và UI ---
st.set_page_config(
    page_title="Hỏi Đáp Pháp Luật", 
    layout="wide", 
    initial_sidebar_state="expanded"
)
inject_custom_css()

# --- XÁC THỰC NGƯỜI DÙNG ---
authenticator = initialize_authenticator()
name, authentication_status, username = authenticator.login(fields={'Form name': 'Login', 'Location': 'main'})

# --- LUỒNG XỬ LÝ DỰA TRÊN TRẠNG THÁI XÁC THỰC ---
if authentication_status is False:
    st.error('Tên người dùng/mật khẩu không chính xác')
elif authentication_status is None:
    st.warning('Vui lòng nhập tên người dùng và mật khẩu của bạn')
elif authentication_status is True:
    render_sidebar(authenticator)
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
            placeholder.markdown("🤔 Bot đang suy nghĩ...")
            
            full_response_content = ""
            sources = None
            
            stream = get_answer_stream_from_api(st.session_state.messages)
            
            # Biến để đảm bảo thông báo "suy nghĩ" bị xóa ở chunk đầu tiên
            is_first_chunk = True
            
            for chunk in stream:
                if "error" in chunk:
                    full_response_content = chunk["error"]
                    placeholder.error(full_response_content)
                    break
                
                if "sources" in chunk:
                    sources = chunk["sources"]
                    continue
                
                if "text" in chunk:
                    # Nếu là chunk đầu tiên, xóa thông báo "đang suy nghĩ"
                    if is_first_chunk:
                        placeholder.empty()
                        is_first_chunk = False

                    # === THAY ĐỔI CỐT LÕI NẰM Ở ĐÂY ===
                    # Lặp qua từng ký tự trong chunk text nhận được
                    for char in chunk["text"]:
                        full_response_content += char
                        placeholder.markdown(full_response_content + "▌")
                        time.sleep(0.01) # Tốc độ gõ chữ, có thể điều chỉnh
            
            # Cập nhật lần cuối không có con trỏ
            placeholder.markdown(full_response_content)

            # Lưu tin nhắn hoàn chỉnh vào session state
            bot_message = {
                "role": "assistant",
                "content": full_response_content,
                "sources": sources
            }
            if st.session_state.messages[-1] != bot_message:
                st.session_state.messages.append(bot_message)
                st.rerun()