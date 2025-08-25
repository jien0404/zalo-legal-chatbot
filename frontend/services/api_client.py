# frontend/services/api_client.py
import streamlit as st
import requests
import json

# === SỬA ĐỔI: Định nghĩa một BASE_URL để tránh lặp lại và gõ sai ===
BASE_API_URL = "http://127.0.0.1:8000"

def get_answer_stream_from_api(chat_history: list[dict], username: str, conversation_id: str | None):
    history_to_send = [{"role": msg["role"], "content": msg["content"]} for msg in chat_history]
    
    try:
        response = requests.post(
            f"{BASE_API_URL}/generate_answer",  # Sử dụng BASE_URL
            json={
                "chat_history": history_to_send, 
                "username": username,
                "conversation_id": conversation_id,
                "top_k_rerank": 5
            },
            stream=True
        )
        response.raise_for_status()
        for line in response.iter_lines():
            if line and line.decode('utf-8').startswith('data: '):
                yield json.loads(line.decode('utf-8')[6:])

    except requests.exceptions.RequestException as e:
        yield {"error": f"Lỗi kết nối đến server: {e}"}
    except Exception as e:
        yield {"error": f"Đã có lỗi xảy ra: {e}"}

def get_conversations_from_api(username: str):
    try:
        response = requests.get(f"{BASE_API_URL}/conversations/{username}") # Sử dụng BASE_URL
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Lỗi khi tải lịch sử chat: {e}")
        return []

def get_messages_from_api(conversation_id: str):
    try:
        response = requests.get(f"{BASE_API_URL}/messages/{conversation_id}") # Sử dụng BASE_URL
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Lỗi khi tải tin nhắn: {e}")
        return []

def create_conversation_on_api(username: str, title: str):
    try:
        response = requests.post(
            f"{BASE_API_URL}/conversations", # Sử dụng BASE_URL
            json={"username": username, "title": title}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        # Thay đổi ở đây để hiển thị lỗi 404 một cách rõ ràng
        st.error(f"Lỗi khi tạo cuộc trò chuyện mới: {e}")
        return None
    except Exception as e:
        st.error(f"Lỗi không xác định: {e}")
        return None
    
def register_user_on_api(username: str, hashed_password: str):
    try:
        response = requests.post(
            f"{BASE_API_URL}/register",
            json={"username": username, "hashed_password": hashed_password}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Lỗi khi đăng ký người dùng trên server: {e}")
        return None

def delete_conversation_on_api(username: str, conversation_id: str):
    """Gửi yêu cầu xóa một cuộc trò chuyện đến backend."""
    try:
        response = requests.post(
            f"{BASE_API_URL}/conversations/delete",
            json={"username": username, "conversation_id": conversation_id}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Lỗi khi xóa cuộc trò chuyện: {e}")
        return None
    
def update_conversation_title_on_api(username: str, conversation_id: str, new_title: str):
    """Gọi API để cập nhật tiêu đề cuộc trò chuyện."""
    try:
        response = requests.post(
            f"{BASE_API_URL}/conversations/update_title",
            json={"username": username, "conversation_id": conversation_id, "new_title": new_title}
        )
        response.raise_for_status()
        # Không cần trả về gì nếu thành công, raise_for_status sẽ xử lý lỗi
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Lỗi khi cập nhật tiêu đề: {e}")
        return False