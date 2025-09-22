# Unique Benchmarking

A practical tool for evaluating AI assistants by running them against a dataset of questions and comparing their responses.

## What It Does

**Core Features:**
- **Batch Evaluation**: Test multiple AI assistants against a dataset of questions simultaneously
- **Golden Answer Generation**: Uses OpenAI to generate reference answers for comparison and review
- **HTML Report Generation**: Creates comprehensive HTML reports to easily review and compare assistant performance
- **Streamlit Dashboard**: Interactive web interface for setting up experiments and monitoring progress
- **Django Backend**: Robust API for managing experiments, storing results, and handling data

## How It Works

1. **Upload or create a dataset** of questions you want to test
2. **Select AI assistants** to evaluate (from Unique.app platform)
3. **Run the experiment** - the system will:
   - Send each question to all selected assistants
   - Generate golden answers using OpenAI for reference
   - Collect and store all responses
4. **Review results** in the generated HTML report with side-by-side comparisons
5. **Analyze performance** using the interactive dashboard

## Use Cases

- **Model Selection**: Compare different AI assistants to choose the best one for your use case
- **Quality Assurance**: Regularly test AI assistant performance against known question sets
- **Research**: Academic evaluation of AI capabilities across different domains
- **Benchmarking**: Establish performance baselines and track improvements over time

## Setup Instructions

### 1. Install Dependencies

```bash
# Install tmux (macOS)
brew install tmux

# Install Python dependencies
poetry install
# OR
pip install django djangorestframework django-cors-headers streamlit openai
```

### 2. Configure API Credentials (Optional)

You can optionally create a `unique.env` file with your API credentials for quick setup:
```bash
USER_ID=your_unique_user_id
COMPANY_ID=your_company_id
APP_ID=your_app_id
API_KEY=your_unique_api_key
BASE_URL=https://api.uat1.unique.app/public/chat
TIMEOUT=600
```

**Note**: Configuration is done through the web interface - this file is just for convenience.

### 3. Initialize Database

```bash
./setup.sh
```

This will:
- Create database tables
- Run migrations
- Optionally create an admin user

### 4. Run the Application

```bash
./run.sh
```

This starts both services in a tmux session:
- **Django Backend**: http://127.0.0.1:8000
- **Streamlit Frontend**: http://localhost:8501

## Using the Application

### Quick Start
1. Open http://localhost:8501 in your browser
2. **Configure API credentials in the sidebar**:
   - Click "Load from ENV" if you created a `unique.env` file
   - Or click "Manual Setup" to enter credentials directly
   - Required: User ID, Company ID, App ID, API Key
   - Optional: Custom base URL, timeout, golden answer model
3. Create a new experiment:
   - Upload your question dataset or enter questions manually
   - Select which AI assistants to test
   - Configure evaluation settings
4. Run the experiment and monitor progress
5. Download the HTML report when complete

### Configuration Details

The system stores all configuration in the Django backend database. You have two options:

**Option 1: Load from Environment File**
- Create `unique.env` with your credentials (see setup instructions)
- Click "📁 Load from ENV" in the sidebar
- System will automatically import and save your settings

**Option 2: Manual Configuration**
- Click "✏️ Manual Setup" in the sidebar
- Enter your Unique.app credentials:
  - **User ID**: Your unique.app user ID (e.g., 335xxxxxx)
  - **Company ID**: Your company ID (e.g., 331xxxxx)  
  - **App ID**: Application ID (e.g., app_m5axxxxxxxx)
  - **API Key**: Your unique.app API key (starts with ukey_xxxxxx)
- Advanced settings:
  - **Base URL**: API endpoint (default: https://api.uat1.unique.app/public/chat)
  - **Timeout**: Request timeout in seconds (default: 600)
  - **Golden Model**: Model for generating reference answers (default: litellm:gpt-5)

### Tmux Controls
- **Switch between services**: `Ctrl+b` then `0` (Django) or `1` (Streamlit)
- **Detach session**: `Ctrl+b` then `d` (keeps running in background)
- **Reattach later**: `tmux attach-session -t unique_benchmarking`
- **Stop everything**: `Ctrl+C` in each window

## Project Structure

```
unique_benchmarking/
├── setup.sh                    # Database setup script
├── run.sh                      # Start both services
├── unique_benchmarking/
│   ├── experiments/            # Django backend
│   │   ├── manage.py
│   │   └── eval_assistants/    # Main app with models and API
│   └── frontend/               # Streamlit interface
│       ├── main.py
│       └── components/         # UI components
└── templates/                  # HTML report templates
```

## Troubleshooting

**Services won't start?**
- Check that virtual environment is activated
- Run `./setup.sh` to ensure database is initialized
- Verify all API credentials are configured

**Can't access the web interface?**
- Ensure ports 8000 and 8501 are not in use
- Check that both Django and Streamlit are running in tmux

**Experiment fails?**
- Verify API credentials are correct and have sufficient quota
- Check the Django logs (tmux window 0) for detailed error messages

## API Endpoints

- **Experiments**: `GET/POST /api/experiments/`
- **Results**: `GET /api/experiments/{id}/results/`
- **Reports**: `GET /api/experiments/{id}/report/`
- **Admin Interface**: http://127.0.0.1:8000/admin/

---

**Ready to start?** Run `./setup.sh` then `./run.sh`
