import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Константы для логирования
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL = logging.INFO
LOG_DIR = "logs"
LOG_FILE_MAX_SIZE = 5 * 1024 * 1024  # 5 МБ
LOG_FILE_BACKUP_COUNT = 3

def get_logger(name):
    """
    Получить настроенный логгер для модуля
    
    Args:
        name: Имя модуля/логгера
        
    Returns:
        Настроенный объект логгера
    """
    logger = logging.getLogger(name)
    
    # Если логгер уже настроен, просто возвращаем его
    if logger.handlers:
        return logger
        
    logger.setLevel(LOG_LEVEL)
    
    # Форматтер для логов
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    
    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Обработчик для вывода в файл
    try:
        # Создаем директорию для логов, если не существует
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_dir = os.path.join(base_dir, LOG_DIR)
        os.makedirs(log_dir, exist_ok=True)
        
        # Создаем имя файла на основе текущей даты
        log_file = os.path.join(log_dir, f"nn_translator_{datetime.now().strftime('%Y%m%d')}.log")
        
        # Настраиваем ротацию логов
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=LOG_FILE_MAX_SIZE, 
            backupCount=LOG_FILE_BACKUP_COUNT
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Не удалось настроить запись логов в файл: {e}")
    
    return logger

def set_log_level(level):
    """
    Установить уровень логирования для всех логгеров
    
    Args:
        level: Уровень логирования (logging.DEBUG, logging.INFO и т.д.)
    """
    for logger_name in logging.root.manager.loggerDict:
        if logger_name.startswith("nn_translator"):
            logging.getLogger(logger_name).setLevel(level)
    
    # Установка уровня для корневого логгера
    root_logger = logging.getLogger("nn_translator")
    root_logger.setLevel(level)
    
    # Обновляем константу
    global LOG_LEVEL
    LOG_LEVEL = level 