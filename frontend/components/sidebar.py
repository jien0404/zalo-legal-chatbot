# frontend/components/sidebar.py
import streamlit as st

# Sửa hàm để nhận vào authenticator
def render_sidebar(authenticator):
    """Hiển thị sidebar và các chức năng của nó."""
    with st.sidebar:
        st.markdown("## ⚖️ Zalo Legal Bot")
        st.markdown("Trợ lý Hỏi-Đáp Pháp luật")
        st.markdown("---")
        
        # Thêm nút Logout từ authenticator
        authenticator.logout(key='unique_key', location='main')
        
        st.markdown("---")
        
        if st.button("➕ Cuộc trò chuyện mới", use_container_width=True):
            st.session_state.messages = [
                {"role": "assistant", "content": "Xin chào! Tôi có thể giúp gì mới cho bạn?"}
            ]
            st.rerun()

        st.markdown("---")
        st.info(
            "**Lưu ý:** Hệ thống này được xây dựng cho mục đích thử nghiệm."
            " Mọi thông tin chỉ mang tính chất tham khảo."
        )