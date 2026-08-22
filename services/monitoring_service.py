from datetime import datetime
import os


def log_system_event(event_type, message):
    os.makedirs("logs", exist_ok=True)

    with open("logs/system.log", "a", encoding="utf-8") as logfile:
        logfile.write(
            f"[{datetime.now()}] "
            f"[{event_type}] "
            f"{message}\n"
        )