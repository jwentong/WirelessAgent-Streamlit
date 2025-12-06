"""
Network Slicing Package for WirelessAgent

This package provides a modular implementation of 5G network slicing
management using LangGraph and LangChain.

Modules:
    - config: Configuration constants and settings
    - network_state: Network state management
    - cqi_utils: CQI and rate calculation utilities
    - knowledge_base: Knowledge base access functions
    - data_io: CSV data loading and export
    - capacity_manager: Capacity and workload management
    - report_generator: Report generation utilities
    - tools: LangChain tool definitions
    - workflow: LangGraph workflow nodes and graph building

Usage:
    # Basic usage
    from network_slicing import run_simulation
    run_simulation(num_users=10, region='north', model='qwen-plus')
    
    # Or via command line
    python run_network_slicing.py --num_users 10 --region north --model qwen-plus
"""

from .config import SliceConfig, LLMConfig, PathConfig, RegionType, LLMModelType
from .network_state import NetworkStateManager
from .cqi_utils import generate_random_cqi, calculate_rate_from_cqi
from .knowledge_base import load_knowledge_base, get_application_slice_type
from .data_io import load_user_data_from_csv, export_results_to_csv
from .capacity_manager import (
    check_slice_capacity,
    find_adjustable_users,
    apply_bandwidth_adjustments,
    check_workload_balance
)
from .report_generator import generate_concise_report, generate_user_allocation_table
from .tools import get_tools
from .workflow import create_network_graph, process_user_request
from .main import run_simulation, main

__version__ = "1.1.0"
__author__ = "WirelessAgent Team"
