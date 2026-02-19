"""
Shared configuration validation utilities for all TGsys services.
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    pass


@dataclass
class ValidationRule:
    """Configuration validation rule."""
    key: str
    required: bool = True
    type_hint: type = str
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    allowed_values: Optional[List[Any]] = None
    default_value: Optional[Any] = None


class ConfigValidator:
    """Validates environment variables and configuration."""

    def __init__(self, prefix: str = ""):
        self.prefix = prefix
        self.rules: Dict[str, ValidationRule] = {}

    def add_rule(self, rule: ValidationRule) -> "ConfigValidator":
        """Add a validation rule."""
        self.rules[rule.key] = rule
        return self

    def validate(self) -> Dict[str, Any]:
        """Validate all configured rules and return validated config."""
        config = {}
        errors = []

        for key, rule in self.rules.items():
            env_key = f"{self.prefix}{key}" if self.prefix else key
            value = os.getenv(env_key)

            if value is None:
                if rule.required:
                    errors.append(f"Missing required environment variable: {env_key}")
                elif rule.default_value is not None:
                    config[key] = rule.default_value
                continue

            # Type validation
            try:
                if rule.type_hint == int:
                    config[key] = int(value)
                elif rule.type_hint == float:
                    config[key] = float(value)
                elif rule.type_hint == bool:
                    config[key] = value.lower() in ('true', '1', 'yes', 'on')
                else:
                    config[key] = value
            except ValueError as e:
                errors.append(f"Invalid type for {env_key}: {e}")
                continue

            # Range validation for integers
            if rule.type_hint == int:
                int_value = config[key]
                if rule.min_value is not None and int_value < rule.min_value:
                    errors.append(f"{env_key} must be >= {rule.min_value}")
                if rule.max_value is not None and int_value > rule.max_value:
                    errors.append(f"{env_key} must be <= {rule.max_value}")

            # Allowed values validation
            if rule.allowed_values and config[key] not in rule.allowed_values:
                errors.append(f"{env_key} must be one of: {rule.allowed_values}")

        if errors:
            raise ConfigurationError(f"Configuration validation failed:\n" + "\n".join(errors))

        return config


def create_postgres_validator() -> ConfigValidator:
    """Create PostgreSQL configuration validator."""
    return ConfigValidator().add_rule(ValidationRule("POSTGRES_USER", required=True)).add_rule(
        ValidationRule("POSTGRES_PASSWORD", required=True)
    ).add_rule(ValidationRule("POSTGRES_DB", required=True)).add_rule(
        ValidationRule("POSTGRES_HOST", default_value="localhost")
    ).add_rule(
        ValidationRule("POSTGRES_PORT", type_hint=int, default_value=5432, min_value=1, max_value=65535)
    )


def create_kafka_validator() -> ConfigValidator:
    """Create Kafka configuration validator."""
    return ConfigValidator().add_rule(ValidationRule("KAFKA_BROKER", required=True)).add_rule(
        ValidationRule("KAFKA_TOPIC", required=True)
    ).add_rule(
        ValidationRule("KAFKA_PORT", type_hint=int, default_value=9092, min_value=1, max_value=65535)
    )


def create_telegram_validator() -> ConfigValidator:
    """Create Telegram API configuration validator."""
    return ConfigValidator().add_rule(
        ValidationRule("TELEGRAM_API_ID", required=True, type_hint=int, min_value=1)
    ).add_rule(ValidationRule("TELEGRAM_API_HASH", required=True)).add_rule(
        ValidationRule("SESSIONS_DIR", default_value="/sessions")
    )


def create_app_validator() -> ConfigValidator:
    """Create application configuration validator."""
    return ConfigValidator().add_rule(
        ValidationRule("LOG_LEVEL", default_value="INFO", allowed_values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    ).add_rule(
        ValidationRule("MIN_HEALTH_SCORE", type_hint=int, default_value=70, min_value=0, max_value=100)
    ).add_rule(
        ValidationRule("COOLDOWN_HOURS", type_hint=int, default_value=1, min_value=0, max_value=168)
    ).add_rule(
        ValidationRule("MAX_RETRIES", type_hint=int, default_value=3, min_value=0, max_value=10)
    ).add_rule(
        ValidationRule("RETRY_DELAY", type_hint=int, default_value=5, min_value=1, max_value=300)
    )
