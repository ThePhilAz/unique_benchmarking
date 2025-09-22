#!/bin/bash
# Launch Django backend and Streamlit frontend in tmux

SESSION_NAME="unique_benchmarking"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo -e "${RED}❌ tmux not found. Install with: brew install tmux${NC}"
    exit 1
fi

# Handle existing session
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Session '$SESSION_NAME' already exists${NC}"
    read -p "Kill existing session? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        tmux kill-session -t "$SESSION_NAME"
    else
        echo -e "${BLUE}Attaching to existing session...${NC}"
        tmux attach-session -t "$SESSION_NAME"
        exit 0
    fi
fi

# Check directories
DJANGO_DIR="$SCRIPT_DIR/unique_benchmarking/experiments"
FRONTEND_DIR="$SCRIPT_DIR/unique_benchmarking/frontend"

if [[ ! -f "$DJANGO_DIR/manage.py" ]]; then
    echo -e "${RED}❌ Django manage.py not found: $DJANGO_DIR${NC}"
    exit 1
fi

if [[ ! -f "$FRONTEND_DIR/main.py" ]]; then
    echo -e "${RED}❌ Frontend main.py not found: $FRONTEND_DIR${NC}"
    exit 1
fi

# Use virtual environment if available
PYTHON_CMD="python"
if [[ -f "$SCRIPT_DIR/.venv/bin/python" ]]; then
    PYTHON_CMD="$SCRIPT_DIR/.venv/bin/python"
fi

echo -e "${BLUE}🚀 Starting services in tmux session: $SESSION_NAME${NC}"

# Create session with Django window
tmux new-session -d -s "$SESSION_NAME" -n "django" -c "$DJANGO_DIR"
tmux send-keys -t "$SESSION_NAME:django" "$PYTHON_CMD manage.py runserver 127.0.0.1:8000" Enter

# Create Streamlit window
tmux new-window -t "$SESSION_NAME" -n "streamlit" -c "$FRONTEND_DIR"
tmux send-keys -t "$SESSION_NAME:streamlit" "sleep 3 && $PYTHON_CMD -m streamlit run main.py --server.port 8501" Enter

# Select Django window
tmux select-window -t "$SESSION_NAME:django"

echo ""
echo -e "${GREEN}✅ Services started!${NC}"
echo -e "${BLUE}📍 URLs:${NC}"
echo "   Django:    http://127.0.0.1:8000"
echo "   Streamlit: http://localhost:8501"
echo ""
echo -e "${BLUE}🎮 Controls:${NC}"
echo "   Switch: Ctrl+b then 0 (Django) or 1 (Streamlit)"
echo "   Detach: Ctrl+b then d"
echo "   Stop:   Ctrl+C in each window"
echo ""

# Attach to session
tmux attach-session -t "$SESSION_NAME"
