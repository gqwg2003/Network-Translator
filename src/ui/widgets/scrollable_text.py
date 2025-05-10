import tkinter as tk
from tkinter import scrolledtext
from typing import Optional, Callable

class ScrollableText(scrolledtext.ScrolledText):
    """
    Enhanced scrollable text widget with additional functionality
    """
    def __init__(
        self, 
        master, 
        placeholder: str = "", 
        readonly: bool = False,
        on_change_callback: Optional[Callable] = None,
        dark_mode: bool = True,
        **kwargs
    ):
        """
        Initialize a scrollable text widget with advanced features
        
        Args:
            master: Parent widget
            placeholder: Placeholder text to display when empty
            readonly: Whether the text field should be read-only
            on_change_callback: Function to call when text changes
            dark_mode: Whether to use dark mode colors
            **kwargs: Additional arguments for ScrolledText
        """
        # Set dark mode colors if not specified
        if dark_mode and 'bg' not in kwargs:
            kwargs['bg'] = '#2A2A3A'  # Темно-синий оттенок для фона
        if dark_mode and 'fg' not in kwargs:
            kwargs['fg'] = '#E0E0E0'  # Светло-серый текст для тёмного фона
        if dark_mode and 'insertbackground' not in kwargs:
            kwargs['insertbackground'] = '#CCCCCC'  # Цвет курсора
            
        super().__init__(master, wrap=tk.WORD, **kwargs)
        
        self.placeholder = placeholder
        self.placeholder_color = "#888888" if dark_mode else "gray"
        self.default_color = self.cget("fg")
        self.readonly = readonly
        self.on_change_callback = on_change_callback
        self.dark_mode = dark_mode
        
        # Bind events
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<<Modified>>", self._on_modified)
        
        # Set initial state
        if readonly:
            self.config(state=tk.DISABLED)
        
        # Show placeholder if needed
        if not self.get("1.0", tk.END).strip():
            self._show_placeholder()
    
    def _on_focus_in(self, event):
        """Handle focus in event"""
        if self.readonly:
            return
        
        if self.get("1.0", tk.END).strip() == self.placeholder:
            self.delete("1.0", tk.END)
            self.config(fg=self.default_color)
    
    def _on_focus_out(self, event):
        """Handle focus out event"""
        if not self.get("1.0", tk.END).strip():
            self._show_placeholder()
    
    def _on_modified(self, event):
        """Handle text modified event"""
        self.edit_modified(False)  # Reset the modified flag
        if self.on_change_callback and not self.readonly:
            self.on_change_callback()
    
    def _show_placeholder(self):
        """Display the placeholder text"""
        if self.readonly:
            return
            
        self.delete("1.0", tk.END)
        self.config(fg=self.placeholder_color)
        self.insert("1.0", self.placeholder)
    
    def get_text(self) -> str:
        """
        Get the text content, ignoring placeholder
        
        Returns:
            The actual text content
        """
        text = self.get("1.0", tk.END).strip()
        if text == self.placeholder:
            return ""
        return text
    
    def set_text(self, text: str):
        """
        Set the text content
        
        Args:
            text: The text to set
        """
        if self.readonly:
            # Temporarily enable to set text
            self.config(state=tk.NORMAL)
            self.delete("1.0", tk.END)
            self.insert("1.0", text)
            self.config(state=tk.DISABLED)
        else:
            self.delete("1.0", tk.END)
            if text:
                self.config(fg=self.default_color)
                self.insert("1.0", text)
            else:
                self._show_placeholder()
    
    def set_readonly(self, readonly: bool):
        """
        Set whether the widget is read-only
        
        Args:
            readonly: Read-only state
        """
        self.readonly = readonly
        if readonly:
            self.config(state=tk.DISABLED)
        else:
            self.config(state=tk.NORMAL)
            
    def set_dark_mode(self, dark_mode: bool):
        """
        Set dark mode colors
        
        Args:
            dark_mode: Whether to use dark mode colors
        """
        self.dark_mode = dark_mode
        if dark_mode:
            self.config(bg='#2A2A3A', fg='#E0E0E0', insertbackground='#CCCCCC')
            self.placeholder_color = "#888888"
        else:
            self.config(bg='white', fg='black', insertbackground='black')
            self.placeholder_color = "gray"
            
        # Update text color if showing placeholder
        if self.get("1.0", tk.END).strip() == self.placeholder:
            self.config(fg=self.placeholder_color) 