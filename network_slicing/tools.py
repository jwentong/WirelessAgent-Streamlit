"""
LangChain Tools Module

Defines tools for the LangGraph workflow to interact with
the network slicing system.
"""

import re
import logging
from typing import Dict, Any, Optional, List

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .config import SliceConfig, LLMConfig
from .network_state import get_state_manager
from .cqi_utils import calculate_rate_from_cqi, validate_rate_for_slice, get_rate_requirements
from .knowledge_base import query_knowledge_base
from .capacity_manager import (
    check_slice_capacity,
    check_and_adjust_capacity as _check_and_adjust_capacity,
    check_workload_balance,
    apply_heuristic_bandwidth,
    apply_heuristic_latency
)

logger = logging.getLogger(__name__)

# Initialize LLM
_llm = None
_llm_config_hash = None


def _get_config_hash() -> str:
    """Get a hash of current LLM config for cache invalidation"""
    return f"{LLMConfig.get_model()}_{LLMConfig.get_api_key()[:8]}_{LLMConfig.get_base_url()}_{LLMConfig.get_temperature()}"


def get_llm() -> ChatOpenAI:
    """Get or create the LLM instance with current configuration"""
    global _llm, _llm_config_hash
    
    current_hash = _get_config_hash()
    
    # Recreate LLM if config changed
    if _llm is None or _llm_config_hash != current_hash:
        _llm = ChatOpenAI(
            api_key=LLMConfig.get_api_key(),
            base_url=LLMConfig.get_base_url(),
            model=LLMConfig.get_model(),
            temperature=LLMConfig.get_temperature()
        )
        _llm_config_hash = current_hash
        logger.info(f"LLM initialized with model: {LLMConfig.get_model()}")
    
    return _llm


def reset_llm():
    """Reset the LLM instance (useful when changing configuration)"""
    global _llm, _llm_config_hash
    _llm = None
    _llm_config_hash = None


