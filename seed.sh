#!/bin/bash

# TelemetryTaco Database Seeding Script
# Seeds the database with realistic historical event data

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🌮 Seeding TelemetryTaco Database${NC}\n"

# Check if we're in the project root
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}❌ Error: This script must be run from the project root directory${NC}"
    exit 1
fi

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}❌ Poetry not found. Please install Poetry: https://python-poetry.org/docs/#installation${NC}"
    exit 1
fi

# Check if backend dependencies are installed
if [ ! -d "backend/.venv" ] && [ ! -f "backend/poetry.lock" ]; then
    echo -e "${YELLOW}⚠️  Backend dependencies not installed. Installing...${NC}"
    cd backend
    poetry install --no-interaction
    cd ..
fi

# Check if database is accessible (optional check)
if command -v docker-compose &> /dev/null; then
    if docker-compose ps db 2>/dev/null | grep -q "Up"; then
        echo -e "${GREEN}✅ Database service is running${NC}\n"
    else
        echo -e "${YELLOW}⚠️  Database service may not be running. Make sure to start services with 'make services' or './start.sh'${NC}\n"
    fi
fi

# Run the seed command with all passed arguments
echo -e "${YELLOW}📊 Running seed_events command...${NC}"
cd backend
poetry run python manage.py seed_events "$@"
cd ..

echo -e "\n${GREEN}✅ Database seeding completed${NC}"
