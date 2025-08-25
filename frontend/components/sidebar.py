# frontend/components/sidebar.py
import streamlit as st
from services.api_client import get_conversations_from_api, delete_conversation_on_api, update_conversation_title_on_api
from style import inject_custom_css 

def render_sidebar(authenticator, username):
    # Tải CSS ngay từ đầu
    inject_custom_css()

    with st.sidebar:
        # --- Phần thông tin người dùng ---
        with st.container():
            st.markdown(f"#### Chào, *{username}*")
            authenticator.logout("Logout", "main")
        
        st.markdown("---", unsafe_allow_html=True)

        # --- Nút tạo cuộc trò chuyện mới ---
        if st.button("➕ Cuộc trò chuyện mới", use_container_width=True):
            st.session_state.conversation_id = None 
            st.session_state.messages = [{"role": "assistant", "content": "Xin chào! Tôi có thể giúp gì mới cho bạn?"}]
            if 'editing_convo_id' in st.session_state:
                del st.session_state.editing_convo_id
            st.rerun()

        st.markdown("---", unsafe_allow_html=True)
        st.markdown("#### Lịch sử trò chuyện")
        
        conversations = get_conversations_from_api(username)
        editing_convo_id = st.session_state.get('editing_convo_id')

        # Dùng st.empty để chứa danh sách, giúp giao diện mượt hơn khi cập nhật
        history_container = st.empty()
        
        with history_container.container():
            for convo in conversations:
                is_active = (st.session_state.get("conversation_id") == convo['id'])
                
                # Chế độ chỉnh sửa
                if editing_convo_id == convo['id']:
                    with st.form(key=f"edit_form_{convo['id']}"):
                        st.markdown('<div class="edit-form">', unsafe_allow_html=True)
                        new_title = st.text_input("Đổi tên:", value=convo['title'], label_visibility="collapsed")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Lưu", use_container_width=True, type="primary"):
                                if new_title.strip():
                                    update_conversation_title_on_api(username, convo['id'], new_title.strip())
                                    del st.session_state.editing_convo_id
                                    st.rerun()
                                else:
                                    st.warning("Tiêu đề không được trống.")
                        with col2:
                            if st.form_submit_button("Hủy", use_container_width=True):
                                del st.session_state.editing_convo_id
                                st.rerun()
                else:
                    # Chế độ hiển thị bình thường (ĐÃ SỬA)
                    active_class = "active" if is_active else ""
                    
                    # Bọc toàn bộ trong một container markdown để áp dụng CSS
                    st.markdown(f'<div class="chat-history-item {active_class}">', unsafe_allow_html=True)

                    # Sử dụng MỘT LẦN st.columns duy nhất với vertical_alignment="center"
                    # Đây là thay đổi quan trọng nhất để căn chỉnh mọi thứ thẳng hàng
                    col1, col2, col3 = st.columns([0.7, 0.15, 0.15], vertical_alignment="center")

                    with col1:
                        # Nút tiêu đề
                        if st.button(convo['title'], key=f"select_{convo['id']}", use_container_width=True):
                            st.session_state.conversation_id = convo['id']
                            st.session_state.load_conversation = True
                            if 'editing_convo_id' in st.session_state:
                                del st.session_state.editing_convo_id
                            st.rerun()

                    # Đặt các nút Sửa và Xóa vào container riêng để CSS có thể ẩn/hiện chúng
                    with st.container():
                        st.markdown('<div class="chat-item-buttons">', unsafe_allow_html=True)
                        
                        with col2:
                            # Nút sửa
                            if st.button("✏️", key=f"edit_{convo['id']}", help="Sửa tiêu đề"):
                                st.session_state.editing_convo_id = convo['id']
                                st.rerun()
                        
                        with col3:
                            # Nút xóa
                            if st.button("🗑️", key=f"delete_{convo['id']}", help="Xóa cuộc trò chuyện"):
                                delete_conversation_on_api(username, convo['id'])
                                if st.session_state.get("conversation_id") == convo['id']:
                                    st.session_state.conversation_id = None
                                    st.session_state.messages = [{"role": "assistant", "content": "Xin chào! Tôi có thể giúp gì cho bạn?"}]
                                if 'editing_convo_id' in st.session_state:
                                    del st.session_state.editing_convo_id
                                st.rerun()
                        