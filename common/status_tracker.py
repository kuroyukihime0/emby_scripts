import time
import datetime
import threading

class TaskStatusTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self.status = "IDLE"          # "IDLE" 或 "RUNNING"
        self.current_task = None      # 当前子模块或描述
        self.last_run_time = None     # 上次执行时间
        self.next_run_time = None     # 下次执行预定时间
        self.stats = {
            "processed_items": 0,
            "updated_items": 0,
            "skipped_items": 0,
            "errors": 0,
        }

    def set_running(self, task_name: str = "Pipeline"):
        with self._lock:
            self.status = "RUNNING"
            self.current_task = task_name
            self.last_run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def set_idle(self, next_run_in_hours: int = None):
        with self._lock:
            self.status = "IDLE"
            self.current_task = None
            if next_run_in_hours and next_run_in_hours > 0:
                next_time = datetime.datetime.now() + datetime.timedelta(hours=next_run_in_hours)
                self.next_run_time = next_time.strftime("%Y-%m-%d %H:%M:%S")
            else:
                self.next_run_time = None

    def update_stats(self, processed_delta=0, updated_delta=0, skipped_delta=0, errors_delta=0):
        with self._lock:
            self.stats["processed_items"] += processed_delta
            self.stats["updated_items"] += updated_delta
            self.stats["skipped_items"] += skipped_delta
            self.stats["errors"] += errors_delta

    def reset_stats(self):
        with self._lock:
            self.stats = {
                "processed_items": 0,
                "updated_items": 0,
                "skipped_items": 0,
                "errors": 0,
            }

    def to_dict(self):
        with self._lock:
            return {
                "status": self.status,
                "current_task": self.current_task,
                "last_run_time": self.last_run_time,
                "next_run_time": self.next_run_time,
                "stats": dict(self.stats)
            }

status_tracker = TaskStatusTracker()
