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
        
        # Determine if we have a theme manager to detect dark mode
        # Try to get theme manager from parent chain
        self.theme_manager = None
        self.use_dark_mode = False
        
        parent = self.master
        while parent:
            if hasattr(parent, 'theme_manager'):
                self.theme_manager = parent.theme_manager
                break
            if hasattr(parent, 'master'):
                parent = parent.master
            else:
                break
        
        # Set dark mode based on theme manager
        if self.theme_manager:
            self.use_dark_mode = self.theme_manager.is_dark_theme()
            # Bind to theme changes
            self.bind("<<ThemeChanged>>", self._on_theme_changed)
        
        # Add a style to make the frame more visible
        style = ttk.Style()
        border_color = "#dddddd" if not self.use_dark_mode else "#444444"
        
        # Configure styles for different frame states
        style.configure(
            "LabeledFrame.TFrame", 
            relief="solid", 
            borderwidth=1,
            bordercolor=border_color
        )
        self.configure(style="LabeledFrame.TFrame")
        
        # Create header frame with gradient background
        self.header_frame = ttk.Frame(self, padding=(8, 5))
        self.header_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Title label
        self.title_var = tk.StringVar(value=title)
        self.title_label = ttk.Label(
            self.header_frame, 
            textvariable=self.title_var, 
            font=("Segoe UI", 10, "bold")
        )
        self.title_label.pack(side=tk.LEFT, anchor=tk.W)
        
        # Expand/collapse indicator for collapsible frames
        self.toggle_button = None
        if collapsible:
            toggle_style = "ToggleDark.TLabel" if self.use_dark_mode else "Toggle.TLabel"
            style.configure(toggle_style, font=("Segoe UI", 10))
            self.toggle_button = ttk.Label(
                self.header_frame,
                text="▼" if not collapsed else "▶",
                cursor="hand2",
                style=toggle_style
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
            self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        
        # Separator
        self.separator = ttk.Separator(self, orient=tk.HORIZONTAL)
        self.separator.pack(fill=tk.X, padx=0, pady=0)
    
    def _on_theme_changed(self, event=None):
        """Handle theme changes to update frame appearance"""
        if self.theme_manager:
            self.use_dark_mode = self.theme_manager.is_dark_theme()
            
            # Update toggle button style
            if self.toggle_button:
                toggle_style = "ToggleDark.TLabel" if self.use_dark_mode else "Toggle.TLabel"
                self.toggle_button.configure(style=toggle_style)
            
            # Update frame border color
            style = ttk.Style()
            border_color = "#dddddd" if not self.use_dark_mode else "#444444"
            style.configure("LabeledFrame.TFrame", bordercolor=border_color)
    
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
            self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
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
        
        # Create a style for toolbar buttons
        style = ttk.Style()
        button_style = "ToolbarDark.TButton" if self.use_dark_mode else "Toolbar.TButton"
        style.configure(button_style, padding=3, font=("Segoe UI", 9))
        
        button = ttk.Button(
            self.toolbar_frame, 
            text=text, 
            command=command, 
            style=button_style,
            **kwargs
        )
        button.pack(side=tk.LEFT, padx=2)
        return button
        
    def get_content_frame(self) -> ttk.Frame:
        """
        Get the content frame to add widgets to
        
        Returns:
            The content frame
        """
        return self.content_frame 