@tool
def network_monitor(slice_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Get network slice status.
    
    Args:
        slice_type: Optional filter for "eMBB" or "URLLC". If None, returns all.
    
    Returns:
        Dictionary containing network state information
    """
    state_manager = get_state_manager()
    current_state = state_manager.get_state()
    
    if slice_type == "eMBB":
        return {"embb_slice": current_state["embb_slice"]}
    elif slice_type == "URLLC":
        return {"urllc_slice": current_state["urllc_slice"]}
    else:
        return current_state


@tool
def knowledge_base_query(query: str) -> str:
    """
    Query knowledge base to get relevant information.
    
    Args:
        query: Search query for the knowledge base
    
    Returns:
        Formatted search results from knowledge base
    """
    return query_knowledge_base(query)


@tool
def check_and_adjust_capacity(slice_type: str, required_bandwidth: int) -> Dict[str, Any]:
    """
    Check if slice has capacity for new user and perform dynamic adjustment if needed.
    
    Args:
        slice_type: "eMBB" or "URLLC"
        required_bandwidth: Bandwidth needed for the new user in MHz
    
    Returns:
        Dictionary with capacity status and adjustment results
    """
    return _check_and_adjust_capacity(slice_type, required_bandwidth)


@tool
def workload_balance_tool(target_slice_type: str, cqi: int, required_bandwidth: int) -> Dict[str, Any]:
    """
    Check if workload should be balanced between slices.
    
    Args:
        target_slice_type: Originally targeted slice type ("eMBB" or "URLLC")
        cqi: User's Channel Quality Indicator
        required_bandwidth: Required bandwidth for the user
    
    Returns:
        Dictionary with balancing recommendation
    """
    state_manager = get_state_manager()
    should_rebalance, recommended_slice, reason = check_workload_balance(
        target_slice_type, cqi, required_bandwidth, state_manager
    )
    
    embb_rate, urllc_rate = state_manager.get_utilization_rates()
    
    return {
        "should_rebalance": should_rebalance,
        "original_slice": target_slice_type,
        "recommended_slice": recommended_slice,
        "reason": reason,
        "current_utilization": {
            "embb": f"{embb_rate:.2%}",
            "urllc": f"{urllc_rate:.2%}"
        }
    }


@tool
def beamforming_tool(user_id: str, slice_type: str, cqi: int, request: str) -> Dict[str, Any]:
    """
    Execute beamforming algorithm using CQI and request analysis.
    
    Args:
        user_id: User identifier
        slice_type: Either "eMBB" or "URLLC"
        cqi: Channel Quality Indicator (1-15)
        request: User's request text
    
    Returns:
        Dictionary containing allocated resources
    """
    state_manager = get_state_manager()
    available_bandwidth = state_manager.get_available_bandwidth(slice_type)
    
    # Get slice parameters
    params = SliceConfig.get_slice_params(slice_type)
    min_bandwidth, max_bandwidth_limit = params["bandwidth_range"]
    min_latency, max_latency = params["latency_range"]
    
    max_bandwidth = min(max_bandwidth_limit, available_bandwidth)
    max_bandwidth = max(max_bandwidth, min_bandwidth)
    
    # Try LLM-based bandwidth recommendation
    allocated_bandwidth = _get_llm_bandwidth_recommendation(
        request, slice_type, cqi, available_bandwidth, min_bandwidth, max_bandwidth
    )
    
    # Determine latency
    allocated_latency = apply_heuristic_latency(slice_type, request)
    
    # Calculate rate
    allocated_rate = calculate_rate_from_cqi(allocated_bandwidth, cqi)
    
    # Validate and adjust rate if needed
    allocated_bandwidth, allocated_rate, adjustment_made, adjustment_reason = _validate_and_adjust_rate(
        slice_type, allocated_bandwidth, allocated_rate, cqi
    )
    
    rate_valid = validate_rate_for_slice(allocated_rate, slice_type)
    
    # Check capacity
    has_capacity, avail_bw, adjustment_needed = check_slice_capacity(
        slice_type, allocated_bandwidth, state_manager
    )
    
    return {
        "status": "success" if rate_valid else "warning",
        "user_id": user_id,
        "slice_type": slice_type,
        "cqi": cqi,
        "allocated_bandwidth": allocated_bandwidth,
        "allocated_rate": allocated_rate,
        "allocated_latency": allocated_latency,
        "rate_valid": rate_valid,
        "adjustment_made": adjustment_made,
        "adjustment_reason": adjustment_reason,
        "rate_requirements": get_rate_requirements(slice_type),
        "has_capacity": has_capacity,
        "available_bandwidth": avail_bw,
        "adjustment_needed": 0 if has_capacity else adjustment_needed
    }


@tool
def slice_allocation(user_id: str, slice_type: str, rate: float, 
                     latency: float, cqi: int, bandwidth: int) -> Dict[str, Any]:
    """
    Allocate user to slice and update network state.
    
    Args:
        user_id: User identifier
        slice_type: Either "eMBB" or "URLLC"
        rate: Data rate in Mbps
        latency: Latency in ms
        cqi: Channel Quality Indicator (1-15)
        bandwidth: Allocated bandwidth in MHz
    
    Returns:
        Dictionary with allocation result
    """
    state_manager = get_state_manager()
    
    new_user = {
        "user_id": user_id,
        "rate": rate,
        "latency": latency,
        "cqi": cqi,
        "bandwidth": bandwidth
    }
    
    state_manager.add_user(slice_type, new_user)
    current_state = state_manager.get_state()
    slice_key = "embb_slice" if slice_type == "eMBB" else "urllc_slice"
    
    return {
        "status": "success",
        "message": f"User {user_id} has been allocated to {slice_type} slice",
        "allocation": {
            "user_id": user_id,
            "slice_type": slice_type,
            "rate": rate,
            "latency": latency,
            "cqi": cqi,
            "bandwidth": bandwidth
        },
        "updated_slice": {
            "users_count": len(current_state[slice_key]["users"]),
            "resource_usage": current_state[slice_key]["resource_usage"],
            "utilization_rate": current_state[slice_key]["utilization_rate"]
        }
    }


def _get_llm_bandwidth_recommendation(request: str, slice_type: str, cqi: int,
                                       available_bandwidth: int, 
                                       min_bandwidth: int, max_bandwidth: int) -> int:
    """Get bandwidth recommendation from LLM"""
    bandwidth_prompt = f"""
Based on the following user request and network conditions, recommend an appropriate bandwidth allocation:

User Request: "{request}"
Slice Type: {slice_type}
CQI (Channel Quality Indicator): {cqi}
Available Bandwidth: {available_bandwidth} MHz

Requirements:
- Bandwidth must be between {min_bandwidth}-{max_bandwidth} MHz (integer values only)

Please respond with a single integer number representing your recommended bandwidth in MHz.
"""
    
    try:
        llm = get_llm()
        messages = [
            SystemMessage(content="You are a network resource allocation expert."),
            HumanMessage(content=bandwidth_prompt)
        ]
        response = llm.invoke(messages)
        
        bandwidth_match = re.search(r'\b(\d+)\b', response.content)
        if bandwidth_match:
            recommended_bandwidth = int(bandwidth_match.group(1))
            if min_bandwidth <= recommended_bandwidth <= max_bandwidth:
                return recommended_bandwidth
            else:
                return max(min_bandwidth, min(recommended_bandwidth, max_bandwidth))
        else:
            return apply_heuristic_bandwidth(slice_type, request)
    except Exception as e:
        logger.warning(f"LLM bandwidth recommendation failed: {e}")
        return apply_heuristic_bandwidth(slice_type, request)


def _validate_and_adjust_rate(slice_type: str, bandwidth: int, rate: float, 
                               cqi: int) -> tuple:
    """Validate rate and adjust bandwidth if needed"""
    adjustment_made = False
    adjustment_reason = ""
    
    if slice_type == "eMBB":
        if rate < SliceConfig.EMBB_RATE_MIN:
            old_bandwidth = bandwidth
            bandwidth = max(bandwidth + 2, 20)
            rate = calculate_rate_from_cqi(bandwidth, cqi)
            adjustment_made = True
            adjustment_reason = f"Rate below eMBB minimum. Increased bandwidth from {old_bandwidth} to {bandwidth} MHz."
        elif rate > SliceConfig.EMBB_RATE_MAX:
            old_bandwidth = bandwidth
            bandwidth = max(SliceConfig.EMBB_BANDWIDTH_MIN, bandwidth - 2)
            rate = calculate_rate_from_cqi(bandwidth, cqi)
            adjustment_made = True
            adjustment_reason = f"Rate above eMBB maximum. Decreased bandwidth from {old_bandwidth} to {bandwidth} MHz."
    else:  # URLLC
        if rate > SliceConfig.URLLC_RATE_MAX:
            old_bandwidth = bandwidth
            bandwidth = max(SliceConfig.URLLC_BANDWIDTH_MIN, bandwidth - 1)
            rate = calculate_rate_from_cqi(bandwidth, cqi)
            adjustment_made = True
            adjustment_reason = f"Rate above URLLC maximum. Decreased bandwidth from {old_bandwidth} to {bandwidth} MHz."
    
    return bandwidth, rate, adjustment_made, adjustment_reason


def get_tools() -> List:
    """Get list of all available tools"""
    return [
        network_monitor,
        knowledge_base_query,
        check_and_adjust_capacity,
        workload_balance_tool,
        beamforming_tool,
        slice_allocation
    ]
