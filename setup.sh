#!/bin/bash
# Setup script for Django backend - handles migrations and initial setup

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DJANGO_DIR="$SCRIPT_DIR/unique_benchmarking/experiments"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔧 Setting up Django backend...${NC}"
echo ""

# Check if Django directory exists
if [[ ! -f "$DJANGO_DIR/manage.py" ]]; then
    echo -e "${RED}❌ Django manage.py not found: $DJANGO_DIR${NC}"
    exit 1
fi

# Use virtual environment if available
PYTHON_CMD="python"
if [[ -f "$SCRIPT_DIR/.venv/bin/python" ]]; then
    PYTHON_CMD="$SCRIPT_DIR/.venv/bin/python"
    echo -e "${GREEN}🐍 Using virtual environment: $PYTHON_CMD${NC}"
else
    echo -e "${YELLOW}⚠️  Using system Python: $PYTHON_CMD${NC}"
fi

# Change to Django directory
cd "$DJANGO_DIR"

echo -e "${BLUE}📊 Creating database migrations...${NC}"
$PYTHON_CMD manage.py makemigrations
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to create migrations${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}🗄️  Running database migrations...${NC}"
$PYTHON_CMD manage.py migrate
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to run migrations${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}📦 Collecting static files...${NC}"
$PYTHON_CMD manage.py collectstatic --noinput --clear
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Static files collected successfully${NC}"
else
    echo -e "${YELLOW}⚠️  Static files collection failed (continuing anyway)${NC}"
fi

echo ""
echo -e "${BLUE}🔍 Checking for existing superuser...${NC}"
SUPERUSER_EXISTS=$($PYTHON_CMD manage.py shell -c "from django.contrib.auth.models import User; print(User.objects.filter(is_superuser=True).exists())" 2>/dev/null)

if [[ "$SUPERUSER_EXISTS" == "False" ]]; then
    echo -e "${YELLOW}👤 No superuser found. Create one for Django admin access?${NC}"
    read -p "Create superuser? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Creating superuser...${NC}"
        $PYTHON_CMD manage.py createsuperuser
    fi
else
    echo -e "${GREEN}✅ Superuser already exists${NC}"
fi

echo ""
echo -e "${GREEN}✅ Django backend setup complete!${NC}"
echo ""
echo -e "${BLUE}📍 Available endpoints:${NC}"
echo "   Admin:        http://127.0.0.1:8000/admin/"
echo "   API:          http://127.0.0.1:8000/api/"
echo "   Experiments:  http://127.0.0.1:8000/api/experiments/"
echo ""
echo -e "${BLUE}🚀 Ready to run:${NC} ./run.sh"
