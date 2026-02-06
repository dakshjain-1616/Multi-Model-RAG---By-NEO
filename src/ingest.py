import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
import json
import PyPDF2
import pandas as pd
from PIL import Image
import pytesseract
from docx import Document

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

class MultimodalIngestion:
    def __init__(self, text_chunk_size: int = 512, text_chunk_overlap: int = 50):
        self.text_chunk_size = text_chunk_size
        self.text_chunk_overlap = text_chunk_overlap
        self.supported_doc_formats = ['.pdf', '.docx', '.txt']
        self.supported_image_formats = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']
        self.supported_table_formats = ['.csv', '.xlsx', '.json']
    
    def process_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        all_chunks = []
        directory = Path(directory_path).resolve()
        
        if not directory.exists():
            logger.warning(f"Directory not found: {directory_path}")
            return all_chunks
        
        files = [f for f in directory.rglob('*') if f.is_file()]
        logger.info(f"Found {len(files)} files in {directory_path}")
        
        for file_path in files:
            try:
                chunks = self.process_file(str(file_path))
                all_chunks.extend(chunks)
                logger.info(f"Processed {file_path.name}: {len(chunks)} chunks")
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
        
        logger.info(f"Total chunks generated: {len(all_chunks)}")
        return all_chunks
    
    def process_file(self, file_path: str) -> List[Dict[str, Any]]:
        path = Path(file_path).resolve()
        
        if not path.exists():
            logger.warning(f"File not found: {file_path}")
            return []
        
        if not path.is_file():
            logger.warning(f"Path is not a file: {file_path}")
            return []
        
        extension = path.suffix.lower()
        
        if extension in self.supported_doc_formats:
            return self._process_document(str(path))
        elif extension in self.supported_image_formats:
            return self._process_image(str(path))
        elif extension in self.supported_table_formats:
            return self._process_table(str(path))
        else:
            logger.warning(f"Unsupported file format: {extension} for {path.name}")
            return []
    
    def _process_document(self, file_path: str) -> List[Dict[str, Any]]:
        chunks = []
        path = Path(file_path).resolve()
        
        try:
            if path.suffix.lower() == '.pdf':
                text = self._extract_pdf_text(str(path))
            elif path.suffix.lower() == '.docx':
                text = self._extract_docx_text(str(path))
            elif path.suffix.lower() == '.txt':
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            else:
                return chunks
            
            if text.strip():
                text_chunks = self._chunk_text(text)
                for idx, chunk in enumerate(text_chunks):
                    chunks.append({
                        'type': 'text',
                        'content': chunk,
                        'metadata': {
                            'source': str(path.name),
                            'file_path': str(path),
                            'chunk_index': idx,
                            'modality': 'text'
                        }
                    })
            else:
                logger.warning(f"No text extracted from {path.name}")
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
        
        return chunks
    
    def _extract_pdf_text(self, file_path: str) -> str:
        text = ""
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
        return text
    
    def _extract_docx_text(self, file_path: str) -> str:
        text = ""
        try:
            doc = Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {e}")
        return text
    
    def _chunk_text(self, text: str) -> List[str]:
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + self.text_chunk_size
            chunk = text[start:end]
            
            if chunk.strip():
                chunks.append(chunk)
            
            start += self.text_chunk_size - self.text_chunk_overlap
        
        return chunks
    
    def _process_image(self, file_path: str) -> List[Dict[str, Any]]:
        chunks = []
        path = Path(file_path).resolve()
        
        try:
            img = Image.open(path)
            
            caption = ""
            try:
                ocr_text = pytesseract.image_to_string(img)
                if ocr_text.strip():
                    caption = ocr_text.strip()
            except Exception as e:
                logger.warning(f"OCR failed for {path.name}: {e}")
            
            chunks.append({
                'type': 'image',
                'content': caption if caption else f"Image: {path.name}",
                'metadata': {
                    'source': str(path.name),
                    'file_path': str(path),
                    'image_path': str(path),
                    'caption': caption,
                    'modality': 'image',
                    'width': img.width,
                    'height': img.height,
                    'format': img.format
                }
            })
            
            logger.info(f"Processed image {path.name}: {img.width}x{img.height}")
        except Exception as e:
            logger.error(f"Error processing image {file_path}: {e}")
        
        return chunks
    
    def _process_table(self, file_path: str) -> List[Dict[str, Any]]:
        chunks = []
        path = Path(file_path).resolve()
        
        try:
            if path.suffix.lower() == '.csv':
                df = pd.read_csv(path, encoding='utf-8', on_bad_lines='skip')
            elif path.suffix.lower() == '.xlsx':
                df = pd.read_excel(path)
            elif path.suffix.lower() == '.json':
                df = pd.read_json(path)
            else:
                return chunks
            
            if df.empty:
                logger.warning(f"Empty table: {path.name}")
                return chunks
            
            table_text = self._serialize_table(df)
            
            chunks.append({
                'type': 'table',
                'content': table_text,
                'metadata': {
                    'source': str(path.name),
                    'file_path': str(path),
                    'modality': 'table',
                    'num_rows': len(df),
                    'num_columns': len(df.columns),
                    'columns': ', '.join(df.columns)
                }
            })
            
            logger.info(f"Processed table {path.name}: {len(df)} rows x {len(df.columns)} columns")
        except Exception as e:
            logger.error(f"Error processing table {file_path}: {e}")
        
        return chunks
    
    def _serialize_table(self, df: pd.DataFrame) -> str:
        text_parts = []
        
        text_parts.append(f"Table with {len(df)} rows and {len(df.columns)} columns.")
        text_parts.append(f"Columns: {', '.join(df.columns)}")
        
        sample_rows = min(10, len(df))
        text_parts.append(f"\nFirst {sample_rows} rows:")
        text_parts.append(df.head(sample_rows).to_string(index=False))
        
        for col in df.columns:
            if df[col].dtype in ['int64', 'float64']:
                stats = df[col].describe()
                text_parts.append(f"\n{col} statistics: mean={stats['mean']:.2f}, min={stats['min']:.2f}, max={stats['max']:.2f}")
        
        return "\n".join(text_parts)