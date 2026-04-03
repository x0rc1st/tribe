#!/bin/bash
# Start the HTB Brain service
# Usage: bash /workspace/tribe/start.sh

set -e

cd /workspace/tribe

# Load HF token
if [ -f /root/.cache/huggingface/token ]; then
    export HF_TOKEN=$(cat /root/.cache/huggingface/token)
fi

export PYTHONPATH=/workspace/tribe/src

# Kill any existing uvicorn
kill $(pgrep -f "uvicorn htb_brain") 2>/dev/null || true
sleep 1

echo "Starting HTB Brain service on port 8000..."
nohup python3 -m uvicorn htb_brain.api.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    > /workspace/tribe/server.log 2>&1 &

echo "PID: $!"
echo "Logs: tail -f /workspace/tribe/server.log"
echo ""
echo "Waiting for startup..."
sleep 10

if curl -s http://localhost:8000/health | grep -q "model_loaded"; then
    echo "Server is UP and healthy!"
    curl -s http://localhost:8000/health | python3 -m json.tool
else
    echo "Server may still be loading. Check: tail -f /workspace/tribe/server.log"
fi
