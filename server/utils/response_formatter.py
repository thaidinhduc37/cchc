# server/utils/response_formatter.py - UNIFIED VERSION

from datetime import datetime

def format_response(text: str, source: str = "unknown", metadata: dict = None) -> dict:
    """
    Unified response formatter cho tất cả components
    
    Args:
        text: Nội dung trả lời
        source: Nguồn trả lời (rag, excel, flow, ollama, fallback, etc)
        metadata: Thông tin bổ sung (sources, confidence, processing_time, etc)
        
    Returns:
        dict: Standardized response format
        {
            "success": bool,
            "data": str,           # Main response content
            "reply": str,          # Backward compatibility
            "source": str,
            "type": str,
            "timestamp": str,
            "metadata": dict
        }
    """
    
    # Determine success based on content
    success = bool(text and text.strip())
    
    # Base response structure
    response = {
        "success": success,
        "data": text if success else "",
        "reply": text,  # Keep for backward compatibility
        "source": source,
        "type": "answer",
        "timestamp": datetime.now().isoformat()
    }
    
    # Initialize metadata
    if metadata is None:
        metadata = {}
    
    # Always include core metadata
    metadata.update({
        'source': source,
        'success': success,
        'response_length': len(text) if text else 0,
        'has_content': success
    })
    
    # Add source-specific metadata enhancements
    if source == 'rag':
        # RAG-specific metadata structure
        metadata.setdefault('sources_count', 0)
        metadata.setdefault('data_sources', [])
        metadata.setdefault('processing_time', 0)
        metadata.setdefault('provider_used', 'unknown')
        metadata.setdefault('strategies_tried', [])
        
    elif source == 'excel':
        # Excel-specific metadata
        metadata.setdefault('domain', 'unknown')
        metadata.setdefault('match_score', 0)
        
    elif source == 'flow':
        # Flow-specific metadata
        metadata.setdefault('flow_id', '')
        metadata.setdefault('step_index', 0)
        metadata.setdefault('wait_for_user', True)
        metadata.setdefault('flow_action', 'continue')
        
    elif source == 'fallback':
        # Fallback metadata
        metadata.setdefault('reason', 'no_match_found')
        metadata.setdefault('suggestions', [])
    
    response["metadata"] = metadata
    
    return response

def format_flow_response(step_data: dict, flow_id: str = "", message: str = "") -> dict:
    """
    Specialized formatter cho flow responses
    
    Args:
        step_data: Data từ flow engine
        flow_id: Flow ID
        message: Custom message
        
    Returns:
        dict: Formatted flow response
    """
    
    # Handle different flow response types
    if step_data.get('done', False):
        # Flow completed
        return format_response(
            text=step_data.get('message', '✅ Hoàn tất!'),
            source='flow',
            metadata={
                'flow_id': flow_id,
                'flow_status': 'completed',
                'flow_action': 'done'
            }
        )
    
    elif step_data.get('error'):
        # Flow error
        return format_response(
            text=step_data.get('error', 'Lỗi flow'),
            source='flow',
            metadata={
                'flow_id': flow_id,
                'flow_status': 'error',
                'flow_action': 'error'
            }
        )
    
    else:
        # Normal flow step
        step = step_data.get('step', {})
        step_index = step_data.get('current', '?')
        
        # Build flow message
        flow_message = message or step.get('description', 'Bước tiếp theo')
        
        # Add step info if available
        if step.get('name'):
            flow_message = f"**{step['name']}**\n\n{flow_message}"
        
        # Add jump message if present
        if step_data.get('jump_message'):
            flow_message = f"{step_data['jump_message']}\n\n{flow_message}"
        
        return format_response(
            text=flow_message,
            source='flow',
            metadata={
                'flow_id': flow_id,
                'step_index': step_index,
                'step_name': step.get('name', ''),
                'wait_for_user': step.get('wait_for_user', True),
                'flow_status': 'active',
                'flow_action': 'continue',
                'jumped': step_data.get('jumped', False)
            }
        )

def format_error_response(error_message: str, source: str = "system", error_code: str = None) -> dict:
    """
    Specialized formatter cho error responses
    
    Args:
        error_message: Error message
        source: Source component where error occurred
        error_code: Optional error code
        
    Returns:
        dict: Formatted error response
    """
    
    return {
        "success": False,
        "data": "",
        "reply": error_message,
        "source": source,
        "type": "error",
        "timestamp": datetime.now().isoformat(),
        "metadata": {
            'source': source,
            'success': False,
            'error_code': error_code,
            'error_type': 'processing_error',
            'has_content': False,
            'response_length': 0
        }
    }

def is_valid_response(response: dict) -> bool:
    """
    Validate response format
    
    Args:
        response: Response dict to validate
        
    Returns:
        bool: True if valid format
    """
    
    required_fields = ['success', 'data', 'source', 'type', 'timestamp']
    
    if not isinstance(response, dict):
        return False
    
    for field in required_fields:
        if field not in response:
            return False
    
    # Additional validation
    if not isinstance(response.get('success'), bool):
        return False
    
    if not isinstance(response.get('data'), str):
        return False
    
    return True

# Backward compatibility functions
def format_simple_response(text: str) -> dict:
    """Simple response for backward compatibility"""
    return format_response(text, source="system")

def format_rag_response(text: str, metadata: dict) -> dict:
    """RAG response for backward compatibility"""
    return format_response(text, source="rag", metadata=metadata)