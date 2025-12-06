"""
Configuration Module for Network Slicing

Contains all configuration constants, API settings, and path definitions.
"""

import os
import logging
from dataclasses import dataclass
from enum import Enum

import yaml

logger = logging.getLogger(__name__)


class RegionType(Enum):
    """Enum for ray tracing region types"""
    NORTH = "north"
    SOUTH = "south"
    CENTER = "center"
    TEST = "test"


class LLMModelType(Enum):
    """Enum for supported LLM models (matching config2.yaml)"""
    QWEN_FLASH = "qwen-flash"
    QWEN_TURBO = "qwen-turbo-latest"
    QWEN_PLUS = "qwen-plus-latest"
    QWEN_MAX = "qwen-max-latest"


@dataclass(frozen=True)
class SliceConfig:
    """Configuration for network slice parameters"""
    
    # eMBB Slice Configuration
    EMBB_CAPACITY: int = 90  # Total capacity in MHz
    EMBB_BANDWIDTH_MIN: int = 6
    EMBB_BANDWIDTH_MAX: int = 20
    EMBB_RATE_MIN: float = 100.0  # Mbps
    EMBB_RATE_MAX: float = 400.0  # Mbps
    EMBB_LATENCY_MIN: int = 10  # ms
    EMBB_LATENCY_MAX: int = 100  # ms
    
    # URLLC Slice Configuration
    URLLC_CAPACITY: int = 30  # Total capacity in MHz
    URLLC_BANDWIDTH_MIN: int = 1
    URLLC_BANDWIDTH_MAX: int = 5
    URLLC_RATE_MIN: float = 1.0  # Mbps
    URLLC_RATE_MAX: float = 100.0  # Mbps
    URLLC_LATENCY_MIN: int = 1  # ms
    URLLC_LATENCY_MAX: int = 10  # ms
    
    # CQI Range
    CQI_MIN: int = 1
    CQI_MAX: int = 15
    
    # Workload balancing threshold
    BALANCE_THRESHOLD: float = 0.2  # 20% difference triggers rebalancing
    
    @classmethod
    def get_slice_params(cls, slice_type: str) -> dict:
        """Get parameters for a specific slice type"""
        if slice_type == "eMBB":
            return {
                "capacity": cls.EMBB_CAPACITY,
                "bandwidth_range": (cls.EMBB_BANDWIDTH_MIN, cls.EMBB_BANDWIDTH_MAX),
                "rate_range": (cls.EMBB_RATE_MIN, cls.EMBB_RATE_MAX),
                "latency_range": (cls.EMBB_LATENCY_MIN, cls.EMBB_LATENCY_MAX)
            }
        elif slice_type == "URLLC":
            return {
                "capacity": cls.URLLC_CAPACITY,
                "bandwidth_range": (cls.URLLC_BANDWIDTH_MIN, cls.URLLC_BANDWIDTH_MAX),
                "rate_range": (cls.URLLC_RATE_MIN, cls.URLLC_RATE_MAX),
                "latency_range": (cls.URLLC_LATENCY_MIN, cls.URLLC_LATENCY_MAX)
            }
        else:
            raise ValueError(f"Unknown slice type: {slice_type}")


