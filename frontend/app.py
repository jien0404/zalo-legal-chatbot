# frontend/app.py
import streamlit as st
import time

from utils.state import initialize_session_state
from services.api_client import get_answer_stream_from_api, get_messages_from_api, create_conversation_on_api, register_user_on_api
from components.sidebar import render_sidebar
from components.chat_elements import display_chat_message
from style import inject_custom_css
from auth_manager import initialize_authenticator, update_config

# --- Cấu hình trang và UI ---
st.set_page_config(
    page_title="Hỏi Đáp Pháp Luật",
    layout="wide",
    initial_sidebar_state="collapsed"
)
inject_custom_css()

# --- XÁC THỰC NGƯỜI DÙNG ---
authenticator, config = initialize_authenticator()
name = st.session_state.get("name")
authentication_status = st.session_state.get("authentication_status")
username = st.session_state.get("username")

# Tạo placeholder để hiển thị form đăng nhập/đăng ký
login_placeholder = st.empty()

if authentication_status is True:
    # Người dùng đã đăng nhập: xóa hoàn toàn phần login
    login_placeholder.empty()
    # Hiển thị giao diện chính
    render_sidebar(authenticator, username)
    st.header(f"⚖️ Chào mừng, *{name}*!")
    # st.caption("...") 
    initialize_session_state()

    if st.session_state.get("load_conversation"):
        convo_id = st.session_state.conversation_id
        st.session_state.messages = get_messages_from_api(convo_id)
        st.session_state.load_conversation = False # Reset cờ

    for message in st.session_state.messages:
        display_chat_message(message)

    # Xử lý input
    if prompt := st.chat_input("Nhập câu hỏi của bạn ở đây..."):
        # Luôn thêm tin nhắn của người dùng vào session state trước tiên
        user_message = {"role": "user", "content": prompt}
        st.session_state.messages.append(user_message)

        # Biến cờ để kiểm tra xem có cần rerun để cập nhật sidebar không
        needs_sidebar_refresh = False

        # Kiểm tra xem đây có phải là tin nhắn đầu tiên của một cuộc trò chuyện mới không
        if "conversation_id" not in st.session_state or st.session_state.conversation_id is None:
            title = " ".join(prompt.split()[:5]) + "..."
            response = create_conversation_on_api(username, title)
            
            # Chỉ cập nhật và đánh dấu cần refresh nếu API gọi thành công
            if response and "conversation_id" in response:
                st.session_state.conversation_id = response["conversation_id"]
                needs_sidebar_refresh = True
            else:
                # Xử lý lỗi nếu không tạo được cuộc trò chuyện
                # Chúng ta sẽ xóa tin nhắn vừa thêm vào để tránh gây lỗi
                st.session_state.messages.pop() 
                st.error("Không thể tạo cuộc trò chuyện mới. Vui lòng thử lại.")
                # Dừng ở đây để người dùng thấy lỗi
                st.stop() 
                
        # Chạy lại ứng dụng. Nếu là cuộc trò chuyện mới, sidebar sẽ được cập nhật.
        # Nếu là cuộc trò chuyện cũ, chỉ có tin nhắn của người dùng được hiển thị.
        st.rerun()

    # --- Logic stream đã được cải tiến ---
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        
        with st.chat_message("assistant", avatar="🤖"):
            placeholder = st.empty()
            placeholder.markdown("🤔 Hãy đợi một chút trong khi tôi suy nhĩ nhé!")
            
            full_response_content = ""
            sources = None
            
            stream = get_answer_stream_from_api(
                st.session_state.messages,
                username,
                st.session_state.conversation_id
            )
            
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

else:
    # Chưa đăng nhập hoặc đăng nhập thất bại
    with login_placeholder.container():
        login_tab, register_tab = st.tabs(["Đăng nhập", "Đăng ký"])
        with login_tab:
            name, authentication_status, username = authenticator.login(fields={'Form name': 'Login'})
            # Nếu đăng nhập thành công thì rerun để chuyển sang UI chính
            if authentication_status:
                st.rerun()
        with register_tab:
            st.info("Mật khẩu phải có ít nhất 8 ký tự.")
            try:
                if authenticator.register_user(fields={'Form name': 'Đăng ký tài khoản', 'preauthorization': False}):
                    update_config(config)
                    new_username = list(config['credentials']['usernames'].keys())[-1]
                    new_user_details = config['credentials']['usernames'][new_username]
                    register_user_on_api(new_username, new_user_details['password'])
                    st.success('Bạn đã đăng ký thành công. Vui lòng chuyển qua tab "Đăng nhập".')
            except Exception as e:
                st.error(e)

    # Nếu nhập sai thông tin
    if authentication_status is False:
        st.error('Tên người dùng/mật khẩu không chính xác')
    elif authentication_status is None:
        st.warning('Vui lòng nhập tên người dùng và mật khẩu của bạn')
