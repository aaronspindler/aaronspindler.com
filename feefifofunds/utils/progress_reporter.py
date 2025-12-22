import os
import sys
import time
from datetime import datetime
from typing import Dict, Optional

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class ProgressReporter:
    def __init__(self, tier: str = "ALL", total_files: int = 0):
        self.tier = tier
        self.total_files = total_files
        self.completed_files = 0
        self.current_file = None
        self.current_records = 0
        self.total_records = 0
        self.start_time = time.time()
        self.file_start_time = None
        self.last_update_time = 0
        self.update_interval = 0.05  # Update every 50ms for smoother progress
        self.terminal_width = self._get_terminal_width()

        # Performance tracking
        self.records_per_second = []
        self.current_speed = 0

        self.process = psutil.Process() if PSUTIL_AVAILABLE else None

    def _get_terminal_width(self) -> int:
        try:
            return os.get_terminal_size().columns
        except (AttributeError, OSError):
            return 80  # Default width

    def _format_size(self, bytes_size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"

    def _format_time(self, seconds: float) -> str:
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"

    def _calculate_eta(self) -> str:
        if self.completed_files == 0 or not self.records_per_second:
            return "calculating..."

        remaining_files = self.total_files - self.completed_files
        if remaining_files <= 0:
            return "0s"

        elapsed = time.time() - self.start_time
        avg_time_per_file = elapsed / self.completed_files
        eta_seconds = remaining_files * avg_time_per_file

        return self._format_time(eta_seconds)

    def _clear_line(self):
        sys.stdout.write("\r" + " " * self.terminal_width + "\r")
        sys.stdout.flush()

    def display_header(self):
        print("\n📊 Sequential OHLCVT Ingestor")
        print("─" * min(self.terminal_width, 60))
        print(f"Tier: {self.tier}")
        print(f"Total files: {self.total_files:,}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("─" * min(self.terminal_width, 60))
        print()

    def start_file(self, filepath: str, file_size: int):
        self.current_file = os.path.basename(filepath)
        self.file_start_time = time.time()
        self.current_records = 0

        file_num = self.completed_files + 1
        progress_pct = (self.completed_files / self.total_files * 100) if self.total_files > 0 else 0

        print(f"\n[{file_num:03d}/{self.total_files:03d}] {self.current_file}")
        print(f"  ├─ Size: {self._format_size(file_size)}")
        print(f"  ├─ Progress: {progress_pct:.1f}% overall")
        sys.stdout.write("  └─ Processing: ")
        sys.stdout.flush()

    def update_records(self, records_processed: int, total_in_file: Optional[int] = None):
        current_time = time.time()

        if current_time - self.last_update_time < self.update_interval:
            return

        self.current_records = records_processed

        # Calculate speed
        if self.file_start_time:
            elapsed = current_time - self.file_start_time
            if elapsed > 0:
                self.current_speed = records_processed / elapsed
                self.records_per_second.append(self.current_speed)

        if total_in_file and total_in_file > 0:
            progress = records_processed / total_in_file
            bar_width = 20
            filled = int(bar_width * progress)
            bar = "█" * filled + "░" * (bar_width - filled)
            pct = progress * 100

            status = f"[{bar}] {pct:.0f}% | {records_processed:,}/{total_in_file:,} | {self.current_speed:,.0f} rec/s"
        else:
            status = f"{records_processed:,} records | {self.current_speed:,.0f} rec/s"

        self._clear_line()
        sys.stdout.write(f"  └─ Processing: {status}")
        sys.stdout.flush()
        self.last_update_time = current_time

    def complete_file(self, success: bool = True, error_msg: Optional[str] = None):
        if success:
            self.completed_files += 1
            self.total_records += self.current_records
            file_time = time.time() - self.file_start_time if self.file_start_time else 0

            self._clear_line()
            avg_speed = sum(self.records_per_second) / len(self.records_per_second) if self.records_per_second else 0
            sys.stdout.write(
                f"  └─ ✓ Completed: {self.current_records:,} records in {self._format_time(file_time)} "
                f"({avg_speed:,.0f} rec/s avg)\n"
            )
        else:
            self._clear_line()
            sys.stdout.write(f"  └─ ✗ Failed: {error_msg}\n")

        sys.stdout.flush()

    def display_summary(self):
        elapsed = time.time() - self.start_time
        avg_speed = self.total_records / elapsed if elapsed > 0 else 0

        print("\n" + "─" * min(self.terminal_width, 60))
        print("✅ Ingestion Complete")
        print("─" * min(self.terminal_width, 60))
        print(f"Files processed: {self.completed_files:,}/{self.total_files:,}")
        print(f"Total records: {self.total_records:,}")
        print(f"Total time: {self._format_time(elapsed)}")
        print(f"Average speed: {avg_speed:,.0f} records/second")

        if self.process:
            mem_info = self.process.memory_info()
            print(f"Peak memory: {self._format_size(mem_info.rss)}")

    def display_error(self, filepath: str, error: Exception, traceback_str: str):
        print("\n" + "─" * min(self.terminal_width, 60))
        print("❌ ERROR OCCURRED")
        print("─" * min(self.terminal_width, 60))
        print(f"File: {filepath}")
        print(f"Error: {str(error)}")
        print("\nFull traceback:")
        print(traceback_str)
        print("─" * min(self.terminal_width, 60))

    def display_resume_info(self, resume_info: Dict):
        if not resume_info["can_resume"]:
            return

        print("\n📝 Resume Information")
        print("─" * min(self.terminal_width, 60))
        print(f"Previously completed: {resume_info['completed_count']} files")
        print(f"Failed files: {resume_info['failed_count']}")

        if resume_info["interrupted_count"] > 0:
            print(f"Interrupted files: {resume_info['interrupted_count']} (will retry)")

        if resume_info["last_error"]:
            error = resume_info["last_error"]
            print("\nLast error:")
            print(f"  File: {os.path.basename(error['filepath'])}")
            print(f"  Error: {error['error_message']}")

        print("─" * min(self.terminal_width, 60))
        print()

    def show_live_stats(self):
        eta = self._calculate_eta()

        status_parts = [
            f"Files: {self.completed_files}/{self.total_files}",
            f"Records: {self.total_records:,}",
            f"Speed: {self.current_speed:,.0f} rec/s",
        ]

        if self.process:
            mem_info = self.process.memory_info()
            mem_usage = self._format_size(mem_info.rss)
            status_parts.append(f"Memory: {mem_usage}")

        status_parts.append(f"ETA: {eta}")

        status_line = " | ".join(status_parts)

        self._clear_line()
        sys.stdout.write(status_line)
        sys.stdout.flush()
