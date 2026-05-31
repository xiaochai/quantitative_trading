import os
import signal
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from scheduler.jobs import run_daily_job, run_weekly_job


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return default
    return int(v)


def main():
    timezone = os.getenv("SCHED_TZ", "Asia/Shanghai")

    daily_hour = _env_int("DAILY_JOB_HOUR", 18)
    daily_minute = _env_int("DAILY_JOB_MINUTE", 30)

    weekly_day = os.getenv("WEEKLY_JOB_DAY", "sat")
    weekly_hour = _env_int("WEEKLY_JOB_HOUR", 6)
    weekly_minute = _env_int("WEEKLY_JOB_MINUTE", 30)

    scheduler = BlockingScheduler(timezone=timezone)

    scheduler.add_job(
        run_daily_job,
        CronTrigger(hour=daily_hour, minute=daily_minute),
        id="daily_trading_summary",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60 * 60,
    )

    scheduler.add_job(
        run_weekly_job,
        CronTrigger(day_of_week=weekly_day, hour=weekly_hour, minute=weekly_minute),
        id="weekly_static_metrics",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=24 * 60 * 60,
    )

    print(
        "[scheduler] started",
        {
            "timezone": timezone,
            "daily": f"{daily_hour:02d}:{daily_minute:02d}",
            "weekly": f"{weekly_day} {weekly_hour:02d}:{weekly_minute:02d}",
            "now": datetime.now().isoformat(timespec="seconds"),
        },
    )

    def _handle(sig, _frame):
        print(f"[scheduler] stopping: signal={sig}")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)

    scheduler.start()


if __name__ == "__main__":
    main()

