"""
Autocomplete/Search functionality for Entry widgets with SQL Server lookup.
Uses pyodbc to fetch results from BUSY SQL Server tables.
"""

import tkinter as tk
from database.sql_server import fetch_autocomplete


class AutocompleteEntry:
    """
    A reusable autocomplete entry widget with SQL Server search functionality.
    
    Usage:
        autocomplete = AutocompleteEntry(
            parent_widget,
            query="SELECT TOP 20 name FROM master1 WHERE mastertype = 6 AND name LIKE ? ORDER BY name",
            query_params=lambda prefix: (prefix + "%",),
            result_column=0
        )
        entry = autocomplete.entry
    """
    
    def __init__(self, parent, query=None, query_params=None, result_column=0, max_results=20, 
                 listbox_height=6, entry_width=None, mastertype=None, **entry_kwargs):
        """
        Initialize the autocomplete entry widget.
        
        Args:
            parent: Parent tkinter widget
            query: (Legacy) SQL query string - unused, Busy uses mastertype
            query_params: (Legacy) Function - unused for Busy
            result_column: Column index (default: 0)
            max_results: Maximum results (default: 20)
            listbox_height: Height of dropdown (default: 6)
            entry_width: Width of entry (default: None)
            mastertype: Busy master type - 6=Item, 2=Party, etc.
            **entry_kwargs: Additional arguments for Entry
        """
        self.query = query
        self.query_params = query_params
        self.mastertype = mastertype if mastertype is not None else 6
        self.result_column = result_column
        self.max_results = max_results
        self.listbox_visible = False
        self.entry_parent = parent
        
        # Get root window for listbox positioning
        self.root = parent.winfo_toplevel()
        
        # Create Entry widget
        entry_kwargs['width'] = entry_width if entry_width else entry_kwargs.get('width', 40)
        self.entry = tk.Entry(parent, **entry_kwargs)
        
        # Create Listbox as child of root window for proper positioning
        self.listbox = tk.Listbox(
            self.root, 
            height=listbox_height, 
            bg="white", 
            relief=tk.SUNKEN, 
            borderwidth=2,
            selectmode=tk.SINGLE,
            exportselection=False
        )
        
        # Bind events
        self.entry.bind("<KeyRelease>", self._on_keyrelease)
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<Escape>", lambda e: self._hide_listbox())
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<Down>", self._on_down_arrow)
        self.entry.bind("<Up>", self._on_up_arrow)
        self.listbox.bind("<<ListboxSelect>>", self._on_listbox_click)
        self.listbox.bind("<Double-Button-1>", self._on_listbox_double_click)
        self.listbox.bind("<Return>", self._on_enter)
        self.listbox.bind("<FocusOut>", lambda e: self._hide_listbox_after_delay())
    
    def _show_listbox(self):
        """Show the autocomplete listbox below the entry."""
        # Always update position when showing
        self.entry.update_idletasks()
        self.root.update_idletasks()
        
        # Get entry position relative to root window
        entry_x = self.entry.winfo_rootx() - self.root.winfo_rootx()
        entry_y = self.entry.winfo_rooty() - self.root.winfo_rooty()
        entry_height = self.entry.winfo_height()
        entry_width = self.entry.winfo_width()
        
        # Position listbox below entry
        x = entry_x
        y = entry_y + entry_height
        width = max(entry_width, 200)  # Minimum width
        
        self.listbox.place(x=x, y=y, width=width)
        self.listbox.lift()  # Bring to front
        # Don't set focus here - keep focus on entry to avoid triggering focus_out
        self.listbox.update_idletasks()
        self.root.update_idletasks()
        self.listbox_visible = True
    
    def _hide_listbox(self):
        """Hide the autocomplete listbox."""
        self.listbox.place_forget()
        self.listbox_visible = False
    
    def _fill_entry(self, value):
        """Fill the entry with selected value and hide listbox."""
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)
        self._hide_listbox()
        # Restore focus to entry
        self.entry.focus_set()
        # Trigger any callback if set
        if hasattr(self, 'on_select'):
            self.on_select(value)
    
    def _fetch_results(self, prefix):
        """
        Fetch search results from Busy database via DLL GetRecordset.
        
        Args:
            prefix: Search prefix string
            
        Returns:
            List of result strings (Name column)
        """
        if not prefix or not prefix.strip():
            return []
        
        try:
            results = fetch_autocomplete(prefix.strip(), self.mastertype, self.max_results)
            return results
        except Exception as e:
            print(f"Error fetching autocomplete results: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _on_keyrelease(self, event):
        """Handle key release events in the entry."""
        if event.keysym in ("Return", "Escape", "Up", "Down"):
            if event.keysym == "Down" and self.listbox_visible and self.listbox.size() > 0:
                # Focus on listbox when down arrow pressed
                self.listbox.focus_set()
                self.listbox.selection_set(0)
            return
        
        text = self.entry.get()
        self.listbox.delete(0, tk.END)
        
        results = self._fetch_results(text)
        
        if not results:
            self._hide_listbox()
            return
        
        # Clear and populate listbox
        self.listbox.delete(0, tk.END)
        for item in results:
            self.listbox.insert(tk.END, item)
        
        # Show listbox with results
        self._show_listbox()
    
    def _on_enter(self, event):
        """Handle Enter key press."""
        if self.listbox.size() > 0 and self.listbox_visible:
            selection = self.listbox.curselection()
            if selection:
                self._fill_entry(self.listbox.get(selection[0]))
            else:
                # If no selection, fill with first item
                self._fill_entry(self.listbox.get(0))
        
        # If this event came from Listbox, we need to manually trigger Return on Entry
        # so that navigation logic (bound to Entry) will fire.
        if event.widget == self.listbox:
             self.entry.event_generate("<Return>")
             
        # Allow event to propagate to other handlers (like navigation)
        return
    
    def _on_listbox_click(self, event):
        """Handle listbox item selection."""
        if not self.listbox.curselection():
            return
        self._fill_entry(self.listbox.get(self.listbox.curselection()))
        # Trigger navigation on click too? Maybe purely focus is enough.
        # User asked for 'enter' behavior mainly. Focus is already set by _fill_entry fix.

    def _on_listbox_double_click(self, event):
        """Handle listbox item double-click."""
        if not self.listbox.curselection():
            return
        self._fill_entry(self.listbox.get(self.listbox.curselection()))
        # Double click usually implies "done", so trigger navigation
        self.entry.event_generate("<Return>")
    
    def _on_down_arrow(self, event):
        """Handle down arrow key."""
        if self.listbox_visible and self.listbox.size() > 0:
            self.listbox.focus_set()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(0)
            self.listbox.activate(0)
        return "break"
    
    def _on_up_arrow(self, event):
        """Handle up arrow key."""
        if self.listbox_visible:
            self._hide_listbox()
        return "break"
    
    def _hide_listbox_after_delay(self):
        """Hide listbox after a delay (used for focus out)."""
        self.root.after(200, self._check_and_hide_listbox)
    
    def _check_and_hide_listbox(self):
        """Check if focus is still on entry or listbox before hiding."""
        focus = self.root.focus_get()
        if focus != self.entry and focus != self.listbox:
            self._hide_listbox()
    
    def _on_focus_out(self, event):
        """Handle focus out event - hide listbox after a short delay."""
        # Only hide if focus is not moving to listbox
        # Use after to allow listbox clicks to register
        self.root.after(200, self._check_and_hide_listbox)
    
    def set_on_select_callback(self, callback):
        """
        Set a callback function to be called when an item is selected.
        
        Args:
            callback: Function that takes one argument (selected value)
        """
        self.on_select = callback
    
    def get(self):
        """Get the current value of the entry."""
        return self.entry.get()
    
    def set(self, value):
        """Set the value of the entry."""
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)
    
    def delete(self, first, last=None):
        """Delete text from the entry."""
        self.entry.delete(first, last)


def create_item_autocomplete(parent, mastertype=6, **kwargs):
    """
    Convenience function to create an autocomplete entry for item/party search.
    
    Args:
        parent: Parent tkinter widget
        mastertype: Busy master type - 6=Item, 2=Party (default: 6)
        **kwargs: Additional arguments for AutocompleteEntry
        
    Returns:
        AutocompleteEntry instance
    """
    return AutocompleteEntry(
        parent,
        mastertype=mastertype,
        result_column=0,
        max_results=20,
        **kwargs
    )

