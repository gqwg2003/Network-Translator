import os
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from typing import List, Optional
from src.utils.logger import get_logger
import time

# Константы для модели
DEFAULT_MODEL_ID = "Helsinki-NLP/opus-mt-en-ru"
MAX_LENGTH = 512
NUM_BEAMS = 4
BATCH_SIZE = 8

class TranslationModel:
    def __init__(self, model_path: str = None, model_id: str = None):
        """
        Initialize the translation model
        
        Args:
            model_path: Path to the model directory
            model_id: Model identifier (for metadata)
        """
        # Инициализация логгера
        self.logger = get_logger("nn_translator.model")
        self.logger.info("Initializing translation model")
        
        if model_path is None:
            # Use default model path
            model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                    "models", "models--Helsinki-NLP--opus-mt-en-ru")
            self.logger.debug(f"Using default model path: {model_path}")
        
        self.model_path = model_path
        self.model_id = model_id or DEFAULT_MODEL_ID
        self.model = None
        self.tokenizer = None
        
        # Определение устройства для вычислений
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger.info(f"Using device: {self.device}")
        
        # Загрузка модели
        self._load_model()
    
    def _load_model(self):
        """Load the model and tokenizer from the specified path"""
        start_time = time.time()
        self.logger.info(f"Loading model from {self.model_path}")
        
        try:
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_path)
            self.model.to(self.device)
            self.model.eval()  # Set model to evaluation mode
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"Model loaded successfully in {elapsed_time:.2f} seconds (device: {self.device})")
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            raise
    
    def change_model(self, model_path: str, model_id: str = None):
        """
        Change the current model to a different one
        
        Args:
            model_path: Path to the new model directory
            model_id: Model identifier (for metadata)
        """
        self.logger.info(f"Changing model to {model_id or model_path}")
        
        # Unload current model to free memory
        self.logger.debug("Unloading current model to free memory")
        self.model = None
        self.tokenizer = None
        
        # Force garbage collection
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            self.logger.debug("CUDA cache cleared")
        
        # Update model path and ID
        self.model_path = model_path
        if model_id:
            self.model_id = model_id
            
        # Load the new model
        self._load_model()
    
    def translate(self, text: str) -> str:
        """
        Translate the given text from English to Russian
        
        Args:
            text: The text to translate
            
        Returns:
            The translated text
        """
        if not text:
            return ""
        
        start_time = time.time()
        self.logger.debug(f"Translating single text ({len(text)} chars)")
        
        try:
            with torch.inference_mode():
                # Tokenize the input text
                inputs = self.tokenizer(text, return_tensors="pt", padding=True)
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                # Generate translation
                outputs = self.model.generate(
                    **inputs,
                    max_length=MAX_LENGTH,
                    num_beams=NUM_BEAMS,
                    early_stopping=True
                )
                
                # Decode the translated text
                translation = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            elapsed_time = time.time() - start_time
            self.logger.debug(f"Translation completed in {elapsed_time:.2f} seconds, result: {len(translation)} chars")
            
            return translation
        except Exception as e:
            self.logger.error(f"Error during translation: {e}")
            return f"Error: {str(e)}"
    
    def translate_batch(self, texts: List[str]) -> List[str]:
        """
        Translate a batch of texts
        
        Args:
            texts: List of texts to translate
            
        Returns:
            List of translated texts
        """
        if not texts:
            return []
        
        start_time = time.time()
        self.logger.info(f"Translating batch of {len(texts)} texts")
        
        try:
            with torch.inference_mode():
                # Tokenize the input texts
                inputs = self.tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=MAX_LENGTH)
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                # Process in batches for better memory management
                translations = []
                
                for i in range(0, len(texts), BATCH_SIZE):
                    batch_start = time.time()
                    batch_texts = texts[i:i+BATCH_SIZE]
                    self.logger.debug(f"Processing batch {i//BATCH_SIZE + 1}/{(len(texts) + BATCH_SIZE - 1)//BATCH_SIZE}: {len(batch_texts)} texts")
                    
                    batch_inputs = {k: v[i:i+BATCH_SIZE] for k, v in inputs.items()}
                    
                    # Generate translations
                    outputs = self.model.generate(
                        **batch_inputs,
                        max_length=MAX_LENGTH,
                        num_beams=NUM_BEAMS,
                        early_stopping=True
                    )
                    
                    # Decode the translated texts
                    batch_translations = [self.tokenizer.decode(output, skip_special_tokens=True) 
                                         for output in outputs]
                    translations.extend(batch_translations)
                    
                    batch_elapsed = time.time() - batch_start
                    self.logger.debug(f"Batch processed in {batch_elapsed:.2f} seconds")
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"Batch translation completed in {elapsed_time:.2f} seconds, avg time per text: {elapsed_time/len(texts):.2f}s")
            
            return translations[:len(texts)]
        except Exception as e:
            self.logger.error(f"Error during batch translation: {e}")
            return [f"Error: {str(e)}"] * len(texts) 