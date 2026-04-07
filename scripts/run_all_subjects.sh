#!/bin/bash
# Autonomous subcortical training pipeline
# Runs unattended: waits for current training, then adds subjects one by one

set -o pipefail
export DATAPATH=/workspace/data
export SAVEPATH=/workspace/tribe/subcortical_training
export PYTHONPATH=/workspace/tribe/src:/workspace/tribev2
LOG=/workspace/tribe/pipeline.log

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

log "=== AUTONOMOUS PIPELINE STARTED ==="

# ---------------------------------------------------------------
# PHASE 1: Wait for current full-config training (subject1)
# ---------------------------------------------------------------
log "PHASE 1: Waiting for current training to finish..."

while pgrep -f "train_subcortical.py" > /dev/null 2>&1; do
    sleep 60
done

log "Current training finished."
log "--- Subject1 results ---"
grep -E "pearson|retrieval|Training complete|checkpoint" /workspace/tribe/subcortical_training_full.log 2>/dev/null | tail -10 >> "$LOG"
tail -20 /workspace/tribe/subcortical_training_full.log >> "$LOG" 2>/dev/null

# Save subject1-only checkpoint
if [ -f "$SAVEPATH/results/best.ckpt" ]; then
    cp "$SAVEPATH/results/best.ckpt" "$SAVEPATH/results/best_1subj.ckpt"
    log "Saved best_1subj.ckpt"
fi

# ---------------------------------------------------------------
# PHASE 2: Download subject2, train on 2 subjects
# ---------------------------------------------------------------
log ""
log "PHASE 2: Adding subject2"

DISK_MB=$(du -sm /workspace/ 2>/dev/null | cut -f1)
log "Disk: ${DISK_MB}MB"

# Clean space
rm -f "$SAVEPATH/results/last.ckpt"

cd /workspace/data/download
log "Downloading subject2 (~14 GB)..."
wget -q -c ftp://purr.purdue.edu/10_4231_R7NS0S1F.zip -O subject2.zip
RC=$?
if [ $RC -ne 0 ]; then
    log "Download failed (rc=$RC). Retrying in 30s..."
    sleep 30
    wget -q -c ftp://purr.purdue.edu/10_4231_R7NS0S1F.zip -O subject2.zip
fi
log "Downloaded: $(ls -lh subject2.zip 2>/dev/null | awk '{print $5}')"

log "Extracting outer zip..."
mkdir -p /tmp/s2ext
unzip -q -o subject2.zip -d /tmp/s2ext/
rm -f subject2.zip
log "Zip deleted."

BUNDLE=$(find /tmp/s2ext/ -name "bundle.zip" -type f | head -1)
if [ -n "$BUNDLE" ]; then
    log "Extracting bundle: $(du -sh "$BUNDLE" | cut -f1)"
    mkdir -p /tmp/s2inner
    unzip -q -o "$BUNDLE" -d /tmp/s2inner/

    # Find subject2 directory wherever it is
    S2DIR=$(find /tmp/s2inner/ -maxdepth 4 -type d -name "subject2" | head -1)
    if [ -n "$S2DIR" ]; then
        mv "$S2DIR" /workspace/data/download/video_fmri_dataset/subject2
        log "subject2 placed OK"
    else
        log "ERROR: subject2 dir not found in bundle"
        find /tmp/s2inner/ -maxdepth 3 -type d >> "$LOG"
    fi
fi
rm -rf /tmp/s2ext /tmp/s2inner

# Verify
if [ -d /workspace/data/download/video_fmri_dataset/subject2/fmri ]; then
    NSEG=$(ls /workspace/data/download/video_fmri_dataset/subject2/fmri/ | wc -l)
    log "subject2 OK: $NSEG fmri segments"

    # Verify MNI files exist
    MNI_COUNT=$(find /workspace/data/download/video_fmri_dataset/subject2/fmri/ -name "*mni*" | wc -l)
    log "subject2 MNI files: $MNI_COUNT"
else
    log "ERROR: subject2 extraction failed. Stopping at 1-subject result."
    exit 1
fi

DISK_MB=$(du -sm /workspace/ 2>/dev/null | cut -f1)
log "Disk after subject2: ${DISK_MB}MB"

log "Starting 2-subject training..."
cd /workspace/tribe
python3 scripts/train_subcortical.py \
    --studies Wen2017 \
    --epochs 15 \
    --batch-size 4 \
    --num-workers 4 \
    --patience 5 \
    > /workspace/tribe/subcortical_training_2subj.log 2>&1

