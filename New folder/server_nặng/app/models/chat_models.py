# app/models/chat_models.py - Pydantic models cho Chat
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime

class ChatRequest(BaseModel):
    """Main chat request model"""
    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    session_id: str = Field(..., min_length=1, description="Session identifier")  
    domain: Optional[str] = Field(None, description="Preferred domain")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    
    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()

class ChatResponse(BaseModel):
    """Main chat response model"""
    response: str = Field(..., description="System response")
    type: str = Field(..., description="Response type (flow/rag/error/help)")
    session_id: str = Field(..., description="Session identifier")
    confidence: float = Field(..., ge=0, le=1, description="Response confidence")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    suggestions: List[str] = Field(default_factory=list, description="Follow-up suggestions")
    flow_data: Optional[Dict[str, Any]] = Field(None, description="Flow-specific data")

# flow_models.py
class FlowStepData(BaseModel):
    """Flow step data model"""
    step_number: str = Field(..., description="Current step number")
    total_steps: int = Field(..., description="Total steps in flow")
    name: str = Field(..., description="Step name")
    description: str = Field(..., description="Step description") 
    tts: Optional[str] = Field(None, description="Text-to-speech content")
    link: Optional[str] = Field(None, description="Related link")
    image: Optional[str] = Field(None, description="Step image URL")
    wait_for_user: bool = Field(True, description="Wait for user action")

class FlowQuestionData(BaseModel):
    """Flow question data model"""
    question_id: str = Field(..., description="Question identifier")
    question: str = Field(..., description="Question text")
    options: List[Dict[str, str]] = Field(..., description="Available options")

class FlowStartRequest(BaseModel):
    """Start flow request"""
    domain: str = Field(..., description="Domain to start flow")
    session_id: str = Field(..., description="Session identifier")

class FlowNavigateRequest(BaseModel):
    """Navigate flow request"""
    choice: str = Field(..., description="User choice/action")
    session_id: str = Field(..., description="Session identifier")