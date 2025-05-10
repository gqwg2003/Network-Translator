import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional

class ThemeManager:
    """
    Manager for application theming and styling
    """
    # Predefined themes
    THEMES = {
        "light": {
            "bg": "#FFFFFF",
            "fg": "#000000",
            "accent": "#1976D2",
            "error": "#D32F2F",
            "success": "#388E3C",
            "warning": "#FFA000",
            "info": "#0288D1",
            "text_bg": "#F5F5F5",  # Светло-серый фон для текстовых полей
            "text_fg": "#000000",
            "font": ("Segoe UI", 10),
            "header_font": ("Segoe UI", 12, "bold"),
        },
        "dark": {
            "bg": "#222222",
            "fg": "#EEEEEE",
            "accent": "#2196F3",
            "error": "#F44336",
            "success": "#4CAF50",
            "warning": "#FFC107",
            "info": "#03A9F4",
            "text_bg": "#333333",  # Тёмно-серый фон для текстовых полей 
            "text_fg": "#EEEEEE",
            "font": ("Segoe UI", 10),
            "header_font": ("Segoe UI", 12, "bold"),
        },
        "dark_blue": {
            "bg": "#1A1B2E",
            "fg": "#EEEEEE",
            "accent": "#3F51B5",
            "error": "#F44336",
            "success": "#4CAF50",
            "warning": "#FF9800",
            "info": "#29B6F6",
            "text_bg": "#2A2A3A",  # Тёмно-синий фон для текстовых полей
            "text_fg": "#E0E0E0",
            "font": ("Segoe UI", 10),
            "header_font": ("Segoe UI", 12, "bold"),
        },
        "plum": {
            "bg": "#2D1B36",
            "fg": "#EEEEEE",
            "accent": "#9C27B0",
            "error": "#F44336",
            "success": "#4CAF50",
            "warning": "#FFB300",
            "info": "#26A69A",
            "text_bg": "#3D2A45",  # Тёмно-сливовый фон для текстовых полей
            "text_fg": "#E0E0E0",
            "font": ("Segoe UI", 10),
            "header_font": ("Segoe UI", 12, "bold"),
        }
    }

    def __init__(self, root: tk.Tk, theme_name: str = "dark_blue"):
        """
        Initialize the theme manager
        
        Args:
            root: Root Tk instance
            theme_name: Name of the initial theme
        """
        self.root = root
        self.current_theme_name = theme_name
        self.style = ttk.Style()
        
        self._apply_theme(theme_name)
    
    def is_dark_theme(self) -> bool:
        """
        Check if the current theme is dark
        
        Returns:
            True if the current theme is dark
        """
        return self.current_theme_name in ["dark", "dark_blue", "plum"]
        
    def _apply_theme(self, theme_name: str):
        """
        Apply the specified theme
        
        Args:
            theme_name: Name of the theme to apply
        """
        # Validate theme_name
        if theme_name not in self.THEMES:
            theme_name = "dark_blue"
        
        self.current_theme_name = theme_name
        theme = self.THEMES[theme_name]
        
        # Set ttk theme
        try:
            # Try using a more modern ttk theme
            if theme_name in ["dark", "dark_blue", "plum"]:
                self.style.theme_use("clam")
            else:
                self.style.theme_use("vista" if self._is_windows() else "clam")
        except tk.TclError:
            # Fallback to a default theme
            try:
                self.style.theme_use("clam")
            except tk.TclError:
                pass
        
        # Configure widget colors and fonts
        self.style.configure(
            "TFrame", 
            background=theme["bg"]
        )
        
        self.style.configure(
            "TLabel", 
            background=theme["bg"],
            foreground=theme["fg"],
            font=theme["font"]
        )
        
        self.style.configure(
            "TButton", 
            background=theme["accent"],
            foreground=theme["fg"],
            font=theme["font"]
        )
        
        self.style.map(
            "TButton",
            background=[('active', theme["accent"])],
            foreground=[('active', theme["fg"])]
        )
        
        self.style.configure(
            "Accent.TButton",
            background=theme["accent"],
            foreground="#FFFFFF",
        )
        
        self.style.configure(
            "TNotebook", 
            background=theme["bg"],
            tabmargins=[2, 5, 2, 0]
        )
        
        self.style.configure(
            "TNotebook.Tab", 
            background=theme["bg"],
            foreground=theme["fg"],
            font=theme["font"],
            padding=[10, 2]
        )
        
        self.style.map(
            "TNotebook.Tab",
            background=[('selected', theme["accent"])],
            foreground=[('selected', "#FFFFFF")]
        )
        
        # Configure entry widgets
        self.style.configure(
            "TEntry",
            fieldbackground=theme["text_bg"],
            foreground=theme["text_fg"]
        )
        
        # Configure root window
        self.root.configure(bg=theme["bg"])
        
        # Notify change
        self.root.event_generate("<<ThemeChanged>>")
        
    def get_theme(self) -> Dict[str, Any]:
        """
        Get the current theme dictionary
        
        Returns:
            The current theme's color and font settings
        """
        return self.THEMES[self.current_theme_name]
    
    def get_theme_name(self) -> str:
        """Get the current theme name"""
        return self.current_theme_name
    
    def set_theme(self, theme_name: str):
        """
        Set the application theme
        
        Args:
            theme_name: Name of the theme to apply
        """
        self._apply_theme(theme_name)
    
    def toggle_theme(self):
        """
        Toggle between light and dark themes
        
        Returns:
            The name of the new theme
        """
        themes = list(self.THEMES.keys())
        current_index = themes.index(self.current_theme_name)
        new_index = (current_index + 1) % len(themes)
        new_theme = themes[new_index]
        self._apply_theme(new_theme)
        return new_theme
        
    def create_custom_theme(self, name: str, settings: Dict[str, Any]):
        """
        Create a custom theme
        
        Args:
            name: Name for the custom theme
            settings: Dictionary of theme settings
        """
        # Create a copy of the light theme as base
        base_theme = self.THEMES["light"].copy()
        
        # Update with custom settings
        base_theme.update(settings)
        
        # Add to available themes
        self.THEMES[name] = base_theme
    
    def _is_windows(self) -> bool:
        """Check if running on Windows"""
        return self.root.tk.call('tk', 'windowingsystem') == 'win32'
    
    def _is_macos(self) -> bool:
        """Check if running on macOS"""
        return self.root.tk.call('tk', 'windowingsystem') == 'aqua' 