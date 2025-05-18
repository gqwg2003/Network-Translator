"""
API utilities for Neural Network Translator
"""
import os
import json
import uuid
import logging
from typing import Dict, Any, Optional, Union, List, Tuple
from datetime import datetime

API_KEYS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "api_keys.json")
MAX_FILE_SIZE_GB = 1.0

logger = logging.getLogger("nn_translator.api_utils")

def _validate_api_key_format(api_key: str) -> None:
    if not isinstance(api_key, str):
        raise ValueError("API key must be a string")
    if not api_key:
        raise ValueError("API key cannot be empty")
    if not api_key.startswith("nt_"):
        raise ValueError("API key must start with 'nt_'")
    if len(api_key) < 32:
        raise ValueError("API key must be at least 32 characters long")
        
def _validate_metadata(metadata: Dict[str, Any]) -> None:
    if not isinstance(metadata, dict):
        raise ValueError("Metadata must be a dictionary")
    if "name" not in metadata:
        raise ValueError("Metadata must contain 'name' field")
    if not isinstance(metadata["name"], str):
        raise ValueError("Name must be a string")
    if not metadata["name"]:
        raise ValueError("Name cannot be empty")
        
def _check_file_size(file_path: str) -> bool:
    if os.path.exists(file_path):
        size_gb = os.path.getsize(file_path) / (1024 ** 3)
        if size_gb > MAX_FILE_SIZE_GB:
            raise RuntimeError(f"File size ({size_gb:.2f}GB) exceeds maximum limit ({MAX_FILE_SIZE_GB}GB)")
    return True

def generate_api_key(name: str) -> str:
    try:
        if not isinstance(name, str):
            raise ValueError("Name must be a string")
        if not name:
            raise ValueError("Name cannot be empty")
            
        api_key = f"nt_{uuid.uuid4().hex}"
        _validate_api_key_format(api_key)
        
        metadata = {
            "name": name,
            "created_at": datetime.utcnow().isoformat(),
            "last_used": None,
            "usage_count": 0
        }
        _validate_metadata(metadata)
        
        if not save_api_key(api_key, metadata):
            raise RuntimeError("Failed to save API key")
            
        return api_key
    except Exception as e:
        logger.error(f"Error generating API key: {e}", exc_info=True)
        raise RuntimeError(f"Failed to generate API key: {str(e)}")

def load_api_keys() -> Dict[str, Dict[str, Any]]:
    try:
        os.makedirs(os.path.dirname(API_KEYS_FILE), exist_ok=True)
        
        if os.path.exists(API_KEYS_FILE):
            try:
                _check_file_size(API_KEYS_FILE)
                
                with open(API_KEYS_FILE, 'r', encoding='utf-8') as f:
                    keys = json.load(f)
                    
                if not isinstance(keys, dict):
                    raise ValueError("Invalid API keys format: expected dictionary")
                    
                for key, metadata in keys.items():
                    _validate_api_key_format(key)
                    _validate_metadata(metadata)
                    
                return keys
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding API keys file: {e}")
                try:
                    backup_path = f"{API_KEYS_FILE}.bak"
                    os.rename(API_KEYS_FILE, backup_path)
                    logger.info(f"Backed up corrupted API keys to {backup_path}")
                except Exception as backup_error:
                    logger.error(f"Failed to backup corrupted API keys: {backup_error}")
                return {}
            except IOError as e:
                logger.error(f"Error reading API keys file: {e}")
                return {}
        return {}
    except Exception as e:
        logger.error(f"Error loading API keys: {e}", exc_info=True)
        raise RuntimeError(f"Failed to load API keys: {str(e)}")

def save_api_key(api_key: str, metadata: Dict[str, Any]) -> bool:
    try:
        _validate_api_key_format(api_key)
        _validate_metadata(metadata)
        
        keys = load_api_keys()
        
        if api_key in keys:
            logger.warning(f"API key {api_key} already exists")
            return False
            
        keys[api_key] = metadata
        
        temp_path = f"{API_KEYS_FILE}.tmp"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(keys, f, indent=2, ensure_ascii=False)
                
            _check_file_size(temp_path)
                
            os.replace(temp_path, API_KEYS_FILE)
            logger.info(f"API key {api_key} saved successfully")
            return True
        except Exception as e:
            try:
                os.remove(temp_path)
            except:
                pass
            raise e
    except Exception as e:
        logger.error(f"Error saving API key: {e}", exc_info=True)
        raise RuntimeError(f"Failed to save API key: {str(e)}")

def validate_api_key(api_key: str) -> bool:
    try:
        _validate_api_key_format(api_key)
        
        keys = load_api_keys()
        
        if api_key not in keys:
            return False
            
        metadata = keys[api_key]
        metadata["last_used"] = datetime.utcnow().isoformat()
        metadata["usage_count"] += 1
        
        if not save_api_key(api_key, metadata):
            logger.error(f"Failed to update API key metadata for {api_key}")
            
        return True
    except Exception as e:
        logger.error(f"Error validating API key: {e}", exc_info=True)
        return False

def revoke_api_key(api_key: str) -> bool:
    try:
        _validate_api_key_format(api_key)
        
        keys = load_api_keys()
        
        if api_key not in keys:
            logger.warning(f"API key {api_key} not found")
            return False
            
        del keys[api_key]
        
        temp_path = f"{API_KEYS_FILE}.tmp"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(keys, f, indent=2, ensure_ascii=False)
                
            _check_file_size(temp_path)
                
            os.replace(temp_path, API_KEYS_FILE)
            logger.info(f"API key {api_key} revoked successfully")
            return True
        except Exception as e:
            try:
                os.remove(temp_path)
            except:
                pass
            raise e
    except Exception as e:
        logger.error(f"Error revoking API key: {e}", exc_info=True)
        raise RuntimeError(f"Failed to revoke API key: {str(e)}")

def get_api_key_info(api_key: str) -> Optional[Dict[str, Any]]:
    try:
        _validate_api_key_format(api_key)
        
        keys = load_api_keys()
        
        if api_key not in keys:
            return None
            
        return keys[api_key]
    except Exception as e:
        logger.error(f"Error getting API key info: {e}", exc_info=True)
        raise RuntimeError(f"Failed to get API key info: {str(e)}")

def list_api_keys() -> List[Dict[str, Any]]:
    try:
        keys = load_api_keys()
        
        result = []
        for key, metadata in keys.items():
            result.append({
                "key": key,
                "name": metadata["name"],
                "created_at": metadata["created_at"],
                "last_used": metadata["last_used"],
                "usage_count": metadata["usage_count"]
            })
            
        return result
    except Exception as e:
        logger.error(f"Error listing API keys: {e}", exc_info=True)
        raise RuntimeError(f"Failed to list API keys: {str(e)}") 