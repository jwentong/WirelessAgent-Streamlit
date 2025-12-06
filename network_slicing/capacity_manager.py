"""
Capacity Manager Module

Provides functions for capacity checking, dynamic bandwidth adjustment,
and workload balancing between network slices.
"""

import logging
from typing import Dict, List, Any, Tuple, Optional

from .config import SliceConfig
from .cqi_utils import calculate_rate_from_cqi, calculate_min_bandwidth_for_rate
from .network_state import NetworkStateManager, get_state_manager

logger = logging.getLogger(__name__)


def check_slice_capacity(slice_type: str, required_bandwidth: int,
                         state_manager: Optional[NetworkStateManager] = None) -> Tuple[bool, int, int]:
    """
    Check if the slice has enough capacity for a new allocation.
    
    Args:
        slice_type: "eMBB" or "URLLC"
        required_bandwidth: Bandwidth needed for the new user in MHz
        state_manager: Optional state manager instance
    
    Returns:
        Tuple of (has_capacity, available_bandwidth, required_adjustment)
    """
    if state_manager is None:
        state_manager = get_state_manager()
    
    available_bandwidth = state_manager.get_available_bandwidth(slice_type)
    
    if available_bandwidth >= required_bandwidth:
        return True, available_bandwidth, 0
    else:
        return False, available_bandwidth, required_bandwidth - available_bandwidth


def find_adjustable_users(slice_type: str, adjustment_needed: int,
                          state_manager: Optional[NetworkStateManager] = None) -> Tuple[bool, List[Tuple], int]:
    """
    Identify users whose bandwidth can be reduced to free up capacity.
    
    Args:
        slice_type: "eMBB" or "URLLC"
        adjustment_needed: Amount of bandwidth that needs to be freed
        state_manager: Optional state manager instance
    
    Returns:
        Tuple of (adjustments_possible, user_adjustments, total_freed_bandwidth)
        user_adjustments is a list of tuples: (user_id, old_bw, new_bw, old_rate, new_rate)
    """
    if state_manager is None:
        state_manager = get_state_manager()
    
    current_state = state_manager.get_state()
    slice_key = "embb_slice" if slice_type == "eMBB" else "urllc_slice"
    
    # Get minimum requirements based on slice type
    if slice_type == "eMBB":
        min_rate = SliceConfig.EMBB_RATE_MIN
        min_bandwidth = SliceConfig.EMBB_BANDWIDTH_MIN
    else:
        min_rate = SliceConfig.URLLC_RATE_MIN
        min_bandwidth = SliceConfig.URLLC_BANDWIDTH_MIN
    
    # Get all users and sort by rate (highest first)
    users = current_state[slice_key]["users"]
    sorted_users = sorted(users, key=lambda u: u["rate"], reverse=True)
    
    user_adjustments = []
    total_freed_bandwidth = 0
    
    for user in sorted_users:
        user_id = user["user_id"]
        current_bandwidth = user["bandwidth"]
        cqi = user["cqi"]
        current_rate = user["rate"]
        
        # Calculate minimum bandwidth needed to meet minimum rate
        min_bandwidth_needed = calculate_min_bandwidth_for_rate(min_rate, cqi)
        min_bandwidth_needed = max(min_bandwidth_needed, min_bandwidth)
        
        # Calculate how much we can reduce for this user
        max_reduction = current_bandwidth - min_bandwidth_needed
        
        if max_reduction > 0:
            new_bandwidth = current_bandwidth - max_reduction
            new_rate = calculate_rate_from_cqi(new_bandwidth, cqi)
            
            user_adjustments.append((user_id, current_bandwidth, new_bandwidth, current_rate, new_rate))
            total_freed_bandwidth += max_reduction
            
            if total_freed_bandwidth >= adjustment_needed:
                # Optimize: give back excess to last adjusted user
                excess = total_freed_bandwidth - adjustment_needed
                if excess > 0 and len(user_adjustments) > 0:
                    user_id, old_bw, new_bw, old_rate, new_rate = user_adjustments[-1]
                    adjusted_new_bw = new_bw + excess
                    adjusted_new_rate = calculate_rate_from_cqi(adjusted_new_bw, cqi)
                    user_adjustments[-1] = (user_id, old_bw, adjusted_new_bw, old_rate, adjusted_new_rate)
                    total_freed_bandwidth = adjustment_needed
                
                return True, user_adjustments, total_freed_bandwidth
    
    return False, user_adjustments, total_freed_bandwidth


