# ⚖️ Zalo Legal Bot - Trợ lý Hỏi-Đáp Pháp luật

**Zalo Legal Bot** là một ứng dụng chatbot thông minh, được xây dựng dựa trên kiến trúc Retrieval-Augmented Generation (RAG), chuyên cung cấp các câu trả lời chính xác và đáng tin cậy cho các câu hỏi liên quan đến hệ thống pháp luật Việt Nam.

Dự án này là một minh chứng hoàn chỉnh về việc xây dựng một hệ thống RAG từ đầu, bao gồm các giai đoạn từ xử lý dữ liệu, fine-tuning mô hình, xây dựng hệ thống retrieval, đến triển khai một ứng dụng web đầy đủ tính năng với giao diện người dùng chuyên nghiệp.

## ✨ Các tính năng nổi bật

-   **Hỏi-Đáp thông minh:** Sử dụng các mô hình ngôn ngữ lớn (LLM) như Gemini để cung cấp các câu trả lời tự nhiên, tổng hợp từ các nguồn tài liệu pháp luật chính thống.
-   **Retrieval Nâng cao:** Kết hợp tìm kiếm ngữ nghĩa (Semantic Search) với Pinecone và tìm kiếm từ khóa (Lexical Search) với BM25, được tăng cường bởi các mô hình Embedding và Reranker đã được fine-tune.
-   **Hiểu ngữ cảnh hội thoại:** Chatbot có khả năng "nhớ" các tin nhắn trước đó trong cuộc trò chuyện để trả lời các câu hỏi nối tiếp một cách chính xác.
-   **Trích dẫn nguồn đáng tin cậy:** Mọi câu trả lời đều đi kèm với các nguồn tài liệu đã được sử dụng để tổng hợp, đảm bảo tính minh bạch và cho phép người dùng tự kiểm chứng.
-   **Giao diện người dùng hiện đại:** Giao diện chatbot chuyên nghiệp, hỗ trợ streaming response (hiệu ứng gõ chữ), giúp mang lại trải nghiệm tương tác mượt mà.
-   **Quản lý người dùng & Lịch sử Chat:** Hỗ trợ đăng ký, đăng nhập và lưu trữ lịch sử các cuộc trò chuyện cho từng người dùng, cho phép họ tiếp tục các phiên làm việc cũ.
-   **Kiến trúc Microservice:** Tách biệt rõ ràng giữa Backend (FastAPI) xử lý logic và Frontend (Streamlit) cung cấp giao diện, sẵn sàng cho việc mở rộng và triển khai.

## 🛠️ Công nghệ sử dụng

-   **Backend:** Python, FastAPI, Uvicorn
-   **Frontend:** Streamlit, Streamlit Authenticator
-   **AI / Machine Learning:**
    -   **LLM:** Google Gemini API (`gemini-1.5-flash`)
    -   **Embedding Model:** `intfloat/multilingual-e5-base` (đã fine-tune)
    -   **Reranker Model:** `BAAI/bge-reranker-large` (đã fine-tune)
    -   **Thư viện:** `sentence-transformers`, `torch`
-   **Cơ sở dữ liệu Vector:** Pinecone
-   **Cơ sở dữ liệu Quan hệ:** SQLite
-   **Deployment:** Docker

## 🚀 Cài đặt và Chạy tại Local

### Yêu cầu

-   Python 3.10+
-   Git

### Hướng dẫn cài đặt

1.  **Clone repository về máy:**
    ```bash
    git clone https://github.com/your-username/zalo-rag-app.git
    cd zalo-rag-app
    ```

2.  **Tạo và kích hoạt môi trường ảo:**
    ```bash
    python -m venv .venv
    # Trên Windows
    .venv\Scripts\activate
    # Trên MacOS/Linux
    source .venv/bin/activate
    ```

3.  **Cài đặt các thư viện cần thiết:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Thiết lập các biến môi trường:**
    -   Tạo một file `.env` trong thư mục gốc của dự án.
    -   Sao chép nội dung từ `.env.example` (nếu có) hoặc thêm các khóa sau:
        ```env
        PINECONE_API_KEY="your_pinecone_api_key"
        GEMINI_API_KEY="your_google_gemini_api_key"
        ```

5.  **Cấu hình xác thực người dùng:**
    -   Mở file `config.yaml`.
    -   Thay đổi `cookie.key` thành một chuỗi bí mật ngẫu nhiên của bạn.
    -   (Tùy chọn) Chạy `python generate_keys.py` để tạo mật khẩu đã được hash và cập nhật cho người dùng mặc định.

6.  **Khởi tạo cơ sở dữ liệu:**
    Chạy lệnh này **một lần duy nhất** để tạo file `chat_history.db` và các bảng cần thiết.
    ```bash
    python core/database.py
    ```

### Chạy ứng dụng

Bạn cần mở **hai cửa sổ terminal** riêng biệt.

1.  **Terminal 1: Chạy Backend API (FastAPI)**
    ```bash
    uvicorn api.main:app --host 0.0.0.0 --port 8000
    ```

2.  **Terminal 2: Chạy Frontend (Streamlit)**
    ```bash
    streamlit run frontend/app.py
    ```

3.  Mở trình duyệt và truy cập vào địa chỉ `http://localhost:8501`.

## 📈 Lộ trình phát triển trong tương lai

-   [ ] **Feedback:** Thêm tính năng đánh giá câu trả lời (👍/👎).
-   [ ] **Cải thiện Retrieval:** Thử nghiệm các phương pháp fusion nâng cao (ví dụ: score-based).
-   [ ] **Deployment:** Đóng gói ứng dụng bằng Docker và triển khai lên một nền tảng cloud (ví dụ: Google Cloud Run, AWS).
-   [ ] **Bộ nhớ dài hạn:** Nghiên cứu và triển khai Conversation Summary Memory để xử lý các cuộc trò chuyện rất dài.
-   [ ] **Testing:** Viết unit test và integration test cho các module quan trọng.