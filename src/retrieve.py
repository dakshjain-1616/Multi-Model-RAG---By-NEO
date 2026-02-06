import os
import sys
import logging
import time
from typing import List, Dict, Any
import chromadb
from sentence_transformers import SentenceTransformer
import torch
import numpy as np

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

class MultimodalRetriever:
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32", 
                 db_path: str = "./chroma_db", top_k: int = 5):
        self.model_name = model_name
        self.db_path = db_path
        self.top_k = top_k
        
        try:
            if "clip" in model_name.lower():
                from transformers import CLIPProcessor, CLIPModel
                self.model = CLIPModel.from_pretrained(model_name)
                self.processor = CLIPProcessor.from_pretrained(model_name)
                self.embedding_type = "clip"
            else:
                self.model = SentenceTransformer(model_name)
                self.embedding_type = "sentence_transformer"
        except Exception as e:
            logger.warning(f"Failed to load {model_name}, falling back to all-MiniLM-L6-v2: {e}")
            self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            self.embedding_type = "sentence_transformer"
        
        self.client = chromadb.PersistentClient(path=db_path)
        
        try:
            self.collection = self.client.get_collection(name="multimodal_rag")
        except Exception as e:
            logger.error(f"Collection not found: {e}")
            raise
    
    def retrieve(self, query: str, top_k: int = None) -> Dict[str, Any]:
        if top_k is None:
            top_k = self.top_k
        
        start_time = time.time()
        
        try:
            query_embedding = self._generate_query_embedding(query)
            
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=top_k
            )
            
            formatted_results = []
            modalities_found = set()
            
            for i in range(len(results['ids'][0])):
                result_dict = {
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'modality': results['metadatas'][0][i].get('modality', 'unknown'),
                    'similarity_score': 1.0 - results['distances'][0][i] if 'distances' in results else 0.0
                }
                formatted_results.append(result_dict)
                modalities_found.add(result_dict['modality'])
            
            elapsed_time = time.time() - start_time
            
            return {
                'results': formatted_results,
                'metadata': {
                    'query': query,
                    'num_results': len(formatted_results),
                    'latency_seconds': elapsed_time,
                    'modalities_found': list(modalities_found)
                }
            }
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return {
                'results': [],
                'metadata': {
                    'query': query,
                    'num_results': 0,
                    'latency_seconds': time.time() - start_time,
                    'modalities_found': [],
                    'error': str(e)
                }
            }
    
    def _generate_query_embedding(self, query: str) -> np.ndarray:
        try:
            if self.embedding_type == "clip":
                inputs = self.processor(text=query, return_tensors="pt", padding=True, truncation=True, max_length=77)
                with torch.no_grad():
                    outputs = self.model.text_model(**inputs)
                    text_features = outputs.pooler_output
                    text_features = self.model.text_projection(text_features)
                    
                    text_features_np = text_features.cpu().numpy()
                    norm = np.linalg.norm(text_features_np, axis=-1, keepdims=True)
                    text_features_np = text_features_np / norm
                return text_features_np.flatten()
            else:
                embedding = self.model.encode(query, convert_to_numpy=True)
                return embedding
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            raise