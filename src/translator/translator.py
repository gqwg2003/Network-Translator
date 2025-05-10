from .model import TranslationModel
from typing import List, Optional

class Translator:
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the translator with a model
        
        Args:
            model_path: Optional path to the translation model
        """
        self.model = TranslationModel(model_path)
    
    def translate(self, text: str) -> str:
        """
        Translate a text from English to Russian
        
        Args:
            text: The text to translate
            
        Returns:
            The translated text
        """
        return self.model.translate(text)
    
    def translate_batch(self, texts: List[str]) -> List[str]:
        """
        Translate multiple texts
        
        Args:
            texts: List of texts to translate
            
        Returns:
            List of translated texts
        """
        return self.model.translate_batch(texts)
    
    def get_model_info(self) -> dict:
        """
        Get information about the loaded model
        
        Returns:
            Dictionary with model information
        """
        return {
            "model_path": self.model.model_path,
            "model_loaded": self.model.model is not None and self.model.tokenizer is not None
        } 