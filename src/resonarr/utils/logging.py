from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys


class TeeStream:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()


def configure_runner_logging(run_name: str):
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    timestamped_log_path = logs_dir / f"{run_name}-{timestamp}.log"
    latest_log_path = logs_dir / f"{run_name}-latest.log"

    timestamped_log_file = timestamped_log_path.open("w", encoding="utf-8")
    latest_log_file = latest_log_path.open("w", encoding="utf-8")

    original_stdout = sys.stdout
    original_stderr = sys.stderr

    sys.stdout = TeeStream(original_stdout, timestamped_log_file, latest_log_file)
    sys.stderr = TeeStream(original_stderr, timestamped_log_file, latest_log_file)

    print(f"[INFO] Timestamped log file: {timestamped_log_path}")
    print(f"[INFO] Latest log file: {latest_log_path}")

    return {
        "timestamped_log_path": timestamped_log_path,
        "latest_log_path": latest_log_path,
    }