def apply_bandwidth_adjustments(slice_type: str, user_adjustments: List[Tuple],
                                 state_manager: Optional[NetworkStateManager] = None) -> Dict[str, Any]:
    """
    Apply bandwidth adjustments to existing users.
    
    Args:
        slice_type: "eMBB" or "URLLC"
        user_adjustments: List of (user_id, old_bw, new_bw, old_rate, new_rate)
        state_manager: Optional state manager instance
    
    Returns:
        Updated network state
    """
    if state_manager is None:
        state_manager = get_state_manager()
    
    for user_id, old_bw, new_bw, old_rate, new_rate in user_adjustments:
        state_manager.update_user_bandwidth(slice_type, user_id, new_bw, new_rate)
        logger.info(f"Adjusted user {user_id}: {old_bw}MHz -> {new_bw}MHz")
    
    return state_manager.get_state()


def check_workload_balance(target_slice_type: str, cqi: int, required_bandwidth: int,
                            state_manager: Optional[NetworkStateManager] = None) -> Tuple[bool, str, str]:
    """
    Check if workload should be balanced between slices.
    
    Args:
        target_slice_type: Originally targeted slice type
        cqi: User's Channel Quality Indicator
        required_bandwidth: Required bandwidth for the user
        state_manager: Optional state manager instance
    
    Returns:
        Tuple of (should_rebalance, recommended_slice, reason)
    """
    if state_manager is None:
        state_manager = get_state_manager()
    
    embb_rate, urllc_rate = state_manager.get_utilization_rates()
    
    # Calculate potential rates for both slice types
    embb_potential_rate = None
    urllc_potential_rate = None
    
    if target_slice_type == "eMBB" or (cqi >= 6 and required_bandwidth <= 5):
        if 1 <= required_bandwidth <= 5:
            urllc_potential_rate = calculate_rate_from_cqi(required_bandwidth, cqi)
    
    if target_slice_type == "URLLC" or required_bandwidth >= 6:
        if required_bandwidth >= 6:
            embb_potential_rate = calculate_rate_from_cqi(required_bandwidth, cqi)
    
    # Check utilization difference
    utilization_diff = abs(embb_rate - urllc_rate)
    
    if utilization_diff > SliceConfig.BALANCE_THRESHOLD:
        less_utilized_slice = "eMBB" if embb_rate < urllc_rate else "URLLC"
        
        if target_slice_type != less_utilized_slice:
            if less_utilized_slice == "eMBB" and embb_potential_rate is not None:
                if SliceConfig.EMBB_RATE_MIN <= embb_potential_rate <= SliceConfig.EMBB_RATE_MAX:
                    return True, "eMBB", f"Rebalancing: eMBB ({embb_rate:.2%}) is less utilized than URLLC ({urllc_rate:.2%})"
            
            elif less_utilized_slice == "URLLC" and urllc_potential_rate is not None:
                if SliceConfig.URLLC_RATE_MIN <= urllc_potential_rate <= SliceConfig.URLLC_RATE_MAX:
                    return True, "URLLC", f"Rebalancing: URLLC ({urllc_rate:.2%}) is less utilized than eMBB ({embb_rate:.2%})"
    
    return False, target_slice_type, "No workload balancing needed"


