from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime

class SearchResult(BaseModel):
    """Search result model"""
    content: str = Field(..., description="Result content")
    confidence: float = Field(..., ge=0, le=1, description="Match confidence")
    source: str = Field(..., description="Source file/document")
    method: str = Field(..., description="Search method used")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class QASearchRequest(BaseModel):
    """Q&A search request"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    domain: str = Field(default="general", description="Search domain")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum results")

class QASearchResponse(BaseModel):
    """Q&A search response"""
    query: str = Field(..., description="Original query")
    domain: str = Field(..., description="Search domain") 
    results: List[SearchResult] = Field(..., description="Search results")
    total_found: int = Field(..., description="Total results found")
    processing_time: float = Field(..., description="Processing time in seconds")

# session_models.py
class SessionInfo(BaseModel):
    """Session information model"""
    session_id: str = Field(..., description="Session identifier")
    created_at: datetime = Field(..., description="Session creation time")
    last_activity: datetime = Field(..., description="Last activity time") 
    total_interactions: int = Field(..., description="Total interactions")
    current_domain: str = Field(..., description="Current domain")
    current_context: str = Field(..., description="Current context type")

class SessionAnalytics(BaseModel):
    """Session analytics model"""
    session_info: SessionInfo = Field(..., description="Basic session info")
    interaction_patterns: Dict[str, Any] = Field(..., description="Interaction patterns")
    flow_analytics: Optional[Dict[str, Any]] = Field(None, description="Flow analytics")
    rag_analytics: Optional[Dict[str, Any]] = Field(None, description="RAG analytics")
    recommendations: List[str] = Field(..., description="Recommendations for user")

class UserPreferences(BaseModel):
    """User preferences model"""
    preferred_domain: str = Field(..., description="Most used domain")
    preferred_context: str = Field(..., description="Most used context type")
    avg_confidence: float = Field(..., description="Average response confidence")
    user_type: str = Field(..., description="Classified user type")
    domain_distribution: Dict[str, int] = Field(..., description="Domain usage distribution")