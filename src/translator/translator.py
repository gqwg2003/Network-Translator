from .model import TranslationModel
from .model_manager import ModelManager
from typing import List, Optional, Dict, Any

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
        base_info = {
            "model_path": self.model.model_path,
            "model_id": self.model.model_id,
            "model_loaded": self.model.model is not None and self.model.tokenizer is not None
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
                
            # Get model path
            model_path = self.model_manager.get_model_path(model_id)
            
            # Change model
            self.model.change_model(model_path, model_id)
            self.current_model_id = model_id
            
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