"""
Knowledge Base Module

Provides functions for loading and querying the knowledge base
to determine appropriate slice types for different applications.
"""

import logging
from typing import List, Tuple, Optional

from .config import PathConfig

logger = logging.getLogger(__name__)

# Cache for knowledge base content
_knowledge_base_cache: Optional[str] = None


def load_knowledge_base(file_path: Optional[str] = None) -> str:
    """
    Load knowledge base content from file.
    
    Args:
        file_path: Path to knowledge base file. If None, uses default path.
    
    Returns:
        str: Knowledge base content
    """
    global _knowledge_base_cache
    
    if file_path is None:
        file_path = PathConfig.get_knowledge_base_path()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        _knowledge_base_cache = content
        logger.info(f"Knowledge base loaded from: {file_path}")
        return content
    except Exception as e:
        logger.warning(f"Failed to read knowledge base file: {e}")
        # Return default knowledge base content
        return _get_default_knowledge_base()


def get_knowledge_base_content() -> str:
    """
    Get cached knowledge base content or load if not cached.
    
    Returns:
        str: Knowledge base content
    """
    global _knowledge_base_cache
    
    if _knowledge_base_cache is None:
        _knowledge_base_cache = load_knowledge_base()
    
    return _knowledge_base_cache


def get_application_slice_type(application_type: str) -> Tuple[str, List[str]]:
    """
    Determine the slice type for an application based on knowledge base.
    
    This function analyzes the application type against the knowledge base
    to recommend either eMBB or URLLC slice.
    
    Args:
        application_type: Description of the application or user request
    
    Returns:
        Tuple[str, List[str]]: (slice_type, list_of_reasons)
    """
    kb_content = get_knowledge_base_content()
    app_lower = application_type.lower()
    
    # Divide knowledge base content into paragraphs
    kb_sections = kb_content.lower().split('\n\n')
    
    # Store matching results
    embb_matches = []
    urllc_matches = []
    exact_match_found = False
    
    # Find matches of application type in the knowledge base
    for section in kb_sections:
        if "embb" in section and app_lower in section:
            for line in section.split('\n'):
                if app_lower in line:
                    embb_matches.append(line.strip())
                    exact_match_found = True
        
        if "urllc" in section and app_lower in section:
            for line in section.split('\n'):
                if app_lower in line:
                    urllc_matches.append(line.strip())
                    exact_match_found = True
    
    # If exact match is found, decide based on match count
    if exact_match_found:
        if len(embb_matches) > len(urllc_matches):
            return "eMBB", [f"Knowledge base match: {', '.join(embb_matches)}"]
        elif len(urllc_matches) > len(embb_matches):
            return "URLLC", [f"Knowledge base match: {', '.join(urllc_matches)}"]
    
    # Apply matching rules
    rules_section = ""
    for section in kb_sections:
        if "matching rules" in section:
            rules_section = section
            break
    
    if rules_section:
        # Check rules about high bandwidth
        if ("high bandwidth" in rules_section and 
            any(kw in app_lower for kw in ["video", "download", "streaming"])):
            return "eMBB", ["Based on knowledge base rules: High bandwidth applications use eMBB"]
        
        # Check rules about low latency
        if ("low latency" in rules_section and 
            any(kw in app_lower for kw in ["control", "medical", "surgery"])):
            return "URLLC", ["Based on knowledge base rules: Low latency applications use URLLC"]
    
    # Apply keyword-based heuristics
    embb_keywords = ["video", "download", "file", "stream", "watch", "movie", 
                     "4k", "8k", "hd", "gaming", "browse", "upload"]
    urllc_keywords = ["control", "real-time", "surgery", "medical", "monitor",
                      "automation", "sensor", "emergency", "robot", "immediate"]
    
    embb_score = sum(1 for kw in embb_keywords if kw in app_lower)
    urllc_score = sum(1 for kw in urllc_keywords if kw in app_lower)
    
    if embb_score > urllc_score:
        return "eMBB", ["Based on keyword analysis: Application indicates high bandwidth needs"]
    elif urllc_score > embb_score:
        return "URLLC", ["Based on keyword analysis: Application indicates low latency needs"]
    
    # Default to eMBB (generally safer for general applications)
    return "eMBB", ["No clear match in knowledge base, defaulting to eMBB"]


def query_knowledge_base(query: str) -> str:
    """
    Query knowledge base for relevant information.
    
    Args:
        query: Search query
    
    Returns:
        str: Formatted search results
    """
    kb_content = get_knowledge_base_content()
    
    result = [
        "# Knowledge Base Search Results",
        "## Complete Knowledge Base",
        kb_content,
        "## Relevant Information Extracted Based on Query"
    ]
    
    # Simple keyword matching
    query_terms = query.lower().split()
    relevant_lines = []
    
    for line in kb_content.split('\n'):
        if any(term in line.lower() for term in query_terms):
            relevant_lines.append(line)
    
    if relevant_lines:
        result.append("\n".join(relevant_lines))
    else:
        result.append("No information directly related to the query was found.")
    
    # Try to infer application types and provide recommendations
    application_types = _infer_application_types(query)
    
    if application_types:
        result.append("\n## Inferred Application Types")
        for app_type in application_types:
            slice_type, reasons = get_application_slice_type(app_type)
            result.append(f"- {app_type}: Recommend using {slice_type} slice (Reason: {', '.join(reasons)})")
    
    return "\n".join(result)


def _infer_application_types(query: str) -> List[str]:
    """
    Infer application types from a query string.
    
    Args:
        query: User query or request
    
    Returns:
        List[str]: List of inferred application types
    """
    query_lower = query.lower()
    application_types = []
    
    if any(kw in query_lower for kw in ["video", "4k", "8k", "watch", "stream"]):
        application_types.append("HD video streaming")
    if any(kw in query_lower for kw in ["download", "game file", "upload"]):
        application_types.append("Large file transfer")
    if any(kw in query_lower for kw in ["surgery", "medical"]):
        application_types.append("Remote medicine/surgery")
    if any(kw in query_lower for kw in ["control", "automation", "robot"]):
        application_types.append("Real-time control system")
    if any(kw in query_lower for kw in ["conference", "meeting", "call"]):
        application_types.append("Video conferencing")
    
    return application_types


def _get_default_knowledge_base() -> str:
    """
    Get default knowledge base content when file is not available.
    
    Returns:
        str: Default knowledge base content
    """
    return """
# Network Slicing Knowledge Base

## eMBB Applications (Enhanced Mobile Broadband)
- Video streaming (4K, 8K, HD)
- Large file downloads
- Online gaming
- Virtual/Augmented Reality
- Video conferencing
- Web browsing
- Social media

## URLLC Applications (Ultra-Reliable Low-Latency)
- Remote surgery
- Industrial automation
- Autonomous vehicles
- Real-time control systems
- IoT sensors
- Emergency services
- Robot control

## Matching Rules
- High bandwidth applications: eMBB
- Low latency applications: URLLC
- Video/streaming: eMBB
- Control/monitoring: URLLC
"""
