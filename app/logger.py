import logging
import colorlog
from logging.handlers import RotatingFileHandler

def setup_colored_logger(name: str, level=logging.DEBUG, log_file="app.log", max_bytes=10*1024*1024, backup_count=5):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        # Обработчик для вывода в консоль с цветами
        console_handler = colorlog.StreamHandler()
        console_formatter = colorlog.ColoredFormatter(
            "{asctime} {log_color}[{levelname}]{reset} {name}: {message}",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'red,bg_white',
            },
            style='{'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # Обработчик для записи в файл с ротацией
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,  # Максимальный размер файла (10 МБ)
            backupCount=backup_count  # Количество резервных файлов
        )
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger