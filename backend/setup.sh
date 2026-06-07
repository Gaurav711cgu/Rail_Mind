#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "===================================================="
# No emoji style as requested by the PRD constraints
echo "         RAILMIND BACKEND ENGINE SETUP              "
echo "===================================================="

# Navigate to script directory
cd "$(dirname "$0")"

# 1. Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment (.venv)..."
    python3 -m venv .venv
else
    echo "Virtual environment (.venv) already exists."
fi

# 2. Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# 3. Upgrade pip and install dependencies
echo "Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Seed SQLite database
echo "Initializing and seeding SQLite database..."
python scripts/seed_railway_graph.py

# 5. Run verification tests
echo "Running backend integrity verification suite..."
python scripts/verify_backend.py

echo "===================================================="
echo "      RAILMIND BACKEND SETUP COMPLETED SUCCESSFULLY!"
echo "===================================================="
echo "To activate the virtual environment manually, run:"
echo "    source .venv/bin/activate"
echo ""
echo "To run the FastAPI server, run:"
echo "    uvicorn app.main:app --reload --port 8000"
echo "===================================================="
