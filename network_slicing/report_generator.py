"""
Report Generator Module

Provides functions for generating network status reports
and user allocation tables.
"""

from typing import Dict, List, Any, Optional
from tabulate import tabulate

from .network_state import NetworkStateManager, get_state_manager


def generate_concise_report(current_state: Dict[str, Any],
                            new_user_id: Optional[str] = None,
                            adjustment_result: Optional[Dict[str, Any]] = None,
                            state_manager: Optional[NetworkStateManager] = None) -> str:
    """
    Generate a concise network status report.
    
    Args:
        current_state: Current network state dictionary
        new_user_id: ID of newly added user (if any)
        adjustment_result: Result of bandwidth adjustments (if any)
        state_manager: Optional state manager instance
    
    Returns:
        str: Formatted report string
    """
    if state_manager is None:
        state_manager = get_state_manager()
    
    embb_slice = current_state["embb_slice"]
    urllc_slice = current_state["urllc_slice"]
    
    # Basic network statistics table
    stats = [
        ["Slice", "Users", "Resource Usage", "Utilization"],
        ["eMBB", len(embb_slice["users"]), 
         f"{embb_slice['resource_usage']}/{embb_slice['total_capacity']} MHz", 
         embb_slice["utilization_rate"]],
        ["URLLC", len(urllc_slice["users"]), 
         f"{urllc_slice['resource_usage']}/{urllc_slice['total_capacity']} MHz", 
         urllc_slice["utilization_rate"]]
    ]
    
    # Calculate rates
    embb_total_rate, urllc_total_rate = state_manager.calculate_total_transmission_rates()
    avg_resource_util = state_manager.calculate_average_resource_utilization()
    
    report = [
        f"Network Status @ {current_state['timestamp']}",
        f"Total Users: {current_state['total_users']}",
        f"Average Resource Utilization: {avg_resource_util}%",
        f"eMBB Total Rate: {embb_total_rate:.2f} Mbps, URLLC Total Rate: {urllc_total_rate:.2f} Mbps",
        "",
        tabulate(stats, headers="firstrow", tablefmt="simple")
    ]
    
    # Show new user details
    if new_user_id:
        new_user = _find_user(current_state, new_user_id)
        if new_user:
            report.append("\nNew User Allocation:")
            report.append(f"User {new_user_id} → {new_user['slice']} Slice")
            report.append(f"CQI: {new_user['cqi']}, Bandwidth: {new_user['bandwidth']} MHz, "
                         f"Rate: {new_user['rate']:.2f} Mbps, Latency: {new_user['latency']} ms")
    
    # Show dynamic adjustments
    if adjustment_result and adjustment_result.get("adjustments_made", False):
        report.append("\nDynamic Resource Adjustments:")
        report.append(f"Users adjusted: {len(adjustment_result['user_adjustments'])}, "
                     f"Bandwidth freed: {adjustment_result['freed_bandwidth']} MHz")
        
        if adjustment_result['user_adjustments']:
            adj_summary = []
            for adj in adjustment_result["user_adjustments"]:
                adj_summary.append(f"User {adj['user_id']}: {adj['old_bandwidth']}→{adj['new_bandwidth']} MHz")
            report.append("  " + ", ".join(adj_summary))
    
    return "\n".join(report)


def generate_user_allocation_table(current_state: Dict[str, Any],
                                    new_user_id: Optional[str] = None,
                                    adjusted_user_ids: Optional[List[str]] = None) -> str:
    """
    Generate a table showing all user allocations.
    
    Args:
        current_state: Current network state dictionary
        new_user_id: ID of newly added user (if any)
        adjusted_user_ids: List of adjusted user IDs
    
    Returns:
        str: Formatted table string
    """
    if adjusted_user_ids is None:
        adjusted_user_ids = []
    
    all_users = []
    
    # Add eMBB users
    for user in current_state["embb_slice"]["users"]:
        status = _get_user_status(user["user_id"], new_user_id, adjusted_user_ids)
        all_users.append({
            "user_id": user["user_id"],
            "slice": "eMBB",
            "cqi": user["cqi"],
            "bandwidth": user["bandwidth"],
            "rate": user["rate"],
            "latency": user["latency"],
            "status": status
        })
    
    # Add URLLC users
    for user in current_state["urllc_slice"]["users"]:
        status = _get_user_status(user["user_id"], new_user_id, adjusted_user_ids)
        all_users.append({
            "user_id": user["user_id"],
            "slice": "URLLC",
            "cqi": user["cqi"],
            "bandwidth": user["bandwidth"],
            "rate": user["rate"],
            "latency": user["latency"],
            "status": status
        })
    
    # Sort by slice type and user_id
    all_users.sort(key=lambda x: (x["slice"], x["user_id"]))
    
    # Format data for table
    rows = []
    for user in all_users:
        row = [
            user["user_id"],
            user["slice"],
            user["cqi"],
            user["bandwidth"],
            f"{user['rate']:.2f}",
            user["latency"],
            user["status"]
        ]
        rows.append(row)
    
    headers = ["User ID", "Slice", "CQI", "BW (MHz)", "Rate (Mbps)", "Latency (ms)", "Status"]
    table = tabulate(rows, headers=headers, tablefmt="grid")
    
    return f"\nCurrent User Allocations:\n{table}"


def generate_summary_table(results: List[Dict[str, Any]]) -> str:
    """
    Generate a summary table of all user allocation results.
    
    Args:
        results: List of allocation result dictionaries
    
    Returns:
        str: Formatted summary table
    """
    rows = []
    for res in results:
        status = "Success" if not res.get("allocation_failed", True) else "Failed"
        intent_match = ""
        if res.get("intent_correct") is not None:
            intent_match = "Yes" if res["intent_correct"] else "No"
        
        rows.append([
            res["user_id"],
            status,
            res.get("slice_type", "Failed"),
            res.get("ground_truth", "N/A"),
            intent_match,
            res["cqi"],
            res.get("bandwidth", "N/A"),
            f"{res.get('rate', 'N/A')}" if res.get("rate") is not None else "N/A",
            res.get("latency", "N/A"),
            "Yes" if res.get("adjustments_made", False) else "No"
        ])
    
    headers = ["User ID", "Status", "Slice", "Ground Truth", "Intent Match", 
               "CQI", "BW (MHz)", "Rate (Mbps)", "Latency (ms)", "Adjusted"]
    
    return tabulate(rows, headers=headers, tablefmt="grid")


def _find_user(current_state: Dict[str, Any], user_id: str) -> Optional[Dict[str, Any]]:
    """Find a user in the current state by ID"""
    for slice_key, slice_name in [("embb_slice", "eMBB"), ("urllc_slice", "URLLC")]:
        for user in current_state[slice_key]["users"]:
            if user["user_id"] == user_id:
                return {**user, "slice": slice_name}
    return None


def _get_user_status(user_id: str, new_user_id: Optional[str], 
                     adjusted_user_ids: List[str]) -> str:
    """Get status label for a user"""
    if user_id == new_user_id:
        return "NEW"
    elif user_id in adjusted_user_ids:
        return "ADJUSTED"
    return ""
