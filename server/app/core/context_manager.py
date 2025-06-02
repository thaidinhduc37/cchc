"""
💬 Context Manager - Quản lý context và memory cho conversation
Track user state, flow progress, và RAG history
"""

import json
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime, timedelta
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class ContextType(Enum):
    FLOW = "flow"
    RAG = "rag"
    HYBRID = "hybrid"
    IDLE = "idle"

class UserIntent(Enum):
    UNKNOWN = "unknown"
    FLOW_GUIDANCE = "flow_guidance" 
    QA_INQUIRY = "qa_inquiry"
    CLARIFICATION = "clarification"
    NAVIGATION = "navigation"

@dataclass
class MessageContext:
    """Context cho một message"""
    timestamp: float
    user_input: str
    intent: UserIntent
    context_type: ContextType
    domain: str
    response: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FlowContext:
    """Context cho Flow state"""
    domain: str
    current_question_id: Optional[str] = None
    current_flow_id: Optional[str] = None
    current_step: Optional[str] = None
    step_history: List[str] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    completed_steps: int = 0
    total_steps: int = 0

@dataclass 
class RAGContext:
    """Context cho RAG conversations"""
    domain: str
    query_history: List[str] = field(default_factory=list)
    answer_history: List[str] = field(default_factory=list)
    topics_discussed: List[str] = field(default_factory=list)
    confidence_scores: List[float] = field(default_factory=list)
    last_query_time: float = field(default_factory=time.time)

@dataclass
class UserSession:
    """User session với complete context"""
    session_id: str
    created_at: float
    last_activity: float
    current_context_type: ContextType
    current_domain: str
    
    # Context histories
    message_history: List[MessageContext] = field(default_factory=list)
    flow_context: Optional[FlowContext] = None
    rag_context: Optional[RAGContext] = None
    
    # Analytics
    total_interactions: int = 0
    preferred_domains: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    user_patterns: Dict[str, Any] = field(default_factory=dict)

