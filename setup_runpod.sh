#!/bin/bash
# HTB Brain Engagement Service — RunPod setup script
# Run this after a pod restart to get everything back up.
#
# Usage:
#   bash /workspace/tribe/setup_runpod.sh [HF_TOKEN]
#
# If HF_TOKEN is not passed as argument, it reads from /root/.cache/huggingface/token

set -e

echo "=== HTB Brain — RunPod Setup ==="

HF_TOKEN="${1:-}"
if [ -z "$HF_TOKEN" ] && [ -f /root/.cache/huggingface/token ]; then
    HF_TOKEN=$(cat /root/.cache/huggingface/token)
fi

if [ -z "$HF_TOKEN" ]; then
    echo "ERROR: No HuggingFace token. Pass as argument or write to /root/.cache/huggingface/token"
    exit 1
fi

# Save token
mkdir -p /root/.cache/huggingface
echo "$HF_TOKEN" > /root/.cache/huggingface/token
export HF_TOKEN="$HF_TOKEN"

# ---- 1. Clone tribev2 if not present ----
if [ ! -d "/workspace/tribev2" ]; then
    echo ">>> Cloning tribev2 from GitHub..."
    git clone https://github.com/facebookresearch/tribev2.git /workspace/tribev2
fi

# ---- 2. Install tribev2 (relax torch constraint) ----
echo ">>> Installing tribev2..."
cd /workspace/tribev2
sed -i 's/torch>=2.5.1,<2.7/torch>=2.5.1/' pyproject.toml 2>/dev/null || true
pip install -e ".[plotting]" 2>&1 | tail -3

# ---- 3. Reinstall PyTorch 2.8 with CUDA 12.8 (for RTX 5090 / Blackwell) ----
echo ">>> Installing PyTorch 2.8+cu128..."
pip install torch==2.8.0+cu128 torchvision==0.23.0+cu128 torchaudio==2.8.0+cu128 \
    --index-url https://download.pytorch.org/whl/cu128 2>&1 | tail -3

# ---- 4. Install htb-brain dependencies ----
echo ">>> Installing htb-brain deps..."
pip install pydantic-settings fastapi uvicorn python-multipart httpx \
    trimesh pygltflib scipy hf_transfer 2>&1 | tail -3

# ---- 5. Fix hf_transfer in uvx cache (for WhisperX) ----
echo ">>> Fixing hf_transfer in uvx environments..."
for d in /workspace/.cache/uv/archive-v0/*/lib/python3.*/site-packages; do
    if [ -d "$d" ]; then
        pip install --target "$d" hf_transfer 2>&1 | tail -1
    fi
done

# ---- 6. Generate brain mesh GLB if not present ----
if [ ! -f "/workspace/tribe/src/htb_brain/static/brain_mesh.glb" ]; then
    echo ">>> Generating brain mesh GLB..."
    cd /workspace/tribe
    PYTHONPATH=/workspace/tribe/src python3 src/htb_brain/visualization/mesh_export.py \
        /workspace/tribe/src/htb_brain/static/brain_mesh.glb
else
    echo ">>> Brain mesh GLB already exists, skipping."
fi

# ---- 7. Verify ----
echo ">>> Verifying installation..."
python3 -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'; print(f'PyTorch {torch.__version__} CUDA OK on {torch.cuda.get_device_name(0)}')"
python3 -c "from tribev2 import TribeModel; print('tribev2 OK')"
python3 -c "import fastapi; print('fastapi OK')"
python3 -c "import nilearn; print('nilearn OK')"

echo ""
echo "=== Setup complete ==="
echo ""
echo "To start the server:"
echo "  cd /workspace/tribe"
echo "  export HF_TOKEN=$HF_TOKEN"
echo "  export PYTHONPATH=/workspace/tribe/src"
echo "  python3 -m uvicorn htb_brain.api.app:app --host 0.0.0.0 --port 8000"
echo ""
echo "Or use the start script:"
echo "  bash /workspace/tribe/start.sh"
