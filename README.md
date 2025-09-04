# Unique Benchmarking Tool

A comprehensive benchmarking application for testing and comparing AI assistant performance using the Unique SDK. This tool provides a Streamlit web interface for running experiments, analyzing results, and comparing assistant capabilities across multiple test scenarios.

## 🚀 Features

### Core Functionality
- **Multi-Assistant Testing**: Test multiple AI assistants simultaneously
- **Batch Question Processing**: Run multiple questions against each assistant
- **Real-time Progress Tracking**: Monitor experiment progress with live updates
- **Comprehensive Metrics**: Track response times, tool usage, search operations, and success rates
- **Interactive Visualizations**: Analyze results with charts, graphs, and detailed breakdowns
- **Experiment Management**: Organize and persist experiment results with timestamped directories

### User Interface
- **Modern Web Interface**: Clean, responsive Streamlit-based UI
- **Tab-based Navigation**: Organized workflow with Configuration, Experiments, and Explorer tabs
- **Real-time Updates**: Live progress indicators and status updates during experiments
- **Export Capabilities**: Download results as JSON for further analysis
- **Historical Analysis**: Browse and compare past experiment results

### Technical Capabilities
- **Unique SDK Integration**: Built on top of `unique-sdk` and `unique-toolkit`
- **Asynchronous Processing**: Efficient concurrent execution of multiple tests
- **Structured Data Models**: Pydantic-based data validation and serialization
- **Error Handling**: Comprehensive error tracking and recovery
- **Detailed Logging**: Full debug information and performance metrics

## 📋 Requirements

- Python 3.12+
- Poetry (recommended) or pip for dependency management
- Access to Unique AI platform with valid API credentials

## 🛠️ Installation

### Using Poetry (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd unique_benchmarking
```

2. Install dependencies with Poetry:
```bash
poetry install
```

3. Activate the virtual environment:
```bash
poetry shell
```

### Using pip

1. Clone the repository:
```bash
git clone <repository-url>
cd unique_benchmarking
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## 🚀 Usage

### Starting the Application

#### Using Poetry Script
```bash
poetry run start
```

#### Using Streamlit Directly
```bash
streamlit run unique_benchmarking/app.py
```

#### Using Python Module
```bash
python -m unique_benchmarking.cli
```

### Web Interface Workflow

1. **Open your browser** to `http://localhost:8501`

2. **Configure Settings** (Configuration Tab):
   - Enter your User ID
   - Provide Company ID
   - Set App ID
   - Input your API Key
   - Save configuration for the session

3. **Set Up Experiments** (Experiments Tab):
   - Add assistant IDs (one per line)
   - Input test questions (one per line)
   - Configure experiment settings
   - Start the experiment run

4. **Analyze Results** (Explorer Tab):
   - Browse completed experiments
   - View detailed performance metrics
   - Compare assistant responses
   - Export results for further analysis

## 📁 Project Structure

```
unique_benchmarking/
├── unique_benchmarking/           # Main application package
│   ├── __init__.py
│   ├── app.py                     # Streamlit application entry point
│   ├── cli.py                     # Command-line interface
│   ├── config.py                  # Configuration management
│   ├── experiment_executor.py     # Core experiment execution logic
│   ├── utils.py                   # Utility functions
│   ├── markdown_template.j2       # Jinja2 template for reports
│   └── components/                # UI components
│       ├── __init__.py
│       ├── main_content.py        # Configuration tab content
│       ├── sidebar.py             # Sidebar navigation
│       ├── experiment_runner.py   # Experiment execution UI
│       └── experiment_explorer.py # Results analysis UI
├── experiments/                   # Generated experiment results
│   └── experiment_YYYYMMDD_HHMMSS/
│       ├── experiment_config.json
│       ├── experiment_summary.json
│       ├── success/               # Successful test results
│       └── error/                 # Failed test results
├── pyproject.toml                 # Poetry configuration
├── poetry.lock                    # Locked dependencies
└── README.md                      # This file
```

## 📊 Results Format

Each experiment generates structured results with the following information:

### Experiment Summary
```json
{
  "total_tests": 10,
  "successful_tests": 8,
  "failed_tests": 2,
  "success_rate": 0.8,
  "total_duration": 120.5,
  "average_response_time": 12.05,
  "experiment_directory": "experiments/experiment_20250904_192132"
}
```

### Individual Test Results
```json
{
  "test_id": "unique_test_identifier",
  "assistant_id": "assistant_abc123",
  "question": "What is the capital of France?",
  "message": "The capital of France is Paris...",
  "assessment": "CORRECT",
  "response_time": 3.2,
  "debug_info": {
    "num_searches": 2,
    "total_time": 3.1,
    "search_time": 1.5,
    "clean_time": 0.3,
    "crawl_time": 1.3,
    "gpt_requests": 1
  },
  "timestamp": "2025-01-04T19:21:32Z",
  "status": "success"
}
```

## ⚙️ Configuration

### Required Settings
- **User ID**: Your unique user identifier in the Unique platform
- **Company ID**: Your organization's identifier
- **App ID**: The application identifier for your use case
- **API Key**: Authentication key for API access

### Optional Settings
- **Max Wait Time**: Maximum time to wait for assistant responses (default: 60 seconds)
- **Concurrent Tests**: Number of simultaneous tests to run (default: 5)

## 🔧 Development

### Code Quality
The project uses Ruff for linting and code formatting:

```bash
# Run linting
poetry run ruff check .

# Fix auto-fixable issues
poetry run ruff check . --fix

# Format code
poetry run ruff format .
```

### Data Models
The application uses Pydantic for data validation and serialization:
- `ExperimentConfig`: Experiment configuration and settings
- `TestResult`: Individual test execution results
- `ExperimentSummary`: Aggregated experiment statistics
- `DebugInfo`: Detailed performance and tool usage metrics

## 🐛 Error Handling

The application includes comprehensive error handling for:
- **Network Issues**: Timeout handling and retry logic
- **API Errors**: Authentication and rate limiting
- **Invalid Configurations**: Missing or malformed settings
- **Assistant Failures**: Individual test failures don't stop the entire experiment
- **Data Validation**: Pydantic model validation for all data structures

## 📈 Performance Metrics

The tool tracks detailed performance metrics:
- **Response Times**: End-to-end assistant response times
- **Tool Usage**: Search operations, web crawling, and API calls
- **Success Rates**: Percentage of successful vs. failed tests
- **Resource Utilization**: Time breakdown by operation type
- **Quality Assessments**: Automated evaluation of response quality

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`poetry run ruff check .`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
1. Check the experiment logs in the `experiments/` directory
2. Review the Streamlit console output for error messages
3. Ensure your API credentials are valid and have appropriate permissions
4. Verify network connectivity to the Unique AI platform

## 🔄 Version History

- **v0.1.0**: Initial release with core benchmarking functionality
  - Multi-assistant testing
  - Streamlit web interface
  - Experiment management and results analysis
  - Unique SDK integration