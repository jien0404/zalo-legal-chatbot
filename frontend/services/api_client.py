# frontend/services/api_client.py
import streamlit as st
import requests

# Lấy URL của API từ secrets hoặc đặt cứng để test local
API_URL = st.secrets.get("API_URL", "http://127.0.0.1:8000/generate_answer")

@st.cache_data(show_spinner=False) # Cache để tránh gọi lại API không cần thiết
def get_answer_from_api(question: str):
    """Gửi câu hỏi đến backend và nhận câu trả lời."""
    try:
        response = requests.post(
            API_URL, 
            json={"question": question, "top_k_rerank": 5}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Lỗi kết nối đến server: {e}"}
    except Exception as e:
        return {"error": f"Đã có lỗi xảy ra: {e}"}