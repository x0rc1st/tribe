from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "HTB_BRAIN_"}

    # TRIBE v2
    model_repo: str = "facebook/tribev2"
    model_cache_dir: str = "/workspace/tribe/cache"
    device: str = "auto"

    # Aggregation
    threshold_percentile: float = 75.0
    bilateral_collapse: bool = True

    # API
    host: str = "0.0.0.0"
    port: int = 8000
    max_text_size_kb: int = 100
    max_video_size_mb: int = 500
    max_video_duration_sec: int = 600

    # Paths
    data_dir: str = "src/htb_brain/data"
    static_dir: str = "src/htb_brain/static"


settings = Settings()
