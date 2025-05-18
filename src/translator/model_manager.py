import os
import json
import shutil
import requests
import torch
import psutil
from typing import List, Dict, Any, Optional, Tuple
from tqdm import tqdm
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from huggingface_hub import snapshot_download
from pathlib import Path
from src.utils.logger import get_logger

# Константы
MIN_MODEL_QUALITY = 0
MAX_MODEL_QUALITY = 100
MIN_FREE_SPACE_GB = 5
API_TIMEOUT = 30
MAX_MODEL_SIZE_GB = 10

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
        self.logger = get_logger("nn_translator.model_manager")
        self.logger.info("Initializing model manager")
        
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
        
        # Check GPU availability
        self.gpu_available = torch.cuda.is_available()
        if self.gpu_available:
            self.logger.info(f"GPU available: {torch.cuda.get_device_name(0)}")
        else:
            self.logger.warning("No GPU available, using CPU")
    
    def _load_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Load model metadata from file or create default
        
        Returns:
            Dictionary with model metadata
            
        Raises:
            RuntimeError: If metadata file is corrupted
        """
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    
                # Validate metadata format
                if not isinstance(metadata, dict):
                    raise ValueError("Invalid metadata format: expected dictionary")
                    
                # Validate each model entry
                for model_id, model_data in metadata.items():
                    if not isinstance(model_data, dict):
                        raise ValueError(f"Invalid model data format for {model_id}")
                    if "name" not in model_data:
                        raise ValueError(f"Missing name in model data for {model_id}")
                    if "quality" not in model_data:
                        raise ValueError(f"Missing quality in model data for {model_id}")
                    if not isinstance(model_data["quality"], (int, float)):
                        raise ValueError(f"Invalid quality value for {model_id}")
                    if model_data["quality"] < MIN_MODEL_QUALITY or model_data["quality"] > MAX_MODEL_QUALITY:
                        raise ValueError(f"Quality out of range for {model_id}")
                
                return metadata
            except (json.JSONDecodeError, IOError, ValueError) as e:
                self.logger.error(f"Error loading model metadata: {e}", exc_info=True)
                # Backup corrupted file
                try:
                    backup_path = f"{self.metadata_file}.bak"
                    os.rename(self.metadata_file, backup_path)
                    self.logger.info(f"Backed up corrupted metadata to {backup_path}")
                except Exception as backup_error:
                    self.logger.error(f"Failed to backup corrupted metadata: {backup_error}")
                
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
                "default": True,
                "gpu_required": False,
                "size_gb": 0.5
            },
            "facebook/m2m100_418M": {
                "name": "facebook/m2m100_418M",
                "display_name": "Facebook M2M100 (418M)",
                "quality": 80,
                "quality_description": "Хорошее качество перевода",
                "description": "Многоязычная модель перевода среднего размера",
                "local_path": None,
                "downloaded": self._check_model_downloaded("facebook/m2m100_418M"),
                "default": False,
                "gpu_required": True,
                "size_gb": 1.5
            },
            "facebook/nllb-200-distilled-600M": {
                "name": "facebook/nllb-200-distilled-600M",
                "display_name": "Facebook NLLB-200 (600M)",
                "quality": 90,
                "quality_description": "Превосходное качество перевода",
                "description": "Дистиллированная модель для 200 языков, включая русский",
                "local_path": None,
                "downloaded": self._check_model_downloaded("facebook/nllb-200-distilled-600M"),
                "default": False,
                "gpu_required": True,
                "size_gb": 2.0
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
            
        Raises:
            RuntimeError: If saving fails
        """
        try:
            # Save to temporary file first
            temp_path = f"{self.metadata_file}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            os.replace(temp_path, self.metadata_file)
            self.logger.debug("Model metadata saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving model metadata: {e}", exc_info=True)
            raise RuntimeError(f"Failed to save model metadata: {str(e)}")
    
    def _check_model_downloaded(self, model_id: str) -> bool:
        """
        Check if a model is already downloaded
        
        Args:
            model_id: Model identifier
            
        Returns:
            True if the model is downloaded
        """
        try:
            model_dir = os.path.join(self.models_dir, f"models--{model_id.replace('/', '--')}")
            return os.path.exists(model_dir)
        except Exception as e:
            self.logger.error(f"Error checking model download status: {e}", exc_info=True)
            return False
    
    def _check_free_space(self, required_gb: float) -> bool:
        """
        Check if there is enough free space
        
        Args:
            required_gb: Required space in gigabytes
            
        Returns:
            True if there is enough space
        """
        try:
            free_gb = psutil.disk_usage(self.models_dir).free / (1024 ** 3)
            return free_gb >= required_gb
        except Exception as e:
            self.logger.error(f"Error checking free space: {e}", exc_info=True)
            return False
    
    def get_model_path(self, model_id: str) -> str:
        """
        Get the local path for a model
        
        Args:
            model_id: Model identifier
            
        Returns:
            Path to the model directory
            
        Raises:
            ValueError: If model is not found
        """
        if model_id not in self.model_metadata:
            raise ValueError(f"Model {model_id} not found")
            
        if not self.model_metadata[model_id]["downloaded"]:
            raise ValueError(f"Model {model_id} is not downloaded")
            
        if self.model_metadata[model_id]["local_path"]:
            return self.model_metadata[model_id]["local_path"]
        else:
            return os.path.join(self.models_dir, f"models--{model_id.replace('/', '--')}")
    
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
            
        Raises:
            ValueError: If model is not found or requirements not met
            RuntimeError: If download fails
        """
        try:
            # Check if model exists in metadata
            if model_id not in self.model_metadata:
                raise ValueError(f"Model {model_id} not found")
                
            # Check if model is already downloaded
            if self.model_metadata[model_id]["downloaded"]:
                return True, f"Model {model_id} is already downloaded"
                
            # Check GPU requirement
            if self.model_metadata[model_id].get("gpu_required", False) and not self.gpu_available:
                raise ValueError(f"Model {model_id} requires GPU, but no GPU is available")
                
            # Check free space
            required_gb = self.model_metadata[model_id].get("size_gb", MAX_MODEL_SIZE_GB)
            if not self._check_free_space(required_gb):
                raise ValueError(f"Not enough free space. Required: {required_gb}GB")
            
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
            self.model_metadata[model_id]["downloaded"] = True
            self.model_metadata[model_id]["local_path"] = model_dir
            
            # Save updated metadata
            self._save_metadata(self.model_metadata)
            
            self.logger.info(f"Successfully downloaded model {model_id}")
            return True, f"Successfully downloaded model {model_id}"
        except ValueError as e:
            self.logger.warning(f"Validation error during model download: {e}")
            return False, str(e)
        except Exception as e:
            self.logger.error(f"Error downloading model: {e}", exc_info=True)
            return False, f"Error downloading model: {str(e)}"
    
    def delete_model(self, model_id: str) -> Tuple[bool, str]:
        """
        Delete a downloaded model
        
        Args:
            model_id: Model identifier
            
        Returns:
            Tuple of (success, message)
            
        Raises:
            ValueError: If model is not found or is default
            RuntimeError: If deletion fails
        """
        try:
            # Check if model exists
            if model_id not in self.model_metadata:
                raise ValueError(f"Model {model_id} not found")
                
            # Cannot delete default model
            if model_id == self.default_model_id:
                raise ValueError("Cannot delete default model")
            
            model_dir = os.path.join(self.models_dir, f"models--{model_id.replace('/', '--')}")
            
            if os.path.exists(model_dir):
                shutil.rmtree(model_dir)
                
                # Update metadata
                self.model_metadata[model_id]["downloaded"] = False
                self.model_metadata[model_id]["local_path"] = None
                self._save_metadata(self.model_metadata)
                
                self.logger.info(f"Successfully deleted model {model_id}")
                return True, f"Successfully deleted model {model_id}"
            else:
                raise ValueError(f"Model {model_id} not found")
                
        except ValueError as e:
            self.logger.warning(f"Validation error during model deletion: {e}")
            return False, str(e)
        except Exception as e:
            self.logger.error(f"Error deleting model: {e}", exc_info=True)
            return False, f"Error deleting model: {str(e)}"
    
    def update_model_quality(self, model_id: str, quality: int, description: str = None) -> Tuple[bool, str]:
        """
        Update quality rating for a model
        
        Args:
            model_id: Model identifier
            quality: Quality percentage (0-100)
            description: Optional quality description
            
        Returns:
            Tuple of (success, message)
            
        Raises:
            ValueError: If model is not found or quality is invalid
            RuntimeError: If update fails
        """
        try:
            # Check if model exists
            if model_id not in self.model_metadata:
                raise ValueError(f"Model {model_id} not found")
                
            # Validate quality value
            if not isinstance(quality, (int, float)):
                raise ValueError("Quality must be a number")
            if quality < MIN_MODEL_QUALITY or quality > MAX_MODEL_QUALITY:
                raise ValueError(f"Quality must be between {MIN_MODEL_QUALITY} and {MAX_MODEL_QUALITY}")
            
            # Update quality
            self.model_metadata[model_id]["quality"] = quality
            
            # Update description if provided
            if description:
                if not isinstance(description, str):
                    raise ValueError("Description must be a string")
                self.model_metadata[model_id]["quality_description"] = description
                
            # Save changes
            self._save_metadata(self.model_metadata)
            
            self.logger.info(f"Successfully updated quality rating for {model_id}")
            return True, f"Successfully updated quality rating for {model_id}"
        except ValueError as e:
            self.logger.warning(f"Validation error during quality update: {e}")
            return False, str(e)
        except Exception as e:
            self.logger.error(f"Error updating quality rating: {e}", exc_info=True)
            return False, f"Error updating quality rating: {str(e)}"
    
    def search_huggingface_models(self, query: str = "translation english russian") -> List[Dict[str, Any]]:
        """
        Search for models on HuggingFace Hub
        
        Args:
            query: Search query
            
        Returns:
            List of model information dictionaries
            
        Raises:
            RuntimeError: If search fails
        """
        try:
            # Validate query
            if not isinstance(query, str):
                raise ValueError("Search query must be a string")
            if not query.strip():
                raise ValueError("Search query cannot be empty")
                
            # HuggingFace API endpoint for model search
            url = f"https://huggingface.co/api/models?search={query}&limit=20"
            response = requests.get(url, timeout=API_TIMEOUT)
            
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
                        "tags": model.get("tags", []),
                        "gpu_required": "large" in model_id.lower() or "xl" in model_id.lower(),
                        "size_gb": self._estimate_model_size(model)
                    })
                
                self.logger.info(f"Found {len(filtered_models)} models matching query: {query}")
                return filtered_models
            else:
                raise RuntimeError(f"API request failed with status code {response.status_code}")
        except ValueError as e:
            self.logger.warning(f"Validation error during model search: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error searching models: {e}", exc_info=True)
            return []
    
    def _estimate_model_size(self, model_info: Dict[str, Any]) -> float:
        """
        Estimate model size based on model information
        
        Args:
            model_info: Model information from HuggingFace API
            
        Returns:
            Estimated size in gigabytes
        """
        try:
            # Try to get size from model info
            size_bytes = model_info.get("size_bytes", 0)
            if size_bytes:
                return size_bytes / (1024 ** 3)
                
            # Estimate based on model name
            model_id = model_info.get("id", "").lower()
            if "large" in model_id or "xl" in model_id:
                return 2.0
            elif "medium" in model_id or "base" in model_id:
                return 1.0
            else:
                return 0.5
        except Exception as e:
            self.logger.warning(f"Error estimating model size: {e}")
            return MAX_MODEL_SIZE_GB 