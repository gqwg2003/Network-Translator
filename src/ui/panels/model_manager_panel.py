import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Callable, Dict, Any, List, Optional

from src.ui.widgets.scrollable_frame import ScrollableFrame
from src.ui.widgets.progress_bar import ProgressBar

class ModelManagerPanel(ttk.Frame):
    """
    Panel for model selection and management
    """
    def __init__(self, parent, translator, on_status_change: Callable[[str, str], None] = None):
        """
        Initialize the model manager panel
        
        Args:
            parent: Parent widget
            translator: Translator instance
            on_status_change: Callback for status changes
        """
        super().__init__(parent)
        self.translator = translator
        self.on_status_change = on_status_change
        
        # Models currently displayed in the list
        self.displayed_models = []
        
        # Create UI elements
        self._create_widgets()
        self._setup_layout()
        
        # Load model list
        self._load_models()
    
    def _create_widgets(self):
        """Create panel widgets"""
        # Notebook for tabs
        self.notebook = ttk.Notebook(self)
        
        # === Tab 1: Model Selection ===
        self.selection_frame = ttk.Frame(self.notebook)
        
        # Model list
        models_frame = ttk.LabelFrame(self.selection_frame, text="Available Models")
        
        # Create a frame with scrollbar for models
        self.models_scroll_frame = ScrollableFrame(models_frame)
        self.models_container = self.models_scroll_frame.scrollable_frame
        
        # Current model info
        current_model_frame = ttk.LabelFrame(self.selection_frame, text="Current Model")
        
        self.current_model_name = ttk.Label(current_model_frame, text="Model: Loading...")
        self.current_model_quality = ttk.Label(current_model_frame, text="Quality: N/A")
        self.current_model_status = ttk.Label(current_model_frame, text="Status: Not loaded")
        
        # === Tab 2: Model Download ===
        self.download_frame = ttk.Frame(self.notebook)
        
        # Search frame
        search_frame = ttk.Frame(self.download_frame)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.search_button = ttk.Button(search_frame, text="Search", command=self._search_models)
        self.search_button.pack(side=tk.LEFT, padx=5)
        
        # Results frame
        results_frame = ttk.LabelFrame(self.download_frame, text="Search Results")
        self.results_scroll_frame = ScrollableFrame(results_frame)
        self.results_container = self.results_scroll_frame.scrollable_frame
        
        # Download progress
        self.download_progress_frame = ttk.Frame(self.download_frame)
        self.download_progress = ProgressBar(self.download_progress_frame)
        self.download_status = ttk.Label(self.download_progress_frame, text="")
        
        # === Tab 3: Model Training ===
        self.training_frame = ttk.Frame(self.notebook)
        
        # Training options
        training_options_frame = ttk.LabelFrame(self.training_frame, text="Model Fine-tuning")
        
        # Model selection for training
        ttk.Label(training_options_frame, text="Select model to fine-tune:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        
        self.training_model_var = tk.StringVar()
        self.training_model_combo = ttk.Combobox(training_options_frame, textvariable=self.training_model_var, state="readonly", width=40)
        self.training_model_combo.grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Training data options
        ttk.Label(training_options_frame, text="Training Data Source:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        
        self.data_source_var = tk.StringVar(value="local")
        ttk.Radiobutton(training_options_frame, text="Local Files", variable=self.data_source_var, value="local").grid(row=1, column=1, sticky=tk.W, padx=10)
        ttk.Radiobutton(training_options_frame, text="Web Resources", variable=self.data_source_var, value="web").grid(row=2, column=1, sticky=tk.W, padx=10)
        
        # Local file selection
        self.file_frame = ttk.Frame(training_options_frame)
        ttk.Label(self.file_frame, text="Select training files:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        ttk.Button(self.file_frame, text="Browse...", command=self._browse_training_files).grid(row=0, column=1, padx=10, pady=5)
        self.file_list = tk.Listbox(self.file_frame, width=40, height=5)
        self.file_list.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky=tk.W+tk.E)
        self.file_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W+tk.E, padx=10, pady=5)
        
        # Web resource frame
        self.web_frame = ttk.Frame(training_options_frame)
        ttk.Label(self.web_frame, text="Website URL:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        
        self.url_var = tk.StringVar()
        ttk.Entry(self.web_frame, textvariable=self.url_var, width=40).grid(row=0, column=1, padx=10, pady=5, sticky=tk.W+tk.E)
        
        ttk.Button(self.web_frame, text="Fetch Content", command=self._fetch_web_content).grid(row=1, column=0, columnspan=2, padx=10, pady=5)
        self.web_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W+tk.E, padx=10, pady=5)
        self.web_frame.grid_remove()  # Hide initially
        
        # Training buttons
        button_frame = ttk.Frame(training_options_frame)
        ttk.Button(button_frame, text="Start Fine-tuning", command=self._start_training).pack(side=tk.LEFT, padx=10, pady=10)
        ttk.Button(button_frame, text="Cancel", command=self._cancel_training).pack(side=tk.LEFT, padx=10, pady=10)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        # Training progress
        training_progress_frame = ttk.LabelFrame(self.training_frame, text="Training Progress")
        
        self.training_progress = ProgressBar(training_progress_frame)
        self.training_progress.pack(fill=tk.X, expand=True, padx=10, pady=5)
        
        self.training_status = ttk.Label(training_progress_frame, text="Ready to start training")
        self.training_status.pack(padx=10, pady=5)
        
        # Add tabs to notebook
        self.notebook.add(self.selection_frame, text="Model Selection")
        self.notebook.add(self.download_frame, text="Download Models")
        self.notebook.add(self.training_frame, text="Model Fine-tuning")
    
    def _setup_layout(self):
        """Set up the panel layout"""
        # Make the notebook fill the panel
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # === Tab 1: Model Selection ===
        # Models list
        models_frame = self.selection_frame.winfo_children()[0]
        models_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.models_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Current model info
        current_model_frame = self.selection_frame.winfo_children()[1]
        current_model_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.current_model_name.pack(anchor=tk.W, padx=10, pady=2)
        self.current_model_quality.pack(anchor=tk.W, padx=10, pady=2)
        self.current_model_status.pack(anchor=tk.W, padx=10, pady=2)
        
        # === Tab 2: Model Download ===
        # Search frame
        search_frame = self.download_frame.winfo_children()[0]
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Results frame
        results_frame = self.download_frame.winfo_children()[1]
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.results_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Download progress
        self.download_progress_frame.pack(fill=tk.X, padx=10, pady=10)
        self.download_progress.pack(fill=tk.X, padx=5, pady=5)
        self.download_status.pack(anchor=tk.W, padx=5, pady=5)
        
        # === Tab 3: Model Training ===
        # Training options frame
        training_options_frame = self.training_frame.winfo_children()[0]
        training_options_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Training progress frame
        training_progress_frame = self.training_frame.winfo_children()[1]
        training_progress_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Bind data source selection
        self.data_source_var.trace("w", self._toggle_data_source)
    
    def _load_models(self):
        """Load and display available models"""
        # Clear previous models
        for widget in self.models_container.winfo_children():
            widget.destroy()
        
        # Get models from translator
        models = self.translator.get_available_models()
        self.displayed_models = models
        
        # Create model cards
        for i, model in enumerate(models):
            self._create_model_card(model, i)
        
        # Update current model info
        self._update_current_model_info()
        
        # Update training model combobox
        self._update_training_model_list()
    
    def _create_model_card(self, model: Dict[str, Any], index: int):
        """Create a card for a model in the list"""
        model_name = model.get("display_name", model.get("name", "Unknown"))
        model_id = model.get("name", "")
        quality = model.get("quality", 0)
        quality_desc = model.get("quality_description", "")
        downloaded = model.get("downloaded", False)
        current = model.get("name", "") == self.translator.current_model_id
        
        # Create a frame for the model card
        card = ttk.Frame(self.models_container)
        card.pack(fill=tk.X, pady=5, padx=5)
        
        # Model name and quality
        info_frame = ttk.Frame(card)
        info_frame.pack(fill=tk.X, side=tk.TOP)
        
        name_label = ttk.Label(info_frame, text=model_name, font=("Default", 10, "bold"))
        name_label.pack(anchor=tk.W, padx=5, pady=2)
        
        # Quality info with progress bar
        quality_frame = ttk.Frame(info_frame)
        quality_frame.pack(fill=tk.X, padx=5, pady=2)
        
        quality_bar = ttk.Progressbar(quality_frame, value=quality, maximum=100, length=200)
        quality_bar.pack(side=tk.LEFT)
        
        quality_label = ttk.Label(quality_frame, text=f"{quality}% - {quality_desc}")
        quality_label.pack(side=tk.LEFT, padx=10)
        
        # Action buttons
        button_frame = ttk.Frame(card)
        button_frame.pack(fill=tk.X, pady=5)
        
        if downloaded:
            select_button = ttk.Button(
                button_frame, 
                text="Select" if not current else "Selected", 
                command=lambda m=model_id: self._select_model(m),
                state="disabled" if current else "normal"
            )
            select_button.pack(side=tk.LEFT, padx=5)
            
            if not model.get("default", False):
                delete_button = ttk.Button(
                    button_frame, 
                    text="Delete", 
                    command=lambda m=model_id: self._delete_model(m)
                )
                delete_button.pack(side=tk.LEFT, padx=5)
        else:
            download_button = ttk.Button(
                button_frame, 
                text="Download", 
                command=lambda m=model_id: self._download_model(m)
            )
            download_button.pack(side=tk.LEFT, padx=5)
        
        # Add separator after each model except the last one
        if index < len(self.displayed_models) - 1:
            ttk.Separator(self.models_container, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5, padx=5)
    
    def _update_current_model_info(self):
        """Update the current model information display"""
        model_info = self.translator.get_model_info()
        
        display_name = model_info.get("display_name", model_info.get("model_id", "Unknown"))
        quality = model_info.get("quality", 0)
        quality_desc = model_info.get("quality_description", "")
        model_loaded = model_info.get("model_loaded", False)
        
        self.current_model_name.config(text=f"Model: {display_name}")
        self.current_model_quality.config(text=f"Quality: {quality}% - {quality_desc}")
        
        status_text = "Loaded" if model_loaded else "Not loaded"
        self.current_model_status.config(text=f"Status: {status_text}")
    
    def _select_model(self, model_id: str):
        """Select a model for translation"""
        if self._update_status("Changing model...", "wait"):
            # Start model change in a thread
            threading.Thread(target=self._change_model_thread, args=(model_id,), daemon=True).start()
    
    def _change_model_thread(self, model_id: str):
        """Thread function for model change"""
        try:
            success = self.translator.change_model(model_id)
            
            if success:
                # Update UI after successful change
                self.after(0, lambda: self._update_status("Model changed successfully", "success"))
                self.after(0, self._update_current_model_info)
                self.after(0, self._load_models)  # Reload to update selection state
            else:
                self.after(0, lambda: self._update_status("Failed to change model", "error"))
        except Exception as e:
            self.after(0, lambda: self._update_status(f"Error: {str(e)}", "error"))
    
    def _download_model(self, model_id: str):
        """Download a model"""
        if self._update_status(f"Downloading model {model_id}...", "wait"):
            # Reset progress
            self.download_progress.set_progress(0)
            self.download_status.config(text="Starting download...")
            
            # Switch to download tab if not already there
            self.notebook.select(1)
            
            # Start download in a thread
            threading.Thread(target=self._download_model_thread, args=(model_id,), daemon=True).start()
    
    def _download_model_thread(self, model_id: str):
        """Thread function for model download"""
        try:
            def progress_callback(progress):
                self.after(0, lambda: self.download_progress.set_progress(progress * 100))
                self.after(0, lambda: self.download_status.config(text=f"Downloading: {progress:.1%}"))
            
            success = self.translator.download_model(model_id, progress_callback)
            
            if success:
                # Update UI after successful download
                self.after(0, lambda: self.download_progress.set_progress(100))
                self.after(0, lambda: self.download_status.config(text="Download complete"))
                self.after(0, lambda: self._update_status("Model downloaded successfully", "success"))
                self.after(0, self._load_models)  # Reload model list
                self.after(0, self._update_training_model_list)  # Update training model list
            else:
                self.after(0, lambda: self._update_status("Failed to download model", "error"))
                self.after(0, lambda: self.download_status.config(text="Download failed"))
        except Exception as e:
            self.after(0, lambda: self._update_status(f"Error: {str(e)}", "error"))
            self.after(0, lambda: self.download_status.config(text="Download error"))
    
    def _delete_model(self, model_id: str):
        """Delete a downloaded model"""
        # Confirm deletion
        if not messagebox.askyesno("Confirm Deletion", 
                                  f"Are you sure you want to delete this model?\nThis cannot be undone."):
            return
        
        if self._update_status(f"Deleting model {model_id}...", "wait"):
            # Start deletion in a thread
            threading.Thread(target=self._delete_model_thread, args=(model_id,), daemon=True).start()
    
    def _delete_model_thread(self, model_id: str):
        """Thread function for model deletion"""
        try:
            success, message = self.translator.model_manager.delete_model(model_id)
            
            if success:
                self.after(0, lambda: self._update_status("Model deleted successfully", "success"))
                self.after(0, self._load_models)  # Reload model list
                self.after(0, self._update_training_model_list)  # Update training model list
            else:
                self.after(0, lambda: self._update_status(f"Failed to delete model: {message}", "error"))
        except Exception as e:
            self.after(0, lambda: self._update_status(f"Error: {str(e)}", "error"))
    
    def _search_models(self):
        """Search for models on HuggingFace Hub"""
        query = self.search_var.get()
        if not query:
            query = "translation english russian"
            
        if self._update_status(f"Searching for models: {query}...", "wait"):
            # Clear previous results
            for widget in self.results_container.winfo_children():
                widget.destroy()
                
            # Start search in a thread
            threading.Thread(target=self._search_models_thread, args=(query,), daemon=True).start()
    
    def _search_models_thread(self, query: str):
        """Thread function for model search"""
        try:
            results = self.translator.model_manager.search_huggingface_models(query)
            
            if results:
                # Display results
                self.after(0, lambda: self._display_search_results(results))
                self.after(0, lambda: self._update_status(f"Found {len(results)} models", "success"))
            else:
                self.after(0, lambda: self._update_status("No models found", "info"))
                
                # Show no results message
                self.after(0, lambda: ttk.Label(
                    self.results_container,
                    text="No models found matching your search query.",
                    wraplength=400
                ).pack(padx=10, pady=10))
        except Exception as e:
            self.after(0, lambda: self._update_status(f"Error: {str(e)}", "error"))
    
    def _display_search_results(self, results: List[Dict[str, Any]]):
        """Display search results"""
        # Clear previous results
        for widget in self.results_container.winfo_children():
            widget.destroy()
            
        for i, model in enumerate(results):
            # Create a frame for this result
            result_frame = ttk.Frame(self.results_container)
            result_frame.pack(fill=tk.X, padx=5, pady=10)
            
            # Model name
            model_id = model.get("name", "")
            display_name = model.get("display_name", model_id)
            
            ttk.Label(result_frame, text=display_name, font=("Default", 10, "bold")).pack(anchor=tk.W, pady=2)
            
            # Description (if available)
            description = model.get("description", "")
            if description:
                desc_label = ttk.Label(result_frame, text=description, wraplength=500)
                desc_label.pack(anchor=tk.W, pady=2)
            
            # Stats
            stats_frame = ttk.Frame(result_frame)
            stats_frame.pack(anchor=tk.W, pady=2)
            
            downloads = model.get("downloads", 0)
            likes = model.get("likes", 0)
            
            ttk.Label(stats_frame, text=f"Downloads: {downloads}").pack(side=tk.LEFT, padx=5)
            ttk.Label(stats_frame, text=f"Likes: {likes}").pack(side=tk.LEFT, padx=5)
            
            # Download button
            ttk.Button(
                result_frame, 
                text="Download", 
                command=lambda m=model_id: self._download_model(m)
            ).pack(anchor=tk.W, pady=5)
            
            # Add separator
            if i < len(results) - 1:
                ttk.Separator(self.results_container, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
    
    def _update_training_model_list(self):
        """Update the list of models available for training"""
        # Get downloaded models
        models = self.translator.get_downloaded_models()
        
        # Populate combobox
        model_names = []
        model_ids = []
        
        for model in models:
            display_name = model.get("display_name", model.get("name", "Unknown"))
            model_id = model.get("name", "")
            
            model_names.append(display_name)
            model_ids.append(model_id)
        
        self.training_model_combo["values"] = model_names
        self.training_model_map = dict(zip(model_names, model_ids))
        
        # Select current model
        current_model_info = self.translator.get_model_info()
        current_name = current_model_info.get("display_name", "")
        
        if current_name and current_name in model_names:
            self.training_model_combo.set(current_name)
        elif model_names:
            self.training_model_combo.set(model_names[0])
    
    def _toggle_data_source(self, *args):
        """Toggle between local files and web resources"""
        source = self.data_source_var.get()
        
        if source == "local":
            self.file_frame.grid()
            self.web_frame.grid_remove()
        else:  # web
            self.file_frame.grid_remove()
            self.web_frame.grid()
    
    def _browse_training_files(self):
        """Open file dialog to select training files"""
        from tkinter import filedialog
        
        files = filedialog.askopenfilenames(
            title="Select Training Files",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if files:
            self.file_list.delete(0, tk.END)
            for file in files:
                self.file_list.insert(tk.END, file)
    
    def _fetch_web_content(self):
        """Fetch content from a website for training"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a valid URL")
            return
            
        if self._update_status("Fetching content from website...", "wait"):
            threading.Thread(target=self._fetch_web_content_thread, args=(url,), daemon=True).start()
    
    def _fetch_web_content_thread(self, url: str):
        """Thread function for fetching web content"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Fetch web content
            response = requests.get(url)
            if response.status_code == 200:
                # Parse HTML
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Extract text content
                paragraphs = soup.find_all("p")
                text = "\n\n".join([p.get_text() for p in paragraphs])
                
                # Save to temporary file
                import tempfile
                import os
                
                temp_dir = tempfile.gettempdir()
                temp_file = os.path.join(temp_dir, "web_content.txt")
                
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(text)
                
                # Update file list
                self.after(0, lambda: (
                    self.file_list.delete(0, tk.END),
                    self.file_list.insert(tk.END, temp_file),
                    self.data_source_var.set("local"),
                    self._toggle_data_source()
                ))
                
                self.after(0, lambda: self._update_status("Web content fetched successfully", "success"))
            else:
                self.after(0, lambda: self._update_status(f"Failed to fetch content: {response.status_code}", "error"))
        except Exception as e:
            self.after(0, lambda: self._update_status(f"Error: {str(e)}", "error"))
    
    def _start_training(self):
        """Start model fine-tuning"""
        # Get selected model
        model_name = self.training_model_combo.get()
        if not model_name or model_name not in self.training_model_map:
            messagebox.showerror("Error", "Please select a model for fine-tuning")
            return
        
        model_id = self.training_model_map[model_name]
        
        # Get training data
        source = self.data_source_var.get()
        training_files = []
        
        if source == "local":
            training_files = list(self.file_list.get(0, tk.END))
            if not training_files:
                messagebox.showerror("Error", "Please select training files")
                return
        else:  # web
            url = self.url_var.get().strip()
            if not url:
                messagebox.showerror("Error", "Please enter a valid URL")
                return
        
        # Start training
        if self._update_status("Starting model fine-tuning...", "wait"):
            # Update progress display
            self.training_progress.set_progress(0)
            self.training_status.config(text="Preparing for training...")
            
            # Start training in a thread
            threading.Thread(
                target=self._training_thread, 
                args=(model_id, training_files, source), 
                daemon=True
            ).start()
    
    def _training_thread(self, model_id: str, files: List[str], source: str):
        """Thread function for model training"""
        # This is a simulated training process
        # In a real implementation, this would use a proper training API
        
        try:
            import time
            import random
            
            # Simulated training steps
            total_steps = 10
            
            # Update progress
            for step in range(1, total_steps + 1):
                # Simulate training work
                time.sleep(1.5)
                progress = step / total_steps
                
                # Update UI
                self.after(0, lambda p=progress: self.training_progress.set_progress(p * 100))
                self.after(0, lambda s=step, t=total_steps: self.training_status.config(
                    text=f"Training in progress... Step {s}/{t}"
                ))
            
            # Simulate a quality improvement
            model_meta = self.translator.model_manager.model_metadata.get(model_id, {})
            old_quality = model_meta.get("quality", 70)
            new_quality = min(100, old_quality + random.randint(1, 10))
            
            # Update model quality
            self.translator.model_manager.update_model_quality(
                model_id, 
                new_quality,
                "Улучшено пользовательским обучением"
            )
            
            # Update UI
            self.after(0, lambda: self.training_progress.set_progress(100))
            self.after(0, lambda q=new_quality: self.training_status.config(
                text=f"Training complete! Quality improved to {q}%"
            ))
            self.after(0, lambda: self._update_status("Model fine-tuning completed successfully", "success"))
            
            # Refresh model list
            self.after(0, self._load_models)
            
        except Exception as e:
            self.after(0, lambda: self._update_status(f"Error during training: {str(e)}", "error"))
            self.after(0, lambda: self.training_status.config(text="Training error occurred"))
    
    def _cancel_training(self):
        """Cancel ongoing training"""
        # In a real implementation, this would signal the training process to stop
        self._update_status("Training cancelled", "info")
        self.training_status.config(text="Training cancelled")
    
    def _update_status(self, message: str, status_type: str = "info") -> bool:
        """Update status message and propagate to parent if needed"""
        if self.on_status_change:
            self.on_status_change(message, status_type)
        return True 