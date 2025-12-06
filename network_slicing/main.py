#!/usr/bin/env python
"""
Network Slicing Main Module

Entry point for the WirelessAgent-based Network Slicing system.
Provides command-line interface for running network slicing simulations.

Usage:
    python -m network_slicing.main --num_users 10 --region north --model qwen-turbo-latest
    
    or via run_network_slicing.py:
    python run_network_slicing.py --num_users 10 --region south --model qwen-flash

Available models (from config2.yaml):
    - qwen-flash: Fast and lightweight model
    - qwen-turbo-latest: Balanced performance model (default)
    - qwen-plus-latest: Enhanced capability model
    - qwen-max-latest: Maximum capability model
"""

import argparse
import logging
from typing import List, Dict, Any, Optional

from network_slicing.config import PathConfig, LLMConfig
from network_slicing.data_io import load_user_data_from_csv, export_results_to_csv
from network_slicing.network_state import get_state_manager
from network_slicing.workflow import process_user_request
from network_slicing.report_generator import generate_summary_table
from network_slicing.tools import reset_llm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_simulation(num_users: int = 4, 
                   region: str = "center",
                   model: str = None,
                   csv_file: Optional[str] = None,
                   export_file: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Run network slicing simulation with CSV-based user testing.
    
    Args:
        num_users: Number of users to test
        region: Ray tracing region ('north', 'south', 'center', 'test')
        model: LLM model to use (e.g., 'qwen-turbo-latest', 'qwen-plus')
        csv_file: Path to user data CSV file (overrides region setting)
        export_file: Path to export results CSV file
    
    Returns:
        List of detailed result dictionaries
    """
    # Configure region
    PathConfig.set_region(region)
    
    # Configure LLM model if specified
    if model:
        LLMConfig.set_model(model)
        reset_llm()  # Reset LLM to pick up new config
    
    # Get paths
    if csv_file is None:
        csv_file = PathConfig.get_ray_tracing_csv()
    
    if export_file is None:
        export_file = PathConfig.get_output_csv()
    
    print("="*60)
    print("NETWORK SLICING SIMULATION")
    print("="*60)
    print(f"Region: {PathConfig.get_region().value}")
    print(f"LLM Model: {LLMConfig.get_model()}")
    print(f"Input CSV: {csv_file}")
    print(f"Output CSV: {export_file}")
    print(f"Number of users: {num_users}")
    print("="*60)
    print()
    
    # Load users from CSV
    users = load_user_data_from_csv(csv_file, num_users)
    print(f"Loaded {len(users)} users from {csv_file}")
    
    # Initialize state manager
    state_manager = get_state_manager()
    
    # Initialize results tracker
    detailed_results = []
    embb_utils = []
    urllc_utils = []
    workload_balanced_count = 0
    
    # Process each user
    for i, user in enumerate(users):
        print(f"\n{'='*80}")
        print(f"PROCESSING USER {user['user_id']} ({i+1}/{len(users)})")
        print(f"Request: \"{user['request']}\"")
        print(f"CQI: {user['cqi']}")
        if user.get('ground_truth'):
            print(f"Ground Truth Slice: {user['ground_truth']}")
        print(f"{'='*80}")
        
        # Reset network state for clean testing
        state_manager.reset()
        
        # Process the user
        result = process_user_request(
            user_id=user['user_id'],
            location=user['location'],
            request=user['request'],
            cqi=user['cqi'],
            ground_truth=user.get('ground_truth')
        )
        
        detailed_results.append(result)
        
        # Track workload balancing
        if result.get("workload_balanced", False):
            workload_balanced_count += 1
        
        # Track slice utilization
        if not result.get("allocation_failed", True):
            _track_utilization(result, embb_utils, urllc_utils)
    
    # Calculate statistics
    stats = _calculate_statistics(detailed_results, embb_utils, urllc_utils, 
                                   workload_balanced_count, state_manager)
    
    # Print summary
    _print_summary(detailed_results, stats)
    
    # Export results
    export_results_to_csv(
        detailed_results,
        stats["slice_stats"],
        stats["intent_stats"],
        export_file
    )
    
    return detailed_results


def _track_utilization(result: Dict[str, Any], 
                       embb_utils: List[float], 
                       urllc_utils: List[float]):
    """Track slice utilization from result"""
    try:
        if "embb_util_after" in result:
            embb_util_str = result["embb_util_after"]
            if isinstance(embb_util_str, str):
                embb_util = float(embb_util_str.replace("%", ""))
            else:
                embb_util = float(embb_util_str)
            embb_utils.append(embb_util)
        
        if "urllc_util_after" in result:
            urllc_util_str = result["urllc_util_after"]
            if isinstance(urllc_util_str, str):
                urllc_util = float(urllc_util_str.replace("%", ""))
            else:
                urllc_util = float(urllc_util_str)
            urllc_utils.append(urllc_util)
    except (ValueError, AttributeError):
        pass


def _calculate_statistics(results: List[Dict[str, Any]],
                          embb_utils: List[float],
                          urllc_utils: List[float],
                          workload_balanced_count: int,
                          state_manager) -> Dict[str, Any]:
    """Calculate summary statistics"""
    # Calculate average utilization
    avg_embb_util = sum(embb_utils) / len(embb_utils) if embb_utils else 0
    avg_urllc_util = sum(urllc_utils) / len(urllc_utils) if urllc_utils else 0
    
    # Get final rates
    final_embb_rate, final_urllc_rate = state_manager.calculate_total_transmission_rates()
    final_avg_util = state_manager.calculate_average_resource_utilization()
    
    # Calculate intent understanding rate
    correct_intents = 0
    total_evaluated = 0
    
    for result in results:
        if result.get("intent_correct") is not None:
            total_evaluated += 1
            if result["intent_correct"]:
                correct_intents += 1
    
    intent_rate = 0 if total_evaluated == 0 else (correct_intents / total_evaluated) * 100
    
    # Calculate workload balancing rate
    total_count = len(results)
    workload_balanced_rate = 0 if total_count == 0 else (workload_balanced_count / total_count) * 100
    
    return {
        "avg_embb_util": avg_embb_util,
        "avg_urllc_util": avg_urllc_util,
        "final_embb_rate": final_embb_rate,
        "final_urllc_rate": final_urllc_rate,
        "final_avg_util": final_avg_util,
        "correct_intents": correct_intents,
        "total_evaluated": total_evaluated,
        "intent_rate": intent_rate,
        "workload_balanced_count": workload_balanced_count,
        "workload_balanced_rate": workload_balanced_rate,
        "slice_stats": {
            "avg_resource_util": f"{final_avg_util:.2f}",
            "final_resource_util": f"{final_avg_util:.2f}",
            "final_embb_total_rate": f"{final_embb_rate:.2f}",
            "final_urllc_total_rate": f"{final_urllc_rate:.2f}"
        },
        "intent_stats": {
            "total": total_evaluated,
            "correct": correct_intents,
            "rate": f"{intent_rate:.2f}"
        }
    }


def _print_summary(results: List[Dict[str, Any]], stats: Dict[str, Any]):
    """Print summary of all results"""
    print("\n" + "="*60)
    print("SUMMARY OF USER ALLOCATIONS")
    print("="*60)
    
    # Generate and print summary table
    summary_table = generate_summary_table(results)
    print(summary_table)
    
    # Print statistics
    success_count = sum(1 for res in results if not res.get("allocation_failed", True))
    total_count = len(results)
    
    print("\nStatistics:")
    print(f"Success rate: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    print("\nIntent Understanding Evaluation:")
    print(f"Correctly identified intents: {stats['correct_intents']}/{stats['total_evaluated']}")
    print(f"Intent understanding rate: {stats['intent_rate']:.1f}%")
    
    print("\nWorkload Balancing Statistics:")
    print(f"Users with workload balancing: {stats['workload_balanced_count']}/{total_count}")
    print(f"Workload balancing rate: {stats['workload_balanced_rate']:.1f}%")
    
    print("\nSlice Utilization Statistics:")
    print(f"Average eMBB utilization: {stats['avg_embb_util']:.2f}%")
    print(f"Average URLLC utilization: {stats['avg_urllc_util']:.2f}%")
    
    print("\nTransmission Rate Statistics:")
    print(f"Final eMBB total rate: {stats['final_embb_rate']:.2f} Mbps")
    print(f"Final URLLC total rate: {stats['final_urllc_rate']:.2f} Mbps")
    
    print("\nResource Utilization:")
    print(f"Average resource utilization: {stats['final_avg_util']:.2f}%")


def main(num_users: int = 3, 
         region: str = "center",
         model: str = None,
         export_file: str = None):
    """
    Main program entry point.
    
    Args:
        num_users: Number of users to test (default: 3)
        region: Ray tracing region ('north', 'south', 'center', 'test')
        model: LLM model to use
        export_file: Path to export results CSV file
    """
    run_simulation(
        num_users=num_users, 
        region=region,
        model=model,
        export_file=export_file
    )


def parse_args():
    """Parse command line arguments"""
    # Available models from config2.yaml
    available_models = ['qwen-flash', 'qwen-turbo-latest', 'qwen-plus-latest', 'qwen-max-latest']
    
    parser = argparse.ArgumentParser(
        description="WirelessAgent Network Slicing Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m network_slicing.main --num_users 10 --region north
  python -m network_slicing.main --num_users 5 --region south --model qwen-flash
  python -m network_slicing.main --region center --model qwen-max-latest
  
Available regions: north, south, center, test
Available models: qwen-flash, qwen-turbo-latest, qwen-plus-latest, qwen-max-latest
        """
    )
    
    parser.add_argument(
        '-n', '--num_users',
        type=int,
        default=3,
        help='Number of users to simulate (default: 3)'
    )
    
    parser.add_argument(
        '-r', '--region',
        type=str,
        default='center',
        choices=['north', 'south', 'center', 'test'],
        help='Ray tracing region (default: center)'
    )
    
    parser.add_argument(
        '-m', '--model',
        type=str,
        default=None,
        choices=available_models,
        help='LLM model to use (default: qwen-turbo-latest). See config2.yaml for configuration.'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Output CSV file path (default: auto-generated based on region)'
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(
        num_users=args.num_users,
        region=args.region,
        model=args.model,
        export_file=args.output
    )
