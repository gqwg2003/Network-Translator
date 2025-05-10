import tkinter as tk
from tkinter import ttk
from typing import Optional

class ProgressBar(ttk.Frame):
    """
    Custom progress bar widget with percentage display
    """
    def __init__(self, parent, initial_value: float = 0, **kwargs):
        """
        Initialize the progress bar
        
        Args:
            parent: Parent widget
            initial_value: Initial progress value (0-100)
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)
        
        # Create widgets
        self.progress_var = tk.DoubleVar(value=initial_value)
        
        self.progressbar = ttk.Progressbar(
            self, 
            variable=self.progress_var,
            maximum=100
        )
        self.progressbar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.percent_label = ttk.Label(self, text=f"{initial_value:.0f}%", width=5)
        self.percent_label.pack(side=tk.LEFT, padx=5)
    
    def set_progress(self, value: float):
        """
        Set the progress value
        
        Args:
            value: Progress value (0-100)
        """
        # Clamp value to 0-100 range
        clamped_value = max(0, min(100, value))
        
        # Update variable and label
        self.progress_var.set(clamped_value)
        self.percent_label.config(text=f"{clamped_value:.0f}%")
        
        # Force update
        self.update_idletasks()
    
    def get_progress(self) -> float:
        """
        Get the current progress value
        
        Returns:
            Current progress value (0-100)
        """
        return self.progress_var.get() 