@dataclass
class LLMConfig:
    """Configuration for LLM API - Supports loading from YAML config file"""
    
    # Default configuration
    API_KEY: str = "sk-4aee6405765f41f2b808a29dedbd983b"
    BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    MODEL: str = "qwen-turbo-latest"
    TEMPERATURE: float = 0.0
    
    # Class-level runtime settings (mutable)
    _current_model: str = None
    _current_api_key: str = None
    _current_base_url: str = None
    _current_temperature: float = None
    _yaml_config: dict = None
    _yaml_loaded: bool = False
    
    # YAML config file path (try local first, then cloud version)
    _config_dir = os.path.dirname(os.path.abspath(__file__))
    CONFIG_FILE = os.path.join(_config_dir, "config2.yaml")
    CONFIG_FILE_CLOUD = os.path.join(_config_dir, "config2.yaml.cloud")
    
    @classmethod
    def _get_config_file(cls) -> str:
        """Get the appropriate config file path"""
        if os.path.exists(cls.CONFIG_FILE):
            return cls.CONFIG_FILE
        elif os.path.exists(cls.CONFIG_FILE_CLOUD):
            return cls.CONFIG_FILE_CLOUD
        # Return cloud file as default even if not found
        return cls.CONFIG_FILE_CLOUD
    
    @classmethod
    def _get_default_models_config(cls) -> dict:
        """Get default models configuration when no YAML file is found"""
        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        return {
            "qwen-flash": {"api_type": "openai", "base_url": base_url, "api_key": "", "temperature": 0},
            "qwen-turbo-latest": {"api_type": "openai", "base_url": base_url, "api_key": "", "temperature": 0},
            "qwen-max-latest": {"api_type": "openai", "base_url": base_url, "api_key": "", "temperature": 0},
            "qwen-plus-latest": {"api_type": "openai", "base_url": base_url, "api_key": "", "temperature": 0},
        }
    
    @classmethod
    def load_yaml_config(cls, config_path: str = None):
        """Load LLM configurations from YAML file
        
        Args:
            config_path: Path to YAML config file. If None, uses default path.
        """
        if config_path is None:
            config_path = cls._get_config_file()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            cls._yaml_config = config.get('models', {})
            
            # Replace ${DASHSCOPE_API_KEY} placeholder with actual env var
            env_api_key = os.environ.get("DASHSCOPE_API_KEY")
            if env_api_key:
                for model_name in cls._yaml_config:
                    if cls._yaml_config[model_name].get('api_key', '').startswith('${'):
                        cls._yaml_config[model_name]['api_key'] = env_api_key
            
            cls._yaml_loaded = True
            logger.info(f"Loaded LLM config from {config_path}")
            logger.info(f"Available models: {list(cls._yaml_config.keys())}")
        except Exception as e:
            logger.warning(f"Failed to load YAML config from {config_path}: {e}")
            # Use default configuration
            cls._yaml_config = cls._get_default_models_config()
            # Try to get API key from environment
            env_api_key = os.environ.get("DASHSCOPE_API_KEY")
            if env_api_key:
                for model_name in cls._yaml_config:
                    cls._yaml_config[model_name]['api_key'] = env_api_key
            cls._yaml_loaded = True
            logger.info(f"Using default models config. Available models: {list(cls._yaml_config.keys())}")
    
    @classmethod
    def get_available_models(cls) -> list:
        """Get list of available models from YAML config"""
        if not cls._yaml_loaded:
            cls.load_yaml_config()
        return list(cls._yaml_config.keys()) if cls._yaml_config else []
    
    @classmethod
    def set_model(cls, model: str):
        """Set the LLM model at runtime
        
        Args:
            model: Model name string or LLMModelType enum value
        """
        if isinstance(model, LLMModelType):
            model_name = model.value
        else:
            model_name = model
        
        # Load YAML config if not loaded
        if not cls._yaml_loaded:
            cls.load_yaml_config()
        
        # Check if model is in YAML config
        if cls._yaml_config and model_name in cls._yaml_config:
            model_config = cls._yaml_config[model_name]
            cls._current_model = model_name
            # Only set API key from YAML if not already set (e.g., from Streamlit secrets)
            if not cls._current_api_key:
                cls._current_api_key = model_config.get('api_key', cls.API_KEY)
            cls._current_base_url = model_config.get('base_url', cls.BASE_URL)
            cls._current_temperature = model_config.get('temperature', cls.TEMPERATURE)
            logger.info(f"Set model to: {model_name} (from YAML config)")
        else:
            # Use default settings
            cls._current_model = model_name
            logger.info(f"Set model to: {model_name} (using default settings)")
    
    @classmethod
    def get_model(cls) -> str:
        """Get the current LLM model"""
        return cls._current_model if cls._current_model else cls.MODEL
    
    @classmethod
    def set_api_config(cls, api_key: str = None, base_url: str = None, temperature: float = None):
        """Set API configuration at runtime"""
        if api_key:
            cls._current_api_key = api_key
        if base_url:
            cls._current_base_url = base_url
        if temperature is not None:
            cls._current_temperature = temperature
    
    @classmethod
    def get_api_key(cls) -> str:
        """Get the current API key (checks runtime config, env var, then default)"""
        if cls._current_api_key:
            logger.debug(f"Using runtime API key (starts with: {cls._current_api_key[:8]}...)")
            return cls._current_api_key
        # Check environment variable
        env_key = os.environ.get("DASHSCOPE_API_KEY")
        if env_key:
            logger.debug(f"Using env API key (starts with: {env_key[:8]}...)")
            return env_key
        logger.debug(f"Using default API key (starts with: {cls.API_KEY[:8]}...)")
        return cls.API_KEY
    
    @classmethod
    def get_base_url(cls) -> str:
        """Get the current base URL"""
        return cls._current_base_url if cls._current_base_url else cls.BASE_URL
    
    @classmethod
    def get_temperature(cls) -> float:
        """Get the current temperature"""
        return cls._current_temperature if cls._current_temperature is not None else cls.TEMPERATURE
    
    @classmethod
    def reset(cls):
        """Reset to default configuration"""
        cls._current_model = None
        cls._current_api_key = None
        cls._current_base_url = None
        cls._current_temperature = None
    
    @classmethod
    def print_config(cls):
        """Print current LLM configuration"""
        print(f"Model: {cls.get_model()}")
        print(f"Base URL: {cls.get_base_url()}")
        print(f"Temperature: {cls.get_temperature()}")
        if cls._yaml_loaded:
            print(f"Available models: {cls.get_available_models()}")


