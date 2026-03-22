import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml
from dotenv import load_dotenv


@dataclass
class ScheduleConfig:
    frequency: str = "weekly"      # daily | weekly | monthly
    time: str = "08:00"
    day_of_week: str = "monday"
    day_of_month: int = 1
    timezone: str = "Europe/Paris"


@dataclass
class EmailConfig:
    enabled: bool = True
    provider: str = "gmail"        # gmail | sendgrid


@dataclass
class WhatsAppConfig:
    enabled: bool = False


@dataclass
class DeliveryConfig:
    email: EmailConfig = field(default_factory=EmailConfig)
    whatsapp: WhatsAppConfig = field(default_factory=WhatsAppConfig)


@dataclass
class AnalysisConfig:
    claude_model: str = "claude-sonnet-4-6"
    news_lookback_days: int = 7
    top_etf_picks: int = 5
    max_news_articles: int = 50
    language: str = "fr"           # fr | es | en


@dataclass
class DataConfig:
    etf_universe_file: str = "data/etf_universe.yaml"
    signal_map_file: str = "config/signal_map.yaml"
    cache_dir: str = ".cache"


@dataclass
class Config:
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    delivery: DeliveryConfig = field(default_factory=DeliveryConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    data: DataConfig = field(default_factory=DataConfig)

    # Secrets from .env
    anthropic_api_key: str = ""
    newsapi_key: str = ""
    gmail_user: str = ""
    gmail_app_password: str = ""
    sendgrid_api_key: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""
    email_recipients: List[str] = field(default_factory=list)
    whatsapp_recipients: List[str] = field(default_factory=list)


def load_config(settings_path: str = "config/settings.yaml", env_path: str = ".env") -> Config:
    # Load .env
    env_file = Path(env_path)
    if env_file.exists():
        load_dotenv(env_file)

    # Load settings.yaml
    cfg = Config()
    settings_file = Path(settings_path)
    if settings_file.exists():
        with open(settings_file, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        s = raw.get("schedule", {})
        cfg.schedule = ScheduleConfig(
            frequency=s.get("frequency", "weekly"),
            time=s.get("time", "08:00"),
            day_of_week=s.get("day_of_week", "monday"),
            day_of_month=int(s.get("day_of_month", 1)),
            timezone=s.get("timezone", "Europe/Paris"),
        )

        d = raw.get("delivery", {})
        e = d.get("email", {})
        w = d.get("whatsapp", {})
        cfg.delivery = DeliveryConfig(
            email=EmailConfig(
                enabled=e.get("enabled", True),
                provider=e.get("provider", "gmail"),
            ),
            whatsapp=WhatsAppConfig(enabled=w.get("enabled", False)),
        )

        a = raw.get("analysis", {})
        cfg.analysis = AnalysisConfig(
            claude_model=a.get("claude_model", "claude-sonnet-4-6"),
            news_lookback_days=int(a.get("news_lookback_days", 7)),
            top_etf_picks=int(a.get("top_etf_picks", 5)),
            max_news_articles=int(a.get("max_news_articles", 50)),
            language=a.get("language", "fr"),
        )

        dt = raw.get("data", {})
        cfg.data = DataConfig(
            etf_universe_file=dt.get("etf_universe_file", "data/etf_universe.yaml"),
            signal_map_file=dt.get("signal_map_file", "config/signal_map.yaml"),
            cache_dir=dt.get("cache_dir", ".cache"),
        )

    # Load secrets from environment
    cfg.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    cfg.newsapi_key = os.getenv("NEWSAPI_KEY", "")
    cfg.gmail_user = os.getenv("GMAIL_USER", "")
    cfg.gmail_app_password = os.getenv("GMAIL_APP_PASSWORD", "")
    cfg.sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "")
    cfg.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    cfg.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    cfg.twilio_whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM", "")

    recipients_raw = os.getenv("EMAIL_RECIPIENTS", "")
    cfg.email_recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]

    wa_raw = os.getenv("WHATSAPP_RECIPIENTS", "")
    cfg.whatsapp_recipients = [r.strip() for r in wa_raw.split(",") if r.strip()]

    _validate(cfg)
    return cfg


def _validate(cfg: Config) -> None:
    errors = []
    if not cfg.anthropic_api_key:
        errors.append("ANTHROPIC_API_KEY is required in .env")
    if cfg.delivery.email.enabled and not cfg.email_recipients:
        errors.append("EMAIL_RECIPIENTS is required when email delivery is enabled")
    if cfg.delivery.email.enabled and cfg.delivery.email.provider == "gmail":
        if not cfg.gmail_user or not cfg.gmail_app_password:
            errors.append("GMAIL_USER and GMAIL_APP_PASSWORD are required for Gmail delivery")
    if cfg.delivery.whatsapp.enabled:
        if not cfg.twilio_account_sid or not cfg.twilio_auth_token:
            errors.append("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are required for WhatsApp delivery")
    if errors:
        raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
