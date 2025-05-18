import os
import torch
import psutil
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from typing import List, Optional, Dict, Any
from src.utils.logger import get_logger
import time

# Константы для модели
DEFAULT_MODEL_ID = "Helsinki-NLP/opus-mt-en-ru"
MAX_LENGTH = 512
NUM_BEAMS = 5
BATCH_SIZE = 8
MIN_TEXT_LENGTH = 1
MAX_TEXT_LENGTH = 5000
MAX_BATCH_TOTAL_LENGTH = 10000
MIN_FREE_MEMORY_GB = 2
MAX_MODEL_SIZE_GB = 10

class TranslationModel:
    """
    Handles translation using a pre-trained model
    """
    def __init__(self, model_id: str = "Helsinki-NLP/opus-mt-en-ru"):
        """
        Initialize the translation model
        
        Args:
            model_id: Model identifier from HuggingFace Hub
            
        Raises:
            RuntimeError: If model initialization fails
            ValueError: If model_id is invalid
        """
        self.logger = get_logger("nn_translator.model")
        self.logger.info(f"Initializing translation model: {model_id}")
        
        # Validate model_id
        if not isinstance(model_id, str):
            raise ValueError("Model ID must be a string")
        if not model_id.strip():
            raise ValueError("Model ID cannot be empty")
            
        self.model_id = model_id
        self.model = None
        self.tokenizer = None
        
        # Check GPU availability
        self.gpu_available = torch.cuda.is_available()
        if self.gpu_available:
            self.device = torch.device("cuda")
            self.logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
        else:
            self.device = torch.device("cpu")
            self.logger.warning("No GPU available, using CPU")
            
        # Check memory
        if not self._check_memory():
            raise RuntimeError("Not enough memory to load the model")
            
        try:
            # Load tokenizer
            self.logger.info("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(model_id)
            
            # Load model
            self.logger.info("Loading model...")
            self.model = AutoModelForSeq2SeqLM.from_pretrained(model_id)
            self.model.to(self.device)
            
            self.logger.info("Model loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading model: {e}", exc_info=True)
            raise RuntimeError(f"Failed to load model: {str(e)}")
    
    def _check_memory(self) -> bool:
        """
        Check if there is enough memory to load the model
        
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
    
    def _validate_text(self, text: str) -> None:
        """
        Validate input text
        
        Args:
            text: Text to validate
            
        Raises:
            ValueError: If text is invalid
        """
        if not isinstance(text, str):
            raise ValueError("Text must be a string")
            
        if not text.strip():
            raise ValueError("Text cannot be empty or contain only whitespace")
            
        if len(text) < MIN_TEXT_LENGTH:
            raise ValueError(f"Text is too short (minimum {MIN_TEXT_LENGTH} characters)")
            
        if len(text) > MAX_TEXT_LENGTH:
            raise ValueError(f"Text is too long (maximum {MAX_TEXT_LENGTH} characters)")
    
    def _validate_batch(self, texts: List[str]) -> None:
        """
        Validate batch of texts
        
        Args:
            texts: List of texts to validate
            
        Raises:
            ValueError: If texts are invalid
        """
        if not isinstance(texts, list):
            raise ValueError("Texts must be a list")
            
        if not texts:
            raise ValueError("Texts list cannot be empty")
            
        total_length = 0
        for i, text in enumerate(texts):
            if not isinstance(text, str):
                raise ValueError(f"Text at index {i} must be a string")
                
            if not text.strip():
                raise ValueError(f"Text at index {i} cannot be empty or contain only whitespace")
                
            if len(text) < MIN_TEXT_LENGTH:
                raise ValueError(f"Text at index {i} is too short (minimum {MIN_TEXT_LENGTH} characters)")
                
            if len(text) > MAX_TEXT_LENGTH:
                raise ValueError(f"Text at index {i} is too long (maximum {MAX_TEXT_LENGTH} characters)")
                
            total_length += len(text)
            
        if total_length > MAX_BATCH_TOTAL_LENGTH:
            raise ValueError(f"Total batch length exceeds maximum limit of {MAX_BATCH_TOTAL_LENGTH} characters")
    
    def translate(self, text: str) -> str:
        """
        Translate the given text from English to Russian
        
        Args:
            text: The text to translate
            
        Returns:
            Translated text
            
        Raises:
            RuntimeError: If model is not loaded
            ValueError: If text is invalid
        """
        try:
            # Validate model state
            if not self.model or not self.tokenizer:
                raise RuntimeError("Translation model is not loaded")
                
            # Validate input
            self._validate_text(text)
            
            # Tokenize
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate translation
            outputs = self.model.generate(
                **inputs,
                max_length=512,
                num_beams=5,
                length_penalty=0.6,
                early_stopping=True
            )
            
            # Decode
            translated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            self.logger.debug(f"Translated: '{text}' -> '{translated}'")
            return translated
            
        except RuntimeError:
            raise
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Error during translation: {e}", exc_info=True)
            raise RuntimeError(f"Translation failed: {str(e)}")
    
    def translate_batch(self, texts: List[str]) -> List[str]:
        """
        Translate a batch of texts from English to Russian
        
        Args:
            texts: List of texts to translate
            
        Returns:
            List of translated texts
            
        Raises:
            RuntimeError: If model is not loaded
            ValueError: If texts are invalid
        """
        try:
            # Validate model state
            if not self.model or not self.tokenizer:
                raise RuntimeError("Translation model is not loaded")
                
            # Validate input
            self._validate_batch(texts)
            
            # Tokenize
            inputs = self.tokenizer(texts, return_tensors="pt", padding=True, truncation=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate translations
            outputs = self.model.generate(
                **inputs,
                max_length=512,
                num_beams=5,
                length_penalty=0.6,
                early_stopping=True
            )
            
            # Decode
            translations = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)
            
            self.logger.debug(f"Translated batch of {len(texts)} texts")
            return translations
            
        except RuntimeError:
            raise
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Error during batch translation: {e}", exc_info=True)
            raise RuntimeError(f"Batch translation failed: {str(e)}")
    
    def unload(self) -> None:
        """
        Unload the model to free memory
        
        Raises:
            RuntimeError: If unloading fails
        """
        try:
            if self.model:
                self.model.cpu()
                del self.model
                self.model = None
                
            if self.tokenizer:
                del self.tokenizer
                self.tokenizer = None
                
            if self.gpu_available:
                torch.cuda.empty_cache()
                
            self.logger.info("Model unloaded successfully")
        except Exception as e:
            self.logger.error(f"Error unloading model: {e}", exc_info=True)
            raise RuntimeError(f"Failed to unload model: {str(e)}")
    
    def change_model(self, model_path: str, model_id: str):
        """
        Change the current model
        
        Args:
            model_path: Path to the new model files
            model_id: New model identifier
            
        Raises:
            RuntimeError: If model change fails
        """
        try:
            self.logger.info(f"Changing model to {model_id}")
            
            # Save old model info for error recovery
            old_model = self.model
            old_tokenizer = self.tokenizer
            
            # Update model info
            self.model_id = model_id
            
            # Try to load new model
            self._load_model()
            
            # If successful, clear old model from memory
            if old_model:
                del old_model
            if old_tokenizer:
                del old_tokenizer
                
            torch.cuda.empty_cache()
            
            self.logger.info("Model changed successfully")
        except Exception as e:
            self.logger.error(f"Error changing model: {e}", exc_info=True)
            raise RuntimeError(f"Failed to change model: {str(e)}")
    
    def _load_model(self):
        """Load the model and tokenizer"""
        try:
            self.logger.info(f"Loading model from {self.model_id}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            
            # Load model
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_id)
            
            # Move model to device
            self.model = self.model.to(self.device)
            
            self.logger.info("Model loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading model: {e}", exc_info=True)
            raise RuntimeError(f"Failed to load translation model: {str(e)}") 