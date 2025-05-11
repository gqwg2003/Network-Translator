from .model import TranslationModel
from .model_manager import ModelManager
from typing import List, Optional, Dict, Any
import json
import os
import hashlib
import time
from src.utils.text_formatter import TextFormatter

class Translator:
    def __init__(self, model_path: Optional[str] = None, model_id: Optional[str] = None):
        """
        Initialize the translator with a model
        
        Args:
            model_path: Optional path to the translation model
            model_id: Optional model identifier
        """
        # Initialize model manager
        self.model_manager = ModelManager()
        
        # Get model path from manager if model_id is provided
        if model_id:
            model_path = self.model_manager.get_model_path(model_id)
        
        # Initialize model
        self.model = TranslationModel(model_path, model_id)
        self.current_model_id = model_id or "Helsinki-NLP/opus-mt-en-ru"
        
        # Initialize translation cache
        self.cache_enabled = True
        self.cache_limit = 5000  # Maximum number of cached translations
        self.translation_cache = {}
        self._load_cache()
        
        # Initialize text formatting
        self.text_formatter = TextFormatter()
        self.formatting_options = {
            "smart_quotes": True,
            "russian_punctuation": True,
            "normalize_whitespace": True,
            "fix_common_issues": True
        }
    
    def _load_cache(self):
        """Load translation cache from disk if it exists"""
        cache_path = self._get_cache_path()
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    self.translation_cache = json.load(f)
                print(f"Loaded {len(self.translation_cache)} cached translations")
            except Exception as e:
                print(f"Error loading translation cache: {e}")
                self.translation_cache = {}
    
    def _save_cache(self):
        """Save translation cache to disk"""
        if not self.cache_enabled:
            return
            
        cache_path = self._get_cache_path()
        try:
            cache_dir = os.path.dirname(cache_path)
            os.makedirs(cache_dir, exist_ok=True)
            
            # If cache is too large, remove oldest entries
            if len(self.translation_cache) > self.cache_limit:
                # Convert to list of tuples for sorting
                cache_items = list(self.translation_cache.items())
                # Sort by timestamp (assuming each value has a 'timestamp' field)
                cache_items.sort(key=lambda x: x[1].get('timestamp', 0))
                # Remove the oldest items
                items_to_remove = len(cache_items) - self.cache_limit
                reduced_cache = dict(cache_items[items_to_remove:])
                self.translation_cache = reduced_cache
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.translation_cache, f, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving translation cache: {e}")
    
    def _get_cache_path(self):
        """Get the path to the cache file"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cache_dir = os.path.join(base_dir, "cache")
        return os.path.join(cache_dir, f"translations_{self.current_model_id.replace('/', '_')}.json")
    
    def _get_cache_key(self, text):
        """Generate a unique cache key for a text"""
        # Use a hash for longer texts to keep keys manageable
        if len(text) > 100:
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
        """
        if not text:
            return ""
            
        # Check cache first if enabled
        if self.cache_enabled:
            cache_key = self._get_cache_key(text)
            if cache_key in self.translation_cache:
                cached = self.translation_cache[cache_key]
                # Check if the cached translation is for the current model
                if cached.get('model_id') == self.current_model_id:
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
        translation_raw = self.model.translate(text)
        
        # Apply formatting if requested
        if apply_formatting:
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
            
            # Periodically save cache to disk (every 20 translations)
            if len(self.translation_cache) % 20 == 0:
                self._save_cache()
                
        return translation
    
    def translate_batch(self, texts: List[str], apply_formatting: bool = True) -> List[str]:
        """
        Translate multiple texts
        
        Args:
            texts: List of texts to translate
            apply_formatting: Whether to apply text formatting to the results
            
        Returns:
            List of translated texts
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
            
            # Save cache if we've added a significant number of new entries
            if self.cache_enabled and len(uncached_texts) >= 5:
                self._save_cache()
        
        return translations
    
    def clear_cache(self):
        """Clear the translation cache"""
        self.translation_cache = {}
        # Try to remove the cache file
        cache_path = self._get_cache_path()
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
            except Exception as e:
                print(f"Error removing cache file: {e}")
    
    def set_cache_enabled(self, enabled: bool):
        """Enable or disable the translation cache"""
        # If enabling the cache and it was previously disabled, try to load it
        if enabled and not self.cache_enabled:
            self._load_cache()
        # If disabling the cache, save any pending changes
        elif not enabled and self.cache_enabled:
            self._save_cache()
        
        self.cache_enabled = enabled
    
    def get_model_info(self) -> dict:
        """
        Get information about the loaded model
        
        Returns:
            Dictionary with model information
        """
        base_info = {
            "model_path": self.model.model_path,
            "model_id": self.model.model_id,
            "model_loaded": self.model.model is not None and self.model.tokenizer is not None,
            "cache_enabled": self.cache_enabled,
            "cache_entries": len(self.translation_cache) if self.cache_enabled else 0
        }
        
        # Get additional metadata if available
        if self.model.model_id in self.model_manager.model_metadata:
            metadata = self.model_manager.model_metadata[self.model.model_id]
            base_info.update({
                "display_name": metadata.get("display_name", self.model.model_id),
                "quality": metadata.get("quality", 0),
                "quality_description": metadata.get("quality_description", "")
            })
            
        return base_info
    
    def change_model(self, model_id: str) -> bool:
        """
        Change the current translation model
        
        Args:
            model_id: The identifier of the model to switch to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if model is available
            if model_id not in self.model_manager.model_metadata:
                return False
                
            # Check if model is downloaded
            metadata = self.model_manager.model_metadata[model_id]
            if not metadata.get("downloaded", False):
                return False
                
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
            
            return True
        except Exception as e:
            print(f"Error changing model: {e}")
            return False
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Get a list of available models
        
        Returns:
            List of model metadata dictionaries
        """
        return self.model_manager.get_available_models()
    
    def get_downloaded_models(self) -> List[Dict[str, Any]]:
        """
        Get a list of downloaded models
        
        Returns:
            List of downloaded model metadata dictionaries
        """
        return self.model_manager.get_downloaded_models()
    
    def download_model(self, model_id: str, callback=None) -> bool:
        """
        Download a model
        
        Args:
            model_id: Model identifier
            callback: Function to call with progress updates
            
        Returns:
            True if successful, False otherwise
        """
        success, _ = self.model_manager.download_model(model_id, callback)
        return success
    
    def set_formatting_options(self, options: Dict[str, bool]):
        """
        Set text formatting options
        
        Args:
            options: Dictionary with formatting options
        """
        self.formatting_options.update(options)
    
    def get_formatting_options(self) -> Dict[str, bool]:
        """
        Get current text formatting options
        
        Returns:
            Dictionary with current formatting options
        """
        return dict(self.formatting_options) 