class ContextManager:
    """
    Context Manager - Quản lý conversation context và memory
    """
    
    def __init__(self, max_history_size: int = 50, session_timeout: int = 3600):
        self.max_history_size = max_history_size
        self.session_timeout = session_timeout  # seconds
        
        # In-memory storage (trong production sẽ dùng Redis/Database)
        self.user_sessions: Dict[str, UserSession] = {}
        
        # Domain switching thresholds
        self.domain_confidence_threshold = 0.7
        self.context_switch_threshold = 0.8
        
        # Analytics
        self.global_stats = {
            "total_sessions": 0,
            "active_sessions": 0,
            "domain_usage": defaultdict(int),
            "context_switches": defaultdict(int)
        }

    def get_or_create_session(self, session_id: str) -> UserSession:
        """
        Get existing session hoặc tạo mới
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            UserSession object
        """
        try:
            # Check if session exists và chưa timeout
            if session_id in self.user_sessions:
                session = self.user_sessions[session_id]
                
                # Check timeout
                if time.time() - session.last_activity > self.session_timeout:
                    logger.info(f"Session {session_id} timed out, creating new one")
                    del self.user_sessions[session_id]
                else:
                    # Update last activity
                    session.last_activity = time.time()
                    return session
            
            # Create new session
            session = UserSession(
                session_id=session_id,
                created_at=time.time(),
                last_activity=time.time(),
                current_context_type=ContextType.IDLE,
                current_domain="general"
            )
            
            self.user_sessions[session_id] = session
            self.global_stats["total_sessions"] += 1
            
            logger.info(f"Created new session: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Error getting/creating session {session_id}: {e}")
            # Return minimal session on error
            return UserSession(
                session_id=session_id,
                created_at=time.time(),
                last_activity=time.time(),
                current_context_type=ContextType.IDLE,
                current_domain="general"
            )

    def add_message_context(self, session_id: str, user_input: str, response: str, 
                           intent: UserIntent, context_type: ContextType, 
                           domain: str, confidence: float, 
                           metadata: Optional[Dict] = None) -> None:
        """
        Add message context to session history
        
        Args:
            session_id: Session identifier
            user_input: User's input message
            response: System response
            intent: Detected user intent
            context_type: Current context type
            domain: Current domain
            confidence: Confidence score
            metadata: Additional metadata
        """
        try:
            session = self.get_or_create_session(session_id)
            
            # Create message context
            msg_context = MessageContext(
                timestamp=time.time(),
                user_input=user_input,
                intent=intent,
                context_type=context_type,
                domain=domain,
                response=response,
                confidence=confidence,
                metadata=metadata or {}
            )
            
            # Add to history
            session.message_history.append(msg_context)
            
            # Maintain history size limit
            if len(session.message_history) > self.max_history_size:
                session.message_history = session.message_history[-self.max_history_size:]
            
            # Update session stats
            session.total_interactions += 1
            session.preferred_domains[domain] += 1
            session.last_activity = time.time()
            
            # Update global stats
            self.global_stats["domain_usage"][domain] += 1
            
            logger.debug(f"Added message context for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error adding message context: {e}")

    def update_flow_context(self, session_id: str, domain: str, 
                           question_id: Optional[str] = None,
                           flow_id: Optional[str] = None,
                           step: Optional[str] = None,
                           completed_steps: int = 0,
                           total_steps: int = 0) -> None:
        """
        Update flow context for session
        
        Args:
            session_id: Session identifier
            domain: Current domain
            question_id: Current question ID
            flow_id: Current flow ID
            step: Current step number
            completed_steps: Number of completed steps
            total_steps: Total steps in flow
        """
        try:
            session = self.get_or_create_session(session_id)
            
            # Create or update flow context
            if session.flow_context is None:
                session.flow_context = FlowContext(domain=domain)
            
            # Update flow state
            if question_id is not None:
                session.flow_context.current_question_id = question_id
            if flow_id is not None:
                session.flow_context.current_flow_id = flow_id
            if step is not None:
                session.flow_context.current_step = step
                # Add to step history if new step
                step_entry = f"{flow_id or 'Q'}:{step}"
                if not session.flow_context.step_history or session.flow_context.step_history[-1] != step_entry:
                    session.flow_context.step_history.append(step_entry)
            
            session.flow_context.completed_steps = completed_steps
            session.flow_context.total_steps = total_steps
            session.flow_context.last_activity = time.time()
            
            # Update session context
            session.current_context_type = ContextType.FLOW
            session.current_domain = domain
            
            logger.debug(f"Updated flow context for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error updating flow context: {e}")

    def update_rag_context(self, session_id: str, domain: str, 
                          query: str, answer: str, confidence: float,
                          topics: Optional[List[str]] = None) -> None:
        """
        Update RAG context for session
        
        Args:
            session_id: Session identifier
            domain: Current domain
            query: User query
            answer: System answer
            confidence: Answer confidence
            topics: Discussed topics
        """
        try:
            session = self.get_or_create_session(session_id)
            
            # Create or update RAG context
            if session.rag_context is None or session.rag_context.domain != domain:
                session.rag_context = RAGContext(domain=domain)
            
            # Update RAG state
            session.rag_context.query_history.append(query)
            session.rag_context.answer_history.append(answer)
            session.rag_context.confidence_scores.append(confidence)
            session.rag_context.last_query_time = time.time()
            
            # Update topics
            if topics:
                for topic in topics:
                    if topic not in session.rag_context.topics_discussed:
                        session.rag_context.topics_discussed.append(topic)
            
            # Maintain history limits
            max_rag_history = 20
            if len(session.rag_context.query_history) > max_rag_history:
                session.rag_context.query_history = session.rag_context.query_history[-max_rag_history:]
                session.rag_context.answer_history = session.rag_context.answer_history[-max_rag_history:]
                session.rag_context.confidence_scores = session.rag_context.confidence_scores[-max_rag_history:]
            
            # Update session context
            session.current_context_type = ContextType.RAG
            session.current_domain = domain
            
            logger.debug(f"Updated RAG context for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error updating RAG context: {e}")

    def should_switch_context(self, session_id: str, new_context_type: ContextType,
                             new_domain: str, confidence: float) -> bool:
        """
        Determine if context should be switched
        
        Args:
            session_id: Session identifier
            new_context_type: Proposed new context type
            new_domain: Proposed new domain
            confidence: Confidence in new context
            
        Returns:
            True if context should be switched
        """
        try:
            session = self.get_or_create_session(session_id)
            
            # Always switch from IDLE
            if session.current_context_type == ContextType.IDLE:
                return True
            
            # High confidence switches
            if confidence >= self.context_switch_threshold:
                return True
            
            # Domain change with reasonable confidence
            if (new_domain != session.current_domain and 
                confidence >= self.domain_confidence_threshold):
                return True
            
            # Context type change with good confidence
            if (new_context_type != session.current_context_type and
                confidence >= 0.6):
                return True
            
            # Time-based switching (if user inactive in current context)
            current_time = time.time()
            if session.current_context_type == ContextType.FLOW and session.flow_context:
                time_since_flow_activity = current_time - session.flow_context.last_activity
                if time_since_flow_activity > 300:  # 5 minutes
                    return True
            
            if session.current_context_type == ContextType.RAG and session.rag_context:
                time_since_rag_activity = current_time - session.rag_context.last_query_time
                if time_since_rag_activity > 600:  # 10 minutes
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking context switch: {e}")
            return False

    def get_conversation_context(self, session_id: str, 
                               context_window: int = 5) -> Dict[str, Any]:
        """
        Get conversation context for LLM/processing
        
        Args:
            session_id: Session identifier
            context_window: Number of recent messages to include
            
        Returns:
            Context dictionary
        """
        try:
            session = self.get_or_create_session(session_id)
            
            # Get recent messages
            recent_messages = session.message_history[-context_window:] if session.message_history else []
            
            context = {
                "session_id": session_id,
                "current_context_type": session.current_context_type.value,
                "current_domain": session.current_domain,
                "total_interactions": session.total_interactions,
                "session_duration": time.time() - session.created_at,
                "recent_messages": [
                    {
                        "user_input": msg.user_input,
                        "response": msg.response[:100] + "..." if len(msg.response) > 100 else msg.response,
                        "intent": msg.intent.value,
                        "confidence": msg.confidence,
                        "timestamp": msg.timestamp
                    }
                    for msg in recent_messages
                ],
                "flow_context": None,
                "rag_context": None
            }
            
            # Add flow context if available
            if session.flow_context:
                context["flow_context"] = {
                    "domain": session.flow_context.domain,
                    "current_question_id": session.flow_context.current_question_id,
                    "current_flow_id": session.flow_context.current_flow_id,
                    "current_step": session.flow_context.current_step,
                    "progress": f"{session.flow_context.completed_steps}/{session.flow_context.total_steps}",
                    "step_history_count": len(session.flow_context.step_history)
                }
            
            # Add RAG context if available
            if session.rag_context:
                context["rag_context"] = {
                    "domain": session.rag_context.domain,
                    "recent_queries": session.rag_context.query_history[-3:],
                    "topics_discussed": session.rag_context.topics_discussed[-5:],
                    "avg_confidence": sum(session.rag_context.confidence_scores[-5:]) / len(session.rag_context.confidence_scores[-5:]) if session.rag_context.confidence_scores else 0,
                    "query_count": len(session.rag_context.query_history)
                }
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return {"session_id": session_id, "error": str(e)}

    def clear_session_context(self, session_id: str, 
                             context_type: Optional[ContextType] = None) -> bool:
        """
        Clear session context (full or specific type)
        
        Args:
            session_id: Session identifier
            context_type: Specific context type to clear (None = clear all)
            
        Returns:
            True if successful
        """
        try:
            if session_id not in self.user_sessions:
                return False
            
            session = self.user_sessions[session_id]
            
            if context_type is None:
                # Clear all context
                session.flow_context = None
                session.rag_context = None
                session.current_context_type = ContextType.IDLE
                session.current_domain = "general"
                logger.info(f"Cleared all context for session {session_id}")
            
            elif context_type == ContextType.FLOW:
                session.flow_context = None
                if session.current_context_type == ContextType.FLOW:
                    session.current_context_type = ContextType.IDLE
                logger.info(f"Cleared flow context for session {session_id}")
            
            elif context_type == ContextType.RAG:
                session.rag_context = None
                if session.current_context_type == ContextType.RAG:
                    session.current_context_type = ContextType.IDLE
                logger.info(f"Cleared RAG context for session {session_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing session context: {e}")
            return False

    def get_user_preferences(self, session_id: str) -> Dict[str, Any]:
        """
        Get user preferences based on usage patterns
        
        Args:
            session_id: Session identifier
            
        Returns:
            User preferences dictionary
        """
        try:
            session = self.get_or_create_session(session_id)
            
            # Analyze preferences
            preferred_domain = max(session.preferred_domains, key=session.preferred_domains.get) if session.preferred_domains else "general"
            
            # Analyze interaction patterns
            context_usage = defaultdict(int)
            for msg in session.message_history[-20:]:  # Last 20 messages
                context_usage[msg.context_type.value] += 1
            
            preferred_context = max(context_usage, key=context_usage.get) if context_usage else "idle"
            
            # Calculate average confidence
            recent_confidences = [msg.confidence for msg in session.message_history[-10:]]
            avg_confidence = sum(recent_confidences) / len(recent_confidences) if recent_confidences else 0
            
            preferences = {
                "preferred_domain": preferred_domain,
                "preferred_context": preferred_context,
                "avg_confidence": avg_confidence,
                "total_interactions": session.total_interactions,
                "session_duration": time.time() - session.created_at,
                "domain_distribution": dict(session.preferred_domains),
                "context_distribution": dict(context_usage),
                "user_type": self._classify_user_type(session)
            }
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return {}

    def _classify_user_type(self, session: UserSession) -> str:
        """Classify user type based on behavior patterns"""
        
        if session.total_interactions < 3:
            return "new_user"
        
        context_usage = defaultdict(int)
        for msg in session.message_history:
            context_usage[msg.context_type.value] += 1
        
        flow_ratio = context_usage["flow"] / session.total_interactions
        rag_ratio = context_usage["rag"] / session.total_interactions
        
        if flow_ratio > 0.7:
            return "flow_focused"
        elif rag_ratio > 0.7:
            return "information_seeker"
        elif abs(flow_ratio - rag_ratio) < 0.2:
            return "balanced_user"
        else:
            return "explorer"

    def get_session_analytics(self, session_id: str) -> Dict[str, Any]:
        """Get detailed session analytics"""
        
        try:
            session = self.get_or_create_session(session_id)
            
            analytics = {
                "session_info": {
                    "session_id": session_id,
                    "created_at": datetime.fromtimestamp(session.created_at).isoformat(),
                    "duration_minutes": (time.time() - session.created_at) / 60,
                    "total_interactions": session.total_interactions,
                    "current_context": session.current_context_type.value,
                    "current_domain": session.current_domain
                },
                "interaction_patterns": {},
                "flow_analytics": {},
                "rag_analytics": {},
                "recommendations": []
            }
            
            # Interaction patterns
            if session.message_history:
                confidences = [msg.confidence for msg in session.message_history]
                analytics["interaction_patterns"] = {
                    "avg_confidence": sum(confidences) / len(confidences),
                    "min_confidence": min(confidences),
                    "max_confidence": max(confidences),
                    "domain_switches": self._count_domain_switches(session),
                    "context_switches": self._count_context_switches(session)
                }
            
            # Flow analytics
            if session.flow_context:
                analytics["flow_analytics"] = {
                    "current_flow": session.flow_context.current_flow_id,
                    "current_step": session.flow_context.current_step,
                    "progress_percentage": (session.flow_context.completed_steps / session.flow_context.total_steps * 100) if session.flow_context.total_steps > 0 else 0,
                    "steps_history_count": len(session.flow_context.step_history),
                    "time_in_flow": time.time() - session.flow_context.started_at
                }
            
            # RAG analytics
            if session.rag_context:
                analytics["rag_analytics"] = {
                    "total_queries": len(session.rag_context.query_history),
                    "unique_topics": len(session.rag_context.topics_discussed),
                    "avg_confidence": sum(session.rag_context.confidence_scores) / len(session.rag_context.confidence_scores) if session.rag_context.confidence_scores else 0,
                    "recent_topics": session.rag_context.topics_discussed[-5:]
                }
            
            # Generate recommendations
            analytics["recommendations"] = self._generate_recommendations(session)
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting session analytics: {e}")
            return {"error": str(e)}

    def _count_domain_switches(self, session: UserSession) -> int:
        """Count number of domain switches in session"""
        
        if len(session.message_history) < 2:
            return 0
        
        switches = 0
        prev_domain = session.message_history[0].domain
        
        for msg in session.message_history[1:]:
            if msg.domain != prev_domain:
                switches += 1
                prev_domain = msg.domain
        
        return switches

    def _count_context_switches(self, session: UserSession) -> int:
        """Count number of context type switches in session"""
        
        if len(session.message_history) < 2:
            return 0
        
        switches = 0
        prev_context = session.message_history[0].context_type
        
        for msg in session.message_history[1:]:
            if msg.context_type != prev_context:
                switches += 1
                prev_context = msg.context_type
        
        return switches

    def _generate_recommendations(self, session: UserSession) -> List[str]:
        """Generate recommendations for user"""
        
        recommendations = []
        
        # Flow completion recommendations
        if session.flow_context and session.flow_context.current_flow_id:
            if session.flow_context.completed_steps < session.flow_context.total_steps:
                recommendations.append("Hoàn thành các bước còn lại trong hướng dẫn hiện tại")
        
        # Low confidence recommendations
        if session.message_history:
            recent_confidences = [msg.confidence for msg in session.message_history[-5:]]
            avg_recent_confidence = sum(recent_confidences) / len(recent_confidences)
            
            if avg_recent_confidence < 0.6:
                recommendations.append("Thử đặt câu hỏi với từ khóa rõ ràng hơn")
                recommendations.append("Sử dụng chức năng hướng dẫn từng bước")
        
        # Domain suggestions
        domain_counts = session.preferred_domains
        if len(domain_counts) == 1:
            other_domains = ["xuatnhapcanh", "cancuoc"]
            current_domain = session.current_domain
            other_domains = [d for d in other_domains if d != current_domain]
            if other_domains:
                recommendations.append(f"Khám phá thêm về {other_domains[0]}")
        
        return recommendations[:3]  # Return top 3 recommendations

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        
        current_time = time.time()
        expired_sessions = []
        
        for session_id, session in self.user_sessions.items():
            if current_time - session.last_activity > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.user_sessions[session_id]
        
        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        return len(expired_sessions)

    def get_global_statistics(self) -> Dict[str, Any]:
        """Get global system statistics"""
        
        current_time = time.time()
        active_sessions = sum(1 for session in self.user_sessions.values() 
                            if current_time - session.last_activity < 1800)  # 30 minutes
        
        self.global_stats["active_sessions"] = active_sessions
        
        return dict(self.global_stats)

