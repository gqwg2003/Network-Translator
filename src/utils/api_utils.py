"""
API utilities for Neural Network Translator
"""
import os
import json
import logging
import secrets
import string
from typing import Dict, Any, Optional
from datetime import datetime

# Константы
API_KEYS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "api_keys.json")
MIN_KEY_LENGTH = 10
MAX_KEY_LENGTH = 100
MAX_FILE_SIZE_GB = 1.0
KEY_PREFIXES = ["nn_tr_", "sk-", "nn_translator_"]
REQUIRED_METADATA = ["created_at"]

# Настройка логирования
logger = logging.getLogger("nn_translator.api_utils")

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
        if size_gb > MAX_FILE_SIZE_GB:
            raise RuntimeError(f"File size ({size_gb:.2f}GB) exceeds maximum limit ({MAX_FILE_SIZE_GB}GB)")
    return True

def _validate_api_key_format(api_key: str) -> bool:
    """
    Validate API key format
    
    Args:
        api_key: The API key to validate
        
    Returns:
        True if the format is valid
        
    Raises:
        ValueError: If the format is invalid
    """
    if not api_key:
        raise ValueError("API key cannot be empty")
        
    if not any(api_key.startswith(prefix) for prefix in KEY_PREFIXES):
        raise ValueError(f"API key must start with one of: {', '.join(KEY_PREFIXES)}")
        
    if len(api_key) < MIN_KEY_LENGTH:
        raise ValueError(f"API key is too short (minimum {MIN_KEY_LENGTH} characters)")
        
    if len(api_key) > MAX_KEY_LENGTH:
        raise ValueError(f"API key is too long (maximum {MAX_KEY_LENGTH} characters)")
        
    return True

def _validate_metadata(metadata: Dict[str, Any]) -> bool:
    """
    Validate API key metadata
    
    Args:
        metadata: The metadata to validate
        
    Returns:
        True if the metadata is valid
        
    Raises:
        ValueError: If the metadata is invalid
    """
    if not isinstance(metadata, dict):
        raise ValueError("Metadata must be a dictionary")
        
    for field in REQUIRED_METADATA:
        if field not in metadata:
            raise ValueError(f"Missing required metadata field: {field}")
            
    if not isinstance(metadata["created_at"], str):
        raise ValueError("created_at must be a string")
        
    try:
        datetime.fromisoformat(metadata["created_at"].replace('Z', '+00:00'))
    except ValueError:
        raise ValueError("created_at must be a valid ISO format datetime")
        
    return True

def generate_api_key() -> str:
    """
    Generate a new API key
    
    Returns:
        The generated API key
        
    Raises:
        RuntimeError: If key generation fails
    """
    try:
        # Load existing keys to check for duplicates
        api_keys = load_api_keys()
        
        # Generate random bytes
        random_bytes = secrets.token_bytes(32)
        
        # Convert to hex string
        hex_string = random_bytes.hex()
        
        # Add prefix
        api_key = f"nn_tr_{hex_string}"
        
        # Check for duplicates
        if api_key in api_keys:
            logger.warning("Generated duplicate API key, retrying...")
            return generate_api_key()
        
        # Validate format
        _validate_api_key_format(api_key)
        
        return api_key
    except ValueError as e:
        logger.error(f"Validation error generating API key: {e}")
        raise
    except Exception as e:
        logger.error(f"Error generating API key: {e}", exc_info=True)
        raise RuntimeError(f"Failed to generate API key: {str(e)}")

def validate_api_key(api_key: str, api_keys: Optional[Dict[str, Dict[str, Any]]] = None) -> bool:
    """
    Validate an API key
    
    Args:
        api_key: The API key to validate
        api_keys: Optional dictionary of API keys to validate against
        
    Returns:
        True if the key is valid
        
    Raises:
        ValueError: If the key is invalid
        RuntimeError: If validation fails
    """
    try:
        # Validate format
        _validate_api_key_format(api_key)
        
        # Load keys if not provided
        if api_keys is None:
            api_keys = load_api_keys()
            
        # Check if key exists
        if api_key not in api_keys:
            raise ValueError("API key not found")
            
        # Validate metadata
        _validate_metadata(api_keys[api_key])
        
        return True
    except ValueError as e:
        logger.error(f"Validation error validating API key: {e}")
        raise
    except Exception as e:
        logger.error(f"Error validating API key: {e}", exc_info=True)
        raise RuntimeError(f"Failed to validate API key: {str(e)}")

