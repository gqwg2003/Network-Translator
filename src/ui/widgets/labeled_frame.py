import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any

class LabeledFrame(ttk.Frame):
    """
    A frame with a label and optional toolbar
    """
    def __init__(
        self, 
        master, 
        title: str,
        padding: int = 10,
        show_toolbar: bool = False,
        **kwargs
    ):
        """
        Initialize a labeled frame
        
        Args:
            master: Parent widget
            title: Title for the frame
            padding: Padding around content
            show_toolbar: Whether to show a toolbar
            **kwargs: Additional arguments for Frame
        """
        super().__init__(master, **kwargs)
        
        # Create header frame
        self.header_frame = ttk.Frame(self)
        self.header_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(5, 0))
        
        # Title label
        self.title_label = ttk.Label(
            self.header_frame, 
            text=title, 
            font=("TkDefaultFont", 10, "bold")
        )
        self.title_label.pack(side=tk.LEFT, anchor=tk.W)
        
        # Toolbar frame (optional)
        self.toolbar_frame = None
        if show_toolbar:
            self.toolbar_frame = ttk.Frame(self.header_frame)
            self.toolbar_frame.pack(side=tk.RIGHT, anchor=tk.E)
            
        # Content frame
        self.content_frame = ttk.Frame(self, padding=padding)
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Separator
        self.separator = ttk.Separator(self, orient=tk.HORIZONTAL)
        self.separator.pack(fill=tk.X, padx=5, pady=(0, 5))
    
    def set_title(self, title: str):
        """
        Set the frame title
        
        Args:
            title: New title text
        """
        self.title_label.config(text=title)
    
    def add_toolbar_button(self, text: str, command, **kwargs) -> ttk.Button:
        """
        Add a button to the toolbar
        
        Args:
            text: Button text
            command: Button command
            **kwargs: Additional button configuration
            
        Returns:
            The created button
        """
        if not self.toolbar_frame:
            self.toolbar_frame = ttk.Frame(self.header_frame)
            self.toolbar_frame.pack(side=tk.RIGHT, anchor=tk.E)
            
        button = ttk.Button(self.toolbar_frame, text=text, command=command, **kwargs)
        button.pack(side=tk.LEFT, padx=2)
        return button
        
    def get_content_frame(self) -> ttk.Frame:
        """
        Get the content frame to add widgets to
        
        Returns:
            The content frame
        """
        return self.content_frame 