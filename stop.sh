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
# Args: PID file path, process name for logging, command pattern to verify, optional process name pattern
# This function performs multiple validations to ensure we're killing the correct process:
# 1. Checks if PID file exists
# 2. Verifies the process exists (kill -0)
# 3. Validates the full command line matches the expected pattern
# 4. Optionally checks the process name (comm field) if provided
verify_and_kill() {
    local pid_file=$1
    local process_name=$2
    local command_pattern=$3
    local process_name_pattern=${4:-""}  # Optional: expected process name (e.g., "python", "celery")
    
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
    
    # Get process information for validation
    # Use multiple ps fields to verify the process
    local process_cmd=$(ps -p "$pid" -o command= 2>/dev/null || echo "")
    local process_comm=$(ps -p "$pid" -o comm= 2>/dev/null || echo "")
    
    if [ -z "$process_cmd" ]; then
        # Process doesn't exist (race condition - died between kill -0 and ps)
        rm -f "$pid_file"
        return 0
    fi
    
    # Validation 1: Check if command matches expected pattern
    local cmd_matches=false
    if echo "$process_cmd" | grep -q "$command_pattern"; then
        cmd_matches=true
    fi
    
    # Validation 2: If process name pattern provided, verify it matches
    local name_matches=true
    if [ -n "$process_name_pattern" ]; then
        if ! echo "$process_comm" | grep -qiE "$process_name_pattern"; then
            name_matches=false
        fi
    fi
    
    # Only kill if both validations pass
    if [ "$cmd_matches" = true ] && [ "$name_matches" = true ]; then
        # Send termination signal
        # We've validated the process matches our expectations, so it's safe to kill
        if kill "$pid" 2>/dev/null; then
            echo -e "${GREEN}✅ Stopped $process_name (PID: $pid)${NC}"
        else
            echo -e "${YELLOW}⚠️  Failed to stop $process_name (PID: $pid) - process may have already exited${NC}"
        fi
    else
        echo -e "${RED}⚠️  PID $pid exists but doesn't match expected $process_name process. Skipping for safety.${NC}"
        if [ "$cmd_matches" = false ]; then
            echo -e "${YELLOW}   Command mismatch. Expected pattern: $command_pattern${NC}"
        fi
        if [ "$name_matches" = false ] && [ -n "$process_name_pattern" ]; then
            echo -e "${YELLOW}   Process name mismatch. Expected: $process_name_pattern, Found: $process_comm${NC}"
        fi
        echo -e "${YELLOW}   Actual command: ${process_cmd:0:100}${NC}"
        echo -e "${YELLOW}   This PID may have been reused by another process. Manual cleanup may be needed.${NC}"
    fi
    
    rm -f "$pid_file"
}

# Stop backend
# Verify it's a Python process running manage.py runserver
verify_and_kill .backend.pid "Django backend" "manage.py runserver" "python"

# Stop Celery
# Verify it's a Python/Celery process running celery worker
verify_and_kill .celery.pid "Celery worker" "celery.*worker" "(python|celery)"

# Stop Docker services (optional - comment out if you want to keep them running)
read -p "Stop Docker services (db, redis)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose stop db redis
    echo -e "${GREEN}✅ Stopped Docker services${NC}"
fi

echo -e "\n${GREEN}✅ All services stopped${NC}"
