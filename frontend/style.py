# frontend/style.py
import streamlit as st

def inject_custom_css():
    """Hàm này sẽ inject CSS tùy chỉnh vào ứng dụng Streamlit."""
    css = """
        <style>
            /* --- CÀI ĐẶT CHUNG --- */
            .main .block-container {
                max-width: 900px;
                padding-top: 2rem;
                padding-bottom: 2rem;
            }
            [data-testid="stSidebar"] {
                width: 320px !important;
            }
            
            /* --- TIN NHẮN CỦA BOT (BÊN TRÁI) --- */
            [data-testid="stChatMessage"]:has(span[data-testid="stChatAvatarIcon-assistant"]) {
                background-color: #F0F2F6;
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 10px;
                color: #1a1a1a;
                max-width: 85%; /* Thêm max-width để trông gọn hơn */
            }
            [data-testid="stChatMessage"]:has(span[data-testid="stChatAvatarIcon-assistant"]) p {
                 color: #1a1a1a;
            }

            /* --- TIN NHẮN CỦA NGƯỜI DÙNG (BÊN PHẢI) --- */
            [data-testid="stChatMessage"]:has(span[data-testid="stChatAvatarIcon-user"]) {
                flex-direction: row-reverse;
                background-color: #0057FF;
                color: white;
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 10px;
                max-width: 85%; /* Thêm max-width */
                margin-left: auto; /* === ĐÂY LÀ THAY ĐỔI QUAN TRỌNG NHẤT === */
            }
            [data-testid="stChatMessage"]:has(span[data-testid="stChatAvatarIcon-user"]) p {
                 color: white;
            }
            /* Không cần căn lề phải cho text nữa, để tự nhiên sẽ đẹp hơn */

        </style>
    """
    st.markdown(css, unsafe_allow_html=True)