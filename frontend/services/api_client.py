# frontend/services/api_client.py
import streamlit as st
import requests
import json

API_URL = "http://127.0.0.1:8000/generate_answer"

def get_answer_stream_from_api(chat_history: list[dict]):
    """
    Gửi lịch sử chat đến backend và nhận về một stream các chunks dữ liệu.
    Đây là một generator function.
    """
    history_to_send = [{"role": msg["role"], "content": msg["content"]} for msg in chat_history]
    
    try:
        # Gọi API với stream=True
        response = requests.post(
            API_URL, 
            json={"chat_history": history_to_send, "top_k_rerank": 5},
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