import json
import os
from typing import Dict, Any, Optional

# Путь к файлу настроек
SETTINGS_FILE = "app_settings.json"

# Структура настроек по умолчанию
DEFAULT_SETTINGS = {
    "server": {
        "host": "127.0.0.1",
        "port": 8000
    },
    "translator": {
        "last_text": "",
        "last_translation": ""
    },
    "batch_translator": {
        "texts": []
    },
    "theme": "dark_blue",
    "api": {
        "last_key": ""
    },
    "window": {
        "width": 900,
        "height": 700
    }
}

def load_settings() -> Dict[str, Any]:
    """
    Загрузка настроек из файла
    
    Returns:
        Словарь с настройками приложения
    """
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                # Объединяем с настройками по умолчанию,
                # чтобы добавить новые параметры, если они появились
                merged_settings = DEFAULT_SETTINGS.copy()
                deep_merge(merged_settings, settings)
                return merged_settings
        except (json.JSONDecodeError, IOError):
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()

def save_settings(settings: Dict[str, Any]) -> bool:
    """
    Сохранение настроек в файл
    
    Args:
        settings: Словарь с настройками для сохранения
        
    Returns:
        True если сохранено успешно, иначе False
    """
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return True
    except IOError:
        return False

def get_setting(key: str, default: Any = None) -> Any:
    """
    Получить значение настройки по ключу
    
    Args:
        key: Ключ настройки в формате "section.key" или просто "key"
        default: Значение по умолчанию, если настройка не найдена
        
    Returns:
        Значение настройки или default, если настройка не найдена
    """
    settings = load_settings()
    
    if '.' in key:
        # Обработка вложенных ключей
        sections = key.split('.')
        value = settings
        for section in sections:
            if section in value:
                value = value[section]
            else:
                return default
        return value
    else:
        # Обычный ключ верхнего уровня
        return settings.get(key, default)

def set_setting(key: str, value: Any) -> bool:
    """
    Установить значение настройки
    
    Args:
        key: Ключ настройки в формате "section.key" или просто "key"
        value: Значение для установки
        
    Returns:
        True если установка прошла успешно, иначе False
    """
    settings = load_settings()
    
    if '.' in key:
        # Обработка вложенных ключей
        sections = key.split('.')
        target = settings
        for section in sections[:-1]:
            if section not in target:
                target[section] = {}
            target = target[section]
        target[sections[-1]] = value
    else:
        # Обычный ключ верхнего уровня
        settings[key] = value
    
    return save_settings(settings)

def deep_merge(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    """
    Глубокое объединение двух словарей
    
    Args:
        target: Целевой словарь
        source: Исходный словарь, значения которого будут добавлены в target
    """
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            deep_merge(target[key], value)
        else:
            target[key] = value 