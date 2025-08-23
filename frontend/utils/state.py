# frontend/utils/state.py
import streamlit as st

def initialize_session_state():
    """Khởi tạo session_state nếu chưa có."""
    if "messages" not in st.session_state:
        # Bắt đầu với một tin nhắn chào mừng từ bot
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Xin chào! Tôi có thể giúp gì cho bạn về pháp luật Việt Nam?"
            }
        ]