# Test cases
if __name__ == "__main__":
    context_mgr = ContextManager()
    
    # Test session creation
    session_id = "test_user_123"
    session = context_mgr.get_or_create_session(session_id)
    print(f"✅ Created session: {session.session_id}")
    
    # Test message context
    context_mgr.add_message_context(
        session_id=session_id,
        user_input="Hướng dẫn làm hộ chiếu",
        response="Tôi sẽ hướng dẫn bạn làm hộ chiếu...",
        intent=UserIntent.FLOW_GUIDANCE,
        context_type=ContextType.FLOW,
        domain="xuatnhapcanh",
        confidence=0.9
    )
    
    # Test flow context
    context_mgr.update_flow_context(
        session_id=session_id,
        domain="xuatnhapcanh",
        flow_id="cap_moi_tu_14",
        step="1",
        completed_steps=0,
        total_steps=9
    )
    
    # Test RAG context
    context_mgr.update_rag_context(
        session_id=session_id,
        domain="xuatnhapcanh",
        query="Phí làm hộ chiếu bao nhiêu?",
        answer="Phí làm hộ chiếu là 200,000 VNĐ",
        confidence=0.95
    )
    
    # Get conversation context
    conv_context = context_mgr.get_conversation_context(session_id)
    print(f"✅ Conversation context: {len(conv_context)} fields")
    
    # Get analytics
    analytics = context_mgr.get_session_analytics(session_id)
    print(f"✅ Session analytics: {analytics['session_info']['total_interactions']} interactions")
    
    # Get preferences
    preferences = context_mgr.get_user_preferences(session_id)
    print(f"✅ User preferences: {preferences['user_type']}")