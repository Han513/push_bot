import os
import logging
from logging.handlers import RotatingFileHandler


_SETUP_DONE = False


def _get_logs_dir() -> str:
    # logs 目錄位於 src 的上層目錄下（push_bot/logs）
    project_root = os.path.dirname(os.path.dirname(__file__))
    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def setup_logging(level: str = None) -> None:
    """集中式日誌設定：將日誌輸出到 push_bot/logs/bot.log（輪轉）。

    - 透過環境變數自訂：
      - LOG_LEVEL（預設 INFO）
      - LOG_FILE（預設 bot.log）
      - LOG_MAX_BYTES（預設 10MB）
      - LOG_BACKUP_COUNT（預設 5）
    - 可多次呼叫，僅首次有效。
    """
    global _SETUP_DONE
    if _SETUP_DONE:
        return

    # 解析等級
    level_name = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    try:
        log_level = getattr(logging, level_name, logging.INFO)
    except Exception:
        log_level = logging.INFO

    # 目的地與檔名
    logs_dir = _get_logs_dir()
    log_file_name = os.getenv("LOG_FILE", "bot.log")
    log_file_path = os.path.join(logs_dir, log_file_name)

    # 構建輪轉 FileHandler
    max_bytes = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 10MB
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    # 標記避免重複添加
    setattr(file_handler, "_byd_file_handler", True)

    root_logger = logging.getLogger()
    # 避免重複添加相同檔案的 handler
    for h in list(root_logger.handlers):
        if getattr(h, "_byd_file_handler", False):
            _SETUP_DONE = True
            return

    root_logger.addHandler(file_handler)
    # 設定 root 等級，確保第三方庫也寫入檔案
    root_logger.setLevel(log_level)

    _SETUP_DONE = True


