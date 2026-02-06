#!/bin/bash

cd /root/claude_tests/MultiModelRag

source venv/bin/activate

export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_SERVER_PORT=8501
export STREAMLIT_SERVER_ADDRESS=0.0.0.0

echo "Starting Multimodal RAG UI..."
echo "Access the UI at: http://localhost:8501"
echo ""

streamlit run app.py --server.headless true --server.port 8501 --server.address 0.0.0.0