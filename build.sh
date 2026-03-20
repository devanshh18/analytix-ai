#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "===================================="
echo "    Analytix AI - Render Build      "
echo "===================================="

# 1. Build the frontend (Node environment required)
echo ">>> Building React Frontend..."
cd frontend
npm install
npm run build
cd ..

# 2. Install backend dependencies (Python environment required)
echo ">>> Installing Python Backend Dependencies..."
cd backend
pip install -U pip
pip install -r requirements.txt
cd ..

echo ">>> Build Complete!"
