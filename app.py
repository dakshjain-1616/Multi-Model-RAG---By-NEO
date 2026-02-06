import streamlit as st
import sys
import os
import time
import json
from pathlib import Path
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))

from src.ingest import MultimodalIngestion
from src.index import MultimodalIndexer
from src.retrieve import MultimodalRetriever
import yaml

st.set_page_config(
    page_title="Multimodal RAG System",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

@st.cache_resource
def initialize_system():
    config = load_config()
    ingestion = MultimodalIngestion(
        text_chunk_size=config['text_chunk_size'],
        text_chunk_overlap=config['text_chunk_overlap']
    )
    indexer = MultimodalIndexer(
        model_name=config['embedding_model'],
        db_path=config['vector_db_path']
    )
    retriever = MultimodalRetriever(
        model_name=config['embedding_model'],
        db_path=config['vector_db_path']
    )
    return ingestion, indexer, retriever, config

def save_uploaded_file(uploaded_file, data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    file_path = data_dir / uploaded_file.name
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path

def render_result(result: dict, idx: int):
    modality = result.get('modality', 'unknown')
    score = result.get('score', 0)
    source = result.get('source', 'Unknown')
    
    modality_colors = {
        'text': '🟦',
        'image': '🟩',
        'table': '🟨'
    }
    
    color_icon = modality_colors.get(modality, '⬜')
    
    with st.container():
        st.markdown(f"### {color_icon} Result {idx + 1}: {modality.upper()}")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Source:** {source}")
        with col2:
            st.metric("Relevance Score", f"{score:.3f}")
        
        if modality == 'image':
            image_path = result.get('image_path', '')
            if image_path and Path(image_path).exists():
                try:
                    img = Image.open(image_path)
                    st.image(img, caption=result.get('caption', 'No caption'), use_container_width=True)
                except Exception as e:
                    st.error(f"Error loading image: {e}")
            
            caption = result.get('caption', '')
            if caption:
                st.markdown(f"**Caption:** {caption}")
        
        elif modality == 'table':
            content = result.get('content', '')
            if content:
                with st.expander("View Table Content"):
                    st.text(content)
            
            file_path = result.get('metadata', {}).get('file_path', '')
            if file_path and Path(file_path).exists():
                try:
                    if file_path.endswith('.csv'):
                        df = pd.read_csv(file_path)
                    elif file_path.endswith('.xlsx'):
                        df = pd.read_excel(file_path)
                    else:
                        df = None
                    
                    if df is not None:
                        st.dataframe(df.head(10), use_container_width=True)
                except Exception as e:
                    st.error(f"Error loading table: {e}")
        
        elif modality == 'text':
            content = result.get('content', '')
            st.markdown(f"**Content:**")
            st.text_area("", content, height=150, key=f"text_{idx}", disabled=True)
        
        st.divider()

def main():
    st.title("🔍 Multimodal RAG System")
    st.markdown("Search across text, images, and tables with unified retrieval")
    
    try:
        ingestion, indexer, retriever, config = initialize_system()
    except Exception as e:
        st.error(f"Failed to initialize system: {e}")
        st.exception(e)
        return
    
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        top_k = st.slider("Number of Results", min_value=1, max_value=20, value=5)
        
        modality_filter = st.multiselect(
            "Filter by Modality",
            options=['text', 'image', 'table'],
            default=[]
        )
        
        st.divider()
        st.header("📤 Upload Files")
        
        uploaded_files = st.file_uploader(
            "Choose files",
            accept_multiple_files=True,
            type=['txt', 'pdf', 'docx', 'png', 'jpg', 'jpeg', 'csv', 'xlsx', 'json'],
            help="Upload documents, images, or tables to index"
        )
        
        if uploaded_files:
            if st.button("🚀 Process Uploaded Files", type="primary", use_container_width=True):
                data_dir = Path("./data")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                success_count = 0
                errors = []
                
                for idx, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Processing {uploaded_file.name}...")
                    
                    try:
                        file_path = save_uploaded_file(uploaded_file, data_dir)
                        st.info(f"✅ Saved: {file_path}")
                        
                        chunks = ingestion.process_file(str(file_path))
                        
                        if chunks:
                            result = indexer.index_chunks(chunks)
                            st.success(f"✅ Indexed {result['indexed']} chunks from {uploaded_file.name}")
                            success_count += 1
                        else:
                            st.warning(f"⚠️ No content extracted from {uploaded_file.name}")
                    
                    except Exception as e:
                        errors.append(f"{uploaded_file.name}: {str(e)}")
                        st.error(f"❌ Error: {e}")
                    
                    progress_bar.progress((idx + 1) / len(uploaded_files))
                
                status_text.empty()
                
                if success_count > 0:
                    st.success(f"✅ Successfully processed {success_count}/{len(uploaded_files)} file(s)")
                
                if errors:
                    st.error("❌ Errors encountered:")
                    for error in errors:
                        st.text(error)
        
        st.divider()
        st.markdown("**📊 System Status**")
        
        try:
            stats = indexer.get_collection_stats()
            st.metric("Total Items", stats['total_items'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Text", stats['text_count'])
            with col2:
                st.metric("Images", stats['image_count'])
            with col3:
                st.metric("Tables", stats['table_count'])
        except Exception as e:
            st.error(f"Error getting stats: {e}")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                if "results" in message:
                    st.markdown(message["content"])
                    for idx, result in enumerate(message["results"]):
                        render_result(result, idx)
                else:
                    st.markdown(message["content"])
            else:
                st.markdown(message["content"])
    
    if query := st.chat_input("Enter your search query (e.g., 'machine learning algorithms' or 'sales data')"):
        st.session_state.messages.append({"role": "user", "content": query})
        
        with st.chat_message("user"):
            st.markdown(query)
        
        with st.chat_message("assistant"):
            with st.spinner("Searching..."):
                start_time = time.time()
                
                try:
                    response = retriever.retrieve(query, top_k=top_k)
                    
                    results = []
                    for r in response['results']:
                        result_dict = {
                            'modality': r.get('modality', 'unknown'),
                            'score': r.get('similarity_score', 0),
                            'source': r.get('metadata', {}).get('source', 'Unknown'),
                            'content': r.get('content', ''),
                            'image_path': r.get('metadata', {}).get('image_path', ''),
                            'caption': r.get('metadata', {}).get('caption', ''),
                            'metadata': r.get('metadata', {})
                        }
                        results.append(result_dict)
                    
                    if modality_filter:
                        results = [r for r in results if r.get('modality') in modality_filter]
                    
                    elapsed_time = response['metadata']['latency_seconds']
                    
                    if results:
                        response_text = f"Found {len(results)} results in {elapsed_time:.3f} seconds"
                        st.markdown(response_text)
                        
                        for idx, result in enumerate(results):
                            render_result(result, idx)
                        
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response_text,
                            "results": results
                        })
                    else:
                        response_text = "No results found. Try a different query or upload more files."
                        st.warning(response_text)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response_text
                        })
                
                except Exception as e:
                    error_text = f"Error during search: {str(e)}"
                    st.error(error_text)
                    st.exception(e)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_text
                    })
    
    with st.expander("ℹ️ How to use this system"):
        st.markdown("""
        ### Search
        1. Type your query in the chat input at the bottom
        2. System will search across all indexed content (text, images, tables)
        3. Results show relevance scores and source information
        
        ### Upload Files
        1. Use the sidebar file uploader
        2. Select multiple files (TXT, PDF, DOCX, PNG, JPG, CSV, XLSX)
        3. Click 'Process Uploaded Files' to index them
        4. Files are saved to `data/` directory and immediately searchable
        
        ### Results
        - 🟦 Text chunks with content preview
        - 🟩 Images displayed with OCR captions
        - 🟨 Tables shown as interactive dataframes
        - Higher scores = more relevant results
        """)

if __name__ == "__main__":
    main()