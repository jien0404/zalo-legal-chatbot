# frontend/components/sidebar.py
import streamlit as st
from services.api_client import get_conversations_from_api, delete_conversation_on_api

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
            # Tạo hai cột: một cho tên, một cho nút xóa
            col1, col2 = st.columns([4, 1])
            
            with col1:
                # Nút chọn cuộc trò chuyện (chiếm phần lớn không gian)
                if st.button(convo['title'], key=f"select_{convo['id']}", use_container_width=True):
                    st.session_state.conversation_id = convo['id']
                    st.session_state.load_conversation = True
                    st.rerun()

            with col2:
                # Nút xóa (chiếm phần nhỏ)
                if st.button("🗑️", key=f"delete_{convo['id']}", help="Xóa cuộc trò chuyện này"):
                    delete_conversation_on_api(username, convo['id'])
                    # Nếu đang xem cuộc trò chuyện bị xóa, hãy reset lại
                    if st.session_state.get("conversation_id") == convo['id']:
                        st.session_state.conversation_id = None
                        st.session_state.messages = [
                            {"role": "assistant", "content": "Xin chào! Tôi có thể giúp gì cho bạn?"}
                        ]
                    st.rerun()