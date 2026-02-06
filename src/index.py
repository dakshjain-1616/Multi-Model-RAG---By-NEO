import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import chromadb
from chromadb.config import Settings

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

class MultimodalIndexer:
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32", db_path: str = "./chroma_db"):
        self.model_name = model_name
        self.db_path = Path(db_path).resolve()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Loading CLIP model: {model_name}")
        logger.info(f"Device: {self.device}")
        
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        try:
            self.collection = self.client.get_collection(name="multimodal_rag")
            logger.info(f"Loaded existing collection with {self.collection.count()} items")
        except:
            self.collection = self.client.create_collection(
                name="multimodal_rag",
                metadata={"description": "Multimodal embeddings for text, images, and tables"}
            )
            logger.info("Created new collection")
    
    def index_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not chunks:
            logger.warning("No chunks to index")
            return {"indexed": 0, "errors": 0}
        
        indexed_count = 0
        error_count = 0
        
        for chunk in chunks:
            try:
                embedding = self._generate_embedding(chunk)
                
                chunk_id = f"{chunk['metadata']['source']}_{chunk['type']}_{indexed_count}"
                
                self.collection.add(
                    embeddings=[embedding.tolist()],
                    documents=[chunk['content']],
                    metadatas=[chunk['metadata']],
                    ids=[chunk_id]
                )
                
                indexed_count += 1
            except Exception as e:
                logger.error(f"Error indexing chunk: {e}")
                error_count += 1
        
        logger.info(f"Indexed {indexed_count} chunks, {error_count} errors")
        return {"indexed": indexed_count, "errors": error_count}
    
    def _generate_embedding(self, chunk: Dict[str, Any]) -> np.ndarray:
        chunk_type = chunk['type']
        
        if chunk_type == 'text':
            return self._embed_text(chunk['content'])
        elif chunk_type == 'image':
            return self._embed_image(chunk['metadata']['image_path'])
        elif chunk_type == 'table':
            return self._embed_text(chunk['content'])
        else:
            raise ValueError(f"Unknown chunk type: {chunk_type}")
    
    def _embed_text(self, text: str) -> np.ndarray:
        inputs = self.processor(text=[text], return_tensors="pt", padding=True, truncation=True, max_length=77)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model.text_model(**inputs)
            text_features = outputs.pooler_output
            text_features = self.model.text_projection(text_features)
            
            text_features_np = text_features.cpu().numpy()
            norm = np.linalg.norm(text_features_np, axis=-1, keepdims=True)
            text_features_np = text_features_np / norm
        
        return text_features_np.flatten()
    
    def _embed_image(self, image_path: str) -> np.ndarray:
        path = Path(image_path).resolve()
        
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        image = Image.open(path).convert("RGB")
        
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model.vision_model(**inputs)
            image_features = outputs.pooler_output
            image_features = self.model.visual_projection(image_features)
            
            image_features_np = image_features.cpu().numpy()
            norm = np.linalg.norm(image_features_np, axis=-1, keepdims=True)
            image_features_np = image_features_np / norm
        
        return image_features_np.flatten()
    
    def get_collection_stats(self) -> Dict[str, Any]:
        total_count = self.collection.count()
        
        if total_count == 0:
            return {
                "total_items": 0,
                "text_count": 0,
                "image_count": 0,
                "table_count": 0
            }
        
        all_data = self.collection.get(include=["metadatas"])
        
        text_count = sum(1 for m in all_data['metadatas'] if m.get('modality') == 'text')
        image_count = sum(1 for m in all_data['metadatas'] if m.get('modality') == 'image')
        table_count = sum(1 for m in all_data['metadatas'] if m.get('modality') == 'table')
        
        return {
            "total_items": total_count,
            "text_count": text_count,
            "image_count": image_count,
            "table_count": table_count
        }
    
    def clear_collection(self):
        self.client.delete_collection(name="multimodal_rag")
        self.collection = self.client.create_collection(
            name="multimodal_rag",
            metadata={"description": "Multimodal embeddings for text, images, and tables"}
        )
        logger.info("Collection cleared")