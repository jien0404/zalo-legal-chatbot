# frontend/services/api_client.py
import streamlit as st
import requests
import json

API_URL = "http://127.0.0.1:8000/generate_answer"

def get_answer_stream_from_api(chat_history: list[dict], username: str, conversation_id: str | None):
    history_to_send = [{"role": msg["role"], "content": msg["content"]} for msg in chat_history]
    
    try:
        # Gọi API với stream=True
        response = requests.post(
            API_URL, 
            json={
                "chat_history": history_to_send, 
                "username": username,
                "conversation_id": conversation_id,
                "top_k_rerank": 5
            },
            stream=True
        )
        response.raise_for_status()
        
        # Lặp qua từng dòng dữ liệu trong stream
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                # Bỏ qua các dòng không phải dữ liệu (ví dụ: dòng trống)
                if decoded_line.startswith('data: '):
                    # Lấy nội dung JSON và parse nó
                    json_content = decoded_line[len('data: '):]
                    yield json.loads(json_content)

    except requests.exceptions.RequestException as e:
        yield {"error": f"Lỗi kết nối đến server: {e}"}
    except Exception as e:
        yield {"error": f"Đã có lỗi xảy ra: {e}"}

def get_conversations_from_api(username: str):
    try:
        response = requests.get(f"http://127.0.0.1:8000/conversations/{username}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Lỗi khi tải lịch sử chat: {e}")
        return []

def get_messages_from_api(conversation_id: str):
    try:
        response = requests.get(f"http://127.0.0.1:8000/messages/{conversation_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Lỗi khi tải tin nhắn: {e}")
        return []

def create_conversation_on_api(username: str, title: str):
    try:
        response = requests.post(
            "http://127.0.0.1:8000/conversations",
            json={"username": username, "title": title}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Lỗi khi tạo cuộc trò chuyện mới: {e}")
        return None
    
def register_user_on_api(username: str, hashed_password: str):
    """Gửi thông tin người dùng mới đến backend để đăng ký trong DB."""
    try:
        response = requests.post(
            "http://12-7.0.0.1:8000/register",
            json={"username": username, "hashed_password": hashed_password}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Lỗi khi đăng ký người dùng trên server: {e}")
        return None