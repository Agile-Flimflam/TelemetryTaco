#!/bin/bash

# TelemetryTaco Development Stop Script
# Stops all running development services

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🛑 Stopping TelemetryTaco services...${NC}\n"

# Stop backend
if [ -f .backend.pid ]; then
    PID=$(cat .backend.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo -e "${GREEN}✅ Stopped Django backend (PID: $PID)${NC}"
    fi
    rm .backend.pid
fi

# Stop Celery
if [ -f .celery.pid ]; then
    PID=$(cat .celery.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo -e "${GREEN}✅ Stopped Celery worker (PID: $PID)${NC}"
    fi
    rm .celery.pid
fi

# Stop Docker services (optional - comment out if you want to keep them running)
read -p "Stop Docker services (db, redis)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose stop db redis
    echo -e "${GREEN}✅ Stopped Docker services${NC}"
fi

echo -e "\n${GREEN}✅ All services stopped${NC}"
