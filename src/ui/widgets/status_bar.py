import tkinter as tk
from tkinter import ttk
from typing import Optional, List, Dict

class StatusBar(ttk.Frame):
    """
    Status bar widget for displaying application status
    """
    def __init__(
        self, 
        master, 
        sections: Optional[List[Dict[str, int]]] = None,
        **kwargs
    ):
        """
        Initialize status bar
        
        Args:
            master: Parent widget
            sections: List of dictionaries with section names and relative widths
                     Example: [{"name": "status", "width": 3}, {"name": "info", "width": 1}]
            **kwargs: Additional arguments for Frame
        """
        super().__init__(master, **kwargs)
        
        self.sections = sections or [{"name": "status", "width": 1}]
        self.section_labels = {}
        
        # Calculate total weight
        total_weight = sum(section["width"] for section in self.sections)
        
        # Create each section
        for section in self.sections:
            name = section["name"]
            weight = section["width"] / total_weight
            
            label = ttk.Label(self, text="", relief=tk.SUNKEN, anchor=tk.W)
            label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1, pady=1)
            
            # Set weight to determine relative width
            self.columnconfigure(len(self.section_labels), weight=int(weight * 100))
            self.section_labels[name] = label
    
    def set_status(self, section: str, text: str, fg: str = None):
        """
        Set text for a section
        
        Args:
            section: Section name
            text: Status text
            fg: Text color (optional)
        """
        if section in self.section_labels:
            label = self.section_labels[section]
            label.config(text=f" {text}")
            if fg:
                label.config(foreground=fg)
    
    def set_status_color(self, section: str, color: str):
        """
        Set the text color for a status section
        
        Args:
            section: Section name
            color: Text color
        """
        if section in self.section_labels:
            self.section_labels[section].config(foreground=color)
    
    def clear(self):
        """Clear all status text"""
        for label in self.section_labels.values():
            label.config(text="", foreground="black") 