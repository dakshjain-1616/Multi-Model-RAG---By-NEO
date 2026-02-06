import os
import sys
import yaml
import logging
import json
from pathlib import Path
from src.ingest import MultimodalIngestion
from src.index import MultimodalIndexer
from src.retrieve import MultimodalRetriever

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class MultimodalRAGPipeline:
    def __init__(self, config_path: str = "./config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.ingestion = MultimodalIngestion(
            text_chunk_size=self.config['text_chunk_size'],
            text_chunk_overlap=self.config['text_chunk_overlap']
        )
        
        self.indexer = None
        self.retriever = None
    
    def ingest_and_index(self, data_path: str):
        logger.info(f"Starting ingestion from: {data_path}")
        chunks = self.ingestion.process_directory(data_path)
        
        if not chunks:
            logger.error("No chunks generated from ingestion")
            return
        
        logger.info(f"Generated {len(chunks)} chunks")
        
        self.indexer = MultimodalIndexer(
            model_name=self.config['embedding_model'],
            db_path=self.config['vector_db_path'],
            batch_size=self.config['batch_size']
        )
        
        indexed_count = self.indexer.index_chunks(chunks)
        logger.info(f"Successfully indexed {indexed_count} chunks")
        
        stats = self.indexer.get_collection_stats()
        logger.info(f"Collection stats: {stats}")
    
    def retrieve(self, query: str, top_k: int = None):
        if top_k is None:
            top_k = self.config['top_k_results']
        
        if self.retriever is None:
            self.retriever = MultimodalRetriever(
                model_name=self.config['embedding_model'],
                db_path=self.config['vector_db_path'],
                top_k=top_k
            )
        
        results = self.retriever.retrieve(query, top_k)
        return results

def main():
    logger.info("=== Multimodal RAG Pipeline ===")
    
    pipeline = MultimodalRAGPipeline()
    
    data_path = "./test_files"
    if len(sys.argv) > 1:
        data_path = sys.argv[1]
    
    if os.path.exists(data_path):
        logger.info(f"Processing data from: {data_path}")
        pipeline.ingest_and_index(data_path)
        
        test_queries = [
            "What is the main topic discussed?",
            "Show me information about images",
            "What data is in the tables?"
        ]
        
        logger.info("\n=== Running Test Queries ===")
        for query in test_queries:
            logger.info(f"\nQuery: {query}")
            results = pipeline.retrieve(query)
            logger.info(f"Latency: {results['metadata']['latency_seconds']}s")
            logger.info(f"Modalities found: {results['metadata']['modalities_found']}")
            for i, result in enumerate(results['results'][:3]):
                logger.info(f"  Result {i+1}: {result['modality']} - Score: {result['similarity_score']:.4f}")
    else:
        logger.error(f"Data path not found: {data_path}")

if __name__ == "__main__":
    main()