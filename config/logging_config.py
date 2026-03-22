"""
统一日志配置
"""
import logging
import sys
from pathlib import Path


def setup_logging(
    level: int = logging.INFO,
    log_file: str = None,
    log_format: str = '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    date_format: str = '%Y-%m-%d %H:%M:%S'
) -> None:
    """
    配置全局日志系统

    Args:
        level: 日志级别（默认 INFO）
        log_file: 日志文件路径（可选）
        log_format: 日志格式
        date_format: 日期格式
    """
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除现有处理器
    root_logger.handlers.clear()

    # 创建格式化器
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件处理器（可选）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        日志记录器实例
    """
    return logging.getLogger(name)


# 初始化默认日志配置（可在导入时调用）
# setup_logging()  # 取消注释以在导入时自动配置
