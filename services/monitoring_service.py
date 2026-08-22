from datetime import datetime
import os
import sys


def log_system_event(event_type, message):
    line = f"[{datetime.now()}] [{event_type}] {message}"

    # Cloud platforms collect process stdout/stderr centrally. Avoid relying on
    # an ephemeral container filesystem for production application logs.
    if (
        os.getenv("FLASK_ENV", "").lower() == "production"
        or os.getenv("LOG_TO_STDOUT", "").lower() == "true"
    ):
        print(line, file=sys.stderr, flush=True)
        return

    os.makedirs("logs", exist_ok=True)

    with open("logs/system.log", "a", encoding="utf-8") as logfile:
        logfile.write(line + "\n")
