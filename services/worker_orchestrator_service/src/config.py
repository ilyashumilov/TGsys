from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class PostgresConfig:
    host: str
    port: int
    db: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> PostgresConfig:
        return cls(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            db=os.getenv("POSTGRES_DB", "tgsys"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "password"),
        )


@dataclass
class DockerConfig:
    base_url: str = "unix:///var/run/docker.sock"
    worker_image: str = "comment_worker:latest"
    network: str = "tgsys_default"

    @classmethod
    def from_env(cls) -> DockerConfig:
        return cls(
            base_url=os.getenv("DOCKER_BASE_URL", "unix:///var/run/docker.sock"),
            worker_image=os.getenv("WORKER_IMAGE", "comment_worker:latest"),
            network=os.getenv("DOCKER_NETWORK", "tgsys_default"),
        )


@dataclass
class AppConfig:
    sessions_dir: str = "/app/sessions"
    template_session_file: str = "/app/sessions/33093187_session.session"
    health_check_interval: int = 60  # seconds
    max_retries: int = 3
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> AppConfig:
        return cls(
            sessions_dir=os.getenv("SESSIONS_DIR", "/app/sessions"),
            template_session_file=os.getenv("TEMPLATE_SESSION_FILE", "/app/sessions/33093187_session.session"),
            health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "60")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


def setup_logging() -> None:
    """Configure logging for the application."""
    import logging
    import sys
    
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
