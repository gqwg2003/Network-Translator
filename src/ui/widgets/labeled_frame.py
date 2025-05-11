import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any

class LabeledFrame(ttk.Frame):
    """
    A frame with a label and optional toolbar, with collapsible content
    """
    def __init__(
        self, 
        master, 
        title: str,
        padding: int = 10,
        show_toolbar: bool = False,
        collapsible: bool = False,
        collapsed: bool = False,
        **kwargs
    ):
        """
        Initialize a labeled frame
        
        Args:
            master: Parent widget
            title: Title for the frame
            padding: Padding around content
            show_toolbar: Whether to show a toolbar
            collapsible: Whether the frame can be collapsed
            collapsed: Initial collapsed state
            **kwargs: Additional arguments for Frame
        """
        # Extract custom options before passing to Frame constructor
        frame_kwargs = kwargs.copy()
        for key in ["collapsible", "collapsed"]:
            if key in frame_kwargs:
                frame_kwargs.pop(key)
                
        super().__init__(master, **frame_kwargs)
        
        # Store properties
        self.collapsible = collapsible
        self._is_collapsed = collapsed
        
        # Create header frame
        self.header_frame = ttk.Frame(self)
        self.header_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(5, 0))
        
        # Title label
        self.title_var = tk.StringVar(value=title)
        self.title_label = ttk.Label(
            self.header_frame, 
            textvariable=self.title_var, 
            font=("TkDefaultFont", 10, "bold")
        )
        self.title_label.pack(side=tk.LEFT, anchor=tk.W)
        
        # Expand/collapse indicator for collapsible frames
        self.toggle_button = None
        if collapsible:
            self.toggle_button = ttk.Label(
                self.header_frame,
                text="▼" if not collapsed else "▶",
                cursor="hand2"
            )
            self.toggle_button.pack(side=tk.LEFT, padx=(5, 0))
            self.toggle_button.bind("<Button-1>", self.toggle_collapsed)
            
            # Make the title clickable too
            self.title_label.bind("<Button-1>", self.toggle_collapsed)
            self.title_label.config(cursor="hand2")
        
        # Toolbar frame (optional)
        self.toolbar_frame = None
        if show_toolbar:
            self.toolbar_frame = ttk.Frame(self.header_frame)
            self.toolbar_frame.pack(side=tk.RIGHT, anchor=tk.E)
            
        # Content frame
        self.content_frame = ttk.Frame(self, padding=padding)
        if not collapsed:
            self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Separator
        self.separator = ttk.Separator(self, orient=tk.HORIZONTAL)
        self.separator.pack(fill=tk.X, padx=5, pady=(0, 5))
    
    def toggle_collapsed(self, event=None):
        """Toggle the collapsed state of the frame"""
        if not self.collapsible:
            return
            
        self._is_collapsed = not self._is_collapsed
        
        if self._is_collapsed:
            self.content_frame.pack_forget()
            if self.toggle_button:
                self.toggle_button.config(text="▶")
        else:
            self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
            if self.toggle_button:
                self.toggle_button.config(text="▼")
    
    def is_collapsed(self) -> bool:
        """Return whether the frame is currently collapsed"""
        return self._is_collapsed
    
    def set_collapsed(self, collapsed: bool):
        """Set the collapsed state of the frame"""
        if self._is_collapsed != collapsed:
            self.toggle_collapsed()
    
    def set_title(self, title: str):
        """
        Set the frame title
        
        Args:
            title: New title text
        """
        self.title_var.set(title)
    
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