# api/dependencies.py
from retriever.retrieval_system import RetrievalSystem
import os

# Đường dẫn có thể được load từ file config
PROCESSED_DATA_DIR = "data/processed_data_chunks" 
EMBEDDING_MODEL_PATH = "models/finetuned-e5-base"
RERANKER_MODEL_PATH = "models/finetuned-reranker-base"

# Singleton pattern: Khởi tạo model một lần và tái sử dụng
retriever = RetrievalSystem(
    processed_data_dir=PROCESSED_DATA_DIR,
    embedding_model_path=EMBEDDING_MODEL_PATH,
    reranker_model_path=RERANKER_MODEL_PATH
)

def get_retriever():
    return retriever