"""
Data I/O Module

Provides functions for loading user data from CSV files
and exporting results to CSV.
"""

import csv
import logging
from typing import Dict, List, Any, Optional

import pandas as pd

from .config import PathConfig

logger = logging.getLogger(__name__)


def load_user_data_from_csv(file_path: Optional[str] = None, 
                            num_users: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Load user data from ray tracing CSV file.
    
    Expected CSV format:
    RX_ID,X,Y,Z,SNR_dB,RX_Power_dBm,CQI,LOS,User_Request,Request_Label
    
    Args:
        file_path: Path to CSV file. If None, uses default path.
        num_users: Optional limit on number of users to load.
    
    Returns:
        List of user dictionaries with keys: user_id, location, request, cqi, ground_truth
    """
    if file_path is None:
        file_path = PathConfig.DEFAULT_RAY_TRACING_CSV
    
    try:
        df = pd.read_csv(file_path)
        users = []
        
        # Limit to specified number of users if needed
        if num_users is not None and num_users < len(df):
            df = df.head(num_users)
        
        for _, row in df.iterrows():
            user = {
                "user_id": str(row['RX_ID']),
                "location": f"({row['X']}, {row['Y']}, {row['Z']})",
                "request": row['User_Request'],
                "cqi": int(row['CQI']),
                "ground_truth": row.get('Request_Label', None)
            }
            users.append(user)
        
        logger.info(f"Loaded {len(users)} users from {file_path}")
        return users
    
    except Exception as e:
        logger.warning(f"Error loading user data from CSV: {e}")
        return _get_default_users(num_users)


def export_results_to_csv(results: List[Dict[str, Any]], 
                          slice_stats: Dict[str, Any],
                          intent_stats: Dict[str, Any],
                          file_path: str = "network_slicing_results.csv") -> bool:
    """
    Export test results to a CSV file with enhanced analytics.
    
    Args:
        results: List of result dictionaries
        slice_stats: Dictionary containing slice utilization statistics
        intent_stats: Dictionary with intent understanding evaluation
        file_path: Path to save the CSV file
    
    Returns:
        bool: True if export successful, False otherwise
    """
    try:
        headers = [
            "User ID", "Allocation Status", "Slice", "Ground Truth", "Intent Correct", "CQI", 
            "Bandwidth (MHz)", "Rate (Mbps)", "Latency (ms)", "Adjustments Made", 
            "eMBB Total Rate Before (Mbps)", "eMBB Total Rate After (Mbps)",
            "URLLC Total Rate Before (Mbps)", "URLLC Total Rate After (Mbps)",
            "Avg Resource Util Before (%)", "Avg Resource Util After (%)",
            "Request"
        ]
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            for result in results:
                allocation_status = "Failed" if result.get("allocation_failed", True) else "Success"
                intent_correct = _format_intent_correct(result.get("intent_correct"))
                
                row = [
                    result["user_id"],
                    allocation_status,
                    result["slice_type"],
                    result.get("ground_truth", "Unknown"),
                    intent_correct,
                    result["cqi"],
                    result.get("bandwidth", "N/A"),
                    result.get("rate", "N/A"),
                    result.get("latency", "N/A"),
                    "Yes" if result.get("adjustments_made", False) else "No",
                    result.get("embb_total_rate_before", "N/A"),
                    result.get("embb_total_rate_after", "N/A"),
                    result.get("urllc_total_rate_before", "N/A"),
                    result.get("urllc_total_rate_after", "N/A"),
                    result.get("avg_resource_util_before", "N/A"),
                    result.get("avg_resource_util_after", "N/A"),
                    result["request"]
                ]
                writer.writerow(row)
            
            # Add summary statistics
            writer.writerow([])
            writer.writerow(["SUMMARY STATISTICS"])
            writer.writerow(["Average Resource Utilization (%)", slice_stats["avg_resource_util"]])
            writer.writerow(["Final Resource Utilization (%)", slice_stats["final_resource_util"]])
            writer.writerow(["Final eMBB Total Rate (Mbps)", slice_stats["final_embb_total_rate"]])
            writer.writerow(["Final URLLC Total Rate (Mbps)", slice_stats["final_urllc_total_rate"]])
            
            # Add intent understanding rate
            writer.writerow([])
            writer.writerow(["INTENT UNDERSTANDING EVALUATION"])
            writer.writerow(["Total Evaluated Requests", intent_stats["total"]])
            writer.writerow(["Correctly Identified Intents", intent_stats["correct"]])
            writer.writerow(["Intent Understanding Rate (%)", intent_stats["rate"]])
        
        logger.info(f"Results exported to {file_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error exporting results to CSV: {e}")
        return False


def _format_intent_correct(value: Optional[bool]) -> str:
    """Format intent correct value for CSV"""
    if value is True:
        return "Yes"
    elif value is False:
        return "No"
    else:
        return "N/A"


def _get_default_users(num_users: int = None) -> List[Dict[str, Any]]:
    """Get default users when CSV loading fails
    
    Args:
        num_users: Optional limit on number of users to return
    
    Returns:
        List of default user dictionaries
    """
    default_users = [
        {
            "user_id": "1",
            "location": "(-39.01, -0.50, 1.50)",
            "request": "I need to stream 8K video content",
            "cqi": 15,
            "ground_truth": "eMBB"
        },
        {
            "user_id": "2",
            "location": "(-62.97, 141.28, 1.50)",
            "request": "I want to watch 4K video",
            "cqi": 9,
            "ground_truth": "eMBB"
        },
        {
            "user_id": "3",
            "location": "(175.82, 31.38, 1.50)",
            "request": "I need to control a remote robot",
            "cqi": 8,
            "ground_truth": "URLLC"
        },
        {
            "user_id": "4",
            "location": "(-43.35, -65.84, 1.50)",
            "request": "I need to participate in a video conference meeting",
            "cqi": 14,
            "ground_truth": "eMBB"
        }
    ]
    
    if num_users is not None and num_users < len(default_users):
        return default_users[:num_users]
    return default_users
