# WirelessAgent Network Slicing Demo

An AI-driven 5G network slicing resource allocation system using LangGraph agents.

## 🌐 Live Demo

Visit the Streamlit app: [Coming soon after deployment]

## Features

- 🤖 **AI Intent Understanding**: Uses LLM to understand user service requests
- 📡 **Smart Slice Allocation**: Automatically allocates eMBB or URLLC slices
- 📊 **Real-time Dashboard**: Visualize network utilization
- ⚡ **Dynamic Resource Management**: Workload balancing and capacity adjustment

## Project Structure

```
NetworkSlicing_Demo/
├── network_slicing/          # Core network slicing module
│   ├── config.py            # Configuration management
│   ├── workflow.py          # LangGraph agent workflow
│   ├── tools.py             # LangChain tools
│   ├── capacity_manager.py  # Resource management
│   └── ...
├── streamlit_app/           # Web UI
│   ├── app.py              # Main Streamlit application
│   └── utils.py            # Utility functions
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Local Development

### 1. Clone the repository

```bash
git clone https://github.com/jwentong/WirelessAgent_R1.git
cd WirelessAgent_R1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up API key

Create `.streamlit/secrets.toml`:
```toml
[api]
DASHSCOPE_API_KEY = "your-api-key-here"
```

Or set environment variable:
```bash
export DASHSCOPE_API_KEY="your-api-key-here"
```

### 4. Run the app

```bash
streamlit run streamlit_app/app.py
```

## Deployment to Streamlit Cloud

1. Fork or push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Select repository and branch
5. Set main file path: `streamlit_app/app.py`
6. Add secrets in the dashboard:
   ```toml
   [api]
   DASHSCOPE_API_KEY = "your-actual-api-key"
   ```

## Command Line Usage

```bash
# Run network slicing simulation
python run_network_slicing.py --num_users 10 --region north --model qwen-plus-latest

# Options:
#   -n, --num_users: Number of users (default: 3)
#   -r, --region: north, south, center, test
#   -m, --model: qwen-flash, qwen-turbo-latest, qwen-plus-latest, qwen-max-latest
```

## Technology Stack

- **LangGraph**: Agent workflow orchestration
- **LangChain**: LLM integration
- **Qwen (DashScope)**: Large Language Model
- **Streamlit**: Web interface
- **Python**: Core implementation

## License

MIT License
