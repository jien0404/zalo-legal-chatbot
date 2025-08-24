# frontend/services/api_client.py
import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/generate_answer"

# === SỬA ĐỔI: Hàm này giờ nhận toàn bộ lịch sử chat ===
@st.cache_data(show_spinner=False)
def get_answer_from_api(chat_history: list[dict]):
    """Gửi toàn bộ lịch sử chat đến backend."""
    
    # Chỉ gửi content và role, không gửi sources
    history_to_send = [{"role": msg["role"], "content": msg["content"]} for msg in chat_history]
    
    try:
        response = requests.post(
            API_URL, 
            # Dữ liệu gửi đi giờ là một object chứa chat_history
            json={"chat_history": history_to_send, "top_k_rerank": 5}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Lỗi kết nối đến server: {e}"}
    except Exception as e:
        return {"error": f"Đã có lỗi xảy ra: {e}"}