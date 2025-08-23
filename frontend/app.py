# frontend/app.py
import streamlit as st
import requests
import json

# Cấu hình trang
st.set_page_config(page_title="Hỏi Đáp Pháp Luật", layout="wide")

st.title("Hệ Thống Hỏi Đáp Thông Minh Về Pháp Luật Việt Nam")
st.markdown("Hệ thống này sử dụng Trí tuệ nhân tạo để tìm kiếm và tổng hợp thông tin từ kho dữ liệu văn bản pháp luật.")

# URL của Backend API
API_URL = "http://127.0.0.1:8000/generate_answer"

# Giao diện
question = st.text_input("Vui lòng nhập câu hỏi của bạn:", "")

if st.button("Tìm kiếm"):
    if question:
        with st.spinner("Đang xử lý, vui lòng chờ..."):
            try:
                # Gửi yêu cầu đến backend
                response = requests.post(API_URL, json={"question": question, "top_k_rerank": 5})
                response.raise_for_status()  # Ném lỗi nếu request không thành công
                
                result = response.json()
                answer = result.get("answer")
                sources = result.get("sources")

                # Hiển thị kết quả
                st.subheader("Câu trả lời tổng hợp:")
                st.markdown(answer)
                
                st.subheader("Các nguồn tài liệu tham khảo:")
                for i, source in enumerate(sources):
                    with st.expander(f"Nguồn {i+1}: Văn bản {source['doc_id']} (Điểm liên quan: {source['score']:.4f})"):
                        st.text(source['text'])
                        
            except requests.exceptions.RequestException as e:
                st.error(f"Lỗi kết nối đến server: {e}")
            except Exception as e:
                st.error(f"Đã có lỗi xảy ra: {e}")
    else:
        st.warning("Vui lòng nhập câu hỏi.")