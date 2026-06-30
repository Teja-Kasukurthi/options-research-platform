from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

app = Celery("options_research")
app.config_from_object(
    {
        "broker_url": settings.celery_broker_url,
        "result_backend": settings.celery_result_backend,
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "timezone": "Asia/Kolkata",
        "enable_utc": False,
        "task_routes": {
            "tasks.market_data.*": {"queue": "market"},
            "tasks.agents.*": {"queue": "ai"},
            "tasks.monitor.*": {"queue": "monitor"},
            "tasks.backtest.*": {"queue": "backtest"},
        },
        "beat_schedule": {
            # Market hours: options chain refresh every 5 min
            "refresh-options-chain": {
                "task": "tasks.market_data.refresh_options_chain",
                "schedule": crontab(minute="*/5", hour="9-15", day_of_week="mon-fri"),
            },
            # Daily AI research cycle at 08:30 IST (pre-market)
            "daily-research-cycle": {
                "task": "tasks.agents.run_research_cycle",
                "schedule": crontab(hour=8, minute=30, day_of_week="mon-fri"),
            },
            # Position monitor every 2 min during market hours
            "monitor-positions": {
                "task": "tasks.monitor.check_positions",
                "schedule": crontab(minute="*/2", hour="9-15", day_of_week="mon-fri"),
            },
            # Evaluator agent daily at 16:30 IST (post-market)
            "daily-evaluator": {
                "task": "tasks.agents.run_evaluator",
                "schedule": crontab(hour=16, minute=30, day_of_week="mon-fri"),
            },
        },
    }
)

app.autodiscover_tasks(["tasks"])
