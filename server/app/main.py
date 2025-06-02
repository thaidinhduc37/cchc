"""
🚀 Main FastAPI Application với Complete API Endpoints
DVC RAG System - Dual Function (Flow + RAG) Chatbot
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
import logging
import time
import asyncio
from pathlib import Path
import json

# Import our core modules
from app.core.smart_router import SmartRouter, RouterResult, IntentType, Domain
from app.core.flow_engine import FlowEngine, FlowResponse, FlowStatus, ResponseType
from app.core.rag_engine import RAGEngine, RAGResponse, ConfidenceLevel
from app.core.context_manager import ContextManager, UserIntent, ContextType
from app.services.gemma_service import GemmaService, create_default_config
from app.services.excel_qa_service import ExcelQAService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic Models
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    session_id: str = Field(..., description="Session identifier")
    domain: Optional[str] = Field(None, description="Preferred domain")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

class ChatResponse(BaseModel):
    response: str = Field(..., description="System response")
    type: str = Field(..., description="Response type (flow/rag/error)")
    session_id: str = Field(..., description="Session identifier")
    confidence: float = Field(..., description="Response confidence")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    suggestions: List[str] = Field(default_factory=list, description="Follow-up suggestions")
    flow_data: Optional[Dict[str, Any]] = Field(None, description="Flow-specific data")

class FlowStartRequest(BaseModel):
    domain: str = Field(..., description="Domain to start flow")
    session_id: str = Field(..., description="Session identifier")

class FlowNavigateRequest(BaseModel):
    choice: str = Field(..., description="User choice/action")
    session_id: str = Field(..., description="Session identifier")

class AdminRebuildRequest(BaseModel):
    domain: Optional[str] = Field(None, description="Domain to rebuild (None = all)")
    rebuild_type: str = Field("full", description="Rebuild type: full/cache/indices")

# Initialize FastAPI app
app = FastAPI(
    title="DVC RAG System",
    description="Dual Function Chatbot - Flow Guidance + Legal Q&A",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for assets (images, etc.)
app.mount("/assets", StaticFiles(directory="data"), name="assets")

# Global components
smart_router: Optional[SmartRouter] = None
flow_engine: Optional[FlowEngine] = None
rag_engine: Optional[RAGEngine] = None
context_manager: Optional[ContextManager] = None
gemma_service: Optional[GemmaService] = None
excel_service: Optional[ExcelQAService] = None

@app.on_event("startup")
async def startup_event():
    """Initialize all services on startup"""
    global smart_router, flow_engine, rag_engine, context_manager, gemma_service, excel_service
    
    try:
        logger.info("🚀 Starting DVC RAG System...")
        
        # Initialize core components
        smart_router = SmartRouter()
        flow_engine = FlowEngine("data")
        rag_engine = RAGEngine("data")
        context_manager = ContextManager()
        excel_service = ExcelQAService("data")
        
        # Initialize Gemma service
        gemma_config = create_default_config()
        gemma_service = GemmaService(gemma_config)
        
        # Test model health
        health_status = await gemma_service.check_model_health()
        logger.info(f"🧠 Model health: {health_status}")
        
        # Load initial data
        available_domains = excel_service._get_available_domains()
        logger.info(f"📁 Available domains: {available_domains}")
        
        for domain in available_domains:
            try:
                df = excel_service.load_domain_qa(domain)
                logger.info(f"✅ Loaded {len(df)} Q&A pairs for {domain}")
            except Exception as e:
                logger.warning(f"⚠️ Could not load {domain}: {e}")
        
        logger.info("✅ DVC RAG System started successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to start system: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down DVC RAG System...")
    
    # Cleanup expired sessions
    if context_manager:
        cleaned = context_manager.cleanup_expired_sessions()
        logger.info(f"🧹 Cleaned {cleaned} expired sessions")

# Main Chat Endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint - handles both Flow và RAG
    """
    try:
        start_time = time.time()
        
        # Get or create user session
        session = context_manager.get_or_create_session(request.session_id)
        
        # Get conversation context
        conv_context = context_manager.get_conversation_context(request.session_id)
        
        # Route request
        router_result = smart_router.route_request(
            request.message, 
            conv_context
        )
        
        # Determine if context should switch
        should_switch = context_manager.should_switch_context(
            request.session_id,
            ContextType(router_result.intent_type.value),
            router_result.domain.value,
            router_result.confidence
        )
        
        response = None
        
        # Handle Flow Intent
        if router_result.intent_type == IntentType.FLOW:
            response = await _handle_flow_intent(
                request, router_result, should_switch
            )
        
        # Handle RAG Intent
        elif router_result.intent_type == IntentType.RAG:
            response = await _handle_rag_intent(
                request, router_result, should_switch
            )
        
        # Handle Unknown Intent
        else:
            response = await _handle_unknown_intent(request, router_result)
        
        # Update context
        intent = UserIntent.FLOW_GUIDANCE if router_result.intent_type == IntentType.FLOW else UserIntent.QA_INQUIRY
        context_type = ContextType.FLOW if router_result.intent_type == IntentType.FLOW else ContextType.RAG
        
        context_manager.add_message_context(
            session_id=request.session_id,
            user_input=request.message,
            response=response.response,
            intent=intent,
            context_type=context_type,
            domain=router_result.domain.value,
            confidence=response.confidence,
            metadata={
                "router_reasoning": router_result.reasoning,
                "processing_time": time.time() - start_time,
                "should_switch": should_switch
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return ChatResponse(
            response=f"Xin lỗi, đã xảy ra lỗi: {str(e)}",
            type="error",
            session_id=request.session_id,
            confidence=0.0,
            metadata={"error": str(e)}
        )

async def _handle_flow_intent(request: ChatRequest, router_result: RouterResult, 
                             should_switch: bool) -> ChatResponse:
    """Handle flow guidance intent"""
    
    try:
        # Get current flow state
        flow_state = flow_engine.get_user_state(request.session_id)
        
        if flow_state is None or should_switch:
            # Start new flow
            flow_response = flow_engine.start_flow(
                request.session_id, 
                router_result.domain.value
            )
        else:
            # Navigate existing flow
            flow_response = flow_engine.navigate_flow(
                request.session_id,
                request.message
            )
        
        # Update flow context
        if flow_response.type == ResponseType.STEP:
            context_manager.update_flow_context(
                session_id=request.session_id,
                domain=router_result.domain.value,
                flow_id=flow_response.metadata.get("flow_id"),
                step=flow_response.content.get("step_number"),
                completed_steps=int(flow_response.content.get("step_number", 0)) - 1,
                total_steps=flow_response.content.get("total_steps", 0)
            )
        elif flow_response.type == ResponseType.QUESTION:
            context_manager.update_flow_context(
                session_id=request.session_id,
                domain=router_result.domain.value,
                question_id=flow_response.content.get("question_id")
            )
        
        # Format response
        if flow_response.type == ResponseType.QUESTION:
            response_text = flow_response.content["question"]
            if flow_response.content.get("options"):
                options_text = "\n\n" + "\n".join([
                    f"👉 {opt['label']}" for opt in flow_response.content["options"]
                ])
                response_text += options_text
        else:
            response_text = flow_response.content.get("name", "") + "\n\n" + \
                          flow_response.content.get("description", "")
        
        # Generate suggestions
        suggestions = []
        if flow_response.next_actions:
            if "next" in flow_response.next_actions:
                suggestions.append("Tiếp theo")
            if "back" in flow_response.next_actions:
                suggestions.append("Quay lại")
            if "restart" in flow_response.next_actions:
                suggestions.append("Bắt đầu lại")
        
        # Add flow completion suggestion
        if flow_response.status == FlowStatus.COMPLETED:
            suggestions.extend([
                "Bắt đầu thủ tục khác",
                "Có câu hỏi gì khác không?"
            ])
        
        return ChatResponse(
            response=response_text,
            type="flow",
            session_id=request.session_id,
            confidence=0.9,  # High confidence for flow responses
            metadata={
                "flow_status": flow_response.status.value,
                "response_type": flow_response.type.value,
                "domain": router_result.domain.value
            },
            suggestions=suggestions,
            flow_data={
                "type": flow_response.type.value,
                "content": flow_response.content,
                "next_actions": flow_response.next_actions,
                "metadata": flow_response.metadata
            }
        )
        
    except Exception as e:
        logger.error(f"Error handling flow intent: {e}")
        raise

async def _handle_rag_intent(request: ChatRequest, router_result: RouterResult,
                            should_switch: bool) -> ChatResponse:
    """Handle RAG Q&A intent"""
    
    try:
        # Search for answer
        rag_response = rag_engine.search_legal_qa(
            query=request.message,
            domain=router_result.domain.value
        )
        
        # Update RAG context
        context_manager.update_rag_context(
            session_id=request.session_id,
            domain=router_result.domain.value,
            query=request.message,
            answer=rag_response.answer,
            confidence=rag_response.confidence
        )
        
        # Generate enhanced response if confidence is low
        if rag_response.confidence < 0.7 and gemma_service:
            try:
                # Get additional context
                context_info = context_manager.get_conversation_context(request.session_id)
                
                # Use LLM to enhance response
                enhanced_response = await gemma_service.generate_legal_answer(
                    query=request.message,
                    context=rag_response.answer,
                    domain=router_result.domain.value
                )
                
                if enhanced_response.confidence > rag_response.confidence:
                    rag_response.answer = enhanced_response.content
                    rag_response.confidence = enhanced_response.confidence
                    
            except Exception as e:
                logger.warning(f"Could not enhance response with LLM: {e}")
        
        # Prepare suggestions
        suggestions = rag_response.follow_up_questions or []
        
        # Add flow suggestion if available
        if rag_response.suggest_flow:
            suggestions.insert(0, f"📋 Hướng dẫn từng bước")
        
        # Add domain exploration
        if router_result.domain != Domain.GENERAL:
            suggestions.append("Tìm hiểu thêm về lĩnh vực khác")
        
        return ChatResponse(
            response=rag_response.answer,
            type="rag",
            session_id=request.session_id,
            confidence=rag_response.confidence,
            metadata={
                "method_used": rag_response.method_used.value,
                "confidence_level": rag_response.confidence_level.value,
                "sources_count": len(rag_response.sources),
                "domain": router_result.domain.value,
                "suggest_flow": rag_response.suggest_flow
            },
            suggestions=suggestions[:5]  # Limit to 5 suggestions
        )
        
    except Exception as e:
        logger.error(f"Error handling RAG intent: {e}")
        raise

async def _handle_unknown_intent(request: ChatRequest, router_result: RouterResult) -> ChatResponse:
    """Handle unknown/unclear intent"""
    
    # Try to get help from LLM
    try:
        if gemma_service:
            help_response = await gemma_service.generate_text(
                f"Người dùng nói: '{request.message}'. Hãy giúp họ bằng cách gợi ý họ có thể hỏi về thủ tục hành chính hoặc yêu cầu hướng dẫn.",
            )
            response_text = help_response.content
        else:
            response_text = (
                "Xin lỗi, tôi chưa hiểu rõ yêu cầu của bạn. "
                "Bạn có thể:\n\n"
                "📋 Yêu cầu hướng dẫn thủ tục (ví dụ: 'Hướng dẫn làm hộ chiếu')\n"
                "❓ Hỏi về quy định, phí, thời gian (ví dụ: 'Phí làm CCCD bao nhiêu?')\n"
                "🔍 Tìm hiểu về các lĩnh vực: xuất nhập cảnh, căn cước công dân"
            )
    except Exception as e:
        logger.warning(f"Could not generate help response: {e}")
        response_text = "Xin lỗi, tôi chưa hiểu rõ yêu cầu của bạn. Vui lòng thử lại với câu hỏi cụ thể hơn."
    
    return ChatResponse(
        response=response_text,
        type="help",
        session_id=request.session_id,
        confidence=0.5,
        metadata={
            "router_reasoning": router_result.reasoning,
            "domain": router_result.domain.value
        },
        suggestions=[
            "Hướng dẫn làm hộ chiếu",
            "Phí làm căn cước công dân",
            "Thủ tục xuất nhập cảnh",
            "Thời gian làm visa"
        ]
    )

# Flow Control Endpoints
@app.post("/api/flow/start")
async def start_flow(request: FlowStartRequest) -> Dict[str, Any]:
    """Start a new flow for user"""
    try:
        flow_response = flow_engine.start_flow(request.session_id, request.domain)
        
        # Update context
        context_manager.update_flow_context(
            session_id=request.session_id,
            domain=request.domain,
            question_id=flow_response.content.get("question_id")
        )
        
        return {
            "success": True,
            "flow_response": {
                "type": flow_response.type.value,
                "content": flow_response.content,
                "status": flow_response.status.value,
                "next_actions": flow_response.next_actions,
                "metadata": flow_response.metadata
            }
        }
        
    except Exception as e:
        logger.error(f"Error starting flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/flow/navigate")
async def navigate_flow(request: FlowNavigateRequest) -> Dict[str, Any]:
    """Navigate in current flow"""
    try:
        flow_response = flow_engine.navigate_flow(request.session_id, request.choice)
        
        # Update context based on response type
        if flow_response.type == ResponseType.STEP:
            context_manager.update_flow_context(
                session_id=request.session_id,
                domain=flow_response.metadata.get("domain", "general"),
                step=flow_response.content.get("step_number"),
                completed_steps=int(flow_response.content.get("step_number", 0)) - 1,
                total_steps=flow_response.content.get("total_steps", 0)
            )
        
        return {
            "success": True,
            "flow_response": {
                "type": flow_response.type.value,
                "content": flow_response.content,
                "status": flow_response.status.value,
                "next_actions": flow_response.next_actions,
                "metadata": flow_response.metadata
            }
        }
        
    except Exception as e:
        logger.error(f"Error navigating flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/flow/reset/{session_id}")
async def reset_flow(session_id: str) -> Dict[str, Any]:
    """Reset user flow state"""
    try:
        success = flow_engine.reset_user_state(session_id)
        
        if success:
            # Clear flow context
            context_manager.clear_session_context(session_id, ContextType.FLOW)
        
        return {
            "success": success,
            "message": "Flow state reset successfully" if success else "No flow state found"
        }
        
    except Exception as e:
        logger.error(f"Error resetting flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/flow/available/{domain}")
async def get_available_flows(domain: str) -> Dict[str, Any]:
    """Get available flows for domain"""
    try:
        flows = flow_engine.get_available_flows(domain)
        return {
            "success": True,
            "domain": domain,
            "flows": flows
        }
        
    except Exception as e:
        logger.error(f"Error getting available flows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Session Management Endpoints
@app.get("/api/session/{session_id}")
async def get_session_info(session_id: str) -> Dict[str, Any]:
    """Get session information"""
    try:
        # Get session analytics
        analytics = context_manager.get_session_analytics(session_id)
        
        # Get user preferences
        preferences = context_manager.get_user_preferences(session_id)
        
        # Get conversation context
        context = context_manager.get_conversation_context(session_id, context_window=10)
        
        return {
            "success": True,
            "session_id": session_id,
            "analytics": analytics,
            "preferences": preferences,
            "context": context
        }
        
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/session/{session_id}")
async def clear_session(session_id: str) -> Dict[str, Any]:
    """Clear session data"""
    try:
        # Clear all contexts
        context_cleared = context_manager.clear_session_context(session_id)
        
        # Reset flow state
        flow_reset = flow_engine.reset_user_state(session_id)
        
        return {
            "success": True,
            "context_cleared": context_cleared,
            "flow_reset": flow_reset,
            "message": "Session cleared successfully"
        }
        
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Admin Endpoints
@app.post("/api/admin/rebuild")
async def rebuild_system(request: AdminRebuildRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Rebuild system components (cache, indices, etc.)"""
    try:
        rebuild_results = {}
        
        if request.rebuild_type in ["full", "indices"]:
            # Rebuild Excel indices
            if request.domain:
                domain_results = excel_service.rebuild_all_indices()
                rebuild_results["excel_indices"] = {request.domain: domain_results.get(request.domain, False)}
            else:
                rebuild_results["excel_indices"] = excel_service.rebuild_all_indices()
        
        if request.rebuild_type in ["full", "cache"]:
            # Clear caches
            cache_sizes = excel_service.clear_cache()
            rebuild_results["cache_cleared"] = cache_sizes
            
            # Clear context cache
            context_manager.cleanup_expired_sessions()
            rebuild_results["sessions_cleaned"] = True
        
        if request.rebuild_type == "full":
            # Rebuild vector indices (if available)
            if hasattr(rag_engine, 'rebuild_vector_index') and request.domain:
                background_tasks.add_task(rag_engine.rebuild_vector_index, request.domain)
                rebuild_results["vector_index"] = "rebuilding_in_background"
        
        return {
            "success": True,
            "rebuild_type": request.rebuild_type,
            "domain": request.domain,
            "results": rebuild_results,
            "message": "Rebuild completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error rebuilding system: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/stats")
async def get_system_stats() -> Dict[str, Any]:
    """Get comprehensive system statistics"""
    try:
        stats = {
            "system_info": {
                "version": "2.0.0",
                "uptime": time.time(),  # Would track actual uptime in production
                "domains_available": excel_service._get_available_domains()
            },
            "router_stats": smart_router.get_routing_stats() if smart_router else {},
            "flow_stats": {
                "active_flows": len(flow_engine.user_states) if flow_engine else 0
            },
            "excel_stats": excel_service.get_service_stats() if excel_service else {},
            "context_stats": context_manager.get_global_statistics() if context_manager else {},
            "gemma_stats": gemma_service.get_service_stats() if gemma_service else {}
        }
        
        return {
            "success": True,
            "timestamp": time.time(),
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/health")
async def health_check() -> Dict[str, Any]:
    """System health check"""
    try:
        health_status = {
            "overall": "healthy",
            "components": {}
        }
        
        # Check core components
        health_status["components"]["smart_router"] = "healthy" if smart_router else "unavailable"
        health_status["components"]["flow_engine"] = "healthy" if flow_engine else "unavailable"
        health_status["components"]["rag_engine"] = "healthy" if rag_engine else "unavailable"
        health_status["components"]["context_manager"] = "healthy" if context_manager else "unavailable"
        health_status["components"]["excel_service"] = "healthy" if excel_service else "unavailable"
        
        # Check Gemma service
        if gemma_service:
            try:
                model_health = await gemma_service.check_model_health()
                health_status["components"]["gemma_service"] = {
                    "status": "healthy" if any(h.get("status") == "healthy" for h in model_health.values()) else "degraded",
                    "providers": model_health
                }
            except Exception as e:
                health_status["components"]["gemma_service"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        else:
            health_status["components"]["gemma_service"] = "unavailable"
        
        # Determine overall health
        component_statuses = [
            comp.get("status", comp) if isinstance(comp, dict) else comp
            for comp in health_status["components"].values()
        ]
        
        if any(status == "unhealthy" for status in component_statuses):
            health_status["overall"] = "unhealthy"
        elif any(status in ["degraded", "unavailable"] for status in component_statuses):
            health_status["overall"] = "degraded"
        
        return {
            "success": True,
            "timestamp": time.time(),
            "health": health_status
        }
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return {
            "success": False,
            "timestamp": time.time(),
            "health": {
                "overall": "unhealthy",
                "error": str(e)
            }
        }

# Domain Management Endpoints
@app.get("/api/domains")
async def get_domains() -> Dict[str, Any]:
    """Get available domains với statistics"""
    try:
        domains = excel_service._get_available_domains()
        domain_info = {}
        
        for domain in domains:
            stats = excel_service.get_domain_statistics(domain)
            flows = flow_engine.get_available_flows(domain)
            
            domain_info[domain] = {
                "qa_pairs": stats.get("total_qa_pairs", 0),
                "flows_available": len(flows),
                "flows": flows
            }
        
        return {
            "success": True,
            "domains": domain_info,
            "total_domains": len(domains)
        }
        
    except Exception as e:
        logger.error(f"Error getting domains: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/domains/{domain}/stats")
async def get_domain_stats(domain: str) -> Dict[str, Any]:
    """Get detailed statistics for specific domain"""
    try:
        # Excel Q&A stats
        qa_stats = excel_service.get_domain_statistics(domain)
        
        # Flow stats
        flows = flow_engine.get_available_flows(domain)
        
        # Usage stats from context manager
        global_stats = context_manager.get_global_statistics()
        domain_usage = global_stats.get("domain_usage", {}).get(domain, 0)
        
        return {
            "success": True,
            "domain": domain,
            "qa_statistics": qa_stats,
            "flow_statistics": {
                "total_flows": len(flows),
                "flows": flows
            },
            "usage_statistics": {
                "total_requests": domain_usage
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting domain stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Search Endpoints
@app.get("/api/search")
async def search_qa(q: str, domain: str = "general", limit: int = 5) -> Dict[str, Any]:
    """Direct Q&A search endpoint"""
    try:
        results = excel_service.search_qa(q, domain, max_results=limit)
        
        formatted_results = []
        for result in results:
            formatted_results.append({
                "question": result.question,
                "answer": result.answer,
                "confidence": result.confidence,
                "match_type": result.match_type.value,
                "metadata": result.metadata
            })
        
        return {
            "success": True,
            "query": q,
            "domain": domain,
            "results": formatted_results,
            "total_found": len(formatted_results)
        }
        
    except Exception as e:
        logger.error(f"Error in search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/similar")
async def get_similar_questions(q: str, domain: str = "general", limit: int = 5) -> Dict[str, Any]:
    """Get similar questions for suggestion"""
    try:
        similar = excel_service.get_similar_questions(q, domain, limit)
        
        return {
            "success": True,
            "query": q,
            "domain": domain,
            "similar_questions": similar
        }
        
    except Exception as e:
        logger.error(f"Error getting similar questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint với system info"""
    return {
        "name": "DVC RAG System",
        "version": "2.0.0",
        "description": "Dual Function Chatbot - Flow Guidance + Legal Q&A",
        "status": "running",
        "endpoints": {
            "chat": "/api/chat",
            "docs": "/docs",
            "health": "/api/admin/health",
            "stats": "/api/admin/stats"
        }
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"success": False, "error": "Endpoint not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"}
    )

# Development server
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )