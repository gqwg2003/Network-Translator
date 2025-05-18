from .model import TranslationModel
from .model_manager import ModelManager
from typing import List, Optional, Dict, Any
import json
import os
import hashlib
import time
from datetime import datetime, timedelta
from src.utils.text_formatter import TextFormatter
from src.utils.logger import get_logger
import torch
import psutil

# Константы для кэширования
CACHE_ENABLED_DEFAULT = True
CACHE_LIMIT_DEFAULT = 5000
CACHE_SAVE_INTERVAL = 20
TEXT_HASH_THRESHOLD = 100
CACHE_EXPIRY_DAYS = 30
CACHE_CLEANUP_INTERVAL = 1000
MIN_FREE_MEMORY_GB = 2
MAX_CACHE_SIZE_GB = 1

class Translator:
    def __init__(self, model_path: Optional[str] = None, model_id: Optional[str] = None):
        """
        Initialize the translator with a model
        
        Args:
            model_path: Optional path to the translation model
            model_id: Optional model identifier
        """
        # Инициализация логгера
        self.logger = get_logger("nn_translator.translator")
        self.logger.info("Initializing translator")
        
        # Initialize model manager
        self.model_manager = ModelManager()
        
        # Check GPU availability
        self.gpu_available = torch.cuda.is_available()
        if self.gpu_available:
            self.logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
        else:
            self.logger.warning("No GPU available, using CPU")
            
        # Check memory
        if not self._check_memory():
            raise RuntimeError("Not enough memory to initialize translator")
        
        try:
            # Get model path from manager if model_id is provided
            if model_id:
                model_path = self.model_manager.get_model_path(model_id)
                self.logger.debug(f"Using model path from model_id: {model_id} -> {model_path}")
            
            # Initialize model
            self.model = TranslationModel(model_id or "Helsinki-NLP/opus-mt-en-ru")
            self.current_model_id = model_id or "Helsinki-NLP/opus-mt-en-ru"
            self.logger.info(f"Translator initialized with model: {self.current_model_id}")
            
            # Initialize text formatting
            self.text_formatter = TextFormatter()
            self.formatting_options = {
                "smart_quotes": True,
                "russian_punctuation": True,
                "normalize_whitespace": True,
                "fix_common_issues": True
            }
            self.logger.debug(f"Text formatting options: {self.formatting_options}")
            
            # Initialize translation cache
            self.cache_enabled = CACHE_ENABLED_DEFAULT
            self.cache_limit = CACHE_LIMIT_DEFAULT
            self.translation_cache = {}
            self.cache_operations = 0
            self._load_cache()
        except Exception as e:
            self.logger.error(f"Error initializing translator: {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize translator: {str(e)}")
    
    def _check_memory(self) -> bool:
        """
        Check if there is enough memory to initialize translator
        
        Returns:
            True if there is enough memory
        """
        try:
            if self.gpu_available:
                # Check GPU memory
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
                return gpu_memory >= MIN_FREE_MEMORY_GB
            else:
                # Check RAM
                free_memory = psutil.virtual_memory().available / (1024 ** 3)
                return free_memory >= MIN_FREE_MEMORY_GB
        except Exception as e:
            self.logger.error(f"Error checking memory: {e}", exc_info=True)
            return False
    
    def _load_cache(self):
        """Load translation cache from disk if it exists"""
        if not self.cache_enabled:
            return
            
        cache_path = self._get_cache_path()
        if os.path.exists(cache_path):
            try:
                # Check cache file size
                cache_size = os.path.getsize(cache_path) / (1024 ** 3)  # Size in GB
                if cache_size > MAX_CACHE_SIZE_GB:
                    self.logger.warning(f"Cache file is too large ({cache_size:.2f}GB), clearing it")
                    self.clear_cache()
                    return
                
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    
                # Validate cache format
                if not isinstance(cache_data, dict):
                    raise ValueError("Invalid cache format: expected dictionary")
                    
                # Clean up expired entries
                current_time = time.time()
                expired_count = 0
                for key in list(cache_data.keys()):
                    entry = cache_data[key]
                    if not isinstance(entry, dict):
                        expired_count += 1
                        del cache_data[key]
                        continue
                        
                    # Validate entry format
                    required_fields = ['translation', 'model_id', 'timestamp']
                    if not all(field in entry for field in required_fields):
                        expired_count += 1
                        del cache_data[key]
                        continue
                        
                    timestamp = entry.get('timestamp', 0)
                    if current_time - timestamp > CACHE_EXPIRY_DAYS * 24 * 3600:
                        expired_count += 1
                        del cache_data[key]
                
                if expired_count > 0:
                    self.logger.info(f"Removed {expired_count} expired cache entries")
                
                self.translation_cache = cache_data
                self.logger.info(f"Loaded {len(self.translation_cache)} cached translations")
            except Exception as e:
                self.logger.error(f"Error loading translation cache: {e}", exc_info=True)
                self.translation_cache = {}
                # Try to backup corrupted cache
                try:
                    backup_path = f"{cache_path}.bak"
                    os.rename(cache_path, backup_path)
                    self.logger.info(f"Backed up corrupted cache to {backup_path}")
                except Exception as backup_error:
                    self.logger.error(f"Failed to backup corrupted cache: {backup_error}")
        else:
            self.logger.info("No translation cache found, starting with empty cache")
    
    def _save_cache(self):
        """Save translation cache to disk"""
        if not self.cache_enabled:
            return
            
        cache_path = self._get_cache_path()
        try:
            cache_dir = os.path.dirname(cache_path)
            os.makedirs(cache_dir, exist_ok=True)
            
            # Clean up old entries if cache is too large
            if len(self.translation_cache) > self.cache_limit:
                self.logger.info(f"Cache limit exceeded ({len(self.translation_cache)} > {self.cache_limit}), cleaning up")
                self._cleanup_cache()
            
            # Save cache to temporary file first
            temp_path = f"{cache_path}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.translation_cache, f, ensure_ascii=False)
            
            # Atomic rename
            os.replace(temp_path, cache_path)
            self.logger.debug(f"Saved {len(self.translation_cache)} cache entries to {cache_path}")
            
            # Reset operations counter
            self.cache_operations = 0
        except Exception as e:
            self.logger.error(f"Error saving translation cache: {e}", exc_info=True)
            # Try to recover from backup if available
            backup_path = f"{cache_path}.bak"
            if os.path.exists(backup_path):
                try:
                    os.replace(backup_path, cache_path)
                    self.logger.info("Recovered cache from backup")
                except Exception as recovery_error:
                    self.logger.error(f"Failed to recover cache from backup: {recovery_error}")
    
    def _cleanup_cache(self):
        """Clean up old cache entries"""
        try:
            current_time = time.time()
            expired_count = 0
            
            # Remove expired entries
            for key in list(self.translation_cache.keys()):
                entry = self.translation_cache[key]
                timestamp = entry.get('timestamp', 0)
                if current_time - timestamp > CACHE_EXPIRY_DAYS * 24 * 3600:
                    expired_count += 1
                    del self.translation_cache[key]
            
            if expired_count > 0:
                self.logger.info(f"Removed {expired_count} expired cache entries")
                
            # If still too large, remove oldest entries
            if len(self.translation_cache) > self.cache_limit:
                # Sort by timestamp
                sorted_entries = sorted(
                    self.translation_cache.items(),
                    key=lambda x: x[1].get('timestamp', 0)
                )
                
                # Remove oldest entries
                entries_to_remove = len(self.translation_cache) - self.cache_limit
                for key, _ in sorted_entries[:entries_to_remove]:
                    del self.translation_cache[key]
                    
                self.logger.info(f"Removed {entries_to_remove} oldest cache entries")
        except Exception as e:
            self.logger.error(f"Error cleaning up cache: {e}", exc_info=True)
            raise RuntimeError(f"Failed to clean up cache: {str(e)}")
    
    def _get_cache_path(self):
        """Get the path to the cache file"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cache_dir = os.path.join(base_dir, "cache")
        return os.path.join(cache_dir, f"translations_{self.current_model_id.replace('/', '_')}.json")
    
    def _get_cache_key(self, text):
        """Generate a unique cache key for a text"""
        # Use a hash for longer texts to keep keys manageable
        if len(text) > TEXT_HASH_THRESHOLD:
            return hashlib.md5(text.encode('utf-8')).hexdigest()
        # Use the text itself for shorter texts (faster lookup)
        return text
    
    def translate(self, text: str, apply_formatting: bool = True) -> str:
        """
        Translate a text from English to Russian
        
        Args:
            text: The text to translate
            apply_formatting: Whether to apply text formatting to the result
            
        Returns:
            The translated text
            
        Raises:
            ValueError: If text is invalid
            RuntimeError: If translation fails
        """
        if not text:
            return ""
        
        text_length = len(text)
        self.logger.info(f"Translating text ({text_length} chars), formatting: {apply_formatting}")
        self.logger.debug(f"Text sample: {text[:50]}...")
        
        start_time = time.time()
        
        # Check cache first if enabled
        cache_hit = False
        if self.cache_enabled:
            cache_key = self._get_cache_key(text)
            if cache_key in self.translation_cache:
                cached = self.translation_cache[cache_key]
                # Check if the cached translation is for the current model
                if cached.get('model_id') == self.current_model_id:
                    cache_hit = True
                    self.logger.debug("Cache hit")
                    # If formatting is requested but the cached version isn't formatted,
                    # or if we have a formatted version but formatting is not requested,
                    # we need to handle it
                    if apply_formatting and not cached.get('formatted', False):
                        translation = self.text_formatter.process_text(
                            cached.get('translation', ''), 
                            self.formatting_options
                        )
                        # Update cache with formatted version
                        cached['translation_formatted'] = translation
                        cached['formatted'] = True
                        self.translation_cache[cache_key] = cached
                        return translation
                    elif not apply_formatting and cached.get('formatted', False):
                        # Return raw translation if we have it
                        if 'translation_raw' in cached:
                            return cached['translation_raw']
                        else:
                            return cached['translation']  # Fallback to whatever we have
                    elif apply_formatting and cached.get('formatted', False):
                        # Return formatted version
                        if 'translation_formatted' in cached:
                            return cached['translation_formatted']
                        # Or format the raw version
                        elif 'translation' in cached:
                            return self.text_formatter.process_text(
                                cached['translation'],
                                self.formatting_options
                            )
                    else:
                        # No formatting needed, return raw
                        return cached.get('translation', '')
        
        # Perform translation
        self.logger.debug("Cache miss, performing translation" if self.cache_enabled else "Cache disabled, performing translation")
        translation_raw = self.model.translate(text)
        
        # Apply formatting if requested
        if apply_formatting:
            self.logger.debug("Applying text formatting")
            translation = self.text_formatter.process_text(translation_raw, self.formatting_options)
        else:
            translation = translation_raw
        
        # Cache the result
        if self.cache_enabled:
            cache_key = self._get_cache_key(text)
            self.translation_cache[cache_key] = {
                'translation': translation,
                'translation_raw': translation_raw,
                'translation_formatted': translation if apply_formatting else None,
                'model_id': self.current_model_id,
                'formatted': apply_formatting,
                'timestamp': time.time()
            }
            
            # Increment operations counter
            self.cache_operations += 1
            
            # Periodically save cache to disk
            if self.cache_operations >= CACHE_SAVE_INTERVAL:
                self.logger.debug(f"Saving cache (interval: {CACHE_SAVE_INTERVAL} translations)")
                self._save_cache()
            
            # Periodically clean up cache
            if self.cache_operations >= CACHE_CLEANUP_INTERVAL:
                self.logger.debug("Running cache cleanup")
                self._cleanup_cache()
                self.cache_operations = 0
        
        elapsed_time = time.time() - start_time
        self.logger.info(f"Translation completed in {elapsed_time:.2f} seconds, result length: {len(translation)} chars")
        
        return translation
    
    def translate_batch(self, texts: List[str], apply_formatting: bool = True) -> List[str]:
        """
        Translate multiple texts
        
        Args:
            texts: List of texts to translate
            apply_formatting: Whether to apply text formatting to the results
            
        Returns:
            List of translated texts
            
        Raises:
            ValueError: If texts are invalid
            RuntimeError: If translation fails
        """
        if not texts:
            return []
            
        # Check what's already cached
        translations = []
        uncached_texts = []
        uncached_indices = []
        
        if self.cache_enabled:
            for i, text in enumerate(texts):
                if not text:
                    translations.append("")
                    continue
                    
                cache_key = self._get_cache_key(text)
                if cache_key in self.translation_cache:
                    cached = self.translation_cache[cache_key]
                    if cached.get('model_id') == self.current_model_id:
                        # Similarly to the single translate method, handle various formatting cases
                        if apply_formatting and not cached.get('formatted', False):
                            if 'translation_raw' in cached:
                                trans = self.text_formatter.process_text(
                                    cached['translation_raw'], 
                                    self.formatting_options
                                )
                                cached['translation_formatted'] = trans
                                cached['formatted'] = True
                                self.translation_cache[cache_key] = cached
                                translations.append(trans)
                            else:
                                trans = self.text_formatter.process_text(
                                    cached.get('translation', ''), 
                                    self.formatting_options
                                )
                                cached['translation_formatted'] = trans
                                cached['formatted'] = True
                                self.translation_cache[cache_key] = cached
                                translations.append(trans)
                            continue
                        elif not apply_formatting and cached.get('formatted', False):
                            if 'translation_raw' in cached:
                                translations.append(cached['translation_raw'])
                            else:
                                translations.append(cached.get('translation', ''))
                            continue
                        elif apply_formatting and cached.get('formatted', False):
                            if 'translation_formatted' in cached:
                                translations.append(cached['translation_formatted'])
                            else:
                                translations.append(cached.get('translation', ''))
                            continue
                        else:
                            translations.append(cached.get('translation', ''))
                            continue
                
                # If we get here, the text wasn't cached or was for a different model
                uncached_texts.append(text)
                uncached_indices.append(i)
                # Add a placeholder that will be replaced with the actual translation
                translations.append(None)
        else:
            # If cache is disabled, translate everything
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))
            translations = [None] * len(texts)
        
        # Translate texts that weren't in the cache
        if uncached_texts:
            new_translations_raw = self.model.translate_batch(uncached_texts)
            
            # Apply formatting if requested
            if apply_formatting:
                new_translations = [
                    self.text_formatter.process_text(trans, self.formatting_options)
                    for trans in new_translations_raw
                ]
            else:
                new_translations = new_translations_raw
            
            # Update the results and cache
            for i, (idx, text, trans_raw, trans) in enumerate(zip(
                uncached_indices, uncached_texts, new_translations_raw, new_translations
            )):
                translations[idx] = trans
                
                if self.cache_enabled and text:  # Don't cache empty strings
                    cache_key = self._get_cache_key(text)
                    self.translation_cache[cache_key] = {
                        'translation': trans,
                        'translation_raw': trans_raw,
                        'translation_formatted': trans if apply_formatting else None,
                        'model_id': self.current_model_id,
                        'formatted': apply_formatting,
                        'timestamp': time.time()
                    }
            
            # Increment operations counter
            self.cache_operations += len(uncached_texts)
            
            # Save cache if we've added a significant number of new entries
            if self.cache_enabled and self.cache_operations >= CACHE_SAVE_INTERVAL:
                self._save_cache()
            
            # Clean up cache if needed
            if self.cache_enabled and self.cache_operations >= CACHE_CLEANUP_INTERVAL:
                self._cleanup_cache()
                self.cache_operations = 0
        
        return translations
    
    def clear_cache(self):
        """Clear the translation cache"""
        try:
            self.translation_cache = {}
            # Try to remove the cache file
            cache_path = self._get_cache_path()
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                    self.logger.info("Cache file removed")
                except Exception as e:
                    self.logger.warning(f"Error removing cache file: {e}")
            
            # Also try to remove backup if it exists
            backup_path = f"{cache_path}.bak"
            if os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                    self.logger.info("Cache backup file removed")
                except Exception as e:
                    self.logger.warning(f"Error removing cache backup file: {e}")
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}", exc_info=True)
            raise RuntimeError(f"Failed to clear cache: {str(e)}")
    
    def set_cache_enabled(self, enabled: bool):
        """Enable or disable the translation cache"""
        try:
            # If enabling the cache and it was previously disabled, try to load it
            if enabled and not self.cache_enabled:
                self._load_cache()
            # If disabling the cache, save any pending changes
            elif not enabled and self.cache_enabled:
                self._save_cache()
            
            self.cache_enabled = enabled
            self.logger.info(f"Cache {'enabled' if enabled else 'disabled'}")
        except Exception as e:
            self.logger.error(f"Error changing cache state: {e}", exc_info=True)
            raise RuntimeError(f"Failed to change cache state: {str(e)}")
    
    def get_model_info(self) -> dict:
        """
        Get information about the loaded model
        
        Returns:
            Dictionary with model information
        """
        try:
            base_info = {
                "model_path": self.model.model_path,
                "model_id": self.model.model_id,
                "model_loaded": self.model.model is not None and self.model.tokenizer is not None,
                "cache_enabled": self.cache_enabled,
                "cache_entries": len(self.translation_cache) if self.cache_enabled else 0,
                "gpu_available": self.gpu_available
            }
            
            # Get additional metadata if available
            if self.model.model_id in self.model_manager.model_metadata:
                metadata = self.model_manager.model_metadata[self.model.model_id]
                base_info.update({
                    "display_name": metadata.get("display_name", self.model.model_id),
                    "quality": metadata.get("quality", 0),
                    "quality_description": metadata.get("quality_description", ""),
                    "gpu_required": metadata.get("gpu_required", False)
                })
                
            return base_info
        except Exception as e:
            self.logger.error(f"Error getting model info: {e}", exc_info=True)
            raise RuntimeError(f"Failed to get model info: {str(e)}")
    
    def change_model(self, model_id: str) -> bool:
        """
        Change the current translation model
        
        Args:
            model_id: The identifier of the model to switch to
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            RuntimeError: If model change fails
        """
        try:
            # Check if model is available
            if model_id not in self.model_manager.model_metadata:
                raise ValueError(f"Model {model_id} not found")
                
            # Check if model is downloaded
            metadata = self.model_manager.model_metadata[model_id]
            if not metadata.get("downloaded", False):
                raise ValueError(f"Model {model_id} is not downloaded")
                
            # Check GPU requirement
            if metadata.get("gpu_required", False) and not self.gpu_available:
                raise ValueError(f"Model {model_id} requires GPU, but no GPU is available")
                
            # Save current cache before changing model
            if self.cache_enabled:
                self._save_cache()
                
            # Get model path
            model_path = self.model_manager.get_model_path(model_id)
            
            # Change model
            self.model.change_model(model_path, model_id)
            self.current_model_id = model_id
            
            # Load cache for the new model
            if self.cache_enabled:
                self.translation_cache = {}
                self._load_cache()
            
            self.logger.info(f"Successfully changed model to {model_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error changing model: {e}", exc_info=True)
            raise RuntimeError(f"Failed to change model: {str(e)}")
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Get a list of available models
        
        Returns:
            List of model metadata dictionaries
        """
        try:
            return self.model_manager.get_available_models()
        except Exception as e:
            self.logger.error(f"Error getting available models: {e}", exc_info=True)
            raise RuntimeError(f"Failed to get available models: {str(e)}")
    
    def get_downloaded_models(self) -> List[Dict[str, Any]]:
        """
        Get a list of downloaded models
        
        Returns:
            List of downloaded model metadata dictionaries
        """
        try:
            return self.model_manager.get_downloaded_models()
        except Exception as e:
            self.logger.error(f"Error getting downloaded models: {e}", exc_info=True)
            raise RuntimeError(f"Failed to get downloaded models: {str(e)}")
    
    def download_model(self, model_id: str, callback=None) -> bool:
        """
        Download a model
        
        Args:
            model_id: Model identifier
            callback: Function to call with progress updates
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            RuntimeError: If download fails
        """
        try:
            success, message = self.model_manager.download_model(model_id, callback)
            if not success:
                raise RuntimeError(message)
            return True
        except Exception as e:
            self.logger.error(f"Error downloading model: {e}", exc_info=True)
            raise RuntimeError(f"Failed to download model: {str(e)}")
    
    def set_formatting_options(self, options: Dict[str, bool]):
        """
        Set text formatting options
        
        Args:
            options: Dictionary with formatting options
            
        Raises:
            ValueError: If options are invalid
        """
        try:
            # Validate options
            for key, value in options.items():
                if key not in self.formatting_options:
                    raise ValueError(f"Invalid formatting option: {key}")
                if not isinstance(value, bool):
                    raise ValueError(f"Formatting option {key} must be a boolean")
            
            self.formatting_options.update(options)
            self.logger.info(f"Updated formatting options: {self.formatting_options}")
        except Exception as e:
            self.logger.error(f"Error setting formatting options: {e}", exc_info=True)
            raise ValueError(f"Failed to set formatting options: {str(e)}")
    
    def get_formatting_options(self) -> Dict[str, bool]:
        """
        Get current text formatting options
        
        Returns:
            Dictionary with current formatting options
        """
        return dict(self.formatting_options) 