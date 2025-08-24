# frontend/components/sidebar.py
import streamlit as st
from services.api_client import get_conversations_from_api

def render_sidebar(authenticator, username): # Nhận thêm username
    with st.sidebar:
        st.markdown(f"#### Chào, *{username}*")
        authenticator.logout()
        st.markdown("---")

        if st.button("➕ Cuộc trò chuyện mới", use_container_width=True):
            # Khi tạo chat mới, xóa ID cuộc trò chuyện hiện tại
            st.session_state.conversation_id = None 
            st.session_state.messages = [
                {"role": "assistant", "content": "Xin chào! Tôi có thể giúp gì mới cho bạn?"}
            ]
            st.rerun()

        st.markdown("---")
        st.markdown("#### Lịch sử trò chuyện")
        
        conversations = get_conversations_from_api(username) 
        for convo in conversations:
            if st.button(convo['title'], key=convo['id'], use_container_width=True):
                # Khi click vào, lưu ID và đánh dấu cần tải lại
                st.session_state.conversation_id = convo['id']
                st.session_state.load_conversation = True # Dùng cờ để tải

        st.markdown("---")
        st.info("...")