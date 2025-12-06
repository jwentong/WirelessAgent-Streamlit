"""
Workflow Module

Defines the LangGraph workflow nodes and builds the state graph
for the network slicing decision process.
"""

import re
import logging
from typing import Dict, List, Any, Optional

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .config import SYSTEM_PROMPT, INTENT_PROMPT_TEMPLATE, SLICE_PROMPT_TEMPLATE
from .network_state import NetworkState, get_state_manager
from .knowledge_base import get_application_slice_type
from .cqi_utils import generate_random_cqi
from .report_generator import generate_concise_report, generate_user_allocation_table
from .tools import (
    network_monitor, knowledge_base_query, check_and_adjust_capacity,
    workload_balance_tool, beamforming_tool, slice_allocation, get_llm
)

logger = logging.getLogger(__name__)


def build_messages(history: List[Dict[str, Any]]) -> List:
    """
    Build LangChain message list from history.
    
    Args:
        history: List of message dictionaries with 'role' and 'content'
    
    Returns:
        List of LangChain message objects
    """
    messages = []
    for msg in history:
        if msg["role"] == "system":
            messages.append(SystemMessage(content=msg["content"]))
        elif msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    return messages


# ====================== Workflow Nodes ======================

def initialize(state: NetworkState) -> NetworkState:
    """Initialize state - Step 1: Receive user request and CQI"""
    state["history"] = []
    state["memory"] = {}
    state["step_count"] = 0
    state["current_step"] = "understand_intent"
    
    # Add system message
    state["history"].append({"role": "system", "content": SYSTEM_PROMPT})
    
    # Add user request
    user_request = f"""
New User ID: {state["user_id"]}
Location: {state["location"]}
Request: "{state["request"]}"
Channel Quality Indicator (CQI): {state["cqi"]}

Please analyze this request to understand the user's intent and network requirements.
"""
    state["history"].append({"role": "user", "content": user_request})
    
    # Get current network state
    network_state = network_monitor.invoke({})
    state["memory"]["network_state"] = network_state
    
    return state


def understand_intent(state: NetworkState) -> NetworkState:
    """Step 1: Understand user intent by analyzing request"""
    state["step_count"] += 1
    
    user_request = state["request"]
    
    # Use knowledge base to determine slice type
    kb_recommended_slice, kb_reasons = get_application_slice_type(user_request)
    state["memory"]["kb_recommended_slice"] = kb_recommended_slice
    state["memory"]["kb_slice_reasons"] = kb_reasons
    
    logger.info(f"Knowledge Base recommended slice: {kb_recommended_slice}")
    print(f"Knowledge Base recommended slice: {kb_recommended_slice} ({kb_reasons[0]})")
    
    # Query knowledge base
    kb_content = knowledge_base_query.invoke({"query": user_request})
    state["memory"]["knowledge_base"] = kb_content
    
    # LLM intent analysis
    intent_prompt = INTENT_PROMPT_TEMPLATE.format(request=state["request"])
    state["history"].append({"role": "user", "content": intent_prompt})
    
    messages = build_messages(state["history"])
    llm = get_llm()
    response = llm.invoke(messages)
    
    state["history"].append({"role": "assistant", "content": response.content})
    state["current_step"] = "allocate_slice_type"
    
    return state


def allocate_slice_type(state: NetworkState) -> NetworkState:
    """Step 2: Allocate appropriate slice type based on intent"""
    state["step_count"] += 1
    
    kb_recommended_slice = state["memory"]["kb_recommended_slice"]
    
    # Get LLM recommendation
    state["history"].append({"role": "user", "content": SLICE_PROMPT_TEMPLATE})
    
    messages = build_messages(state["history"])
    llm = get_llm()
    response = llm.invoke(messages)
    decision = response.content
    
    state["history"].append({"role": "assistant", "content": decision})
    
    # Extract slice type from LLM response
    slice_match = re.search(r"I recommend using (eMBB|URLLC) slice", decision)
    
    if slice_match:
        llm_recommended_slice = slice_match.group(1)
        state["memory"]["llm_recommended_slice"] = llm_recommended_slice
        
        # Compare with knowledge base recommendation
        if llm_recommended_slice != kb_recommended_slice:
            logger.info(f"LLM recommended {llm_recommended_slice}, KB recommended {kb_recommended_slice}")
            print(f"Using knowledge base recommendation: {kb_recommended_slice}")
            state["memory"]["final_slice"] = kb_recommended_slice
            state["memory"]["intent_override_applied"] = True
        else:
            state["memory"]["final_slice"] = llm_recommended_slice
            state["memory"]["intent_override_applied"] = False
    else:
        state["memory"]["final_slice"] = kb_recommended_slice
        state["memory"]["intent_override_applied"] = True
        logger.warning("LLM didn't provide explicit recommendation. Using KB recommendation.")
    
    # Check workload balance
    final_slice = state["memory"]["final_slice"]
    estimated_bandwidth = 10 if final_slice == "eMBB" else 3
    
    balance_result = workload_balance_tool.invoke({
        "target_slice_type": final_slice,
        "cqi": state["cqi"],
        "required_bandwidth": estimated_bandwidth
    })
    
    state["memory"]["balance_result"] = balance_result
    
    if balance_result["should_rebalance"]:
        state["memory"]["final_slice"] = balance_result["recommended_slice"]
        state["memory"]["balance_applied"] = True
        logger.info(f"Workload balancing applied: {balance_result['reason']}")
    else:
        state["memory"]["balance_applied"] = False
    
    state["current_step"] = "allocate_resources"
    
    return state


