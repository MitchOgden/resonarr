from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sys
import time


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

def format_elapsed(seconds: float) -> str:
    return f"{seconds:.2f}s"


class RunnerProgress:
    def __init__(self, total_steps: int):
        self.total_steps = max(1, total_steps)
        self.current_step = 0
        self.started_at = time.perf_counter()

    def _render_bar(self, width: int = 20) -> str:
        completed = int(width * self.current_step / self.total_steps)
        return "#" * completed + "-" * (width - completed)

    def step(self, label: str):
        self.current_step += 1
        if self.current_step > self.total_steps:
            self.current_step = self.total_steps

        percent = int((self.current_step / self.total_steps) * 100)
        bar = self._render_bar()
        print(
            f"[PROGRESS] [{self.current_step}/{self.total_steps}] "
            f"[{bar}] {percent}% {label}"
        )

    def finish(self):
        elapsed = time.perf_counter() - self.started_at
        print(f"[INFO] Total elapsed: {format_elapsed(elapsed)}")


@contextmanager
def timed_step(label: str):
    started_at = time.perf_counter()
    print(f"[INFO] Starting: {label}")
    try:
        yield
    finally:
        elapsed = time.perf_counter() - started_at
        print(f"[INFO] Step completed in {format_elapsed(elapsed)}: {label}")