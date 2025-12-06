# WirelessAgent Network Slicing - Streamlit Demo

An interactive web interface for demonstrating AI-driven 5G network slicing resource allocation.

## Features

- 🎯 **Single User Allocation**: Process individual user requests with real-time AI analysis
- 📋 **Batch Processing**: Process multiple users from the dataset
- 📊 **Network Dashboard**: Real-time visualization of eMBB/URLLC utilization
- 📈 **History & Analytics**: Track allocation history and performance metrics

## Quick Start

### 1. Install Dependencies

```bash
cd streamlit_app
pip install -r requirements.txt
```

### 2. Run the App

```bash
streamlit run app.py
```

Or from parent directory:
```bash
cd NetworkSilicing_Demo
streamlit run streamlit_app/app.py
```

### 3. Open in Browser

The app will automatically open at `http://localhost:8501`

## Usage

1. **Initialize System**: Click "🔄 Initialize System" in the sidebar
2. **Select Configuration**: Choose region and LLM model
3. **Enter Request**: Type a user request or use example buttons
4. **Allocate**: Click "🚀 Allocate Slice" to process

## Configuration

- **Region**: north, south, center, test (different ray tracing datasets)
- **LLM Model**: qwen-flash, qwen-turbo-latest, qwen-plus-latest, qwen-max-latest

## Deployment to Streamlit Cloud

1. Push this folder to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set the main file path to `streamlit_app/app.py`
5. Add secrets in Streamlit Cloud dashboard for API keys

## Project Structure

```
streamlit_app/
├── app.py              # Main Streamlit application
├── utils.py            # Utility functions bridging to network_slicing
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── .streamlit/
    └── config.toml     # Streamlit configuration
```
