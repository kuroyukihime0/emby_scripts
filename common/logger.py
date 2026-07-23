import os
import logging

def setup_logger(name='emby_scripts', log_file='logs.log', level=logging.DEBUG):
    """
    配置并返回一个统一格式与漂亮排版的 Logger 实例
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    
    # 统一精美格式： 时间 | 级别 (5字符左对齐) | 模块 (15字符左对齐) | 日志内容
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-5s | [%(name)-15s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台输出
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # 文件日志输出
    try:
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except Exception as e:
        print(f"⚠️ Warning: Failed to create log file handler: {e}")

    return logger
