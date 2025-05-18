"""
Configuration utilities for Neural Network Translator
"""
import os
import json
import logging
from typing import Dict, Any, Optional, Union, List, Tuple

# Константы
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "config.json")
MIN_FREE_MEMORY_GB = 2
MAX_CONFIG_SIZE_GB = 1

# Валидаторы типов
TYPE_VALIDATORS = {
    str: lambda x: isinstance(x, str),
    int: lambda x: isinstance(x, int),
    float: lambda x: isinstance(x, float),
    bool: lambda x: isinstance(x, bool),
    list: lambda x: isinstance(x, list),
    dict: lambda x: isinstance(x, dict)
}

# Валидаторы значений
VALUE_VALIDATORS = {
    "server.port": lambda x: isinstance(x, int) and 1024 <= x <= 65535,
    "server.host": lambda x: isinstance(x, str) and len(x) > 0,
    "cache.enabled": lambda x: isinstance(x, bool),
    "cache.expiry_days": lambda x: isinstance(x, int) and 1 <= x <= 365,
    "cache.max_size_gb": lambda x: isinstance(x, (int, float)) and 0.1 <= x <= 10,
    "model.default": lambda x: isinstance(x, str) and len(x) > 0,
    "model.gpu_required": lambda x: isinstance(x, bool),
    "formatting.smart_quotes": lambda x: isinstance(x, bool),
    "formatting.russian_punctuation": lambda x: isinstance(x, bool),
    "formatting.normalize_whitespace": lambda x: isinstance(x, bool),
    "formatting.fix_common_issues": lambda x: isinstance(x, bool)
}

# Настройки по умолчанию
DEFAULT_CONFIG = {
    "server": {
        "host": "127.0.0.1",
        "port": 8000
    },
    "cache": {
        "enabled": True,
        "expiry_days": 30,
        "max_size_gb": 1
    },
    "model": {
        "default": "Helsinki-NLP/opus-mt-en-ru",
        "gpu_required": False
    },
    "formatting": {
        "smart_quotes": True,
        "russian_punctuation": True,
        "normalize_whitespace": True,
        "fix_common_issues": True
    }
}

# Настройка логирования
logger = logging.getLogger("nn_translator.config")

def _validate_setting(key: str, value: Any) -> bool:
    """
    Validate a setting value
    
    Args:
        key: The setting key
        value: The setting value
        
    Returns:
        True if the value is valid
        
    Raises:
        ValueError: If the value is invalid
    """
    # Check if we have a validator for this key
    if key in VALUE_VALIDATORS:
        if not VALUE_VALIDATORS[key](value):
            raise ValueError(f"Invalid value for setting {key}")
            
    # Check type based on default value
    for section, settings in DEFAULT_CONFIG.items():
        if key.startswith(f"{section}."):
            setting_name = key.split(".")[-1]
            if setting_name in settings:
                default_value = settings[setting_name]
                if not TYPE_VALIDATORS[type(default_value)](value):
                    raise ValueError(f"Invalid type for setting {key}")
                    
    return True

def _check_file_size(file_path: str) -> bool:
    """
    Check if file size is within limits
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if file size is within limits
        
    Raises:
        RuntimeError: If file size exceeds limit
    """
    if os.path.exists(file_path):
        size_gb = os.path.getsize(file_path) / (1024 ** 3)
        if size_gb > MAX_CONFIG_SIZE_GB:
            raise RuntimeError(f"File size ({size_gb:.2f}GB) exceeds maximum limit ({MAX_CONFIG_SIZE_GB}GB)")
    return True

