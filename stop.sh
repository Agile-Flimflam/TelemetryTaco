#!/bin/bash

# TelemetryTaco Development Stop Script
# Stops all running development services

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🛑 Stopping TelemetryTaco services...${NC}\n"

# Function to verify and kill a process by PID and expected command pattern
# Args: PID file path, process name for logging, command pattern to verify
verify_and_kill() {
    local pid_file=$1
    local process_name=$2
    local command_pattern=$3
    
    if [ ! -f "$pid_file" ]; then
        return 0
    fi
    
    local pid=$(cat "$pid_file")
    
    # Check if process exists
    if ! kill -0 "$pid" 2>/dev/null; then
        rm -f "$pid_file"
        return 0
    fi
    
    # Verify the process command matches expected pattern
    # Use ps to get the full command line and check if it matches
    local process_cmd=$(ps -p "$pid" -o command= 2>/dev/null || echo "")
    
    if [ -z "$process_cmd" ]; then
        # Process doesn't exist (race condition)
        rm -f "$pid_file"
        return 0
    fi
    
    # Check if command matches expected pattern
    if echo "$process_cmd" | grep -q "$command_pattern"; then
        kill "$pid" 2>/dev/null || true
        echo -e "${GREEN}✅ Stopped $process_name (PID: $pid)${NC}"
    else
        echo -e "${YELLOW}⚠️  PID $pid exists but doesn't match expected $process_name process. Skipping.${NC}"
        echo -e "${YELLOW}   Found: ${process_cmd:0:80}${NC}"
    fi
    
    rm -f "$pid_file"
}

# Stop backend
verify_and_kill .backend.pid "Django backend" "manage.py runserver"

# Stop Celery
verify_and_kill .celery.pid "Celery worker" "celery.*worker"

# Stop Docker services (optional - comment out if you want to keep them running)
read -p "Stop Docker services (db, redis)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose stop db redis
    echo -e "${GREEN}✅ Stopped Docker services${NC}"
fi

echo -e "\n${GREEN}✅ All services stopped${NC}"
