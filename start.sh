#!/bin/bash
# Start the HTB Brain service (cortical + subcortical)
# Usage: bash /workspace/tribe/start.sh

set -e

cd /workspace/tribe

# Load HF token
if [ -f /root/.cache/huggingface/token ]; then
    export HF_TOKEN=$(cat /root/.cache/huggingface/token)
fi

export PYTHONPATH=/workspace/tribe/src:/workspace/tribev2

# Subcortical model (auto-detect if checkpoint exists)
if [ -f /workspace/tribe/subcortical_training/results/best.ckpt ]; then
    export HTB_BRAIN_SUBCORTICAL_CHECKPOINT_DIR=/workspace/tribe/subcortical_training/results
    echo "Subcortical model: ENABLED"
fi
if [ -f /workspace/tribe/src/htb_brain/static/brain_mesh_combined.json ]; then
    export HTB_BRAIN_SUBCORTICAL_MESH_META=/workspace/tribe/src/htb_brain/static/brain_mesh_combined.json
fi

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
echo "Waiting for startup (loading both cortical + subcortical models)..."
sleep 30

if curl -s http://localhost:8000/health | grep -q "model_loaded"; then
    echo "Server is UP!"
    curl -s http://localhost:8000/health | python3 -m json.tool
else
    echo "Server may still be loading. Check: tail -f /workspace/tribe/server.log"
fi
