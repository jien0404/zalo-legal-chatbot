import streamlit as st

def inject_custom_css():
    """Inject CSS tùy chỉnh vào ứng dụng Streamlit."""
    css = """
    <style>
        /* --- CÀI ĐẶT CHUNG CHO NỘI DUNG --- */
        .main .block-container {
            max-width: 700px;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        /* --- TIN NHẮN BOT (BÊN TRÁI) --- */
        [data-testid="stChatMessage"]:has(span[data-testid="stChatAvatarIcon-assistant"]) {
            background-color: #F0F2F6;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            color: #1a1a1a;
            max-width: 90%;
        }
        [data-testid="stChatMessage"]:has(span[data-testid="stChatAvatarIcon-assistant"]) p {
             color: #1a1a1a;
        }

        /* --- TIN NHẮN NGƯỜI DÙNG (BÊN PHẢI) --- */
        [data-testid="stChatMessage"]:has(span[data-testid="stChatAvatarIcon-user"]) {
            flex-direction: row-reverse;
            background-color: #0057FF;
            color: white;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            max-width: 85%;
            margin-left: auto;
        }
        [data-testid="stChatMessage"]:has(span[data-testid="stChatAvatarIcon-user"]) p {
             color: white;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
