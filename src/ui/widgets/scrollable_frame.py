import tkinter as tk
from tkinter import ttk

class ScrollableFrame(ttk.Frame):
    """
    A frame with a scrollbar that allows content to scroll vertically
    """
    def __init__(self, container, **kwargs):
        """
        Initialize the scrollable frame
        
        Args:
            container: The parent container widget
            **kwargs: Additional frame options
        """
        super().__init__(container, **kwargs)
        
        # Create a canvas for scrolling
        self.canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        
        # Create a frame inside the canvas to hold content
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Configure scrolling
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Add scrollable frame to canvas
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Configure canvas to expand horizontally with frame
        self.scrollable_frame.bind("<Configure>", self._configure_canvas)
        self.canvas.bind("<Configure>", self._configure_canvas_width)
        
        # Configure scrollbar
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Layout canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel scrolling
        self._bind_mouse_scroll(self.scrollable_frame)
        self._bind_mouse_scroll(self.canvas)
        
    def _configure_canvas(self, event):
        """Adjust the canvas to fit the content"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def _configure_canvas_width(self, event):
        """Adjust the width of canvas window to match canvas width"""
        self.canvas.itemconfig(self.canvas_frame, width=event.width)
        
    def _bind_mouse_scroll(self, widget):
        """Bind mouse wheel scrolling to widget"""
        widget.bind("<MouseWheel>", self._on_mousewheel)  # Windows
        widget.bind("<Button-4>", self._on_mousewheel)    # Linux scroll up
        widget.bind("<Button-5>", self._on_mousewheel)    # Linux scroll down
        
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units") 