def _load_config() -> Dict[str, Any]:
    """
    Load configuration from file
    
    Returns:
        Dictionary with configuration settings
        
    Raises:
        RuntimeError: If loading fails
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        
        if os.path.exists(CONFIG_FILE):
            try:
                # Check config file size
                _check_file_size(CONFIG_FILE)
                
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # Validate config format
                if not isinstance(config, dict):
                    raise ValueError("Invalid config format: expected dictionary")
                    
                # Validate each setting
                for key, value in config.items():
                    _validate_setting(key, value)
                    
                return config
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding config file: {e}")
                # Try to backup corrupted file
                try:
                    backup_path = f"{CONFIG_FILE}.bak"
                    os.rename(CONFIG_FILE, backup_path)
                    logger.info(f"Backed up corrupted config to {backup_path}")
                except Exception as backup_error:
                    logger.error(f"Failed to backup corrupted config: {backup_error}")
                return DEFAULT_CONFIG
            except IOError as e:
                logger.error(f"Error reading config file: {e}")
                return DEFAULT_CONFIG
        return DEFAULT_CONFIG
    except Exception as e:
        logger.error(f"Error loading config: {e}", exc_info=True)
        raise RuntimeError(f"Failed to load config: {str(e)}")

def _save_config(config: Dict[str, Any]) -> bool:
    """
    Save configuration to file
    
    Args:
        config: The configuration to save
        
    Returns:
        True if the config was saved successfully
        
    Raises:
        ValueError: If the config is invalid
        RuntimeError: If saving fails
    """
    try:
        # Validate each setting
        for key, value in config.items():
            _validate_setting(key, value)
            
        # Save to temporary file first
        temp_path = f"{CONFIG_FILE}.tmp"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
            # Check file size
            _check_file_size(temp_path)
                
            # Atomic rename
            os.replace(temp_path, CONFIG_FILE)
            logger.info("Config saved successfully")
            return True
        except Exception as e:
            # Clean up temporary file
            try:
                os.remove(temp_path)
            except:
                pass
            raise e
    except ValueError as e:
        logger.error(f"Validation error saving config: {e}")
        raise
    except Exception as e:
        logger.error(f"Error saving config: {e}", exc_info=True)
        raise RuntimeError(f"Failed to save config: {str(e)}")

def get_setting(key: str, default: Any = None) -> Any:
    """
    Get a configuration setting
    
    Args:
        key: The setting key
        default: Default value if setting is not found
        
    Returns:
        The setting value
        
    Raises:
        RuntimeError: If loading fails
    """
    try:
        config = _load_config()
        
        # Check if key exists
        if key in config:
            return config[key]
            
        # Check if key exists in default config
        for section, settings in DEFAULT_CONFIG.items():
            if key.startswith(f"{section}."):
                setting_name = key.split(".")[-1]
                if setting_name in settings:
                    return settings[setting_name]
                    
        return default
    except Exception as e:
        logger.error(f"Error getting setting {key}: {e}", exc_info=True)
        raise RuntimeError(f"Failed to get setting {key}: {str(e)}")

def set_setting(key: str, value: Any) -> bool:
    """
    Set a configuration setting
    
    Args:
        key: The setting key
        value: The setting value
        
    Returns:
        True if the setting was saved successfully
        
    Raises:
        ValueError: If the value is invalid
        RuntimeError: If saving fails
    """
    try:
        # Validate value
        _validate_setting(key, value)
        
        # Load current config
        config = _load_config()
        
        # Check for duplicates
        if key in config and config[key] == value:
            logger.info(f"Setting {key} already has value {value}")
            return True
        
        # Update setting
        config[key] = value
        
        # Save config
        return _save_config(config)
    except ValueError as e:
        logger.error(f"Validation error setting {key}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error setting {key}: {e}", exc_info=True)
        raise RuntimeError(f"Failed to set {key}: {str(e)}")

def get_all_settings() -> Dict[str, Any]:
    """
    Get all configuration settings
    
    Returns:
        Dictionary with all settings
        
    Raises:
        RuntimeError: If loading fails
    """
    try:
        config = _load_config()
        
        # Merge with default config
        result = {}
        for section, settings in DEFAULT_CONFIG.items():
            for key, value in settings.items():
                full_key = f"{section}.{key}"
                result[full_key] = config.get(full_key, value)
                
        return result
    except Exception as e:
        logger.error(f"Error getting all settings: {e}", exc_info=True)
        raise RuntimeError(f"Failed to get all settings: {str(e)}")

def reset_settings() -> bool:
    """
    Reset all settings to default values
    
    Returns:
        True if the settings were reset successfully
        
    Raises:
        RuntimeError: If reset fails
    """
    try:
        # Save default config
        return _save_config(DEFAULT_CONFIG)
    except Exception as e:
        logger.error(f"Error resetting settings: {e}", exc_info=True)
        raise RuntimeError(f"Failed to reset settings: {str(e)}") 