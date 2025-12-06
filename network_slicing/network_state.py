"""
Network State Management Module

Provides a class-based approach to managing network slice state,
replacing global variables with encapsulated state management.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, TypedDict
import logging

from .config import SliceConfig

logger = logging.getLogger(__name__)


class NetworkState(TypedDict):
    """Type definition for workflow state"""
    user_id: str
    location: str
    request: str
    cqi: int
    history: List[Dict[str, Any]]
    memory: Dict[str, Any]
    step_count: int
    current_step: str
    final_result: Optional[str]


class SliceState(TypedDict):
    """Type definition for a single slice state"""
    users: List[Dict[str, Any]]
    total_capacity: int
    resource_usage: int
    utilization_rate: str


class NetworkStateManager:
    """
    Manages the global network state for both eMBB and URLLC slices.
    
    This class encapsulates all network state management, replacing
    global variables with instance-based state tracking.
    """
    
    def __init__(self):
        """Initialize network state manager with default state"""
        self._state: Dict[str, Any] = self._create_initial_state()
        self._previous_state: Optional[Dict[str, Any]] = None
    
    def _create_initial_state(self) -> Dict[str, Any]:
        """Create initial network state"""
        return {
            "embb_slice": {
                "users": [],
                "total_capacity": SliceConfig.EMBB_CAPACITY,
                "resource_usage": 0,
                "utilization_rate": "0%"
            },
            "urllc_slice": {
                "users": [],
                "total_capacity": SliceConfig.URLLC_CAPACITY,
                "resource_usage": 0,
                "utilization_rate": "0%"
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_users": 0
        }
    
    def get_state(self) -> Dict[str, Any]:
        """Get a copy of the current network state"""
        return self._state.copy()
    
    def get_slice_state(self, slice_type: str) -> Dict[str, Any]:
        """Get state for a specific slice"""
        slice_key = "embb_slice" if slice_type == "eMBB" else "urllc_slice"
        return self._state[slice_key].copy()
    
    def update_state(self, new_state: Dict[str, Any]) -> bool:
        """Update global network state"""
        self._previous_state = self._state.copy()
        self._state = new_state
        return True
    
    def get_previous_state(self) -> Optional[Dict[str, Any]]:
        """Get the previous state before the last update"""
        return self._previous_state
    
    def reset(self) -> bool:
        """Reset network state to initial values"""
        self._state = self._create_initial_state()
        self._previous_state = None
        logger.info("Network state reset to initial values")
        return True
    
    def add_user(self, slice_type: str, user: Dict[str, Any]) -> bool:
        """Add a user to a slice"""
        slice_key = "embb_slice" if slice_type == "eMBB" else "urllc_slice"
        
        self._state[slice_key]["users"].append(user)
        self._state[slice_key]["resource_usage"] += user["bandwidth"]
        self._state[slice_key]["utilization_rate"] = self._calculate_utilization_rate(
            self._state[slice_key]["resource_usage"],
            self._state[slice_key]["total_capacity"]
        )
        self._state["total_users"] = (
            len(self._state["embb_slice"]["users"]) + 
            len(self._state["urllc_slice"]["users"])
        )
        self._state["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"User {user['user_id']} added to {slice_type} slice")
        return True
    
    def update_user_bandwidth(self, slice_type: str, user_id: str, 
                               new_bandwidth: int, new_rate: float) -> bool:
        """Update a user's bandwidth and rate"""
        slice_key = "embb_slice" if slice_type == "eMBB" else "urllc_slice"
        
        for user in self._state[slice_key]["users"]:
            if user["user_id"] == user_id:
                old_bandwidth = user["bandwidth"]
                user["bandwidth"] = new_bandwidth
                user["rate"] = new_rate
                
                # Update resource usage
                self._state[slice_key]["resource_usage"] -= (old_bandwidth - new_bandwidth)
                self._state[slice_key]["utilization_rate"] = self._calculate_utilization_rate(
                    self._state[slice_key]["resource_usage"],
                    self._state[slice_key]["total_capacity"]
                )
                return True
        return False
    
    def get_available_bandwidth(self, slice_type: str) -> int:
        """Get available bandwidth for a slice"""
        slice_key = "embb_slice" if slice_type == "eMBB" else "urllc_slice"
        return (self._state[slice_key]["total_capacity"] - 
                self._state[slice_key]["resource_usage"])
    
    def get_utilization_rates(self) -> tuple:
        """Get utilization rates for both slices"""
        embb_total = self._state["embb_slice"]["total_capacity"]
        embb_used = self._state["embb_slice"]["resource_usage"]
        embb_rate = embb_used / embb_total if embb_total > 0 else 0
        
        urllc_total = self._state["urllc_slice"]["total_capacity"]
        urllc_used = self._state["urllc_slice"]["resource_usage"]
        urllc_rate = urllc_used / urllc_total if urllc_total > 0 else 0
        
        return embb_rate, urllc_rate
    
    def calculate_total_transmission_rates(self) -> tuple:
        """Calculate total transmission rate for each slice"""
        embb_total_rate = sum(
            user["rate"] for user in self._state["embb_slice"]["users"]
        )
        urllc_total_rate = sum(
            user["rate"] for user in self._state["urllc_slice"]["users"]
        )
        return embb_total_rate, urllc_total_rate
    
    def calculate_average_resource_utilization(self) -> float:
        """Calculate weighted average resource utilization across all slices"""
        embb_usage = self._state["embb_slice"]["resource_usage"]
        embb_capacity = self._state["embb_slice"]["total_capacity"]
        urllc_usage = self._state["urllc_slice"]["resource_usage"]
        urllc_capacity = self._state["urllc_slice"]["total_capacity"]
        
        total_usage = embb_usage + urllc_usage
        total_capacity = embb_capacity + urllc_capacity
        
        avg_util = (total_usage / total_capacity) * 100 if total_capacity > 0 else 0
        return round(avg_util, 2)
    
    @staticmethod
    def _calculate_utilization_rate(usage: int, capacity: int) -> str:
        """Calculate utilization rate percentage string"""
        return f"{(usage / capacity * 100):.2f}%"


# Global instance for convenience (optional, for backward compatibility)
_global_state_manager: Optional[NetworkStateManager] = None


def get_state_manager() -> NetworkStateManager:
    """Get or create the global state manager instance"""
    global _global_state_manager
    if _global_state_manager is None:
        _global_state_manager = NetworkStateManager()
    return _global_state_manager


def reset_global_state_manager():
    """Reset the global state manager"""
    global _global_state_manager
    if _global_state_manager is not None:
        _global_state_manager.reset()
    else:
        _global_state_manager = NetworkStateManager()
