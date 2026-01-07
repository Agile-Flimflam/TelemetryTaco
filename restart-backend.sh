#!/bin/bash

# TelemetryTaco Backend Restart Script
# Restarts just the Django backend server

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔄 Restarting Django backend server...${NC}\n"

# Stop existing backend if running
if [ -f .backend.pid ]; then
    PID=$(cat .backend.pid)
    if kill -0 $PID 2>/dev/null; then
        echo -e "${YELLOW}   Stopping existing backend (PID: $PID)...${NC}"
        kill $PID
        sleep 1
        echo -e "${GREEN}✅ Stopped existing backend${NC}"
    fi
    rm .backend.pid
fi

# Start backend in background
echo -e "${YELLOW}   Starting new backend server...${NC}"
cd backend
poetry run python manage.py runserver > ../.backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../.backend.pid
cd ..

echo -e "${GREEN}✅ Backend restarted with PID: $BACKEND_PID${NC}"
echo -e "${YELLOW}   Logs: .backend.log${NC}\n"
