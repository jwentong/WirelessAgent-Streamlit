"""
WirelessAgent Network Slicing Demo - Streamlit Application

An interactive web interface for demonstrating AI-driven network slicing
resource allocation using LangGraph-based agents.
"""

import streamlit as st
import sys
import os

# Add parent directory to path to import network_slicing module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    initialize_system, 
    process_single_user, 
    get_network_status,
    reset_network_state,
    get_available_users,
    get_available_models,
    get_available_regions
)

# Page configuration
st.set_page_config(
    page_title="WirelessAgent Network Slicing",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .result-box {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        border-radius: 5px;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        border-radius: 5px;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
    st.session_state.results_history = []
    st.session_state.network_state = None

# Header
st.markdown('<div class="main-header">🌐 WirelessAgent Network Slicing</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-Driven 5G Network Slice Resource Allocation Demo</div>', unsafe_allow_html=True)

# Sidebar - Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Region selection
    regions = get_available_regions()
    selected_region = st.selectbox(
        "📍 Select Region",
        options=regions,
        index=regions.index("center") if "center" in regions else 0,
        help="Choose the ray tracing region for simulation"
    )
    
    # Model selection
    models = get_available_models()
    selected_model = st.selectbox(
        "🤖 LLM Model",
        options=models,
        index=0,
        help="Select the AI model for intent understanding"
    )
    
    st.divider()
    
    # Initialize button
    if st.button("🔄 Initialize System", use_container_width=True):
        with st.spinner("Initializing..."):
            success = initialize_system(selected_region, selected_model)
            if success:
                st.session_state.initialized = True
                st.session_state.network_state = get_network_status()
                st.success("System initialized!")
            else:
                st.error("Initialization failed!")
    
    # Reset button
    if st.button("🗑️ Reset Network State", use_container_width=True):
        reset_network_state()
        st.session_state.results_history = []
        st.session_state.network_state = get_network_status()
        st.info("Network state reset!")
    
    st.divider()
    
    # Network Status Display
    st.header("📊 Network Status")
    if st.session_state.network_state:
        state = st.session_state.network_state
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("eMBB Util", f"{state.get('embb_util', 0):.1f}%")
        with col2:
            st.metric("URLLC Util", f"{state.get('urllc_util', 0):.1f}%")
        
        # Progress bars for utilization
        st.caption("eMBB Capacity")
        st.progress(min(state.get('embb_util', 0) / 100, 1.0))
        
        st.caption("URLLC Capacity")
        st.progress(min(state.get('urllc_util', 0) / 100, 1.0))

# Main content area
tab1, tab2, tab3 = st.tabs(["🎯 Single User Allocation", "📋 Batch Processing", "📈 History & Analytics"])

# Tab 1: Single User Allocation
with tab1:
    st.subheader("Single User Slice Allocation")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # User request input
        user_request = st.text_area(
            "📝 User Request",
            placeholder="Enter user's service request, e.g., 'I need to stream 4K video content'",
            height=100,
            help="Describe what the user wants to do. The AI will analyze the intent and allocate appropriate network slice."
        )
        
        # Example requests
        st.caption("💡 Example requests:")
        example_cols = st.columns(2)
        with example_cols[0]:
            if st.button("📺 4K Video Streaming", use_container_width=True):
                st.session_state.example_request = "I want to stream 4K video content smoothly"
            if st.button("🎮 VR Gaming", use_container_width=True):
                st.session_state.example_request = "I want to participate in a virtual reality gaming session"
        with example_cols[1]:
            if st.button("🏥 Medical Device", use_container_width=True):
                st.session_state.example_request = "I need reliable connectivity for implanted medical devices"
            if st.button("🤖 Robot Control", use_container_width=True):
                st.session_state.example_request = "I need to control a robotic arm in real time"
        
        # Check if example was clicked
        if 'example_request' in st.session_state:
            user_request = st.session_state.example_request
            del st.session_state.example_request
            st.rerun()
    
    with col2:
        # CQI input
        cqi_value = st.slider(
            "📶 CQI Value",
            min_value=1,
            max_value=15,
            value=10,
            help="Channel Quality Indicator (1-15). Higher values indicate better channel conditions."
        )
        
        # User ID
        user_id = st.text_input(
            "🆔 User ID",
            value="demo_user",
            help="Identifier for this user"
        )
        
        # Location (optional)
        location = st.text_input(
            "📍 Location (optional)",
            value="(0.0, 0.0, 1.5)",
            help="User location coordinates (x, y, z)"
        )
    
    # Allocate button
    if st.button("🚀 Allocate Slice", type="primary", use_container_width=True):
        if not user_request:
            st.warning("Please enter a user request!")
        elif not st.session_state.initialized:
            st.warning("Please initialize the system first (use sidebar button)!")
        else:
            with st.spinner("🔄 Processing request with AI agent..."):
                result = process_single_user(
                    user_id=user_id,
                    request=user_request,
                    cqi=cqi_value,
                    location=location
                )
                
                # Update network state
                st.session_state.network_state = get_network_status()
                
                # Add to history
                st.session_state.results_history.append(result)
            
            # Display results
            st.divider()
            st.subheader("📋 Allocation Result")
            
            if result.get('success', False):
                st.markdown('<div class="success-box">', unsafe_allow_html=True)
                
                result_cols = st.columns(4)
                with result_cols[0]:
                    slice_emoji = "📺" if result.get('slice_type') == 'eMBB' else "⚡"
                    st.metric("Slice Type", f"{slice_emoji} {result.get('slice_type', 'N/A')}")
                with result_cols[1]:
                    st.metric("Bandwidth", f"{result.get('bandwidth', 'N/A')} MHz")
                with result_cols[2]:
                    st.metric("Rate", f"{result.get('rate', 'N/A')} Mbps")
                with result_cols[3]:
                    st.metric("Latency", f"{result.get('latency', 'N/A')} ms")
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Intent understanding
                with st.expander("🧠 AI Intent Analysis", expanded=True):
                    st.write(f"**Identified Intent:** {result.get('intent', 'N/A')}")
                    st.write(f"**Ground Truth Match:** {'✅ Correct' if result.get('intent_correct') else '❌ Incorrect' if result.get('intent_correct') is False else '❓ Unknown'}")
                    if result.get('explanation'):
                        st.info(result.get('explanation'))
            else:
                st.markdown('<div class="error-box">', unsafe_allow_html=True)
                st.error(f"Allocation failed: {result.get('error', 'Unknown error')}")
                st.markdown('</div>', unsafe_allow_html=True)

# Tab 2: Batch Processing
with tab2:
    st.subheader("Batch User Processing")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Number of users
        num_users = st.number_input(
            "👥 Number of Users",
            min_value=1,
            max_value=50,
            value=5,
            help="Number of users to process from the CSV dataset"
        )
        
        # Get available users preview
        if st.session_state.initialized:
            available_users = get_available_users(num_users)
            if available_users:
                st.caption(f"📊 Preview: {len(available_users)} users loaded")
                with st.expander("View User Data"):
                    for user in available_users[:5]:
                        st.write(f"**User {user['user_id']}:** {user['request'][:50]}...")
    
    with col2:
        if st.button("▶️ Run Batch Processing", type="primary", use_container_width=True):
            if not st.session_state.initialized:
                st.warning("Please initialize the system first!")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                available_users = get_available_users(num_users)
                batch_results = []
                
                for i, user in enumerate(available_users):
                    status_text.text(f"Processing user {user['user_id']} ({i+1}/{len(available_users)})...")
                    
                    result = process_single_user(
                        user_id=user['user_id'],
                        request=user['request'],
                        cqi=user['cqi'],
                        location=user.get('location', '(0,0,0)')
                    )
                    batch_results.append(result)
                    st.session_state.results_history.append(result)
                    
                    progress_bar.progress((i + 1) / len(available_users))
                
                status_text.text("✅ Batch processing complete!")
                st.session_state.network_state = get_network_status()
                
                # Summary
                success_count = sum(1 for r in batch_results if r.get('success'))
                st.success(f"Processed {len(batch_results)} users. Success rate: {success_count}/{len(batch_results)}")

# Tab 3: History & Analytics
with tab3:
    st.subheader("Allocation History & Analytics")
    
    if st.session_state.results_history:
        # Summary metrics
        total = len(st.session_state.results_history)
        success = sum(1 for r in st.session_state.results_history if r.get('success'))
        embb_count = sum(1 for r in st.session_state.results_history if r.get('slice_type') == 'eMBB')
        urllc_count = sum(1 for r in st.session_state.results_history if r.get('slice_type') == 'URLLC')
        
        metric_cols = st.columns(4)
        with metric_cols[0]:
            st.metric("Total Requests", total)
        with metric_cols[1]:
            st.metric("Success Rate", f"{(success/total*100):.1f}%")
        with metric_cols[2]:
            st.metric("eMBB Allocations", embb_count)
        with metric_cols[3]:
            st.metric("URLLC Allocations", urllc_count)
        
        st.divider()
        
        # Results table
        import pandas as pd
        df_data = []
        for r in st.session_state.results_history:
            df_data.append({
                "User ID": r.get('user_id', 'N/A'),
                "Status": "✅" if r.get('success') else "❌",
                "Slice": r.get('slice_type', 'N/A'),
                "Bandwidth (MHz)": r.get('bandwidth', 'N/A'),
                "Rate (Mbps)": r.get('rate', 'N/A'),
                "Latency (ms)": r.get('latency', 'N/A'),
                "Request": r.get('request', 'N/A')[:50] + "..."
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
        
        # Clear history button
        if st.button("🗑️ Clear History"):
            st.session_state.results_history = []
            st.rerun()
    else:
        st.info("No allocation history yet. Process some users to see results here.")

# Footer
st.divider()
st.caption("🌐 WirelessAgent Network Slicing Demo | Powered by LangGraph & Streamlit")
