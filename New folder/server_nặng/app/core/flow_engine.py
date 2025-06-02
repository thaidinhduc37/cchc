"""
📋 Flow Engine - Hướng dẫn từng bước thông qua flow.json
Quản lý navigation, state và formatting cho flow guidance
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class FlowStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    ERROR = "error"

class ResponseType(Enum):
    QUESTION = "question"
    STEP = "step"
    COMPLETION = "completion"
    ERROR = "error"

@dataclass
class FlowStep:
    """Đại diện cho một bước trong flow"""
    name: str
    description: str
    tts: str
    link: Optional[str] = None
    image: Optional[str] = None
    type: str = "say"
    wait_for_user: bool = True

@dataclass
class FlowQuestion:
    """Đại diện cho một câu hỏi trong flow"""
    id: str
    question: str
    options: List[Dict[str, str]]

@dataclass
class FlowDefinition:
    """Đại diện cho một flow definition"""
    name: str
    description: str
    steps: Dict[str, FlowStep]

@dataclass
class FlowResponse:
    """Response từ Flow Engine"""
    type: ResponseType
    content: Dict[str, Any]
    status: FlowStatus
    next_actions: List[str]
    metadata: Dict[str, Any]

@dataclass
class FlowState:
    """Trạng thái hiện tại của user trong flow"""
    session_id: str
    domain: str
    current_question_id: Optional[str] = None
    current_flow_id: Optional[str] = None
    current_step: Optional[str] = None
    step_history: List[str] = None
    status: FlowStatus = FlowStatus.ACTIVE
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.step_history is None:
            self.step_history = []
        if self.metadata is None:
            self.metadata = {}

class FlowEngine:
    """
    Flow Engine - Core engine cho flow guidance
    Quản lý loading, navigation và formatting flows
    """
    
    def __init__(self, data_path: str = "data"):
        self.data_path = Path(data_path)
        self.flows_cache = {}  # Cache loaded flows
        self.user_states = {}  # Track user states
        
    def load_flow_config(self, domain: str) -> Dict[str, Any]:
        """
        Load flow configuration từ domain folder
        
        Args:
            domain: Domain name (xuatnhapcanh, cancuoc)
            
        Returns:
            Flow configuration dict
        """
        try:
            # Check cache first
            if domain in self.flows_cache:
                return self.flows_cache[domain]
            
            flow_file = self.data_path / domain / "flow.json"
            
            if not flow_file.exists():
                raise FileNotFoundError(f"Flow file not found: {flow_file}")
            
            with open(flow_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validate config structure
            self._validate_flow_config(config)
            
            # Cache the config
            self.flows_cache[domain] = config
            
            logger.info(f"Loaded flow config for domain: {domain}")
            return config
            
        except Exception as e:
            logger.error(f"Error loading flow config for {domain}: {e}")
            raise

    def start_flow(self, session_id: str, domain: str) -> FlowResponse:
        """
        Bắt đầu flow cho user
        
        Args:
            session_id: User session ID
            domain: Domain to start flow
            
        Returns:
            FlowResponse với first question
        """
        try:
            # Load flow config
            config = self.load_flow_config(domain)
            
            # Initialize user state
            state = FlowState(
                session_id=session_id,
                domain=domain,
                current_question_id="start",  # Always start with 'start' question
                status=FlowStatus.ACTIVE
            )
            
            self.user_states[session_id] = state
            
            # Get first question
            questions = config.get("questions", [])
            start_question = next((q for q in questions if q["id"] == "start"), None)
            
            if not start_question:
                raise ValueError("No 'start' question found in flow config")
            
            # Format response
            response = FlowResponse(
                type=ResponseType.QUESTION,
                content={
                    "question": start_question["question"],
                    "options": start_question["options"],
                    "question_id": start_question["id"]
                },
                status=FlowStatus.ACTIVE,
                next_actions=["choose_option"],
                metadata={
                    "domain": domain,
                    "total_questions": len(questions),
                    "total_flows": len(config.get("flows", {}))
                }
            )
            
            logger.info(f"Started flow for session {session_id}, domain: {domain}")
            return response
            
        except Exception as e:
            logger.error(f"Error starting flow: {e}")
            return self._create_error_response(str(e))

    def navigate_flow(self, session_id: str, user_choice: str) -> FlowResponse:
        """
        Navigate flow based on user choice
        
        Args:
            session_id: User session ID
            user_choice: User's choice/option label
            
        Returns:
            FlowResponse với next step hoặc question
        """
        try:
            # Get user state
            state = self.user_states.get(session_id)
            if not state:
                return self._create_error_response("Session not found. Please start a new flow.")
            
            # Load flow config
            config = self.load_flow_config(state.domain)
            
            # Handle navigation based on current state
            if state.current_question_id:
                return self._handle_question_navigation(state, config, user_choice)
            elif state.current_flow_id:
                return self._handle_flow_navigation(state, config, user_choice)
            else:
                return self._create_error_response("Invalid flow state")
                
        except Exception as e:
            logger.error(f"Error navigating flow: {e}")
            return self._create_error_response(str(e))

    def _handle_question_navigation(self, state: FlowState, config: Dict, user_choice: str) -> FlowResponse:
        """Handle navigation từ question"""
        
        # Find current question
        questions = config.get("questions", [])
        current_q = next((q for q in questions if q["id"] == state.current_question_id), None)
        
        if not current_q:
            return self._create_error_response("Current question not found")
        
        # Find matching option
        selected_option = None
        for option in current_q["options"]:
            if option["label"] == user_choice:
                selected_option = option
                break
        
        if not selected_option:
            # Try fuzzy matching
            from fuzzywuzzy import fuzz
            best_match = max(current_q["options"], 
                           key=lambda opt: fuzz.ratio(opt["label"].lower(), user_choice.lower()))
            if fuzz.ratio(best_match["label"].lower(), user_choice.lower()) > 70:
                selected_option = best_match
        
        if not selected_option:
            return FlowResponse(
                type=ResponseType.ERROR,
                content={
                    "error": "Lựa chọn không hợp lệ",
                    "available_options": [opt["label"] for opt in current_q["options"]]
                },
                status=state.status,
                next_actions=["choose_option"],
                metadata={}
            )
        
        # Update history
        state.step_history.append(f"Q:{state.current_question_id}:{user_choice}")
        
        # Navigate based on option
        if "next" in selected_option:
            # Navigate to next question
            state.current_question_id = selected_option["next"]
            next_q = next((q for q in questions if q["id"] == selected_option["next"]), None)
            
            if next_q:
                return FlowResponse(
                    type=ResponseType.QUESTION,
                    content={
                        "question": next_q["question"],
                        "options": next_q["options"],
                        "question_id": next_q["id"]
                    },
                    status=FlowStatus.ACTIVE,
                    next_actions=["choose_option"],
                    metadata={"step_count": len(state.step_history)}
                )
                
        elif "flow" in selected_option:
            # Navigate to flow
            state.current_question_id = None
            state.current_flow_id = selected_option["flow"]
            state.current_step = "1"
            
            return self._get_flow_step_response(state, config)
        
        return self._create_error_response("Invalid navigation option")

    def _handle_flow_navigation(self, state: FlowState, config: Dict, user_action: str) -> FlowResponse:
        """Handle navigation trong flow steps"""
        
        # Handle flow commands
        if user_action.lower() in ["tiếp theo", "next", "tiếp tục"]:
            return self._go_next_step(state, config)
        elif user_action.lower() in ["quay lại", "back", "trước"]:
            return self._go_previous_step(state, config)
        elif user_action.lower() in ["restart", "bắt đầu lại"]:
            return self._restart_flow(state, config)
        elif user_action.lower() in ["hoàn thành", "done", "xong"]:
            return self._complete_flow(state)
        else:
            # Default to next step
            return self._go_next_step(state, config)

    def _go_next_step(self, state: FlowState, config: Dict) -> FlowResponse:
        """Go to next step in flow"""
        
        flows = config.get("flows", {})
        current_flow = flows.get(state.current_flow_id)
        
        if not current_flow:
            return self._create_error_response("Flow not found")
        
        steps = current_flow.get("steps", {})
        current_step_num = int(state.current_step)
        next_step_num = current_step_num + 1
        
        if str(next_step_num) in steps:
            state.current_step = str(next_step_num)
            state.step_history.append(f"F:{state.current_flow_id}:{next_step_num}")
            return self._get_flow_step_response(state, config)
        else:
            # Flow completed
            return self._complete_flow(state)

    def _go_previous_step(self, state: FlowState, config: Dict) -> FlowResponse:
        """Go to previous step in flow"""
        
        current_step_num = int(state.current_step)
        if current_step_num > 1:
            state.current_step = str(current_step_num - 1)
            return self._get_flow_step_response(state, config)
        else:
            return FlowResponse(
                type=ResponseType.ERROR,
                content={"error": "Đã ở bước đầu tiên"},
                status=state.status,
                next_actions=["next", "restart"],
                metadata={}
            )

    def _get_flow_step_response(self, state: FlowState, config: Dict) -> FlowResponse:
        """Get response for current flow step"""
        
        flows = config.get("flows", {})
        current_flow = flows.get(state.current_flow_id)
        steps = current_flow.get("steps", {})
        step = steps.get(state.current_step)
        
        if not step:
            return self._create_error_response("Step not found")
        
        # Resolve image path
        image_path = None
        if step.get("image"):
            image_path = self._resolve_asset_path(state.domain, step["image"])
        
        response_content = {
            "step_number": state.current_step,
            "total_steps": len(steps),
            "name": step["name"],
            "description": step["description"],
            "tts": step.get("tts", step["description"]),
            "link": step.get("link"),
            "image": image_path,
            "flow_name": current_flow["name"],
            "wait_for_user": step.get("wait_for_user", True)
        }
        
        # Determine next actions
        next_actions = ["next"]
        if int(state.current_step) > 1:
            next_actions.append("back")
        next_actions.extend(["restart", "complete"])
        
        return FlowResponse(
            type=ResponseType.STEP,
            content=response_content,
            status=FlowStatus.ACTIVE,
            next_actions=next_actions,
            metadata={
                "progress": f"{state.current_step}/{len(steps)}",
                "domain": state.domain
            }
        )

    def _complete_flow(self, state: FlowState) -> FlowResponse:
        """Complete current flow"""
        
        state.status = FlowStatus.COMPLETED
        
        return FlowResponse(
            type=ResponseType.COMPLETION,
            content={
                "message": "🎉 Bạn đã hoàn thành hướng dẫn thành công!",
                "summary": f"Đã hoàn thành flow: {state.current_flow_id}",
                "steps_completed": len(state.step_history)
            },
            status=FlowStatus.COMPLETED,
            next_actions=["start_new_flow", "ask_question"],
            metadata={"completion_time": "now"}
        )

    def _restart_flow(self, state: FlowState, config: Dict) -> FlowResponse:
        """Restart current flow"""
        
        state.current_step = "1"
        state.step_history = []
        state.status = FlowStatus.ACTIVE
        
        return self._get_flow_step_response(state, config)

    def get_user_state(self, session_id: str) -> Optional[FlowState]:
        """Get current user state"""
        return self.user_states.get(session_id)

    def reset_user_state(self, session_id: str) -> bool:
        """Reset user state"""
        if session_id in self.user_states:
            del self.user_states[session_id]
            return True
        return False

    def _validate_flow_config(self, config: Dict) -> None:
        """Validate flow configuration structure"""
        
        required_keys = ["questions", "flows"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required key: {key}")
        
        # Validate questions
        questions = config["questions"]
        if not isinstance(questions, list):
            raise ValueError("Questions must be a list")
        
        # Validate flows
        flows = config["flows"]
        if not isinstance(flows, dict):
            raise ValueError("Flows must be a dict")

    def _resolve_asset_path(self, domain: str, relative_path: str) -> str:
        """Resolve asset path to full path"""
        
        if relative_path.startswith("dataset/"):
            # Old format - convert to new format
            relative_path = relative_path.replace("dataset/", "data/")
        
        # Return relative path that frontend can use
        return f"/assets/{domain}/{relative_path.split('/')[-1]}"

    def _create_error_response(self, error_msg: str) -> FlowResponse:
        """Create error response"""
        
        return FlowResponse(
            type=ResponseType.ERROR,
            content={"error": error_msg},
            status=FlowStatus.ERROR,
            next_actions=["restart", "start_new_flow"],
            metadata={}
        )

    def get_available_flows(self, domain: str) -> List[Dict[str, str]]:
        """Get list of available flows for domain"""
        
        try:
            config = self.load_flow_config(domain)
            flows = config.get("flows", {})
            
            available_flows = []
            for flow_id, flow_data in flows.items():
                available_flows.append({
                    "id": flow_id,
                    "name": flow_data.get("name", flow_id),
                    "description": flow_data.get("description", ""),
                    "steps_count": len(flow_data.get("steps", {}))
                })
            
            return available_flows
            
        except Exception as e:
            logger.error(f"Error getting available flows for {domain}: {e}")
            return []

    def get_flow_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get flow statistics for user session"""
        
        state = self.user_states.get(session_id)
        if not state:
            return {}
        
        try:
            config = self.load_flow_config(state.domain)
            flows = config.get("flows", {})
            current_flow = flows.get(state.current_flow_id)
            
            stats = {
                "session_id": session_id,
                "domain": state.domain,
                "status": state.status.value,
                "total_steps_in_flow": len(current_flow.get("steps", {})) if current_flow else 0,
                "current_step": state.current_step,
                "steps_completed": len([h for h in state.step_history if h.startswith("F:")]),
                "total_interactions": len(state.step_history)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting flow statistics: {e}")
            return {}

# Test và example usage
if __name__ == "__main__":
    # Test FlowEngine
    engine = FlowEngine("data")
    
    # Test load config
    try:
        config = engine.load_flow_config("xuatnhapcanh")
        print("✅ Loaded flow config successfully")
        print(f"Questions: {len(config.get('questions', []))}")
        print(f"Flows: {len(config.get('flows', {}))}")
    except Exception as e:
        print(f"❌ Error loading config: {e}")
    
    # Test start flow
    session_id = "test_session_123"
    response = engine.start_flow(session_id, "xuatnhapcanh")
    print(f"\n✅ Started flow: {response.type.value}")
    print(f"Content: {response.content.get('question', '')[:50]}...")
    
    # Test navigation
    if response.content.get("options"):
        first_option = response.content["options"][0]["label"]
        nav_response = engine.navigate_flow(session_id, first_option)
        print(f"\n✅ Navigation result: {nav_response.type.value}")
        
        # Get statistics
        stats = engine.get_flow_statistics(session_id)
        print(f"\n📊 Flow Statistics: {stats}")
    
    # Test available flows
    available = engine.get_available_flows("xuatnhapcanh")
    print(f"\n📋 Available flows: {len(available)}")
    for flow in available:
        print(f"  - {flow['name']}: {flow['steps_count']} steps")