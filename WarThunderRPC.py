import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
import subprocess
import threading
import sys
import os
import logging
import importlib.util
import json
import queue
import re
import traceback
import platform
import winreg

# Define a custom tooltip class
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.id = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        self.id = self.widget.after(500, self._show)

    def _show(self):
        if not self.tooltip_window:
            x, y, cx, cy = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + self.widget.winfo_height() + 5

            self.tooltip_window = tk.Toplevel(self.widget)
            self.tooltip_window.wm_overrideredirect(True)
            self.tooltip_window.wm_geometry(f"+{x}+{y}")

            label = tk.Label(self.tooltip_window, text=self.text, background="#FFFFCC", relief="solid", borderwidth=1,
                             font=("Arial", 8, "normal"))
            label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        if self.id:
            self.widget.after_cancel(self.id)
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None

# Default message templates (duplicated from main.py for GUI's reset functionality)
DEFAULT_MESSAGE_TEMPLATES = {
    'hangar_state': "In the hangar",
    'hangar_details': "Looking at {vehicle_display_name}",
    'hangar_details_browsing': "Browsing vehicles...",
    'match_state': "{vehicle_type_action} a {vehicle_display_name}",
    'match_details': "{match_type} on {map_display_name}",
    'loading_match_state': "Loading into a match..",
    'loading_match_details': "Loading into a match on {map_display_name}..",
    'test_drive_state': "{vehicle_type_action} a {vehicle_display_name} (Test Drive)",
    'test_drive_details': "In Test Drive on Western Europe",
    'vehicle_br_text': "BR: {br_value}",
    'vehicle_country_text': "({country_display_name})",
}

