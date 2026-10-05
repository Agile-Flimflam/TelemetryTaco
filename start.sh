#!/bin/bash

# TelemetryTaco Development Startup Script
# This script starts all required services for local development

# Use set -e for strict error handling, but we'll handle expected failures explicitly
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
POETRY_CACHE_DIR="${POETRY_CACHE_DIR:-/tmp/pypoetry-cache}"

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
# docker-compose exec may fail if container isn't ready yet, so disable set -e for this loop
set +e
until docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; do
    sleep 1
    counter=$((counter + 1))
    if [ $counter -ge $timeout ]; then
        echo -e "${RED}❌ PostgreSQL failed to start within $timeout seconds${NC}"
        set -e  # Re-enable set -e before exiting
        exit 1
    fi
done
set -e  # Re-enable set -e after the loop
echo -e "${GREEN}✅ PostgreSQL is ready${NC}"

# Step 2: Check if backend .env exists
if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}⚠️  backend/.env not found. Creating from template...${NC}"
    
    # Generate a secure SECRET_KEY for development
    # Use Python to generate a Django-compatible secret key, or openssl as fallback
    SECRET_KEY=""
    if command -v python3 &> /dev/null; then
        SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" 2>/dev/null || \
                     python3 -c "import secrets; print(secrets.token_urlsafe(50))" 2>/dev/null || true)
    fi
    
    # If Python failed or is not available, try openssl
    if [ -z "$SECRET_KEY" ] && command -v openssl &> /dev/null; then
        SECRET_KEY=$(openssl rand -base64 50 | tr -d '\n' | head -c 50)
    fi
    
    # If both methods failed, exit with an error
    if [ -z "$SECRET_KEY" ]; then
        echo -e "${RED}❌ Cannot generate SECRET_KEY: Python3 or OpenSSL is required${NC}"
        echo -e "${YELLOW}   Please install Python3 or OpenSSL and try again${NC}"
        exit 1
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
        POETRY_CACHE_DIR="${POETRY_CACHE_DIR}" poetry install --no-interaction
    else
        # Just sync to ensure everything is installed
        POETRY_CACHE_DIR="${POETRY_CACHE_DIR}" poetry install --no-interaction --sync
    fi
else
    echo -e "${RED}❌ Poetry not found. Please install Poetry: https://python-poetry.org/docs/#installation${NC}"
    exit 1
fi
cd ..

# Step 4: Run migrations
echo -e "${YELLOW}🔄 Running database migrations...${NC}"
cd backend
# --fake-initial adopts the existing core_event table in databases created before the
# core -> events app rename; on a new database it migrates normally.
POETRY_CACHE_DIR="${POETRY_CACHE_DIR}" poetry run python manage.py migrate --noinput --fake-initial
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
POETRY_CACHE_DIR="${POETRY_CACHE_DIR}" poetry run python manage.py runserver > "${BACKEND_LOG_FILE}" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "${BACKEND_PID_FILE}"
cd ..

# Django logs to a file, so a crash at startup is otherwise invisible behind the
# frontend's proxy errors. Wait for it to answer, and show the log if it doesn't.
echo -e "${YELLOW}⏳ Waiting for the backend on http://localhost:8000...${NC}"
backend_ready=false
for _ in $(seq 1 30); do
    if curl -s -o /dev/null --max-time 2 "http://localhost:8000/api/health/live"; then
        backend_ready=true
        break
    fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        break
    fi
    sleep 1
done
if [ "$backend_ready" != true ]; then
    echo -e "${RED}❌ The backend didn't start. Last lines of ${BACKEND_LOG_FILE}:${NC}"
    tail -n 30 "${BACKEND_LOG_FILE}"
    kill "$BACKEND_PID" 2>/dev/null || true
    rm -f "${BACKEND_PID_FILE}"
    exit 1
fi
echo -e "${GREEN}✅ Backend is up${NC}"

# Start Celery worker in background
echo -e "${GREEN}▶️  Starting Celery worker...${NC}"
cd backend
POETRY_CACHE_DIR="${POETRY_CACHE_DIR}" poetry run celery -A config worker -B --loglevel=info > "${CELERY_LOG_FILE}" 2>&1 &
CELERY_PID=$!
echo $CELERY_PID > "${CELERY_PID_FILE}"
cd ..

# Start frontend
echo -e "${GREEN}▶️  Starting frontend dev server...${NC}"
echo -e "${YELLOW}   Frontend will run in the foreground. Press Ctrl+C to stop.${NC}\n"

# Helper function to safely kill a process by PID file with validation
# Args: PID file path, process name for logging, command pattern to verify, process name pattern
safe_kill_process() {
    local pid_file=$1
    local process_name=$2
    local command_pattern=$3
    local process_name_pattern=$4
    
    if [ ! -f "$pid_file" ]; then
        return 0
    fi
    
    local pid=$(cat "$pid_file")
    
    # Validate PID is numeric
    if ! [[ "$pid" =~ ^[0-9]+$ ]]; then
        echo -e "${YELLOW}⚠️  Invalid PID in $pid_file: $pid${NC}"
        rm -f "$pid_file"
        return 1
    fi
    
    # Check if process exists
    if ! kill -0 "$pid" 2>/dev/null; then
        # Process doesn't exist, clean up PID file
        rm -f "$pid_file"
        return 0
    fi
    
    # Validate the process matches expected pattern before killing
    local process_cmd=$(ps -p "$pid" -o command= 2>/dev/null || echo "")
    local process_comm=$(ps -p "$pid" -o comm= 2>/dev/null || echo "")
    
    if [ -z "$process_cmd" ]; then
        # Process doesn't exist (race condition)
        rm -f "$pid_file"
        return 0
    fi
    
    # Verify command and process name match expected patterns
    local cmd_matches=false
    local name_matches=false
    
    if echo "$process_cmd" | grep -q "$command_pattern"; then
        cmd_matches=true
    fi
    
    if [ -n "$process_name_pattern" ]; then
        if echo "$process_comm" | grep -qiE "$process_name_pattern"; then
            name_matches=true
        fi
    else
        name_matches=true  # If no pattern specified, consider it a match
    fi
    
    # Only kill if validations pass
    if [ "$cmd_matches" = true ] && [ "$name_matches" = true ]; then
        if kill "$pid" 2>/dev/null; then
            echo -e "${GREEN}✅ Stopped $process_name (PID: $pid)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  PID $pid doesn't match expected $process_name process. Skipping for safety.${NC}"
    fi
    
    rm -f "$pid_file"
}

# Function to cleanup on exit
# Uses variables from outer scope (PROJECT_ROOT, BACKEND_PID_FILE, CELERY_PID_FILE)
cleanup() {
    echo -e "\n${YELLOW}🛑 Stopping services...${NC}"
    
    # Use the variables already defined in outer scope (lines 111-113)
    # This avoids duplication and ensures consistency
    safe_kill_process "${BACKEND_PID_FILE}" "Django backend" "manage.py runserver" "python"
    safe_kill_process "${CELERY_PID_FILE}" "Celery worker" "celery.*worker" "(python|celery)"
    
    echo -e "${GREEN}✅ Services stopped${NC}"
}

trap cleanup EXIT INT TERM

# Start frontend (foreground)
cd frontend
pnpm dev
