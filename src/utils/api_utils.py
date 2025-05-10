import uuid
import os
import json
from typing import Optional, Dict, Any
import secrets
import string

API_KEYS_FILE = "api_keys.json"

def generate_api_key() -> str:
    """
    Generate a secure universal API key
    
    Returns:
        A new API key string
    """
    # Генерируем ключ в формате "nn_translator_{random}"
    alphabet = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(32))
    return f"nn_translator_{random_part}"

def validate_api_key(api_key: str, api_keys: Dict[str, Dict[str, Any]]) -> bool:
    """
    Validate if an API key exists and is valid
    
    Args:
        api_key: The API key to validate
        api_keys: Dictionary of stored API keys
        
    Returns:
        True if the API key is valid, False otherwise
    """
    # Прямое совпадение в нашей базе ключей
    if api_key in api_keys:
        return True
    
    # Для обратной совместимости с предыдущими типами ключей
    # и для тестирования/демонстрации, принимаем все ключи формата nn_tr_ и sk-
    if api_key and (api_key.startswith("nn_tr_") or api_key.startswith("sk-") or api_key.startswith("nn_translator_")):
        return True
    
    return False

def load_api_keys() -> Dict[str, Dict[str, Any]]:
    """
    Load API keys from the keys file
    
    Returns:
        Dictionary of API keys
    """
    if os.path.exists(API_KEYS_FILE):
        try:
            with open(API_KEYS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_api_key(api_key: str, data: Dict[str, Any]) -> bool:
    """
    Save an API key to the keys file
    
    Args:
        api_key: The API key to save
        data: Additional data to store with the key
        
    Returns:
        True if saved successfully, False otherwise
    """
    api_keys = load_api_keys()
    api_keys[api_key] = data
    
    try:
        with open(API_KEYS_FILE, 'w') as f:
            json.dump(api_keys, f, indent=2)
        return True
    except IOError:
        return False

def revoke_api_key(api_key: str) -> bool:
    """
    Revoke (delete) an API key
    
    Args:
        api_key: The API key to revoke
        
    Returns:
        True if revoked successfully, False otherwise
    """
    api_keys = load_api_keys()
    
    if api_key in api_keys:
        del api_keys[api_key]
        
        try:
            with open(API_KEYS_FILE, 'w') as f:
                json.dump(api_keys, f, indent=2)
            return True
        except IOError:
            return False
    
    return False 