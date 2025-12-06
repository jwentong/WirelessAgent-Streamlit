"""
CQI Utilities Module

Provides functions for CQI generation and data rate calculation
based on Shannon's formula.
"""

import math
import random

from .config import SliceConfig


def generate_random_cqi() -> int:
    """
    Generate a random CQI value between 1 and 15.
    
    Returns:
        int: Random CQI value in range [1, 15]
    """
    return random.randint(SliceConfig.CQI_MIN, SliceConfig.CQI_MAX)


def calculate_rate_from_cqi(bandwidth: int, cqi: int) -> float:
    """
    Calculate data rate based on CQI using Shannon's formula.
    
    The formula used is: rate = bandwidth * log10(1 + SNR) * 10
    where SNR = 10^(CQI/10)
    
    Args:
        bandwidth: Allocated bandwidth in MHz
        cqi: Channel Quality Indicator (1-15)
    
    Returns:
        float: Calculated data rate in Mbps, rounded to 2 decimal places
    """
    # Convert CQI to SNR in linear scale
    snr = 10 ** (cqi / 10)
    
    # Calculate rate using Shannon's formula with scaling factor
    rate = bandwidth * math.log10(1 + snr) * 10
    
    return round(rate, 2)


def calculate_min_bandwidth_for_rate(min_rate: float, cqi: int) -> int:
    """
    Calculate minimum bandwidth needed to achieve a target rate.
    
    Inverts Shannon's formula to find: min_bandwidth = min_rate / (log10(1 + 10^(CQI/10)) * 10)
    
    Args:
        min_rate: Minimum required rate in Mbps
        cqi: Channel Quality Indicator (1-15)
    
    Returns:
        int: Minimum bandwidth in MHz (ceiling value)
    """
    snr = 10 ** (cqi / 10)
    shannon_factor = math.log10(1 + snr) * 10
    min_bandwidth = math.ceil(min_rate / shannon_factor)
    return min_bandwidth


def validate_rate_for_slice(rate: float, slice_type: str) -> bool:
    """
    Validate if a rate meets the requirements for a slice type.
    
    Args:
        rate: Data rate in Mbps
        slice_type: "eMBB" or "URLLC"
    
    Returns:
        bool: True if rate is valid for the slice type
    """
    if slice_type == "eMBB":
        return SliceConfig.EMBB_RATE_MIN <= rate <= SliceConfig.EMBB_RATE_MAX
    elif slice_type == "URLLC":
        return SliceConfig.URLLC_RATE_MIN <= rate <= SliceConfig.URLLC_RATE_MAX
    else:
        return False


def get_rate_requirements(slice_type: str) -> str:
    """
    Get the rate requirement string for a slice type.
    
    Args:
        slice_type: "eMBB" or "URLLC"
    
    Returns:
        str: Rate requirement string (e.g., "100-400 Mbps")
    """
    if slice_type == "eMBB":
        return f"{int(SliceConfig.EMBB_RATE_MIN)}-{int(SliceConfig.EMBB_RATE_MAX)} Mbps"
    else:
        return f"{int(SliceConfig.URLLC_RATE_MIN)}-{int(SliceConfig.URLLC_RATE_MAX)} Mbps"
