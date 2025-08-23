# retriever/retrieval_system.py

import os
import json
import torch
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
from pinecone import Pinecone
from pyvi import ViTokenizer
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv() # Tải các biến môi trường từ file .env

class RetrievalSystem:
    def __init__(self, processed_data_dir, embedding_model_path, reranker_model_path):
        print("Initializing Retrieval System...")
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # 1. Tải models
        print("Loading models...")
        self.embedding_model = SentenceTransformer(embedding_model_path, device=self.device)
        self.reranker_model = CrossEncoder(reranker_model_path, device=self.device)
        
        # 2. Kết nối Pinecone
        print("Connecting to Pinecone...")
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = "zalo-legal-retrieval-chunked-v2" # Hoặc lấy từ config
        pc = Pinecone(api_key=pinecone_api_key)
        self.index = pc.Index(self.index_name)
        
        # 3. Tải và xây dựng BM25
        print("Loading data and building BM25 index...")
        chunks_path = os.path.join(processed_data_dir, "legal_corpus_chunks.jsonl")
        tokenized_chunks_path = os.path.join(processed_data_dir, "legal_corpus_chunks_tokenized.json")
        
        self.corpus_chunks = []
        with open(chunks_path, 'r', encoding='utf-8') as f:
            for line in f:
                self.corpus_chunks.append(json.loads(line))
        
        with open(tokenized_chunks_path, 'r', encoding='utf-8') as f:
            tokenized_chunks = json.load(f)
            
        self.bm25 = BM25Okapi(tokenized_chunks)
        self.chunk_ids_bm25 = [chunk['chunk_id'] for chunk in self.corpus_chunks]
        
        # 4. Tạo các map để truy cập nhanh
        self.chunk_id_to_text = {chunk['chunk_id']: chunk['text'] for chunk in self.corpus_chunks}
        self.chunk_id_to_doc_id = {chunk['chunk_id']: chunk['doc_id'] for chunk in self.corpus_chunks}
        
        print("Retrieval System initialized successfully!")

    def _vector_search(self, query, k):
        query_embedding = self.embedding_model.encode(query).tolist()
        results = self.index.query(vector=query_embedding, top_k=k)
        return [match['id'] for match in results['matches']]

    def _hybrid_search(self, query, k_semantic=100, k_lexical=100, rrf_k=60):
        semantic_ids = self._vector_search(query, k=k_semantic)
        
        tokenized_query = ViTokenizer.tokenize(query).split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        top_n_indices = np.argsort(bm25_scores)[::-1][:k_lexical]
        lexical_ids = [self.chunk_ids_bm25[i] for i in top_n_indices]

        rrf_scores = defaultdict(float)
        for rank, chunk_id in enumerate(semantic_ids):
            rrf_scores[chunk_id] += 1.0 / (rrf_k + rank + 1)
        for rank, chunk_id in enumerate(lexical_ids):
            rrf_scores[chunk_id] += 1.0 / (rrf_k + rank + 1)

        sorted_rrf = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)
        return [chunk_id for chunk_id, score in sorted_rrf]

    def retrieve_chunks(self, query: str, top_k_retrieval: int = 20, top_k_rerank: int = 5):
        """
        Thực hiện toàn bộ pipeline retrieve và rerank để lấy ra các chunks liên quan nhất.
        """
        retrieved_chunk_ids = self._hybrid_search(query)[:top_k_retrieval]
        
        retrieved_chunk_texts = [self.chunk_id_to_text.get(cid, "") for cid in retrieved_chunk_ids]
        pairs = [[query, text] for text in retrieved_chunk_texts]
        
        if not pairs:
            return []
            
        scores = self.reranker_model.predict(pairs, show_progress_bar=False, batch_size=128)
        reranked_chunks = sorted(zip(retrieved_chunk_ids, scores), key=lambda x: x[1], reverse=True)
        
        # Lấy top k chunks cuối cùng sau khi rerank
        final_chunks = []
        for chunk_id, score in reranked_chunks[:top_k_rerank]:
            final_chunks.append({
                "chunk_id": chunk_id,
                "doc_id": self.chunk_id_to_doc_id.get(chunk_id),
                "text": self.chunk_id_to_text.get(chunk_id),
                "score": float(score)
            })
            
        return final_chunks