# Dockerfile

# Sử dụng base image Python chính thức
FROM python:3.10-slim

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Sao chép file requirements trước để tận dụng caching của Docker
COPY requirements.txt .

# Cài đặt các thư viện
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ code của dự án vào container
COPY . .

# Mở port 8000 để API có thể được truy cập từ bên ngoài
EXPOSE 8000

# Lệnh để chạy ứng dụng khi container khởi động
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]