def check_and_adjust_capacity(slice_type: str, required_bandwidth: int,
                               state_manager: Optional[NetworkStateManager] = None) -> Dict[str, Any]:
    """
    Check if slice has capacity and perform dynamic adjustment if needed.
    
    Args:
        slice_type: "eMBB" or "URLLC"
        required_bandwidth: Bandwidth needed for the new user in MHz
        state_manager: Optional state manager instance
    
    Returns:
        Dictionary with capacity status and adjustment results
    """
    if state_manager is None:
        state_manager = get_state_manager()
    
    has_capacity, available_bandwidth, adjustment_needed = check_slice_capacity(
        slice_type, required_bandwidth, state_manager
    )
    
    if has_capacity:
        return {
            "status": "success",
            "has_capacity": True,
            "message": f"Sufficient capacity available: {available_bandwidth} MHz",
            "adjustments_made": False,
            "user_adjustments": [],
            "freed_bandwidth": 0
        }
    
    # Try to adjust existing users
    adjustments_possible, user_adjustments, freed_bandwidth = find_adjustable_users(
        slice_type, adjustment_needed, state_manager
    )
    
    if not adjustments_possible:
        return {
            "status": "failure",
            "has_capacity": False,
            "message": f"Insufficient capacity. Need {required_bandwidth} MHz but only {available_bandwidth} MHz available.",
            "adjustments_made": False,
            "user_adjustments": [],
            "freed_bandwidth": freed_bandwidth
        }
    
    # Apply adjustments
    apply_bandwidth_adjustments(slice_type, user_adjustments, state_manager)
    
    # Format adjustment summary
    adjustment_summary = []
    for user_id, old_bw, new_bw, old_rate, new_rate in user_adjustments:
        adjustment_summary.append({
            "user_id": user_id,
            "old_bandwidth": old_bw,
            "new_bandwidth": new_bw,
            "bandwidth_reduction": old_bw - new_bw,
            "old_rate": old_rate,
            "new_rate": new_rate
        })
    
    return {
        "status": "success",
        "has_capacity": True,
        "message": f"Dynamically adjusted {len(user_adjustments)} user(s) to free {freed_bandwidth} MHz",
        "adjustments_made": True,
        "user_adjustments": adjustment_summary,
        "freed_bandwidth": freed_bandwidth
    }


def apply_heuristic_bandwidth(slice_type: str, request: str) -> int:
    """
    Apply heuristic rules to determine bandwidth based on request type.
    
    Args:
        slice_type: "eMBB" or "URLLC"
        request: User's request text
    
    Returns:
        int: Recommended bandwidth in MHz
    """
    request_lower = request.lower()
    
    if slice_type == "eMBB":
        if any(kw in request_lower for kw in ["video", "stream", "watch", "movie", "4k", "8k"]):
            return 15
        elif any(kw in request_lower for kw in ["download", "file", "upload"]):
            return 12
        elif any(kw in request_lower for kw in ["conference", "meeting", "call"]):
            return 10
        else:
            return 8
    else:  # URLLC
        if any(kw in request_lower for kw in ["surgery", "medical", "emergency"]):
            return 5
        elif any(kw in request_lower for kw in ["control", "automation", "robot"]):
            return 3
        else:
            return 2


def apply_heuristic_latency(slice_type: str, request: str) -> int:
    """
    Apply heuristic rules to determine latency based on request type.
    
    Args:
        slice_type: "eMBB" or "URLLC"
        request: User's request text
    
    Returns:
        int: Recommended latency in ms
    """
    request_lower = request.lower()
    
    if slice_type == "eMBB":
        if any(kw in request_lower for kw in ["video", "stream", "watch", "movie", "4k", "8k"]):
            return 50
        elif any(kw in request_lower for kw in ["download", "file", "upload"]):
            return 80
        elif any(kw in request_lower for kw in ["conference", "meeting", "call"]):
            return 30
        else:
            return 40
    else:  # URLLC
        if any(kw in request_lower for kw in ["surgery", "medical", "emergency"]):
            return 1
        elif any(kw in request_lower for kw in ["control", "automation", "robot"]):
            return 3
        else:
            return 5
