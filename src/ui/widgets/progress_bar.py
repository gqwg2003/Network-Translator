import tkinter as tk
from tkinter import ttk
from typing import Optional

class ProgressBar(ttk.Frame):
    """
    Custom progress bar widget with percentage display and color support
    """
    def __init__(
        self, 
        parent, 
        initial_value: float = 0, 
        bar_color: str = None,
        height: int = 16,
        **kwargs
    ):
        """
        Initialize the progress bar
        
        Args:
            parent: Parent widget
            initial_value: Initial progress value (0-100)
            bar_color: Color of the progress bar (hex or color name)
            height: Height of the progress bar in pixels
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)
        
        # Store properties
        self.bar_color = bar_color
        self.bar_height = height
        
        # Create unique style name for this instance
        self.style_name = f"Custom.{id(self)}.Horizontal.TProgressbar"
        
        # Configure style
        style = ttk.Style()
        if bar_color:
            style.configure(
                self.style_name,
                thickness=height,
                background=bar_color
            )
        else:
            # Determine color based on value
            self._update_color_for_value(initial_value)
        
        # Create widgets
        self.progress_var = tk.DoubleVar(value=initial_value)
        
        self.progressbar = ttk.Progressbar(
            self, 
            variable=self.progress_var,
            maximum=100,
            style=self.style_name
        )
        self.progressbar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.percent_label = ttk.Label(
            self, 
            text=f"{initial_value:.0f}%", 
            width=5,
            font=("Segoe UI", 9)
        )
        self.percent_label.pack(side=tk.LEFT, padx=5)
    
    def _update_color_for_value(self, value: float):
        """Update progress bar color based on value if no fixed color is set"""
        if self.bar_color:
            return
            
        # Choose color based on value
        if value >= 85:
            color = "#4a86e8"  # Blue for excellent
        elif value >= 70:
            color = "#63b946"  # Green for good
        elif value >= 50:
            color = "#e8b84a"  # Yellow/Orange for average
        else:
            color = "#e85c5c"  # Red for poor
            
        # Update style
        style = ttk.Style()
        style.configure(
            self.style_name,
            thickness=self.bar_height,
            background=color
        )
    
    def set_progress(self, value: float):
        """
        Set the progress value
        
        Args:
            value: Progress value (0-100)
        """
        # Clamp value to 0-100 range
        clamped_value = max(0, min(100, value))
        
        # Update color based on value
        self._update_color_for_value(clamped_value)
        
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
        
    def set_color(self, color: str):
        """
        Set the progress bar color
        
        Args:
            color: Color as hex code or color name
        """
        self.bar_color = color
        
        style = ttk.Style()
        style.configure(
            self.style_name,
            background=color
        ) 