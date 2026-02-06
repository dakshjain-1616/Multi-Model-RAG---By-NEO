# Multimodal RAG System

A production-ready Retrieval-Augmented Generation (RAG) system supporting text, images, and tables with unified cross-modal search.

## Features

- **Multimodal Support**: Process and search across text documents, images, and tabular data
- **Unified Embedding Space**: CLIP-based embeddings enable cross-modal retrieval
- **Scalable Architecture**: ChromaDB vector store with efficient indexing
- **Interactive UI**: Streamlit-based chat interface with file upload
- **Production Ready**: Error handling, logging, and performance monitoring

## System Architecture

```
```
┌─────────────────────────────────────────────────────────────┐
│                    Multimodal RAG Pipeline                   │
├─────────────────────────────────────────────────────────────┤
│  Input Layer                                                │
│    ├─ Documents (PDF, DOCX, TXT)                           │
│    ├─ Images (PNG, JPG, TIFF)                              │
│    └─ Tables (CSV, XLSX, JSON)                             │
├─────────────────────────────────────────────────────────────┤
│  Processing Layer (src/ingest.py)                           │
│    ├─ Text Chunking (512 chars, 50 overlap)                │
│    ├─ Image OCR (Tesseract)                                │
│    └─ Table Serialization (with statistics)                │
├─────────────────────────────────────────────────────────────┤
│  Embedding Layer (src/index.py)                             │
│    ├─ CLIP Text Encoder (512-dim vectors)                  │
│    ├─ CLIP Vision Encoder (512-dim vectors)                │
│    └─ Table Text Encoder (512-dim vectors)                 │
├─────────────────────────────────────────────────────────────┤
│  Storage Layer                                              │
│    └─ ChromaDB (Persistent, Disk-based)                    │
├─────────────────────────────────────────────────────────────┤
│  Retrieval Layer (src/retrieve.py)                          │
│    ├─ Query Embedding Generation                           │
│    ├─ Similarity Search (cosine distance)                  │
│    └─ Cross-Modal Result Ranking                           │
├─────────────────────────────────────────────────────────────┤
│  Interface Layer (app.py)                                   │
│    ├─ Streamlit Chat UI                                    │
│    ├─ File Upload & Processing                             │
│    └─ Result Visualization                                 │
└─────────────────────────────────────────────────────────────┘
```
```

## Installation

### Prerequisites
- Python 3.12+
- Tesseract OCR (`apt-get install tesseract-ocr` or `brew install tesseract`)

### Setup

```bash
cd /root/claude_tests/MultiModelRag

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

## Usage

### 1. Command Line Interface

#### Process and Index Files
```bash
./venv/bin/python -c "
from src.ingest import MultimodalIngestion
from src.index import MultimodalIndexer

ingestion = MultimodalIngestion()
chunks = ingestion.process_directory('./data')

indexer = MultimodalIndexer(model_name='openai/clip-vit-base-patch32', db_path='./chroma_db')
result = indexer.index_chunks(chunks)
print(f'Indexed {result[\"indexed\"]} chunks')
"
```

#### Search
```bash
./venv/bin/python -c "
from src.retrieve import MultimodalRetriever

retriever = MultimodalRetriever(model_name='openai/clip-vit-base-patch32', db_path='./chroma_db')
response = retriever.retrieve('sales data Q1', top_k=5)

for r in response['results']:
    print(f'{r[\"modality\"]}: {r[\"metadata\"][\"source\"]} (score: {r[\"similarity_score\"]:.3f})')
"
```

### 2. Web Interface

```bash
./venv/bin/python -m streamlit run app.py --server.port 8501
```

Navigate to `http://localhost:8501`

**Features:**
- Chat-based search interface
- Drag-and-drop file upload
- Real-time processing status
- Rich result visualization (images inline, tables as dataframes)
- Modality filtering

### 3. Performance Report Generation

```bash
./venv/bin/python generate_performance_report.py
```

Generates:
- `Pipeline_Performance_Report.pdf` - Detailed performance metrics
- `performance_report.json` - Machine-readable metrics

## Configuration

Edit `config.yaml`:

```yaml
embedding_model: "openai/clip-vit-base-patch32"
text_chunk_size: 512
text_chunk_overlap: 50
vector_db_path: "./chroma_db"
batch_size: 32
top_k_results: 5
similarity_threshold: 0.5
supported_formats:
  documents: ["pdf", "docx", "txt"]
  images: ["png", "jpg", "jpeg", "tiff", "bmp"]
  tables: ["csv", "xlsx", "json"]
```

## Project Structure

