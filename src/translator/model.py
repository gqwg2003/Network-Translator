import os
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from typing import List, Optional

class TranslationModel:
    def __init__(self, model_path: str = None, model_id: str = None):
        """
        Initialize the translation model
        
        Args:
            model_path: Path to the model directory
            model_id: Model identifier (for metadata)
        """
        if model_path is None:
            # Use default model path
            model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                    "models", "models--Helsinki-NLP--opus-mt-en-ru")
        
        self.model_path = model_path
        self.model_id = model_id or "Helsinki-NLP/opus-mt-en-ru"
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """Load the model and tokenizer from the specified path"""
        try:
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_path)
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            print(f"Model loaded successfully from {self.model_path}")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
    
    def change_model(self, model_path: str, model_id: str = None):
        """
        Change the current model to a different one
        
        Args:
            model_path: Path to the new model directory
            model_id: Model identifier (for metadata)
        """
        # Unload current model to free memory
        self.model = None
        self.tokenizer = None
        
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
        
        # Tokenize the input text
        inputs = self.tokenizer(text, return_tensors="pt", padding=True)
        
        # Generate translation
        outputs = self.model.generate(**inputs)
        
        # Decode the translated text
        translation = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        return translation
    
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
        
        # Tokenize the input texts
        inputs = self.tokenizer(texts, return_tensors="pt", padding=True)
        
        # Generate translations
        outputs = self.model.generate(**inputs)
        
        # Decode the translated texts
        translations = [self.tokenizer.decode(output, skip_special_tokens=True) 
                       for output in outputs]
        
        return translations 