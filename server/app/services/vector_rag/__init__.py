# services/vector_rag/__init__.py
"""
Vector RAG package for Vietnamese legal documents
"""

# Import main components
from .rag_engine import RAGEngine
from .rag_config import config

__all__ = ['RAGEngine', 'config']