def allocate_resources(state: NetworkState) -> NetworkState:
    """Step 3: Allocate bandwidth and calculate transmission rate"""
    state["step_count"] += 1
    
    final_slice = state["memory"]["final_slice"]
    cqi = state["cqi"]
    
    # Execute beamforming
    beamforming_result = beamforming_tool.invoke({
        "user_id": state["user_id"],
        "slice_type": final_slice,
        "cqi": cqi,
        "request": state["request"]
    })
    
    state["memory"]["beamforming_result"] = beamforming_result
    
    # Check workload balance again if not applied
    if not state["memory"].get("balance_applied", False):
        balance_result = workload_balance_tool.invoke({
            "target_slice_type": final_slice,
            "cqi": cqi,
            "required_bandwidth": beamforming_result["allocated_bandwidth"]
        })
        
        state["memory"]["balance_result"] = balance_result
        
        if balance_result["should_rebalance"]:
            state["memory"]["original_slice"] = final_slice
            final_slice = balance_result["recommended_slice"]
            state["memory"]["final_slice"] = final_slice
            state["memory"]["balance_applied"] = True
            
            # Re-run beamforming with new slice type
            beamforming_result = beamforming_tool.invoke({
                "user_id": state["user_id"],
                "slice_type": final_slice,
                "cqi": cqi,
                "request": state["request"]
            })
            state["memory"]["beamforming_result"] = beamforming_result
    
    # Check capacity
    has_capacity = beamforming_result["has_capacity"]
    required_bandwidth = beamforming_result["allocated_bandwidth"]
    
    if not has_capacity:
        adjustment_result = check_and_adjust_capacity.invoke({
            "slice_type": final_slice,
            "required_bandwidth": required_bandwidth
        })
        state["memory"]["adjustment_result"] = adjustment_result
        
        if not adjustment_result["has_capacity"]:
            state["memory"]["allocation_failed"] = True
    else:
        state["memory"]["adjustment_result"] = {
            "has_capacity": True,
            "adjustments_made": False,
            "user_adjustments": [],
            "freed_bandwidth": 0
        }
    
    state["current_step"] = "evaluate_network"
    
    return state


def evaluate_network(state: NetworkState) -> NetworkState:
    """Step 4: Evaluate network state and complete allocation"""
    state["step_count"] += 1
    
    state_manager = get_state_manager()
    
    # Check if allocation failed
    if state["memory"].get("allocation_failed", False):
        print(f"\n{'-'*40}")
        print(f"ALLOCATION FAILED FOR USER {state['user_id']}")
        print(f"{'-'*40}")
        print(f"Request: {state['request']}")
        print(f"Slice type: {state['memory']['final_slice']}")
        print("Reason: Insufficient capacity")
        
        state["final_result"] = "Allocation failed due to insufficient capacity"
        return state
    
    # Execute resource allocation
    beamforming_result = state["memory"]["beamforming_result"]
    final_slice = state["memory"]["final_slice"]
    adjustment_result = state["memory"]["adjustment_result"]
    
    allocation_result = slice_allocation.invoke({
        "user_id": state["user_id"],
        "slice_type": final_slice,
        "rate": beamforming_result["allocated_rate"],
        "latency": beamforming_result["allocated_latency"],
        "cqi": state["cqi"],
        "bandwidth": beamforming_result["allocated_bandwidth"]
    })
    
    state["memory"]["allocation_result"] = allocation_result
    
    # Get updated network state
    updated_network_state = network_monitor.invoke({})
    state["memory"]["updated_network_state"] = updated_network_state
    
    # Get adjusted user IDs
    adjusted_user_ids = []
    if adjustment_result["adjustments_made"]:
        adjusted_user_ids = [adj["user_id"] for adj in adjustment_result["user_adjustments"]]
    
    # Print results
    print(f"\n{'-'*40}")
    print(f"ALLOCATION RESULT FOR USER {state['user_id']}")
    print(f"{'-'*40}")
    
    current_state = state_manager.get_state()
    concise_report = generate_concise_report(current_state, state["user_id"], adjustment_result, state_manager)
    print(concise_report)
    
    user_table = generate_user_allocation_table(current_state, state["user_id"], adjusted_user_ids)
    print(user_table)
    
    state["final_result"] = "Allocation successful"
    
    return state