class PathConfig:
    """Configuration for file paths with runtime region selection"""
    
    # Module directory (where this config.py file is located)
    MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Base directory (parent of module directory)
    BASE_DIR = os.path.dirname(MODULE_DIR)
    
    # Knowledge base path
    KNOWLEDGE_BASE_PATH = os.path.join(
        BASE_DIR, "Knowledge_Base", "Intent_Understand.txt"
    )
    
    # Ray tracing CSV files for different regions (located in MODULE_DIR)
    RAY_TRACING_FILES = {
        RegionType.NORTH: "ray_tracing_results_north.csv",
        RegionType.SOUTH: "ray_tracing_results_south.csv",
        RegionType.CENTER: "ray_tracing_results_center.csv",
        RegionType.TEST: "ray_tracing_results_test.csv",
    }
    
    # Default region
    _current_region: RegionType = RegionType.CENTER
    
    # Default output file
    DEFAULT_OUTPUT_CSV = "network_slicing_results.csv"
    
    @classmethod
    def set_region(cls, region: str):
        """Set the ray tracing region at runtime
        
        Args:
            region: One of 'north', 'south', 'center', 'test'
        """
        if isinstance(region, RegionType):
            cls._current_region = region
        else:
            region_lower = region.lower()
            region_map = {
                'north': RegionType.NORTH,
                'south': RegionType.SOUTH,
                'center': RegionType.CENTER,
                'test': RegionType.TEST
            }
            if region_lower in region_map:
                cls._current_region = region_map[region_lower]
            else:
                raise ValueError(f"Unknown region: {region}. Valid options: north, south, center, test")
    
    @classmethod
    def get_region(cls) -> RegionType:
        """Get the current region"""
        return cls._current_region
    
    @classmethod
    def get_ray_tracing_csv(cls, region: str = None) -> str:
        """Get the ray tracing CSV file path for the specified or current region
        
        Args:
            region: Optional region override ('north', 'south', 'center', 'test')
        
        Returns:
            str: Full path to the ray tracing CSV file
        """
        if region:
            if isinstance(region, RegionType):
                target_region = region
            else:
                region_map = {
                    'north': RegionType.NORTH,
                    'south': RegionType.SOUTH,
                    'center': RegionType.CENTER,
                    'test': RegionType.TEST
                }
                target_region = region_map.get(region.lower(), cls._current_region)
        else:
            target_region = cls._current_region
        
        filename = cls.RAY_TRACING_FILES.get(target_region, "ray_tracing_results_center.csv")
        return os.path.join(cls.MODULE_DIR, filename)
    
    @classmethod
    def get_output_csv(cls, region: str = None) -> str:
        """Get the output CSV file path with region suffix
        
        Args:
            region: Optional region for naming the output file
        
        Returns:
            str: Output CSV filename
        """
        if region:
            if isinstance(region, RegionType):
                region_name = region.value
            else:
                region_name = region.lower()
        else:
            region_name = cls._current_region.value
        
        return f"network_slicing_results_{region_name}.csv"
    
    @classmethod
    def get_knowledge_base_path(cls) -> str:
        """Get knowledge base file path, with fallback"""
        if os.path.exists(cls.KNOWLEDGE_BASE_PATH):
            return cls.KNOWLEDGE_BASE_PATH
        # Fallback to alternative path
        alt_path = r"C:\Users\Jingwen TONG\Desktop\Simulation\WirelessAgent_V1\First_Stage_Results\NetworkSilicing_Demo\Knowledge_Base\Intent_Understand.txt"
        if os.path.exists(alt_path):
            return alt_path
        return cls.KNOWLEDGE_BASE_PATH
    
    @classmethod
    def list_available_regions(cls) -> list:
        """List all available regions"""
        return [r.value for r in RegionType]


