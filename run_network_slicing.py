#!/usr/bin/env python
"""
WirelessAgent Network Slicing - Modular Version

This is the entry point for running the modular network slicing system.

Usage:
    # Default run (3 users, center region, qwen-turbo-latest)
    python run_network_slicing.py
    
    # Specify number of users
    python run_network_slicing.py --num_users 10
    python run_network_slicing.py -n 10
    
    # Specify region (north, south, center, test)
    python run_network_slicing.py --region north
    python run_network_slicing.py -r south
    
    # Specify LLM model
    python run_network_slicing.py --model qwen-plus
    python run_network_slicing.py -m qwen-max
    
    # Combined options
    python run_network_slicing.py -n 10 -r north -m qwen-plus
    python run_network_slicing.py --num_users 5 --region south --model qwen-turbo-latest
    
    # Specify output file
    python run_network_slicing.py -n 10 -r north -o my_results.csv

Available regions:
    - north: ray_tracing_results_north.csv
    - south: ray_tracing_results_south.csv  
    - center: ray_tracing_results.csv
    - test: ray_tracing_results_test.csv

Available LLM models:
    - qwen-turbo-latest (default)
    - qwen-plus-latest
    - qwen-max-latest
"""

from network_slicing.main import main, parse_args

if __name__ == "__main__":
    args = parse_args()
    main(
        num_users=args.num_users,
        region=args.region,
        model=args.model,
        export_file=args.output
    )