log "2-subject training finished."
tail -25 /workspace/tribe/subcortical_training_2subj.log >> "$LOG" 2>/dev/null

if [ -f "$SAVEPATH/results/best.ckpt" ]; then
    cp "$SAVEPATH/results/best.ckpt" "$SAVEPATH/results/best_2subj.ckpt"
    log "Saved best_2subj.ckpt"
fi

# ---------------------------------------------------------------
# PHASE 3: Check if subject3 fits
# ---------------------------------------------------------------
log ""
log "PHASE 3: Checking space for subject3"

# Aggressive cleanup
rm -f "$SAVEPATH/results/last.ckpt"
rm -f "$SAVEPATH/results/best_1subj.ckpt"

DISK_MB=$(du -sm /workspace/ 2>/dev/null | cut -f1)
log "Disk after cleanup: ${DISK_MB}MB"

if [ "$DISK_MB" -gt 82000 ]; then
    log "STOP: ${DISK_MB}MB used. Subject3 needs ~15GB more. Resize volume to 150GB."
    log "Best 2-subject checkpoint: $SAVEPATH/results/best_2subj.ckpt"
    log "=== PIPELINE STOPPED (disk full) ==="
    exit 0
fi

cd /workspace/data/download
log "Downloading subject3 (~15 GB)..."
wget -q -c ftp://purr.purdue.edu/10_4231_R7J101BV.zip -O subject3.zip
RC=$?
if [ $RC -ne 0 ]; then
    log "Download failed. Retrying..."
    sleep 30
    wget -q -c ftp://purr.purdue.edu/10_4231_R7J101BV.zip -O subject3.zip
fi
log "Downloaded: $(ls -lh subject3.zip 2>/dev/null | awk '{print $5}')"

log "Extracting..."
mkdir -p /tmp/s3ext
unzip -q -o subject3.zip -d /tmp/s3ext/
rm -f subject3.zip
log "Zip deleted."

BUNDLE=$(find /tmp/s3ext/ -name "bundle.zip" -type f | head -1)
if [ -n "$BUNDLE" ]; then
    log "Extracting bundle..."
    mkdir -p /tmp/s3inner
    unzip -q -o "$BUNDLE" -d /tmp/s3inner/

    S3DIR=$(find /tmp/s3inner/ -maxdepth 4 -type d -name "subject3" | head -1)
    if [ -n "$S3DIR" ]; then
        mv "$S3DIR" /workspace/data/download/video_fmri_dataset/subject3
        log "subject3 placed OK"
    else
        log "ERROR: subject3 dir not found"
        find /tmp/s3inner/ -maxdepth 3 -type d >> "$LOG"
    fi
fi
rm -rf /tmp/s3ext /tmp/s3inner

if [ -d /workspace/data/download/video_fmri_dataset/subject3/fmri ]; then
    NSEG=$(ls /workspace/data/download/video_fmri_dataset/subject3/fmri/ | wc -l)
    log "subject3 OK: $NSEG fmri segments"
else
    log "ERROR: subject3 failed. 2-subject checkpoint still valid."
    exit 1
fi

DISK_MB=$(du -sm /workspace/ 2>/dev/null | cut -f1)
log "Disk after subject3: ${DISK_MB}MB"

if [ "$DISK_MB" -gt 98000 ]; then
    log "STOP: Disk critically full. Cannot train. Resize to 150GB."
    exit 0
fi

log "Starting 3-subject training..."
cd /workspace/tribe
python3 scripts/train_subcortical.py \
    --studies Wen2017 \
    --epochs 15 \
    --batch-size 4 \
    --num-workers 4 \
    --patience 5 \
    > /workspace/tribe/subcortical_training_3subj.log 2>&1

log "3-subject training finished."
tail -25 /workspace/tribe/subcortical_training_3subj.log >> "$LOG" 2>/dev/null

if [ -f "$SAVEPATH/results/best.ckpt" ]; then
    cp "$SAVEPATH/results/best.ckpt" "$SAVEPATH/results/best_3subj.ckpt"
    log "Saved best_3subj.ckpt"
fi

log ""
log "=== PIPELINE COMPLETE ==="
log "Checkpoints:"
ls -lh "$SAVEPATH/results/best"*.ckpt 2>/dev/null | tee -a "$LOG"
log "Disk: $(du -sh /workspace/ 2>/dev/null | cut -f1)"