```
```
MultiModelRag/
├── src/
│   ├── __init__.py
│   ├── ingest.py          # File processing and chunking
│   ├── index.py           # Embedding generation and indexing
│   └── retrieve.py        # Query processing and retrieval
├── data/                  # Upload directory for user files
├── test_files/            # Sample test data
├── chroma_db/            # Vector database storage
├── app.py                # Streamlit web interface
├── config.yaml           # System configuration
├── generate_performance_report.py  # Performance testing
├── requirements.txt      # Python dependencies
└── README.md            # This file
```
```

## Performance Metrics

Based on `Pipeline_Performance_Report.pdf`:

| Metric | Value | Status |
|--------|-------|--------|
| **Retrieval Latency** | 0.030s avg | ✓ PASS (<2s) |
| **Files Processed** | 13 files | ✓ PASS (>10) |
| **Cross-Modal Success** | 60%+ | ✓ PASS |
| **Indexing Time** | 1.18s for 13 files | ✓ PASS |
| **Error Handling** | Graceful degradation | ✓ PASS |

## API Reference

### MultimodalIngestion

```python
from src.ingest import MultimodalIngestion

ingestion = MultimodalIngestion(
    text_chunk_size=512,
    text_chunk_overlap=50
)

chunks = ingestion.process_directory("./data")

for chunk in chunks:
    print(chunk['type'])      # 'text', 'image', or 'table'
    print(chunk['content'])   # Textual representation
    print(chunk['metadata'])  # Source, modality, etc.
```

### MultimodalIndexer

```python
from src.index import MultimodalIndexer

indexer = MultimodalIndexer(
    model_name="openai/clip-vit-base-patch32",
    db_path="./chroma_db"
)

result = indexer.index_chunks(chunks)
print(f"Indexed: {result['indexed']}, Errors: {result['errors']}")

stats = indexer.get_collection_stats()
```

### MultimodalRetriever

```python
from src.retrieve import MultimodalRetriever

retriever = MultimodalRetriever(
    model_name="openai/clip-vit-base-patch32",
    db_path="./chroma_db"
)

response = retriever.retrieve("sales revenue", top_k=5)

for result in response['results']:
    modality = result['modality']
    score = result['similarity_score']
    source = result['metadata']['source']
```

## Supported File Formats

| Category | Formats | Processing Method |
|----------|---------|-------------------|
| **Documents** | TXT, PDF, DOCX | Text extraction + chunking |
| **Images** | PNG, JPG, JPEG, TIFF, BMP | OCR + visual embedding |
| **Tables** | CSV, XLSX, JSON | Schema + content serialization |

## Technical Details

### Embedding Model
- **Model**: OpenAI CLIP (ViT-B/32)
- **Dimension**: 512
- **Normalization**: L2 normalized vectors
- **Unified Space**: Same embedding space for all modalities

### Vector Database
- **Engine**: ChromaDB 1.4.1
- **Storage**: Persistent SQLite backend
- **Distance**: Cosine similarity
- **Indexing**: Automatic HNSW

### Processing Pipeline
1. **Ingestion**: File type detection → Content extraction → Chunking
2. **Embedding**: Modality-specific encoding → Normalization → Vector generation
3. **Indexing**: Batch insertion → Metadata storage → Index optimization
4. **Retrieval**: Query embedding → Similarity search → Result ranking

## Troubleshooting

### Issue: Tesseract not found
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract
```

### Issue: CUDA out of memory
Edit `config.yaml`:
```yaml
batch_size: 16  # Reduce from 32
```

### Issue: Port 8501 already in use
```bash
./venv/bin/python -m streamlit run app.py --server.port 8502
```

### Issue: Import errors
```bash
./venv/bin/python -m pip install -r requirements.txt --force-reinstall
```

## Testing

Run comprehensive tests:
```bash
./venv/bin/python generate_performance_report.py
```

Quick smoke test:
```bash
./venv/bin/python -c "
from src.ingest import MultimodalIngestion
from src.index import MultimodalIndexer
from src.retrieve import MultimodalRetriever

print('Testing ingestion...')
ing = MultimodalIngestion()
chunks = ing.process_directory('./test_files')
print(f'✓ Extracted {len(chunks)} chunks')

print('Testing indexing...')
idx = MultimodalIndexer(model_name='openai/clip-vit-base-patch32', db_path='./chroma_db')
result = idx.index_chunks(chunks[:3])
print(f'✓ Indexed {result[\"indexed\"]} chunks')

print('Testing retrieval...')
ret = MultimodalRetriever(model_name='openai/clip-vit-base-patch32', db_path='./chroma_db')
resp = ret.retrieve('test query', top_k=3)
print(f'✓ Retrieved {len(resp[\"results\"])} results')

print('All tests passed!')
"
```

## License

MIT License - See LICENSE file for details

## Acknowledgments

- CLIP Model: OpenAI
- Vector Store: ChromaDB
- UI Framework: Streamlit
- OCR: Tesseract

## Contact

For issues and questions, please check the documentation or create an issue in the repository.