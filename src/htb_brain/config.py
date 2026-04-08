from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "HTB_BRAIN_", "env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # TRIBE v2 (cortical)
    model_repo: str = "facebook/tribev2"
    model_cache_dir: str = "/workspace/tribe/cache"
    device: str = "auto"

    # Subcortical model — auto-detect from well-known path if not set
    subcortical_checkpoint_dir: str = ""
    subcortical_mesh_meta: str = ""

    def model_post_init(self, __context):
        # Auto-detect subcortical checkpoint if not explicitly configured
        if not self.subcortical_checkpoint_dir:
            default_ckpt = Path("/workspace/tribe/subcortical_training/results/best.ckpt")
            if default_ckpt.exists():
                self.subcortical_checkpoint_dir = str(default_ckpt.parent)
        if not self.subcortical_mesh_meta:
            default_meta = Path("/workspace/tribe/src/htb_brain/static/brain_mesh_combined.json")
            if default_meta.exists():
                self.subcortical_mesh_meta = str(default_meta)

    # Aggregation
    threshold_percentile: float = 75.0
    bilateral_collapse: bool = True

    # Subcortical blending — scales per-group evidence weights from the cognitive map.
    # Increase as subcortical model improves (r=0.12 → 0.25; r=0.25 → 0.45; r=0.50 → 1.0).
    subcortical_reliability: float = 0.25

    # API
    host: str = "0.0.0.0"
    port: int = 8000
    max_text_size_kb: int = 100
    max_video_size_mb: int = 2000
    max_video_duration_sec: int = 0  # 0 = no limit

    # Paths
    data_dir: str = "src/htb_brain/data"
    static_dir: str = "src/htb_brain/static"


settings = Settings()
