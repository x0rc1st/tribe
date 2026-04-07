# HTB Brain Engagement Service

TRIBE v2 integration for predicting brain engagement patterns in cybersecurity learning content. Combines Meta's cortical surface model (20,484 vertices) with a custom-trained subcortical model (8,808 voxels across 7 deep brain structures) to map how content engages 10 cognitive capability groups.

## Quick Recovery (after pod restart/destroy)

```bash
bash /workspace/tribe/setup_runpod.sh   # ~5 min (installs pip packages, generates meshes)
bash /workspace/tribe/start.sh          # ~60 sec (loads cortical + subcortical models)
```

The server will be available on port 8000 (or 8888 if configured).

## Architecture

```
Input (text / video / audio)
    │
    ├──► [TRIBE v2 Cortical Model]  →  20,484 vertex activations (fsaverage5)
    │        facebook/tribev2 (HuggingFace)
    │
    ├──► [Subcortical Model]  →  8,808 voxel activations (Harvard-Oxford atlas)
    │        trained checkpoint on network volume
    │
    ▼
[Aggregator + Translator]  →  10 capability group scores (70% cortical + 30% subcortical)
    │
    ▼
[3D Glass Brain Viewer]  →  26,866 vertex combined mesh
    cortical surface (glass) + subcortical structures (solid glow)
```

## 10 Capability Groups

| # | Name | Cortical | Subcortical |
|---|------|----------|-------------|
| 1 | Strategic Thinking & Decision-Making | Prefrontal cortex | Caudate |
| 2 | Procedural Fluency & Muscle Memory | Sensorimotor strip | Putamen, Pallidum |
| 3 | Technical Comprehension & Language Processing | Perisylvian network | Thalamus |
| 4 | Visual Processing & Pattern Detection | Occipital + ventral | — |
| 5 | Situational Awareness & Focus | Dorsal parietal | Thalamus |
| 6 | Motivation & Adaptive Drive | Anterior/mid cingulate | Accumbens |
| 7 | Memory Encoding & Knowledge Retention | Medial temporal | Hippocampus |
| 8 | Knowledge Synthesis & Transfer | Inferior parietal | — |
| 9 | Threat Awareness & Emotional Encoding | Insular cortex | Amygdala |
| 10 | Deep Internalization & Reflective Processing | DMN (posterior cingulate) | — |

## Network Volume Layout (/workspace)

Everything critical lives on the RunPod network volume and persists across pod restarts.

```
/workspace/
├── tribe/                          # This repo
│   ├── setup_runpod.sh             # Full environment setup (run after pod restart)
│   ├── start.sh                    # Start server (auto-detects subcortical checkpoint)
│   ├── .env                        # Environment overrides (optional)
│   ├── src/htb_brain/              # Application code
│   │   ├── api/                    # FastAPI routes + schemas
│   │   ├── core/                   # Predictor, atlas, translator, subcortical modules
│   │   ├── data/                   # Cognitive maps (cortical + subcortical)
│   │   ├── visualization/          # Mesh export, summary generation
│   │   └── static/                 # 3D viewer + generated GLB meshes
│   ├── scripts/                    # Training + validation scripts
│   ├── subcortical_training/       # [gitignored — network volume only]
│   │   ├── results/
│   │   │   ├── best.ckpt           # Trained subcortical model (2.1 GB)
│   │   │   └── config.yaml         # Model config
│   │   └── cache/                  # Feature extraction cache (1.7 GB)
│   └── cache/                      # Cortical model inference cache (1.7 GB)
├── tribev2/                        # Meta's TRIBE v2 repo (cloned by setup_runpod.sh)
└── data/                           # Wen2017 fMRI training dataset (25 GB)
    └── download/video_fmri_dataset/
        ├── subject1/fmri/          # MNI-space NIfTI files
        └── stimuli/                # Video stimuli (.mp4)
```

## What Does NOT Persist (container disk)

These are reinstalled by `setup_runpod.sh`:
- pip packages (tribev2, lightning, fastapi, etc.)
- HuggingFace model cache (`/root/.cache/huggingface/`)
- Spacy models, NLTK data

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Model status (cortical + subcortical) |
| `/api/v1/predict` | POST | Text prediction (returns job_id for polling) |
| `/api/v1/predict/video` | POST | Video prediction (file upload) |
| `/api/v1/jobs/{job_id}` | GET | Poll for prediction result |
| `/api/v1/aggregate` | POST | Combine multiple predictions |
| `/` | GET | 3D brain viewer UI |

### Prediction Response

```json
{
  "vertex_activations": [...],        // 26,866 floats (20,484 cortical + 6,382 subcortical)
  "group_scores": [...],              // 10 groups ranked by engagement
  "narrative_summary": "...",         // Markdown narrative
  "subcortical_regions": [            // 7 structures with z-scores
    {"name": "Hippocampus", "z_score": 1.6, "engaged": true, "group_ids": [7]},
    {"name": "Amygdala", "z_score": 1.2, "engaged": true, "group_ids": [9]},
    ...
  ],
  "n_cortical_vertices": 20484,
  "n_subcortical_vertices": 6382
}
```

## Training the Subcortical Model

The subcortical model is already trained and lives on the network volume. To retrain or improve:

```bash
# Set paths
export DATAPATH=/workspace/data
export SAVEPATH=/workspace/tribe/subcortical_training

# Train (full config, ~5 hours on RTX 5090)
python scripts/train_subcortical.py --studies Wen2017 --epochs 15 --patience 5

# Train with frozen backbone (faster, ~30 min after feature extraction)
python scripts/train_subcortical.py --studies Wen2017 --freeze-backbone --epochs 15
```

### Current Model Metrics (subject1, full-config V-JEPA2-vitG)

| Metric | Value |
|--------|-------|
| Test Pearson correlation | 0.120 |
| Retrieval top-1 accuracy | 55% |
| Output voxels | 8,808 |
| Subcortical structures | 7 (Thalamus, Caudate, Putamen, Pallidum, Hippocampus, Amygdala, Accumbens) |

## Environment Variables

All use the `HTB_BRAIN_` prefix. Auto-detected defaults work for standard RunPod setup.

```bash
# Optional overrides (see .env.example)
HTB_BRAIN_SUBCORTICAL_CHECKPOINT_DIR=/workspace/tribe/subcortical_training/results
HTB_BRAIN_SUBCORTICAL_MESH_META=/workspace/tribe/src/htb_brain/static/brain_mesh_combined.json
HTB_BRAIN_MODEL_REPO=facebook/tribev2
HTB_BRAIN_DEVICE=auto
```

## License

CC-BY-NC-4.0 (inherits from TRIBE v2).
