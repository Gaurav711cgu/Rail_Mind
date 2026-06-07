#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "===================================================="
echo "         RAILMIND SYSTEM SETUP ORCHESTRATOR         "
echo "===================================================="

# Navigate to orchestrator script directory
PROJECT_ROOT="$(dirname "$0")"
cd "$PROJECT_ROOT"

# 1. Build and verify Backend
echo ""
echo ">>> [Phase 1: Setting up FastAPI Backend] <<<"
chmod +x backend/setup.sh
./backend/setup.sh

# 2. Build and verify Frontend
echo ""
echo ">>> [Phase 2: Setting up Vite React Frontend] <<<"
cd frontend
echo "Installing node modules..."
npm install
echo "Running Vite production build test..."
npm run build
cd ..

echo ""
echo "===================================================="
echo "    RAILMIND SYSTEM ORCHESTRATION COMPLETED!        "
echo "===================================================="
echo "To run the system in development mode:"
echo ""
echo "1. Start the backend API server:"
echo "    cd backend"
echo "    source .venv/bin/activate"
echo "    uvicorn app.main:app --reload --port 8000"
echo ""
echo "2. Start the frontend development server:"
echo "    cd frontend"
echo "    npm run dev"
echo ""
echo "The frontend will automatically proxy /api calls to the backend."
echo "===================================================="
