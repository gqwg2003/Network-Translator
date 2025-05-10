import os
import json
import shutil
import requests
from typing import List, Dict, Any, Optional, Tuple
from tqdm import tqdm
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from huggingface_hub import snapshot_download
from pathlib import Path

class ModelManager:
    """
    Manages multiple translation models, including downloading, selection, and quality ratings
    """
    def __init__(self, models_dir: str = None):
        """
        Initialize the model manager
        
        Args:
            models_dir: Directory to store models
        """
        if models_dir is None:
            # Use default models directory
            self.models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
        else:
            self.models_dir = models_dir
            
        # Ensure models directory exists
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Path to model metadata file
        self.metadata_file = os.path.join(self.models_dir, "models_metadata.json")
        
        # Load or create model metadata
        self.model_metadata = self._load_metadata()
        
        # Set default model
        self.default_model_id = "Helsinki-NLP/opus-mt-en-ru"
        
    def _load_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Load model metadata from file or create default
        
        Returns:
            Dictionary with model metadata
        """
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
                
        # Default metadata with predefined models
        default_metadata = {
            "Helsinki-NLP/opus-mt-en-ru": {
                "name": "Helsinki-NLP/opus-mt-en-ru",
                "display_name": "Helsinki-NLP Opus MT (English → Russian)",
                "quality": 85,
                "quality_description": "Высокое качество перевода",
                "description": "Базовая модель для перевода с английского на русский",
                "local_path": None,
                "downloaded": self._check_model_downloaded("Helsinki-NLP/opus-mt-en-ru"),
                "default": True
            },
            "facebook/m2m100_418M": {
                "name": "facebook/m2m100_418M",
                "display_name": "Facebook M2M100 (418M)",
                "quality": 80,
                "quality_description": "Хорошее качество перевода",
                "description": "Многоязычная модель перевода среднего размера",
                "local_path": None,
                "downloaded": self._check_model_downloaded("facebook/m2m100_418M"),
                "default": False
            },
            "facebook/nllb-200-distilled-600M": {
                "name": "facebook/nllb-200-distilled-600M",
                "display_name": "Facebook NLLB-200 (600M)",
                "quality": 90,
                "quality_description": "Превосходное качество перевода",
                "description": "Дистиллированная модель для 200 языков, включая русский",
                "local_path": None,
                "downloaded": self._check_model_downloaded("facebook/nllb-200-distilled-600M"),
                "default": False
            }
        }
        
        # Save default metadata
        self._save_metadata(default_metadata)
        return default_metadata
    
    def _save_metadata(self, metadata: Dict[str, Dict[str, Any]]) -> None:
        """
        Save model metadata to file
        
        Args:
            metadata: Dictionary with model metadata
        """
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving model metadata: {e}")
    
    def _check_model_downloaded(self, model_id: str) -> bool:
        """
        Check if a model is already downloaded
        
        Args:
            model_id: Model identifier
            
        Returns:
            True if the model is downloaded
        """
        model_dir = os.path.join(self.models_dir, f"models--{model_id.replace('/', '--')}")
        return os.path.exists(model_dir)
    
    def get_model_path(self, model_id: str) -> str:
        """
        Get the local path for a model
        
        Args:
            model_id: Model identifier
            
        Returns:
            Path to the model directory
        """
        if model_id in self.model_metadata and self.model_metadata[model_id]["downloaded"]:
            if self.model_metadata[model_id]["local_path"]:
                return self.model_metadata[model_id]["local_path"]
            else:
                return os.path.join(self.models_dir, f"models--{model_id.replace('/', '--')}")
        else:
            # Return default model path if model is not available
            return os.path.join(self.models_dir, f"models--{self.default_model_id.replace('/', '--')}")
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Get list of available models with metadata
        
        Returns:
            List of model metadata dictionaries
        """
        return list(self.model_metadata.values())
    
    def get_downloaded_models(self) -> List[Dict[str, Any]]:
        """
        Get list of downloaded models
        
        Returns:
            List of downloaded model metadata dictionaries
        """
        return [model for model in self.model_metadata.values() if model["downloaded"]]
    
    def download_model(self, model_id: str, callback=None) -> Tuple[bool, str]:
        """
        Download a model from HuggingFace Hub
        
        Args:
            model_id: Model identifier
            callback: Function to call with progress updates
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Create model dir with huggingface structure
            model_dir = os.path.join(self.models_dir, f"models--{model_id.replace('/', '--')}")
            
            # Progress callback for progress reporting
            def download_progress(progress):
                if callback:
                    callback(progress)
            
            # Download the model files
            snapshot_download(
                repo_id=model_id,
                local_dir=model_dir,
                local_dir_use_symlinks=False
            )
            
            # Update metadata
            if model_id in self.model_metadata:
                self.model_metadata[model_id]["downloaded"] = True
                self.model_metadata[model_id]["local_path"] = model_dir
            else:
                # Add new model to metadata
                self.model_metadata[model_id] = {
                    "name": model_id,
                    "display_name": model_id,
                    "quality": 70,  # Default quality
                    "quality_description": "Неизвестное качество перевода",
                    "description": "Загруженная пользователем модель",
                    "local_path": model_dir,
                    "downloaded": True,
                    "default": False
                }
            
            # Save updated metadata
            self._save_metadata(self.model_metadata)
            
            return True, f"Successfully downloaded model {model_id}"
        except Exception as e:
            return False, f"Error downloading model: {e}"
    
    def delete_model(self, model_id: str) -> Tuple[bool, str]:
        """
        Delete a downloaded model
        
        Args:
            model_id: Model identifier
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Cannot delete default model
            if model_id == self.default_model_id:
                return False, "Cannot delete default model"
            
            model_dir = os.path.join(self.models_dir, f"models--{model_id.replace('/', '--')}")
            
            if os.path.exists(model_dir):
                shutil.rmtree(model_dir)
                
                # Update metadata
                if model_id in self.model_metadata:
                    self.model_metadata[model_id]["downloaded"] = False
                    self.model_metadata[model_id]["local_path"] = None
                    self._save_metadata(self.model_metadata)
                
                return True, f"Successfully deleted model {model_id}"
            else:
                return False, f"Model {model_id} not found"
                
        except Exception as e:
            return False, f"Error deleting model: {e}"
    
    def update_model_quality(self, model_id: str, quality: int, description: str = None) -> Tuple[bool, str]:
        """
        Update quality rating for a model
        
        Args:
            model_id: Model identifier
            quality: Quality percentage (0-100)
            description: Optional quality description
            
        Returns:
            Tuple of (success, message)
        """
        if model_id not in self.model_metadata:
            return False, f"Model {model_id} not found"
            
        try:
            # Update quality
            self.model_metadata[model_id]["quality"] = max(0, min(100, quality))
            
            # Update description if provided
            if description:
                self.model_metadata[model_id]["quality_description"] = description
                
            # Save changes
            self._save_metadata(self.model_metadata)
            
            return True, f"Successfully updated quality rating for {model_id}"
        except Exception as e:
            return False, f"Error updating quality rating: {e}"
    
    def search_huggingface_models(self, query: str = "translation english russian") -> List[Dict[str, Any]]:
        """
        Search for models on HuggingFace Hub
        
        Args:
            query: Search query
            
        Returns:
            List of model information dictionaries
        """
        try:
            # HuggingFace API endpoint for model search
            url = f"https://huggingface.co/api/models?search={query}&limit=20"
            response = requests.get(url)
            
            if response.status_code == 200:
                models = response.json()
                
                # Filter for translation models
                filtered_models = []
                for model in models:
                    model_id = model.get("id", "")
                    
                    # Skip if already in metadata
                    if model_id in self.model_metadata:
                        continue
                        
                    # Add to filtered list
                    filtered_models.append({
                        "name": model_id,
                        "display_name": model.get("modelId", model_id),
                        "description": model.get("description", ""),
                        "downloads": model.get("downloads", 0),
                        "likes": model.get("likes", 0),
                        "tags": model.get("tags", [])
                    })
                
                return filtered_models
            else:
                print(f"Error searching models: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error searching models: {e}")
            return [] 