def load_api_keys() -> Dict[str, Dict[str, Any]]:
    """
    Load API keys from file
    
    Returns:
        Dictionary of API keys and their metadata
        
    Raises:
        RuntimeError: If loading fails
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(API_KEYS_FILE), exist_ok=True)
        
        if os.path.exists(API_KEYS_FILE):
            try:
                # Check file size
                _check_file_size(API_KEYS_FILE)
                
                with open(API_KEYS_FILE, 'r', encoding='utf-8') as f:
                    api_keys = json.load(f)
                    
                # Validate format
                if not isinstance(api_keys, dict):
                    raise ValueError("Invalid API keys format: expected dictionary")
                    
                # Validate each key and its metadata
                for key, metadata in api_keys.items():
                    _validate_api_key_format(key)
                    _validate_metadata(metadata)
                    
                return api_keys
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding API keys file: {e}")
                # Try to backup corrupted file
                try:
                    backup_path = f"{API_KEYS_FILE}.bak"
                    os.rename(API_KEYS_FILE, backup_path)
                    logger.info(f"Backed up corrupted API keys file to {backup_path}")
                except Exception as backup_error:
                    logger.error(f"Failed to backup corrupted API keys file: {backup_error}")
                return {}
            except IOError as e:
                logger.error(f"Error reading API keys file: {e}")
                return {}
        return {}
    except Exception as e:
        logger.error(f"Error loading API keys: {e}", exc_info=True)
        raise RuntimeError(f"Failed to load API keys: {str(e)}")

def save_api_key(api_key: str, metadata: Dict[str, Any]) -> bool:
    """
    Save a new API key
    
    Args:
        api_key: The API key to save
        metadata: The metadata for the key
        
    Returns:
        True if the key was saved successfully
        
    Raises:
        ValueError: If the key or metadata is invalid
        RuntimeError: If saving fails
    """
    try:
        # Validate key and metadata
        _validate_api_key_format(api_key)
        _validate_metadata(metadata)
        
        # Load existing keys
        api_keys = load_api_keys()
        
        # Check for duplicates
        if api_key in api_keys:
            raise ValueError("API key already exists")
            
        # Add new key
        api_keys[api_key] = metadata
        
        # Save to temporary file first
        temp_path = f"{API_KEYS_FILE}.tmp"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(api_keys, f, indent=2, ensure_ascii=False)
                
            # Check file size
            _check_file_size(temp_path)
                
            # Atomic rename
            os.replace(temp_path, API_KEYS_FILE)
            logger.info(f"Saved new API key: {api_key}")
            return True
        except Exception as e:
            # Clean up temporary file
            try:
                os.remove(temp_path)
            except:
                pass
            raise e
    except ValueError as e:
        logger.error(f"Validation error saving API key: {e}")
        raise
    except Exception as e:
        logger.error(f"Error saving API key: {e}", exc_info=True)
        raise RuntimeError(f"Failed to save API key: {str(e)}")

def revoke_api_key(api_key: str) -> bool:
    """
    Revoke an API key
    
    Args:
        api_key: The API key to revoke
        
    Returns:
        True if the key was revoked successfully
        
    Raises:
        ValueError: If the key is invalid
        RuntimeError: If revocation fails
    """
    try:
        # Validate format
        _validate_api_key_format(api_key)
        
        # Load existing keys
        api_keys = load_api_keys()
        
        # Check if key exists
        if api_key not in api_keys:
            raise ValueError("API key not found")
            
        # Remove key
        del api_keys[api_key]
        
        # Save to temporary file first
        temp_path = f"{API_KEYS_FILE}.tmp"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(api_keys, f, indent=2, ensure_ascii=False)
                
            # Check file size
            _check_file_size(temp_path)
                
            # Atomic rename
            os.replace(temp_path, API_KEYS_FILE)
            logger.info(f"Revoked API key: {api_key}")
            return True
        except Exception as e:
            # Clean up temporary file
            try:
                os.remove(temp_path)
            except:
                pass
            raise e
    except ValueError as e:
        logger.error(f"Validation error revoking API key: {e}")
        raise
    except Exception as e:
        logger.error(f"Error revoking API key: {e}", exc_info=True)
        raise RuntimeError(f"Failed to revoke API key: {str(e)}") 