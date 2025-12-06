"""
Utility functions for Streamlit app

Bridges the Streamlit UI with the network_slicing module.
"""

import sys
import os
import logging

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import streamlit for secrets
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

# Import network_slicing modules
try:
    from network_slicing.config import PathConfig, LLMConfig
    from network_slicing.data_io import load_user_data_from_csv
    from network_slicing.network_state import get_state_manager
    from network_slicing.workflow import process_user_request
    from network_slicing.tools import reset_llm
    MODULES_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import network_slicing modules: {e}")
    MODULES_AVAILABLE = False


def _load_api_key_from_secrets() -> str:
    """Load API key from Streamlit secrets or environment variable"""
    # Try Streamlit secrets first
    if HAS_STREAMLIT:
        try:
            return st.secrets["api"]["DASHSCOPE_API_KEY"]
        except Exception:
            pass
    
    # Try environment variable
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if api_key:
        return api_key
    
    # Return None if not found (will use default from config)
    return None


def get_available_regions() -> list:
    """Get list of available regions"""
    return ["north", "south", "center", "test"]


def get_available_models() -> list:
    """Get list of available LLM models"""
    if MODULES_AVAILABLE:
        try:
            return LLMConfig.get_available_models() or [
                "qwen-flash",
                "qwen-turbo-latest", 
                "qwen-plus-latest",
                "qwen-max-latest"
            ]
        except Exception:
            pass
    return ["qwen-turbo-latest", "qwen-plus-latest", "qwen-max-latest"]


def initialize_system(region: str, model: str) -> bool:
    """
    Initialize the network slicing system with specified configuration.
    
    Args:
        region: Ray tracing region ('north', 'south', 'center', 'test')
        model: LLM model name
    
    Returns:
        bool: True if initialization successful
    """
    if not MODULES_AVAILABLE:
        logger.error("Network slicing modules not available")
        return False
    
    try:
        # Set region
        PathConfig.set_region(region)
        logger.info(f"Set region to: {region}")
        
        # Try to load API key from secrets
        api_key = _load_api_key_from_secrets()
        if api_key:
            LLMConfig.set_api_config(api_key=api_key)
            logger.info("API key loaded from secrets")
        
        # Set LLM model
        LLMConfig.set_model(model)
        reset_llm()
        logger.info(f"Set model to: {model}")
        
        # Initialize state manager
        state_manager = get_state_manager()
        state_manager.reset()
        logger.info("State manager initialized")
        
        return True
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return False


def reset_network_state():
    """Reset the network state to initial values"""
    if MODULES_AVAILABLE:
        try:
            state_manager = get_state_manager()
            state_manager.reset()
            logger.info("Network state reset")
        except Exception as e:
            logger.error(f"Reset failed: {e}")


def get_network_status() -> dict:
    """
    Get current network status including slice utilization.
    
    Returns:
        dict with embb_util, urllc_util, etc.
    """
    if not MODULES_AVAILABLE:
        return {"embb_util": 0, "urllc_util": 0}
    
    try:
        state_manager = get_state_manager()
        state = state_manager.get_state()
        
        # Calculate utilization percentages
        embb_capacity = 90  # MHz
        urllc_capacity = 30  # MHz
        
        embb_used = state.get('eMBB_allocated_bandwidth', 0)
        urllc_used = state.get('URLLC_allocated_bandwidth', 0)
        
        return {
            "embb_util": (embb_used / embb_capacity) * 100 if embb_capacity > 0 else 0,
            "urllc_util": (urllc_used / urllc_capacity) * 100 if urllc_capacity > 0 else 0,
            "embb_used": embb_used,
            "urllc_used": urllc_used,
            "embb_rate": state.get('eMBB_total_rate', 0),
            "urllc_rate": state.get('URLLC_total_rate', 0),
            "embb_users": state.get('eMBB_user_count', 0),
            "urllc_users": state.get('URLLC_user_count', 0)
        }
    except Exception as e:
        logger.error(f"Failed to get network status: {e}")
        return {"embb_util": 0, "urllc_util": 0}


def get_available_users(num_users: int = 10) -> list:
    """
    Get available users from the CSV dataset.
    
    Args:
        num_users: Number of users to load
    
    Returns:
        List of user dictionaries
    """
    if not MODULES_AVAILABLE:
        return []
    
    try:
        csv_file = PathConfig.get_ray_tracing_csv()
        users = load_user_data_from_csv(csv_file, num_users)
        return users
    except Exception as e:
        logger.error(f"Failed to load users: {e}")
        return []


def process_single_user(user_id: str, request: str, cqi: int, location: str = "(0,0,0)") -> dict:
    """
    Process a single user request through the network slicing workflow.
    
    Args:
        user_id: User identifier
        request: User's service request text
        cqi: Channel Quality Indicator (1-15)
        location: User location string
    
    Returns:
        dict with allocation results
    """
    if not MODULES_AVAILABLE:
        return {
            "success": False,
            "error": "Network slicing modules not available",
            "user_id": user_id,
            "request": request
        }
    
    try:
        # Process the request through the workflow
        result = process_user_request(
            user_id=user_id,
            location=location,
            request=request,
            cqi=cqi,
            ground_truth=None
        )
        
        # Format result for UI
        return {
            "success": not result.get("allocation_failed", True),
            "user_id": user_id,
            "request": request,
            "slice_type": result.get("slice_type", "Unknown"),
            "bandwidth": result.get("bandwidth", "N/A"),
            "rate": round(result.get("rate", 0), 2) if result.get("rate") else "N/A",
            "latency": result.get("latency", "N/A"),
            "intent": result.get("intent", ""),
            "intent_correct": result.get("intent_correct"),
            "explanation": result.get("explanation", ""),
            "adjustments_made": result.get("adjustments_made", False),
            "workload_balanced": result.get("workload_balanced", False),
            "error": result.get("error", None)
        }
    except Exception as e:
        logger.error(f"Processing failed for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id,
            "request": request,
            "slice_type": "Error"
        }


# For testing
if __name__ == "__main__":
    print("Testing utils module...")
    print(f"Modules available: {MODULES_AVAILABLE}")
    print(f"Regions: {get_available_regions()}")
    print(f"Models: {get_available_models()}")
    
    if MODULES_AVAILABLE:
        # Test initialization
        success = initialize_system("center", "qwen-turbo-latest")
        print(f"Initialization: {'Success' if success else 'Failed'}")
        
        # Test network status
        status = get_network_status()
        print(f"Network status: {status}")
        
        # Test user loading
        users = get_available_users(3)
        print(f"Loaded {len(users)} users")
