#!/bin/bash

# TelemetryTaco Development Startup Script
# This script starts all required services for local development

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🌮 Starting TelemetryTaco Development Environment${NC}\n"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Step 1: Start Docker services (database and Redis)
echo -e "${YELLOW}📦 Starting Docker services (PostgreSQL & Redis)...${NC}"
docker-compose up -d db redis

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}⏳ Waiting for PostgreSQL to be ready...${NC}"
timeout=30
counter=0
until docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; do
    sleep 1
    counter=$((counter + 1))
    if [ $counter -ge $timeout ]; then
        echo -e "${RED}❌ PostgreSQL failed to start within $timeout seconds${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ PostgreSQL is ready${NC}"

# Step 2: Check if backend .env exists
if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}⚠️  backend/.env not found. Creating from template...${NC}"
    
    # Generate a secure SECRET_KEY for development
    # Use Python to generate a Django-compatible secret key
    if command -v python3 &> /dev/null; then
        SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" 2>/dev/null || \
                     python3 -c "import secrets; print(secrets.token_urlsafe(50))")
    else
        # Fallback: generate a random string if Python is not available
        SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || date +%s | sha256sum | base64 | head -c 50)
    fi
    
    cat > backend/.env << EOF
DEBUG=True
SECRET_KEY=${SECRET_KEY}
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/telemetry_taco
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
EOF
    echo -e "${YELLOW}⚠️  Please update backend/.env with your actual database credentials if needed${NC}"
    echo -e "${YELLOW}   Check: docker-compose exec db env | grep POSTGRES${NC}\n"
fi

# Step 3: Install/update backend dependencies
echo -e "${YELLOW}📦 Installing backend dependencies...${NC}"
cd backend
if command -v poetry &> /dev/null; then
    # Check if poetry.lock exists, if not or if pyproject.toml is newer, install
    if [ ! -f "poetry.lock" ] || [ "pyproject.toml" -nt "poetry.lock" ]; then
        echo -e "${YELLOW}   Installing dependencies (this may take a moment)...${NC}"
        poetry install --no-interaction
    else
        # Just sync to ensure everything is installed
        poetry install --no-interaction --sync
    fi
else
    echo -e "${RED}❌ Poetry not found. Please install Poetry: https://python-poetry.org/docs/#installation${NC}"
    exit 1
fi
cd ..

# Step 4: Run migrations
echo -e "${YELLOW}🔄 Running database migrations...${NC}"
cd backend
poetry run python manage.py migrate --noinput
cd ..

# Step 5: Start services
echo -e "\n${GREEN}🚀 Starting development servers...${NC}\n"
echo -e "${YELLOW}📝 Note: This will start services in the background.${NC}"
echo -e "${YELLOW}   Use 'pnpm stop' or './stop.sh' to stop all services.${NC}\n"

# Get absolute path to project root for PID files
# This ensures consistency regardless of where the script is run from
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PID_FILE="${PROJECT_ROOT}/.backend.pid"
CELERY_PID_FILE="${PROJECT_ROOT}/.celery.pid"
BACKEND_LOG_FILE="${PROJECT_ROOT}/.backend.log"
CELERY_LOG_FILE="${PROJECT_ROOT}/.celery.log"

# Start backend in background
echo -e "${GREEN}▶️  Starting Django backend server...${NC}"
cd backend
poetry run python manage.py runserver > "${BACKEND_LOG_FILE}" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "${BACKEND_PID_FILE}"
cd ..

# Start Celery worker in background
echo -e "${GREEN}▶️  Starting Celery worker...${NC}"
cd backend
poetry run celery -A core worker --loglevel=info > "${CELERY_LOG_FILE}" 2>&1 &
CELERY_PID=$!
echo $CELERY_PID > "${CELERY_PID_FILE}"
cd ..

# Start frontend
echo -e "${GREEN}▶️  Starting frontend dev server...${NC}"
echo -e "${YELLOW}   Frontend will run in the foreground. Press Ctrl+C to stop.${NC}\n"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🛑 Stopping services...${NC}"
    # Use the same absolute paths defined above
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local backend_pid_file="${project_root}/.backend.pid"
    local celery_pid_file="${project_root}/.celery.pid"
    
    if [ -f "${backend_pid_file}" ]; then
        kill $(cat "${backend_pid_file}") 2>/dev/null || true
        rm -f "${backend_pid_file}"
    fi
    if [ -f "${celery_pid_file}" ]; then
        kill $(cat "${celery_pid_file}") 2>/dev/null || true
        rm -f "${celery_pid_file}"
    fi
    echo -e "${GREEN}✅ Services stopped${NC}"
}

trap cleanup EXIT INT TERM

# Start frontend (foreground)
cd frontend
pnpm dev