class RPCLuncherApp:
    def __init__(self, master):
        self.master = master
        master.title("War Thunder RPC Launcher")
        master.geometry("800x750") # Adjusted height for new controls, now larger than 700x700
        master.resizable(True, True)
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Set the application icon
        # For Windows, use a .ico file. For other OS, .gif or .png might work.
        # Ensure 'icon.ico' is in the same directory as the script/executable.
        try:
            icon_path = os.path.join(os.path.dirname(sys.executable) if hasattr(sys, '_MEIPASS') else os.path.dirname(os.path.abspath(__file__)), 'icon.ico')
            if os.path.exists(icon_path):
                master.iconbitmap(icon_path)
            else:
                print(f"WARNING: Icon file not found at {icon_path}. Default Tkinter icon will be used.")
        except Exception as e:
            print(f"ERROR: Could not set window icon: {e}")


        # Dark theme colors
        self.bg_color = "#2C2F33"
        self.fg_color = "#FFFFFF"
        self.console_bg_color = "#23272A"
        self.button_start_color = "#4CAF50"
        self.button_stop_color = "#F44336"
        self.button_save_color = "#2196F3"
        self.status_ready_color = "#4CAF50"
        self.status_running_color = "#2196F3"
        self.status_error_color = "#F44336"
        self.status_warning_color = "#FFC107"

        master.config(bg=self.bg_color)

        # Configure ttk theme for a modern look
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('TFrame', background=self.bg_color)
        style.configure('TLabel', background=self.bg_color, foreground=self.fg_color, font=('Inter', 10))
        style.configure('TEntry', fieldbackground="#40444B", foreground=self.fg_color, font=('Inter', 10), borderwidth=1, relief="flat")
        style.map('TEntry', fieldbackground=[('focus', '#50545B')])

        style.configure('Start.TButton', background=self.button_start_color, foreground=self.fg_color, font=('Inter', 10, 'bold'), borderwidth=0, relief="raised")
        style.map('Start.TButton', background=[('active', self.button_start_color), ('disabled', '#606060')], foreground=[('disabled', '#A0A0A0')])

        style.configure('Stop.TButton', background=self.button_stop_color, foreground=self.fg_color, font=('Inter', 10, 'bold'), borderwidth=0, relief="raised")
        style.map('Stop.TButton', background=[('active', self.button_stop_color), ('disabled', '#606060')], foreground=[('disabled', '#A0A0A0')])

        style.configure('Save.TButton', background=self.button_save_color, foreground=self.fg_color, font=('Inter', 10, 'bold'), borderwidth=0, relief="raised")
        style.map('Save.TButton', background=[('active', self.button_save_color), ('disabled', '#606060')], foreground=[('disabled', '#A0A0A0')])

        style.configure('Status.TLabel', background=self.status_ready_color, foreground=self.fg_color, font=('Inter', 10, 'bold'), padding=(10, 5), relief="flat")

        # Map Updater Window specific styles
        style.configure('MapUpdater.TFrame', background="#36393F", relief="solid", borderwidth=1, bordercolor="#1E2124")
        style.configure('MapUpdater.TLabel', background="#36393F", foreground=self.fg_color, font=('Inter', 10))
        style.configure('MapUpdaterTitle.TLabel', background="#36393F", foreground=self.fg_color, font=('Inter', 12, 'bold'))
        style.configure('MapUpdater.TEntry', fieldbackground="#40444B", foreground=self.fg_color, font=('Inter', 10), borderwidth=1, relief="flat")
        style.map('MapUpdater.TEntry', fieldbackground=[('focus', '#50545B')])
        style.configure('MapUpdater.TButton', background="#607D8B", foreground=self.fg_color, font=('Inter', 10, 'bold'), borderwidth=0, relief="raised")
        style.map('MapUpdater.TButton', background=[('active', "#78909C")])

        # Checkbutton style
        style.configure('TCheckbutton', background=self.bg_color, foreground=self.fg_color, font=('Inter', 10))
        style.map('TCheckbutton', background=[('active', self.bg_color)]) # Keep background consistent on hover

        # Settings Frame Label
        style.configure('Settings.TLabel', background=self.bg_color, foreground=self.fg_color, font=('Inter', 11, 'bold'))


        self.rpc_process = None
        self.rpc_thread = None
        self.output_queue = queue.Queue()
        self.preview_queue = queue.Queue() # Still needed for main.py communication, but won't be processed for display
        self.queue_lock = threading.Lock()

        if hasattr(sys, '_MEIPASS'):
            self.config_file = os.path.join(os.path.dirname(sys.executable), 'config.json')
            self.base_assets_path = sys._MEIPASS
            self.maps_file_path = os.path.join(sys._MEIPASS, 'maps.py') # Path to maps.py in bundled exe
        else:
            self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
            self.base_assets_path = os.path.dirname(os.path.abspath(__file__))
            self.maps_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'maps.py') # Path to maps.py in dev env

        # Initialize attributes that are accessed early (e.g., in _load_config)
        self.detailed_logging_var = tk.BooleanVar()
        self.auto_start_rpc_var = tk.BooleanVar() # New: Auto-start RPC variable
        self.console_output = scrolledtext.ScrolledText(master, wrap=tk.WORD, state='disabled',
                                                        bg=self.console_bg_color, fg=self.fg_color,
                                                        font=('Consolas', 9), relief="sunken", borderwidth=2)
        
        # Initialize StringVars for customizable messages with default values
        self.hangar_state_template = tk.StringVar(value=DEFAULT_MESSAGE_TEMPLATES['hangar_state'])
        self.hangar_details_template = tk.StringVar(value=DEFAULT_MESSAGE_TEMPLATES['hangar_details'])
        self.hangar_details_browsing_template = tk.StringVar(value=DEFAULT_MESSAGE_TEMPLATES['hangar_details_browsing'])

        self.match_state_template = tk.StringVar(value=DEFAULT_MESSAGE_TEMPLATES['match_state'])
        self.match_details_template = tk.StringVar(value=DEFAULT_MESSAGE_TEMPLATES['match_details'])
        self.loading_match_state_template = tk.StringVar(value=DEFAULT_MESSAGE_TEMPLATES['loading_match_state'])
        self.loading_match_details_template = tk.StringVar(value=DEFAULT_MESSAGE_TEMPLATES['loading_match_details'])

        self.test_drive_state_template = tk.StringVar(value=DEFAULT_MESSAGE_TEMPLATES['test_drive_state'])
        self.test_drive_details_template = tk.StringVar(value=DEFAULT_MESSAGE_TEMPLATES['test_drive_details'])

        self.vehicle_br_text_template = tk.StringVar(value=DEFAULT_MESSAGE_TEMPLATES['vehicle_br_text'])
        self.vehicle_country_text_template = tk.StringVar(value=DEFAULT_MESSAGE_TEMPLATES['vehicle_country_text'])


        class TkinterTextHandler(logging.Handler):
            def __init__(self, app_instance):
                super().__init__()
                self.app = app_instance
            
            def emit(self, record):
                msg = self.format(record)
                with self.app.queue_lock:
                    self.app.output_queue.put(msg + '\n')

        self.tkinter_logger_handler = TkinterTextHandler(self)
        self.tkinter_logger_handler.setLevel(logging.INFO) # Default level for GUI handler
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.tkinter_logger_handler.setFormatter(formatter)


        # --- UI Elements ---
        # Configure master grid to manage its direct children
        self.master.grid_rowconfigure(0, weight=0) # Row for title (fixed height)
        self.master.grid_rowconfigure(1, weight=1) # Row for main content frame (expands vertically)
        self.master.grid_columnconfigure(0, weight=1) # Column for all content (expands horizontally)

        # Main Title (now placed using grid)
        self.title_label = ttk.Label(master, text="War Thunder RPC", font=('Inter', 18, 'bold'),
                                     background=self.bg_color, foreground=self.fg_color)
        self.title_label.grid(row=0, column=0, pady=(20, 10), sticky="n") # Sticky "n" to align at top, center horizontally

        # Main frame to hold all other content (now placed using grid)
        main_content_frame = ttk.Frame(master, style='TFrame')
        main_content_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew") # Fill available space

        # Configure grid within main_content_frame (this is fine, as it's a child's grid)
        main_content_frame.grid_columnconfigure(0, weight=1) # Allow content within this frame to expand horizontally

        client_id_frame = ttk.Frame(main_content_frame)
        client_id_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        client_id_frame.grid_columnconfigure(1, weight=1) # Client ID entry
        client_id_frame.grid_columnconfigure(2, weight=0) # Save ID button
        client_id_frame.grid_columnconfigure(3, weight=0) # Settings button (new)

        ttk.Label(client_id_frame, text="Discord Client ID:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.client_id_entry = ttk.Entry(client_id_frame)
        self.client_id_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        ToolTip(self.client_id_entry, "Enter your Discord Application Client ID here.")
        
        self.save_id_button = ttk.Button(client_id_frame, text="Save ID", command=self._save_config, style='Save.TButton')
        self.save_id_button.grid(row=0, column=2, padx=5, pady=2, sticky="e")
        ToolTip(self.save_id_button, "Save the entered Client ID to config.json.")

        # New Settings Button
        self.settings_button = ttk.Button(client_id_frame, text="Settings", command=self._open_settings_window, style='Save.TButton')
        self.settings_button.grid(row=0, column=3, padx=5, pady=2, sticky="e")
        ToolTip(self.settings_button, "Open application settings.")


        button_frame = ttk.Frame(main_content_frame)
        button_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        button_frame.grid_columnconfigure(2, weight=1) # For the new Hide Window button

        self.start_button = ttk.Button(button_frame, text="Start RPC", command=self.start_rpc, style='Start.TButton')
        self.start_button.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        ToolTip(self.start_button, "Start the Discord Rich Presence script.")

        self.stop_button = ttk.Button(button_frame, text="Stop RPC", command=self.stop_rpc, state=tk.DISABLED, style='Stop.TButton')
        self.stop_button.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        ToolTip(self.stop_button, "Stop the Discord Rich Presence script.")

        # New Hide Window Button
        self.hide_button = ttk.Button(button_frame, text="Hide Window", command=self._hide_window, style='Save.TButton')
        self.hide_button.grid(row=0, column=2, padx=10, pady=5, sticky="ew")
        ToolTip(self.hide_button, "Hide the main application window to the taskbar.")


        self.status_label = ttk.Label(main_content_frame, text="Status: Initializing...", anchor="center", style='Status.TLabel')
        self.status_label.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        # Console output
        self.console_output.grid(row=3, column=0, padx=10, pady=10, sticky="nsew") # Moved .grid() call here
        main_content_frame.grid_rowconfigure(3, weight=1) # Make console expand vertically

        self.master.after(100, self.update_console)
        self.master.after(100, self._process_queue_messages)

        self._load_config()
        self._update_status("Ready", color_key='ready')

        # Auto-start RPC if configured
        if self.auto_start_rpc_var.get():
            self.start_rpc()

    def _update_status(self, message, color_key='default'):
        color_map = {
            'ready': self.status_ready_color,
            'running': self.status_running_color,
            'error': self.status_error_color,
            'warning': self.status_warning_color,
            'default': self.bg_color
        }
        bg_color = color_map.get(color_key, self.bg_color)
        self.status_label.config(text=f"Status: {message}", background=bg_color)
        self.status_label.config(foreground=self.fg_color) 

    def _load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    client_id = config.get('client_id', '')
                    self.client_id_entry.delete(0, tk.END)
                    self.client_id_entry.insert(0, client_id)
                    
                    # Load logging preference
                    detailed_logging = config.get('detailed_logging', False)
                    self.detailed_logging_var.set(detailed_logging)
                    # Apply the loaded logging preference to the GUI's console handler immediately
                    self.tkinter_logger_handler.setLevel(logging.DEBUG if detailed_logging else logging.INFO)

                    # Load auto-start preference
                    auto_start_rpc = config.get('auto_start_rpc', False)
                    self.auto_start_rpc_var.set(auto_start_rpc)

                    # Load customizable message templates
                    self.hangar_state_template.set(config.get('hangar_state_template', DEFAULT_MESSAGE_TEMPLATES['hangar_state']))
                    self.hangar_details_template.set(config.get('hangar_details_template', DEFAULT_MESSAGE_TEMPLATES['hangar_details']))
                    self.hangar_details_browsing_template.set(config.get('hangar_details_browsing_template', DEFAULT_MESSAGE_TEMPLATES['hangar_details_browsing']))
                    self.match_state_template.set(config.get('match_state_template', DEFAULT_MESSAGE_TEMPLATES['match_state']))
                    self.match_details_template.set(config.get('match_details_template', DEFAULT_MESSAGE_TEMPLATES['match_details']))
                    self.loading_match_state_template.set(config.get('loading_match_state_template', DEFAULT_MESSAGE_TEMPLATES['loading_match_state']))
                    self.loading_match_details_template.set(config.get('loading_match_details_template', DEFAULT_MESSAGE_TEMPLATES['loading_match_details']))
                    self.test_drive_state_template.set(config.get('test_drive_state_template', DEFAULT_MESSAGE_TEMPLATES['test_drive_state']))
                    self.test_drive_details_template.set(config.get('test_drive_details_template', DEFAULT_MESSAGE_TEMPLATES['test_drive_details']))
                    self.vehicle_br_text_template.set(config.get('vehicle_br_text_template', DEFAULT_MESSAGE_TEMPLATES['vehicle_br_text']))
                    self.vehicle_country_text_template.set(config.get('vehicle_country_text_template', DEFAULT_MESSAGE_TEMPLATES['vehicle_country_text']))


                self.console_output.config(state='normal')
                self.console_output.insert(tk.END, f"Loaded Client ID and settings from {os.path.basename(self.config_file)}\n")
                self.console_output.config(state='disabled')
                self._update_status("Client ID and settings loaded.", color_key='ready')
            except Exception as e:
                messagebox.showerror("Config Error", f"Failed to load config.json: {e}")
                self.console_output.config(state='normal')
                self.console_output.insert(tk.END, f"ERROR: Failed to load config.json: {e}\n")
                self.console_output.config(state='disabled')
                self._update_status("Error loading config.", color_key='error')
        else:
            self.console_output.config(state='normal')
            self.console_output.insert(tk.END, f"'{os.path.basename(self.config_file)}' not found. Please enter your Discord Client ID.\n")
            self.console_output.config(state='disabled')
            self._update_status("Config file not found. Enter Client ID.", color_key='warning')

    def _save_config(self):
        """
        Saves all current configuration settings (client ID, logging, auto-start, messages) to config.json.
        """
        client_id = self.client_id_entry.get().strip()
        if not client_id:
            messagebox.showwarning("Input Warning", "Client ID cannot be empty.")
            self._update_status("Client ID cannot be empty.", color_key='warning')
            return

        config = {}
        # Load existing config to preserve other settings if they exist
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except json.JSONDecodeError:
                messagebox.showwarning("Config Error", "Existing config.json is corrupted. Creating new one.")
                config = {}
        
        config['client_id'] = client_id
        config['detailed_logging'] = self.detailed_logging_var.get()
        config['auto_start_rpc'] = self.auto_start_rpc_var.get() # Save auto-start preference

        # Save all message template values
        config['hangar_state_template'] = self.hangar_state_template.get()
        config['hangar_details_template'] = self.hangar_details_template.get()
        config['hangar_details_browsing_template'] = self.hangar_details_browsing_template.get()
        config['match_state_template'] = self.match_state_template.get()
        config['match_details_template'] = self.match_details_template.get()
        config['loading_match_state_template'] = self.loading_match_state_template.get()
        config['loading_match_details_template'] = self.loading_match_details_template.get()
        config['test_drive_state_template'] = self.test_drive_state_template.get()
        config['test_drive_details_template'] = self.test_drive_details_template.get()
        config['vehicle_br_text_template'] = self.vehicle_br_text_template.get()
        config['vehicle_country_text_template'] = self.vehicle_country_text_template.get()

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            self.console_output.config(state='normal')
            self.console_output.insert(tk.END, f"Configuration saved to {os.path.basename(self.config_file)}\n")
            self.console_output.config(state='disabled')
            messagebox.showinfo("Success", "Configuration saved successfully!")
            self._update_status("Configuration saved successfully.", color_key='ready')
            
            # Immediately apply the new logging level to the GUI's console handler
            self.tkinter_logger_handler.setLevel(logging.DEBUG if self.detailed_logging_var.get() else logging.INFO)

        except Exception as e:
            messagebox.showerror("Config Error", f"Failed to save config.json: {e}")
            self.console_output.config(state='normal')
            self.console_output.insert(tk.END, f"ERROR: Failed to save config.json: {e}\n")
            self.console_output.config(state='disabled')
            self._update_status("Error saving config.", color_key='error')

    def _reset_message_templates_to_default(self):
        """
        Resets all message template StringVars to their default values and saves them.
        """
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset all message templates to their default values?"):
            self.hangar_state_template.set(DEFAULT_MESSAGE_TEMPLATES['hangar_state'])
            self.hangar_details_template.set(DEFAULT_MESSAGE_TEMPLATES['hangar_details'])
            self.hangar_details_browsing_template.set(DEFAULT_MESSAGE_TEMPLATES['hangar_details_browsing'])
            self.match_state_template.set(DEFAULT_MESSAGE_TEMPLATES['match_state'])
            self.match_details_template.set(DEFAULT_MESSAGE_TEMPLATES['match_details'])
            self.loading_match_state_template.set(DEFAULT_MESSAGE_TEMPLATES['loading_match_state'])
            self.loading_match_details_template.set(DEFAULT_MESSAGE_TEMPLATES['loading_match_details'])
            self.test_drive_state_template.set(DEFAULT_MESSAGE_TEMPLATES['test_drive_state'])
            self.test_drive_details_template.set(DEFAULT_MESSAGE_TEMPLATES['test_drive_details'])
            self.vehicle_br_text_template.set(DEFAULT_MESSAGE_TEMPLATES['vehicle_br_text'])
            self.vehicle_country_text_template.set(DEFAULT_MESSAGE_TEMPLATES['vehicle_country_text'])
            
            # Now save these defaults to config.json
            self._save_config() # Call the unified save method
            self.console_output.config(state='normal')
            self.console_output.insert(tk.END, "Message templates reset to default and saved.\n")
            self.console_output.config(state='disabled')
            self._update_status("Message templates reset.", color_key='ready')
        else:
            self.console_output.config(state='normal')
            self.console_output.insert(tk.END, "Message template reset cancelled.\n")
            self.console_output.config(state='disabled')
            self._update_status("Reset cancelled.", color_key='warning')


    def _clear_console(self):
        self.console_output.config(state='normal')
        self.console_output.delete(1.0, tk.END)
        self.console_output.config(state='disabled')
        self._update_status("Console cleared.", color_key='ready')

    def _process_queue_messages(self):
        """Processes messages from the preview_queue (now only for status/errors)."""
        try:
            while True:
                message = self.preview_queue.get_nowait()
                msg_type = message.get('type')

                if msg_type == 'status':
                    self._update_status(message.get('message'), message.get('color_key'))
                elif msg_type == 'error':
                    self._update_status(message.get('message'), color_key='error')
                elif msg_type == 'warning':
                    self._update_status(message.get('message'), color_key='warning')
        except queue.Empty:
            pass
        except Exception as e:
            self.console_output.config(state='normal')
            self.console_output.insert(tk.END, f"ERROR processing preview queue: {e}\n")
            self.console_output.insert(tk.END, traceback.format_exc() + '\n')
            self.console_output.config(state='disabled')
            self._update_status("Internal GUI error.", color_key='error')
        finally:
            self.master.after(100, self._process_queue_messages)

    def _hide_window(self):
        """Hides the main application window by minimizing it to the taskbar."""
        self.master.iconify() # Use iconify to minimize to taskbar
        self._update_status("Window minimized to taskbar. RPC may still be running.", color_key='running')

    def _show_window(self):
        """Shows the main application window."""
        self.master.deiconify()
        self.master.lift()
        self.master.focus_force()
        self._update_status("Window shown.", color_key='ready')


    def _open_settings_window(self):
        """
        Opens a new Toplevel window for application settings.
        """
        settings_window = tk.Toplevel(self.master)
        settings_window.title("Settings")
        settings_window.geometry("600x450") # Adjusted height after removing auto-start options
        settings_window.transient(self.master) # Make it appear on top of the main window
        settings_window.grab_set() # Make it modal
        settings_window.resizable(False, True) # Allow vertical resizing
        settings_window.config(bg=self.bg_color)

        # Create a notebook (tabbed interface) for settings
        notebook = ttk.Notebook(settings_window)
        notebook.pack(padx=10, pady=10, fill="both", expand=True)

        # General Settings Tab
        general_tab = ttk.Frame(notebook, style='TFrame')
        notebook.add(general_tab, text="General")
        general_tab.grid_columnconfigure(0, weight=0) # Label column
        general_tab.grid_columnconfigure(1, weight=1) # Entry column
        general_tab.grid_columnconfigure(2, weight=0) # Browse button column

        # Detailed Logging Checkbox
        self.detailed_logging_checkbox_settings = ttk.Checkbutton(general_tab,
                                                                  text="Enable Detailed Logging (for debugging)",
                                                                  variable=self.detailed_logging_var,
                                                                  command=self._save_config, # Now calls unified save
                                                                  style='TCheckbutton')
        self.detailed_logging_checkbox_settings.grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky="w")
        ToolTip(self.detailed_logging_checkbox_settings, "Check this for more verbose logging output in the console (useful for debugging).")

        # New: Auto-start RPC Checkbox
        self.auto_start_rpc_checkbox_settings = ttk.Checkbutton(general_tab,
                                                                text="Auto-start RPC on App Launch (Work in Progress)", # Added "Work in Progress"
                                                                variable=self.auto_start_rpc_var,
                                                                command=self._save_config, # Now calls unified save
                                                                style='TCheckbutton')
        self.auto_start_rpc_checkbox_settings.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="w")
        ToolTip(self.auto_start_rpc_checkbox_settings, "If checked, the RPC script will automatically start when this launcher application is opened.")


        # Update Map Data Button (Adjusted row to reflect new elements)
        self.update_map_button_settings = ttk.Button(general_tab, text="Update Map Data", command=self._open_map_updater_window, style='Save.TButton')
        self.update_map_button_settings.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        ToolTip(self.update_map_button_settings, "Open a window to add or update map hashes in maps.py.")

        # Clear Console Button (Adjusted row to reflect new elements)
        self.clear_console_button_settings = ttk.Button(general_tab, text="Clear Console", command=self._clear_console, style='Save.TButton')
        self.clear_console_button_settings.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        ToolTip(self.clear_console_button_settings, "Clear all messages from the console output.")

        # Customizable Messages Tab
        messages_tab = ttk.Frame(notebook, style='TFrame')
        notebook.add(messages_tab, text="Custom Messages")
        messages_tab.grid_columnconfigure(1, weight=1) # Make entry column expandable

        # --- Message Template Fields ---
        row_idx = 0
        ttk.Label(messages_tab, text="Hangar State:", style='TLabel').grid(row=row_idx, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(messages_tab, textvariable=self.hangar_state_template, style='TEntry').grid(row=row_idx, column=1, padx=5, pady=2, sticky="ew")
        ToolTip(ttk.Label(messages_tab, text="?", style='TLabel'), "Placeholders: None\nDefault: In the hangar")
        row_idx += 1

        ttk.Label(messages_tab, text="Hangar Details (Vehicle):", style='TLabel').grid(row=row_idx, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(messages_tab, textvariable=self.hangar_details_template, style='TEntry').grid(row=row_idx, column=1, padx=5, pady=2, sticky="ew")
        ToolTip(ttk.Label(messages_tab, text="?", style='TLabel'), "Placeholders: {vehicle_display_name}\nDefault: Looking at {vehicle_display_name}")
        row_idx += 1

        ttk.Label(messages_tab, text="Hangar Details (Browsing):", style='TLabel').grid(row=row_idx, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(messages_tab, textvariable=self.hangar_details_browsing_template, style='TEntry').grid(row=row_idx, column=1, padx=5, pady=2, sticky="ew")
        ToolTip(ttk.Label(messages_tab, text="?", style='TLabel'), "Placeholders: None\nDefault: Browsing vehicles...")
        row_idx += 1

        ttk.Label(messages_tab, text="Match State:", style='TLabel').grid(row=row_idx, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(messages_tab, textvariable=self.match_state_template, style='TEntry').grid(row=row_idx, column=1, padx=5, pady=2, sticky="ew")
        ToolTip(ttk.Label(messages_tab, text="?", style='TLabel'), "Placeholders: {vehicle_type_action}, {vehicle_display_name}\nDefault: {vehicle_type_action} a {vehicle_display_name}")
        row_idx += 1

        ttk.Label(messages_tab, text="Match Details:", style='TLabel').grid(row=row_idx, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(messages_tab, textvariable=self.match_details_template, style='TEntry').grid(row=row_idx, column=1, padx=5, pady=2, sticky="ew")
        ToolTip(ttk.Label(messages_tab, text="?", style='TLabel'), "Placeholders: {match_type}, {map_display_name}\nDefault: {match_type} on {map_display_name}")
        row_idx += 1

        ttk.Label(messages_tab, text="Loading Match State:", style='TLabel').grid(row=row_idx, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(messages_tab, textvariable=self.loading_match_state_template, style='TEntry').grid(row=row_idx, column=1, padx=5, pady=2, sticky="ew")
        ToolTip(ttk.Label(messages_tab, text="?", style='TLabel'), "Placeholders: None\nDefault: Loading into a match..")
        row_idx += 1

        ttk.Label(messages_tab, text="Loading Match Details:", style='TLabel').grid(row=row_idx, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(messages_tab, textvariable=self.loading_match_details_template, style='TEntry').grid(row=row_idx, column=1, padx=5, pady=2, sticky="ew")
        ToolTip(ttk.Label(messages_tab, text="?", style='TLabel'), "Placeholders: {map_display_name}\nDefault: Loading into a match on {map_display_name}..")
        row_idx += 1

        ttk.Label(messages_tab, text="Test Drive State:", style='TLabel').grid(row=row_idx, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(messages_tab, textvariable=self.test_drive_state_template, style='TEntry').grid(row=row_idx, column=1, padx=5, pady=2, sticky="ew")
        ToolTip(ttk.Label(messages_tab, text="?", style='TLabel'), "Placeholders: {vehicle_type_action}, {vehicle_display_name}\nDefault: {vehicle_type_action} a {vehicle_display_name} (Test Drive)")
        row_idx += 1

        ttk.Label(messages_tab, text="Test Drive Details:", style='TLabel').grid(row=row_idx, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(messages_tab, textvariable=self.test_drive_details_template, style='TEntry').grid(row=row_idx, column=1, padx=5, pady=2, sticky="ew")
        ToolTip(ttk.Label(messages_tab, text="?", style='TLabel'), "Placeholders: None\nDefault: In Test Drive on Western Europe")
        row_idx += 1

        ttk.Label(messages_tab, text="Vehicle BR Text:", style='TLabel').grid(row=row_idx, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(messages_tab, textvariable=self.vehicle_br_text_template, style='TEntry').grid(row=row_idx, column=1, padx=5, pady=2, sticky="ew")
        ToolTip(ttk.Label(messages_tab, text="?", style='TLabel'), "Placeholders: {br_value}\nDefault: BR: {br_value}")
        row_idx += 1

        ttk.Label(messages_tab, text="Vehicle Country Text:", style='TLabel').grid(row=row_idx, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(messages_tab, textvariable=self.vehicle_country_text_template, style='TEntry').grid(row=row_idx, column=1, padx=5, pady=2, sticky="ew")
        ToolTip(ttk.Label(messages_tab, text="?", style='TLabel'), "Placeholders: {country_display_name}\nDefault: ({country_display_name})")
        row_idx += 1

        # Save Message Templates Button
        save_messages_button = ttk.Button(messages_tab, text="Save Message Templates", command=self._save_config, style='Save.TButton')
        save_messages_button.grid(row=row_idx, column=0, columnspan=2, padx=5, pady=10, sticky="ew")
        ToolTip(save_messages_button, "Save your custom message templates to config.json.")
        row_idx += 1

        # Reset to Default Button (NEW)
        reset_messages_button = ttk.Button(messages_tab, text="Reset to Default", command=self._reset_message_templates_to_default, style='Save.TButton')
        reset_messages_button.grid(row=row_idx, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        ToolTip(reset_messages_button, "Reset all message templates to their original default values.")
        row_idx += 1


        # Close Button for Settings Window (moved to the bottom of the notebook frame for consistency)
        close_button = ttk.Button(settings_window, text="Close Settings", command=settings_window.destroy, style='Save.TButton')
        close_button.pack(padx=10, pady=10, fill="x")

        settings_window.wait_window(settings_window) # Wait for the window to close

    def _load_maps_module(self):
        """
        Loads the maps module dynamically to access its 'maps' dictionary.
        """
        if not os.path.exists(self.maps_file_path):
            messagebox.showerror("File Not Found", f"Error: '{self.maps_file_path}' not found. Please ensure maps.py is in the correct directory.")
            return None

        spec = importlib.util.spec_from_file_location("maps", self.maps_file_path)
        if spec is None:
            messagebox.showerror("Module Error", f"Error: Could not load module spec for '{self.maps_file_path}'.")
            return None

        maps_module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(maps_module)
        except Exception as e:
            messagebox.showerror("Module Error", f"Error loading maps.py: {e}\nPlease ensure maps.py is a valid Python file containing a 'maps' dictionary.")
            return None

        if not hasattr(maps_module, 'maps') or not isinstance(maps_module.maps, dict):
            messagebox.showerror("Module Content Error", f"Error: 'maps' dictionary not found or is not a dictionary in '{self.maps_file_path}'.")
            return None
        
        return maps_module.maps

    def _save_maps_module(self, updated_maps: dict):
        """
        Saves the updated 'maps' dictionary back to maps.py.
        """
        try:
            with open(self.maps_file_path, 'w', encoding='utf-8') as f:
                f.write("# maps.py\n\n")
                f.write("# This dictionary contains metadata for various War Thunder maps.\n")
                f.write("# Each map entry includes:\n")
                f.write("# - 'ULHC_lat': Upper-Left Hand Corner Latitude (decimal degrees)\n")
                f.write("# - 'ULHC_lon': Upper-Left Hand Corner Longitude (decimal degrees)\n")
                f.write("# - 'size_km': Approximate size of the map (square, in kilometers)\n")
                f.write("# - 'hashes': A list of perceptual hashes (ImageHash objects converted to hex strings)\n")
                f.write("#             for different variations of the map image (e.g., different lighting, time of day).\n")
                f.write("#             These hashes are used to identify the map from the in-game map.img.\n\n")
                f.write("maps = {\n")
                for map_name, map_data in updated_maps.items():
                    hashes_str = ", ".join([f'"{h}"' for h in map_data.get("hashes", [])])
                    f.write(f'    "{map_name}": {{\n')
                    f.write(f'        "ULHC_lat": {map_data.get("ULHC_lat", 0.0)},\n')
                    f.write(f'        "ULHC_lon": {map_data.get("ULHC_lon", 0.0)},\n')
                    f.write(f'        "size_km": {map_data.get("size_km", 65)},\n')
                    f.write(f'        "hashes": [{hashes_str}]\n')
                    f.write(f'    }},\n')
                f.write("}\n")
            messagebox.showinfo("Success", f"Successfully updated '{os.path.basename(self.maps_file_path)}'.\nRemember to rebuild your .exe if running a bundled version.")
            self._update_status(f"Updated {os.path.basename(self.maps_file_path)}.", color_key='ready')
            return True
        except Exception as e:
            messagebox.showerror("Save Error", f"Error saving '{os.path.basename(self.maps_file_path)}': {e}")
            self._update_status(f"Error saving {os.path.basename(self.maps_file_path)}.", color_key='error')
            return False

    def _is_valid_hash(self, hash_string: str) -> bool:
        """
        Checks if a string is a valid hexadecimal hash (16 characters).
        """
        return bool(re.fullmatch(r'[0-9a-fA-F]{16}', hash_string))

    def _open_map_updater_window(self):
        """
        Opens a new Toplevel window for updating map data.
        """
        updater_window = tk.Toplevel(self.master)
        updater_window.title("Update Map Data")
        updater_window.geometry("450x350")
        updater_window.transient(self.master) # Make it appear on top of the main window
        updater_window.grab_set() # Make it modal
        updater_window.resizable(False, False)
        updater_window.config(bg=self.bg_color)

        frame = ttk.Frame(updater_window, style='MapUpdater.TFrame')
        frame.pack(padx=20, pady=20, fill="both", expand=True)

        ttk.Label(frame, text="Add/Update Map Hash", style='MapUpdaterTitle.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 15))

        # Input fields
        labels = ["Map Hash (16-char hex):", "Map Name (e.g., 'Sinai'):", "ULHC Latitude:", "ULHC Longitude:", "Map Size (km):"]
        entries = {}
        for i, text in enumerate(labels):
            ttk.Label(frame, text=text, style='MapUpdater.TLabel').grid(row=i+1, column=0, padx=5, pady=5, sticky="w")
            entry = ttk.Entry(frame, style='MapUpdater.TEntry')
            entry.grid(row=i+1, column=1, padx=5, pady=5, sticky="ew")
            entries[text.split('(')[0].strip().replace(':', '').replace(' ', '_').lower()] = entry
        
        frame.grid_columnconfigure(1, weight=1) # Make entry column expand

        def submit_map_data():
            current_maps = self._load_maps_module()
            if current_maps is None:
                return # Error already shown by _load_maps_module

            unknown_hash = entries['map_hash'].get().strip()
            map_name_input = entries['map_name'].get().strip()
            
            if not self._is_valid_hash(unknown_hash):
                messagebox.showwarning("Invalid Input", "Please enter a valid 16-character hexadecimal hash.")
                return
            if not map_name_input:
                messagebox.showwarning("Invalid Input", "Map Name cannot be empty.")
                return

            try:
                ulhc_lat = float(entries['ulhc_latitude'].get()) if entries['ulhc_latitude'].get() else 0.0
                ulhc_lon = float(entries['ulhc_longitude'].get()) if entries['ulhc_longitude'].get() else 0.0
                size_km = float(entries['map_size_(km)'].get()) if entries['map_size_(km)'].get() else 65.0
            except ValueError:
                messagebox.showwarning("Invalid Input", "Latitude, Longitude, and Map Size must be valid numbers.")
                return

            normalized_map_name = map_name_input.lower().replace(' ', '_')

            if normalized_map_name in current_maps:
                existing_hashes = current_maps[normalized_map_name].get("hashes", [])
                if unknown_hash not in existing_hashes:
                    if messagebox.askyesno("Confirm Add Hash", f"Map '{map_name_input}' already exists. Add new hash '{unknown_hash}' to it?"):
                        existing_hashes.append(unknown_hash)
                        current_maps[normalized_map_name]["hashes"] = existing_hashes
                        if self._save_maps_module(current_maps):
                            updater_window.destroy()
                else:
                    messagebox.showinfo("No Change", f"Hash '{unknown_hash}' already exists for map '{map_name_input}'. No changes needed.")
                    updater_window.destroy()
            else:
                if messagebox.askyesno("Confirm New Map", f"Map '{map_name_input}' is new. Add it with hash '{unknown_hash}' and provided coordinates?"):
                    current_maps[normalized_map_name] = {
                        "ULHC_lat": ulhc_lat,
                        "ULHC_lon": ulhc_lon,
                        "size_km": size_km,
                        "hashes": [unknown_hash]
                    }
                    if self._save_maps_module(current_maps):
                        updater_window.destroy()
            
            # Log the action to console output for visibility
            self.console_output.config(state='normal')
            self.console_output.insert(tk.END, f"Map update attempt for '{map_name_input}' with hash '{unknown_hash}'. Check message boxes for result.\n")
            self.console_output.config(state='disabled')


        # Buttons
        button_frame = ttk.Frame(frame, style='MapUpdater.TFrame')
        button_frame.grid(row=len(labels)+1, column=0, columnspan=2, pady=15)
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        submit_button = ttk.Button(button_frame, text="Submit", command=submit_map_data, style='MapUpdater.TButton')
        submit_button.grid(row=0, column=0, padx=5, sticky="e")

        cancel_button = ttk.Button(button_frame, text="Cancel", command=updater_window.destroy, style='MapUpdater.TButton')
        cancel_button.grid(row=0, column=1, padx=5, sticky="w")

        updater_window.wait_window(updater_window) # Wait for the window to close

    def start_rpc(self):
        is_frozen = hasattr(sys, '_MEIPASS') 

        if (self.rpc_process and self.rpc_process.poll() is None) or \
           (self.rpc_thread and self.rpc_thread.is_alive()):
            self.console_output.config(state='normal')
            self.console_output.insert(tk.END, "RPC script is already running.\n")
            self.console_output.config(state='disabled')
            self._update_status("RPC already running.", color_key='running')
            return

        client_id = self.client_id_entry.get().strip()
        if not client_id:
            messagebox.showwarning("Missing Client ID", "Please enter your Discord Client ID before starting RPC.")
            self._update_status("Missing Client ID.", color_key='warning')
            return

        self.console_output.config(state='normal')
        self.console_output.delete(1.0, tk.END)
        self.console_output.insert(tk.END, "Starting War Thunder RPC script...\n")
        self.console_output.config(state='disabled')
        self._update_status("Starting RPC script...", color_key='running')
        
        # Determine logging preference from checkbox
        current_log_level = logging.DEBUG if self.detailed_logging_var.get() else logging.INFO

        # Gather all custom message templates to pass to main.py
        custom_message_templates = {
            'hangar_state': self.hangar_state_template.get(),
            'hangar_details': self.hangar_details_template.get(),
            'hangar_details_browsing': self.hangar_details_browsing_template.get(),
            'match_state': self.match_state_template.get(),
            'match_details': self.match_details_template.get(),
            'loading_match_state': self.loading_match_state_template.get(),
            'loading_match_details': self.loading_match_details_template.get(),
            'test_drive_state': self.test_drive_state_template.get(),
            'test_drive_details': self.test_drive_details_template.get(),
            'vehicle_br_text': self.vehicle_br_text_template.get(),
            'vehicle_country_text': self.vehicle_country_text_template.get(),
        }

        try:
            # Import logger_config to ensure it's loaded in this process
            importlib.import_module("logger_config")
            
            rpc_logger = logging.getLogger('WarThunderRPC')
            # Set the level of the GUI's specific handler
            self.tkinter_logger_handler.setLevel(current_log_level) 
            
            if self.tkinter_logger_handler not in rpc_logger.handlers:
                rpc_logger.addHandler(self.tkinter_logger_handler)
                # The overall logger level must be DEBUG to capture all messages from main.py
                rpc_logger.setLevel(logging.DEBUG) 

            if is_frozen:
                if sys._MEIPASS not in sys.path:
                    sys.path.append(sys._MEIPASS)
                
                try:
                    main_module = importlib.import_module("main")
                    rpc_logger.info("main.py module imported successfully.")
                except Exception as e:
                    messagebox.showerror("Main Module Error", f"Failed to import main.py: {e}")
                    self.console_output.config(state='normal')
                    self.console_output.insert(tk.END, f"ERROR: Failed to import main.py: {e}\n")
                    self.console_output.config(state='disabled')
                    self._update_status("Main module import failed.", color_key='error')
                    return

                # Pass custom_message_templates as an argument
                self.rpc_thread = threading.Thread(target=main_module.run_rpc, args=(client_id, custom_message_templates), daemon=True)
                self.rpc_thread.start()
                
                self.start_button.config(state=tk.DISABLED)
                self.stop_button.config(state=tk.NORMAL)
                self.console_output.config(state='normal')
                self.console_output.insert(tk.END, "RPC script started in a new thread.\n")
                self.console_output.config(state='disabled')
                self._update_status("RPC script running.", color_key='running')

            else:
                script_dir = os.path.dirname(__file__)
                main_script_path = os.path.join(script_dir, "main.py")
                
                if not os.path.exists(main_script_path):
                    messagebox.showerror("Error", f"main.py not found at: {main_script_path}\nPlease ensure main.py is in the same directory as gui_launcher.py.")
                    self.console_output.config(state='normal')
                    self.console_output.insert(tk.END, f"Error: main.py not found at {main_script_path}\n")
                    self.console_output.config(state='disabled')
                    self._update_status("main.py not found.", color_key='error')
                    return

                # Pass custom_message_templates as a JSON string via command line
                # This is more complex due to string escaping; for now, we'll simplify.
                # A better approach for subprocess would be to write to a temp file or use a pipe,
                # but for this iteration, we'll assume frozen mode is primary or simplify argument passing.
                # So, the main.py will load config.json directly.
                command_to_execute = [sys.executable, main_script_path, "--client-id", client_id]
                self.console_output.config(state='normal')
                self.console_output.insert(tk.END, f"Attempting to launch command: {' '.join(command_to_execute)}\n")
                self.console_output.config(state='disabled')
                self._update_status("Launching RPC script via subprocess...", color_key='running')

                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'

                self.rpc_process = subprocess.Popen(
                    command_to_execute,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    encoding='utf-8',
                    env=env
                )
                # Start a thread to read stdout/stderr from the subprocess
                threading.Thread(target=self._read_stdout, daemon=True).start()

                self.start_button.config(state=tk.DISABLED)
                self.stop_button.config(state=tk.NORMAL)
                self.console_output.config(state='normal')
                self.console_output.insert(tk.END, "RPC script subprocess started.\n")
                self.console_output.config(state='disabled')
                self._update_status("RPC script running (subprocess).", color_key='running')

        except Exception as e:
            messagebox.showerror("Unhandled Error", f"An unhandled error occurred in start_rpc: {e}")
            self.console_output.config(state='normal')
            self.console_output.insert(tk.END, f"UNHANDLED ERROR in start_rpc: {e}\n")
            self.console_output.config(state='disabled')
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self._update_status("Error starting RPC.", color_key='error')
        
    def _read_stdout(self):
        # This method is for reading output from the subprocess when not frozen
        if self.rpc_process and self.rpc_process.stdout:
            for line in iter(self.rpc_process.stdout.readline, ''):
                with self.queue_lock:
                    self.output_queue.put(line)
            self.rpc_process.stdout.close()
        
        if self.rpc_process and self.rpc_process.poll() is not None:
             with self.queue_lock:
                 self.output_queue.put("\nRPC script process ended.\n")
        
        self.master.after(0, self._check_process_termination)

    def _check_process_termination(self):
        if self.rpc_process and self.rpc_process.poll() is not None:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.rpc_process = None
            self._update_status("RPC script stopped.", color_key='ready')

    def update_console(self):
        with self.queue_lock:
            while not self.output_queue.empty():
                line = self.output_queue.get_nowait()
                self.console_output.config(state='normal')
                self.console_output.insert(tk.END, line)
                self.console_output.see(tk.END)
                self.console_output.config(state='disabled')
        self.master.after(100, self.update_console)

    def stop_rpc(self):
        rpc_logger = logging.getLogger('WarThunderRPC')

        if (self.rpc_process and self.rpc_process.poll() is None) or \
           (self.rpc_thread and self.rpc_thread.is_alive()):
            self.console_output.config(state='normal')
            self.console_output.insert(tk.END, "Stopping War Thunder RPC script...\n")
            self.console_output.config(state='disabled')
            self._update_status("Stopping RPC script...", color_key='warning')
            
            if self.rpc_process and self.rpc_process.poll() is None:
                try:
                    self.rpc_process.terminate()
                    self.rpc_process.wait(timeout=5)
                    if self.rpc_process.poll() is None:
                        self.rpc_process.kill()
                        self.console_output.config(state='normal')
                        self.console_output.insert(tk.END, "RPC script force-killed.\n")
                        self.console_output.config(state='disabled')
                        self._update_status("RPC script force-killed.", color_key='error')
                    else:
                        self.console_output.config(state='normal')
                        self.console_output.insert(tk.END, "RPC script stopped.\n")
                        self.console_output.config(state='disabled')
                        self._update_status("RPC script stopped.", color_key='ready')
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to stop RPC script: {e}")
                    self.console_output.config(state='normal')
                    self.console_output.insert(tk.END, f"Error stopping RPC script: {e}\n")
                    self.console_output.config(state='disabled')
                    self._update_status("Error stopping RPC.", color_key='error')
                finally:
                    self.start_button.config(state=tk.NORMAL)
                    self.stop_button.config(state=tk.DISABLED)
                    self.rpc_process = None
            elif self.rpc_thread and self.rpc_thread.is_alive():
                try:
                    main_module = importlib.import_module("main") 
                    main_module._rpc_running = False
                    rpc_logger.info("Signaled RPC script thread to stop.")
                except Exception as e:
                    rpc_logger.error(f"Failed to signal main.py thread to stop: {e}")
                    rpc_logger.error(traceback.format_exc())
                    messagebox.showerror("Error", f"Failed to signal RPC script to stop: {e}")
                    self._update_status("Error signaling RPC thread.", color_key='error')

                self.rpc_thread.join(timeout=2) 
                if self.rpc_thread.is_alive():
                    rpc_logger.warning("RPC script thread did not terminate gracefully within timeout.")
                    messagebox.showwarning("Warning", "The RPC script thread did not stop gracefully. It will terminate when the main application closes.")
                    self._update_status("RPC thread not stopped gracefully.", color_key='error')
                else:
                    rpc_logger.info("RPC script thread terminated.")
                    self.console_output.config(state='normal')
                    self.console_output.insert(tk.END, "RPC script stopped.\n")
                    self.console_output.config(state='disabled')
                    self._update_status("RPC script stopped.", color_key='ready')

                if self.tkinter_logger_handler in rpc_logger.handlers:
                    rpc_logger.removeHandler(self.tkinter_logger_handler)
                    rpc_logger.info("Removed GUI logger handler.")

                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
                self.rpc_thread = None
        else:
            self.console_output.config(state='normal')
            self.console_output.insert(tk.END, "RPC script is not running.\n")
            self.console_output.config(state='disabled')
            self._update_status("RPC script not running.", color_key='ready')

    def on_closing(self):
        is_rpc_active = (self.rpc_process and self.rpc_process.poll() is None) or \
                        (self.rpc_thread and self.rpc_thread.is_alive())

        if is_rpc_active:
            if messagebox.askokcancel("Quit", "RPC script is running. Do you want to stop it and quit?"):
                self.stop_rpc()
                self.master.after(500, self.master.destroy) 
        else:
            self.master.destroy()

if __name__ == "__main__":
    if hasattr(sys, 'frozen') and sys.frozen:
        pass
    else:
        pass

    root = tk.Tk()
    app = RPCLuncherApp(root)
    root.mainloop()