def route_next(state: NetworkState) -> str:
    """Route to next node based on current step"""
    if state["step_count"] >= 10:
        return END
    
    step_map = {
        "understand_intent": "understand_intent",
        "allocate_slice_type": "allocate_slice_type",
        "allocate_resources": "allocate_resources",
        "evaluate_network": "evaluate_network"
    }
    
    return step_map.get(state["current_step"], END)


# ====================== Build Workflow ======================

def create_network_graph():
    """Create network slice management workflow graph"""
    graph = StateGraph(NetworkState)
    
    # Add nodes
    graph.add_node("initialize", initialize)
    graph.add_node("understand_intent", understand_intent)
    graph.add_node("allocate_slice_type", allocate_slice_type)
    graph.add_node("allocate_resources", allocate_resources)
    graph.add_node("evaluate_network", evaluate_network)
    
    # Set entry point
    graph.set_entry_point("initialize")
    
    # Add edges (simplified linear flow)
    graph.add_edge("initialize", "understand_intent")
    graph.add_edge("understand_intent", "allocate_slice_type")
    graph.add_edge("allocate_slice_type", "allocate_resources")
    graph.add_edge("allocate_resources", "evaluate_network")
    graph.add_edge("evaluate_network", END)
    
    return graph.compile()


def process_user_request(user_id: str, location: str, request: str,
                         cqi: Optional[int] = None, 
                         ground_truth: Optional[str] = None) -> Dict[str, Any]:
    """
    Process a user request through the workflow.
    
    Args:
        user_id: User identifier
        location: User location coordinates
        request: Text of user request
        cqi: Channel Quality Indicator (1-15), generated randomly if None
        ground_truth: Ground truth slice label for evaluation
    
    Returns:
        Dictionary with detailed results
    """
    if cqi is None:
        cqi = generate_random_cqi()
    
    workflow = create_network_graph()
    state_manager = get_state_manager()
    
    # Get initial metrics
    initial_embb_rate, initial_urllc_rate = state_manager.calculate_total_transmission_rates()
    initial_avg_util = state_manager.calculate_average_resource_utilization()
    
    initial_state = {
        "user_id": user_id,
        "location": location,
        "request": request,
        "cqi": cqi,
        "history": [],
        "memory": {},
        "step_count": 0,
        "current_step": "",
        "final_result": None
    }
    
    try:
        result = workflow.invoke(initial_state)
        
        # Get final metrics
        final_embb_rate, final_urllc_rate = state_manager.calculate_total_transmission_rates()
        final_avg_util = state_manager.calculate_average_resource_utilization()
        final_state = state_manager.get_state()
        
        detailed_result = {
            "user_id": user_id,
            "request": request,
            "cqi": cqi,
            "ground_truth": ground_truth,
            "allocation_failed": result["memory"].get("allocation_failed", False),
            "slice_type": result["memory"].get("final_slice", "Failed"),
            "embb_total_rate_before": initial_embb_rate,
            "embb_total_rate_after": final_embb_rate,
            "urllc_total_rate_before": initial_urllc_rate,
            "urllc_total_rate_after": final_urllc_rate,
            "avg_resource_util_before": initial_avg_util,
            "avg_resource_util_after": final_avg_util,
            "embb_util_after": final_state["embb_slice"]["utilization_rate"],
            "urllc_util_after": final_state["urllc_slice"]["utilization_rate"]
        }
        
        # Check intent correctness
        if ground_truth is not None and detailed_result["slice_type"] != "Failed":
            detailed_result["intent_correct"] = (detailed_result["slice_type"] == ground_truth)
        else:
            detailed_result["intent_correct"] = None
        
        # Add beamforming details
        if "beamforming_result" in result["memory"]:
            bf = result["memory"]["beamforming_result"]
            detailed_result["bandwidth"] = bf["allocated_bandwidth"]
            detailed_result["rate"] = bf["allocated_rate"]
            detailed_result["latency"] = bf["allocated_latency"]
        
        # Add adjustment info
        if "adjustment_result" in result["memory"]:
            detailed_result["adjustments_made"] = result["memory"]["adjustment_result"].get("adjustments_made", False)
        
        return detailed_result
        
    except Exception as e:
        logger.error(f"Workflow execution error: {e}")
        return {
            "user_id": user_id,
            "request": request,
            "cqi": cqi,
            "ground_truth": ground_truth,
            "slice_type": "Failed",
            "allocation_failed": True,
            "intent_correct": None,
            "error": str(e),
            "embb_total_rate_before": initial_embb_rate,
            "embb_total_rate_after": initial_embb_rate,
            "urllc_total_rate_before": initial_urllc_rate,
            "urllc_total_rate_after": initial_urllc_rate,
            "avg_resource_util_before": initial_avg_util,
            "avg_resource_util_after": initial_avg_util
        }