# System prompt for the LLM
SYSTEM_PROMPT = """You are a 5G network slicing management expert, responsible for allocating network resources for users.

The current network has two types of slices:
- eMBB (Enhanced Mobile Broadband): Suitable for high bandwidth applications such as video streaming
  - Bandwidth: 6-20 MHz (integer values only)
  - Data rate: 100-400 Mbps
  - Latency: 10-100ms
  - Total capacity: 90 MHz
  
- URLLC (Ultra-Reliable Low Latency): Suitable for low latency applications such as remote control
  - Bandwidth: 1-5 MHz (integer values only)
  - Data rate: 1-100 Mbps
  - Latency: 1-10ms
  - Total capacity: 30 MHz

Please consider the user's Channel Quality Indicator (CQI) which ranges from 1-15, indicating the signal quality. Higher CQI values allow for higher data rates with the same bandwidth.

When a slice reaches capacity, you can dynamically adjust bandwidth for existing users to accommodate new users, prioritizing users with highest rates for adjustment while ensuring all users still meet minimum requirements.

The data rate is calculated using Shannon's formula: rate = bandwidth * log10(1 + 10^(CQI/10)) * 10

When deciding on the slice type, also consider network load balancing - if one slice is significantly more utilized than another (>20% difference) and the user can be accommodated in either slice, prefer the less utilized slice.

Please clearly state in your answer: "I recommend using [eMBB/URLLC] slice, because...", and provide detailed reasons."""


# Intent analysis prompt template
INTENT_PROMPT_TEMPLATE = """
Based on the user request: "{request}"

Your task is to accurately classify this request as requiring either eMBB or URLLC network slice based ONLY on the application requirements.

CLASSIFICATION GUIDELINES:
1. eMBB (Enhanced Mobile Broadband) - Choose when the application primarily needs:
   - High bandwidth/data rate
   - Can tolerate moderate latency (10-100ms)
   - Example applications: video streaming, large file downloads/uploads, AR/VR, high-resolution video calls

2. URLLC (Ultra-Reliable Low-Latency Communications) - Choose when the application primarily needs:
   - Very low latency (<10ms)
   - High reliability
   - Example applications: remote control, autonomous driving, industrial automation, real-time monitoring, IoT sensors

KEY INDICATORS FOR SLICES:
- Words indicating eMBB: stream, download, upload, video, HD, 4K, 8K, movie, watch, gaming, browse, surfing
- Words indicating URLLC: control, real-time, monitor, automation, sensors, immediate, mission-critical, safety, emergency

Please provide a detailed analysis with a clear slice recommendation.
"""


# Slice allocation prompt template
SLICE_PROMPT_TEMPLATE = """
Based on your intent analysis, I need your EXPLICIT recommendation for the appropriate network slice.

YOUR TASK:
Make a definitive choice between eMBB and URLLC for this request, with clear reasoning.

NETWORK SLICE CHARACTERISTICS:
- eMBB (Enhanced Mobile Broadband):
  * For high bandwidth applications
  * Data rate: 100-400 Mbps
  * Bandwidth: 6-20 MHz
  * Latency: 10-100ms
  * Best for: video streaming, downloads, gaming, web browsing

- URLLC (Ultra-Reliable Low-Latency):
  * For time-sensitive applications
  * Data rate: 1-100 Mbps 
  * Bandwidth: 1-5 MHz
  * Latency: 1-10ms
  * Best for: remote control, IoT, automation, real-time monitoring

DETAILED RECOMMENDATION REQUIRED:
Your response MUST begin with the exact phrase: "I recommend using [eMBB/URLLC] slice, because..."

Follow this with 2-3 sentences explaining:
1. Why this slice type is appropriate for the specific application
2. The key requirements that led to this decision (bandwidth vs. latency needs)
"""
