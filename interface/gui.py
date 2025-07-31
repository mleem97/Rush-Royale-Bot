#!/usr/bin/env python3
"""
Rush Royale Bot - Modern GUI Interface
Clean, modern interface using CustomTkinter
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    print("CustomTkinter not available, falling back to standard tkinter")

import pandas as pd
from PIL import Image, ImageTk

from core.bot import RushRoyaleBot
from core.config import ConfigManager
from modules.automation import AutomationEngine


class ModernBotGUI:
    """Modern GUI interface for Rush Royale Bot"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Bot components
        self.bot: Optional[RushRoyaleBot] = None
        self.automation: Optional[AutomationEngine] = None
        self.config_manager = ConfigManager()
        
        # GUI state
        self.running = False
        self.automation_running = False
        self.last_screenshot = None
        
        # Initialize GUI
        self._setup_gui()
        self._setup_logging_handler()
        
        self.logger.info("Modern GUI initialized")
    
    def _setup_gui(self):
        """Set up the main GUI"""
        if CTK_AVAILABLE:
            # Use CustomTkinter for modern look
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            self.root = ctk.CTk()
            self._setup_modern_ui()
        else:
            # Fall back to standard tkinter
            self.root = tk.Tk()
            self._setup_standard_ui()
        
        self.root.title("Rush Royale Bot v2.0")
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Status variables
        self.status_var = tk.StringVar(value="Ready")
        self.device_var = tk.StringVar(value="No device")
        self.battle_count_var = tk.StringVar(value="0")
        self.success_rate_var = tk.StringVar(value="0%")
    
    def _setup_modern_ui(self):
        """Set up modern UI using CustomTkinter"""
        # Create main frames
        self.sidebar = ctk.CTkFrame(self.root, width=300)
        self.sidebar.pack(side="left", fill="y", padx=10, pady=10)
        self.sidebar.pack_propagate(False)
        
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(side="right", fill="both", expand=True, padx=(0, 10), pady=10)
        
        # Sidebar content
        self._create_sidebar_content()
        
        # Main content
        self._create_main_content()
    
    def _setup_standard_ui(self):
        """Set up standard UI using tkinter"""
        # Create main frames using ttk for better appearance
        style = ttk.Style()
        style.theme_use('clam')
        
        # Sidebar
        self.sidebar = ttk.Frame(self.root, width=300)
        self.sidebar.pack(side="left", fill="y", padx=5, pady=5)
        self.sidebar.pack_propagate(False)
        
        # Main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        # Create content
        self._create_sidebar_content_standard()
        self._create_main_content_standard()
    
    def _create_sidebar_content(self):
        """Create sidebar content (CustomTkinter version)"""
        # Title
        title = ctk.CTkLabel(self.sidebar, text="Rush Royale Bot", 
                            font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=20)
        
        # Device section
        device_frame = ctk.CTkFrame(self.sidebar)
        device_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(device_frame, text="Device Status", 
                    font=ctk.CTkFont(weight="bold")).pack(pady=5)
        ctk.CTkLabel(device_frame, textvariable=self.device_var).pack()
        
        self.connect_btn = ctk.CTkButton(device_frame, text="Connect Device", 
                                        command=self._connect_device)
        self.connect_btn.pack(pady=5)
        
        # Control buttons
        control_frame = ctk.CTkFrame(self.sidebar)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(control_frame, text="Bot Control", 
                    font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.start_btn = ctk.CTkButton(control_frame, text="Start Bot", 
                                      command=self._start_bot, state="disabled")
        self.start_btn.pack(pady=2, fill="x")
        
        self.stop_btn = ctk.CTkButton(control_frame, text="Stop Bot", 
                                     command=self._stop_bot, state="disabled")
        self.stop_btn.pack(pady=2, fill="x")
        
        self.automation_btn = ctk.CTkButton(control_frame, text="Start Automation", 
                                           command=self._toggle_automation, state="disabled")
        self.automation_btn.pack(pady=2, fill="x")
        
        # Settings section
        settings_frame = ctk.CTkFrame(self.sidebar)
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(settings_frame, text="Quick Settings", 
                    font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        # Chapter selection
        ctk.CTkLabel(settings_frame, text="Chapter:").pack()
        self.chapter_var = tk.StringVar(value="1")
        chapter_menu = ctk.CTkOptionMenu(settings_frame, values=["1", "2", "3", "4", "5"], 
                                        variable=self.chapter_var)
        chapter_menu.pack(pady=2)
        
        # Battle type
        ctk.CTkLabel(settings_frame, text="Battle Type:").pack()
        self.battle_type_var = tk.StringVar(value="PvE")
        battle_menu = ctk.CTkOptionMenu(settings_frame, values=["PvE", "PvP"], 
                                       variable=self.battle_type_var)
        battle_menu.pack(pady=2)
        
        # Max battles
        ctk.CTkLabel(settings_frame, text="Max Battles:").pack()
        self.max_battles_entry = ctk.CTkEntry(settings_frame)
        self.max_battles_entry.insert(0, "50")
        self.max_battles_entry.pack(pady=2)
    
    def _create_sidebar_content_standard(self):
        """Create sidebar content (standard tkinter version)"""
        # Title
        title = ttk.Label(self.sidebar, text="Rush Royale Bot", 
                         font=("Arial", 16, "bold"))
        title.pack(pady=20)
        
        # Device section
        device_frame = ttk.LabelFrame(self.sidebar, text="Device Status")
        device_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(device_frame, textvariable=self.device_var).pack(pady=5)
        
        self.connect_btn = ttk.Button(device_frame, text="Connect Device", 
                                     command=self._connect_device)
        self.connect_btn.pack(pady=5)
        
        # Control buttons
        control_frame = ttk.LabelFrame(self.sidebar, text="Bot Control")
        control_frame.pack(fill="x", padx=10, pady=10)
        
        self.start_btn = ttk.Button(control_frame, text="Start Bot", 
                                   command=self._start_bot, state="disabled")
        self.start_btn.pack(pady=2, fill="x")
        
        self.stop_btn = ttk.Button(control_frame, text="Stop Bot", 
                                  command=self._stop_bot, state="disabled")
        self.stop_btn.pack(pady=2, fill="x")
        
        self.automation_btn = ttk.Button(control_frame, text="Start Automation", 
                                        command=self._toggle_automation, state="disabled")
        self.automation_btn.pack(pady=2, fill="x")
        
        # Settings section
        settings_frame = ttk.LabelFrame(self.sidebar, text="Quick Settings")
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        # Chapter selection
        ttk.Label(settings_frame, text="Chapter:").pack()
        self.chapter_var = tk.StringVar(value="1")
        chapter_menu = ttk.Combobox(settings_frame, values=["1", "2", "3", "4", "5"], 
                                   textvariable=self.chapter_var, state="readonly")
        chapter_menu.pack(pady=2)
        
        # Battle type
        ttk.Label(settings_frame, text="Battle Type:").pack()
        self.battle_type_var = tk.StringVar(value="PvE")
        battle_menu = ttk.Combobox(settings_frame, values=["PvE", "PvP"], 
                                  textvariable=self.battle_type_var, state="readonly")
        battle_menu.pack(pady=2)
        
        # Max battles
        ttk.Label(settings_frame, text="Max Battles:").pack()
        self.max_battles_entry = ttk.Entry(settings_frame)
        self.max_battles_entry.insert(0, "50")
        self.max_battles_entry.pack(pady=2)
    
    def _create_main_content(self):
        """Create main content area (CustomTkinter version)"""
        # Create tabview
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Status tab
        self.status_tab = self.tabview.add("Status")
        self._create_status_tab()
        
        # Screen tab
        self.screen_tab = self.tabview.add("Screen")
        self._create_screen_tab()
        
        # Logs tab
        self.logs_tab = self.tabview.add("Logs")
        self._create_logs_tab()
        
        # Settings tab
        self.settings_tab = self.tabview.add("Settings")
        self._create_settings_tab()
    
    def _create_main_content_standard(self):
        """Create main content area (standard tkinter version)"""
        # Create notebook
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Status tab
        self.status_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.status_tab, text="Status")
        self._create_status_tab_standard()
        
        # Screen tab
        self.screen_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.screen_tab, text="Screen")
        self._create_screen_tab_standard()
        
        # Logs tab
        self.logs_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.logs_tab, text="Logs")
        self._create_logs_tab_standard()
        
        # Settings tab
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="Settings")
        self._create_settings_tab_standard()
    
    def _create_status_tab(self):
        """Create status tab content"""
        # Status indicators
        status_frame = ctk.CTkFrame(self.status_tab)
        status_frame.pack(fill="x", padx=10, pady=5)
        
        # Status grid
        ctk.CTkLabel(status_frame, text="Bot Status:", 
                    font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ctk.CTkLabel(status_frame, textvariable=self.status_var).grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        ctk.CTkLabel(status_frame, text="Battles Completed:", 
                    font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ctk.CTkLabel(status_frame, textvariable=self.battle_count_var).grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        ctk.CTkLabel(status_frame, text="Success Rate:", 
                    font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="w", padx=5, pady=2)
        ctk.CTkLabel(status_frame, textvariable=self.success_rate_var).grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        # Performance metrics
        perf_frame = ctk.CTkFrame(self.status_tab)
        perf_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ctk.CTkLabel(perf_frame, text="Performance Metrics", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
        
        # Performance text area
        self.performance_text = ctk.CTkTextbox(perf_frame)
        self.performance_text.pack(fill="both", expand=True, padx=5, pady=5)
    
    def _create_status_tab_standard(self):
        """Create status tab content (standard version)"""
        # Status indicators
        status_frame = ttk.LabelFrame(self.status_tab, text="Current Status")
        status_frame.pack(fill="x", padx=10, pady=5)
        
        # Status grid
        ttk.Label(status_frame, text="Bot Status:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(status_frame, textvariable=self.status_var).grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(status_frame, text="Battles Completed:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(status_frame, textvariable=self.battle_count_var).grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(status_frame, text="Success Rate:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(status_frame, textvariable=self.success_rate_var).grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        # Performance metrics
        perf_frame = ttk.LabelFrame(self.status_tab, text="Performance Metrics")
        perf_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Performance text area
        self.performance_text = tk.Text(perf_frame, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(perf_frame, orient="vertical", command=self.performance_text.yview)
        self.performance_text.configure(yscrollcommand=scrollbar.set)
        
        self.performance_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _create_screen_tab(self):
        """Create screen tab content"""
        # Screen display
        self.screen_label = ctk.CTkLabel(self.screen_tab, text="No screenshot available")
        self.screen_label.pack(expand=True)
        
        # Screen controls
        controls_frame = ctk.CTkFrame(self.screen_tab)
        controls_frame.pack(fill="x", padx=10, pady=5)
        
        refresh_btn = ctk.CTkButton(controls_frame, text="Refresh Screenshot", 
                                   command=self._refresh_screenshot)
        refresh_btn.pack(side="left", padx=5)
        
        save_btn = ctk.CTkButton(controls_frame, text="Save Screenshot", 
                                command=self._save_screenshot)
        save_btn.pack(side="left", padx=5)
    
    def _create_screen_tab_standard(self):
        """Create screen tab content (standard version)"""
        # Screen display
        self.screen_label = ttk.Label(self.screen_tab, text="No screenshot available")
        self.screen_label.pack(expand=True)
        
        # Screen controls
        controls_frame = ttk.Frame(self.screen_tab)
        controls_frame.pack(fill="x", padx=10, pady=5)
        
        refresh_btn = ttk.Button(controls_frame, text="Refresh Screenshot", 
                                command=self._refresh_screenshot)
        refresh_btn.pack(side="left", padx=5)
        
        save_btn = ttk.Button(controls_frame, text="Save Screenshot", 
                             command=self._save_screenshot)
        save_btn.pack(side="left", padx=5)
    
    def _create_logs_tab(self):
        """Create logs tab content"""
        if CTK_AVAILABLE:
            self.log_text = ctk.CTkTextbox(self.logs_tab)
            self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
        else:
            self.log_text = tk.Text(self.logs_tab, wrap=tk.WORD)
            log_scrollbar = ttk.Scrollbar(self.logs_tab, orient="vertical", command=self.log_text.yview)
            self.log_text.configure(yscrollcommand=log_scrollbar.set)
            
            self.log_text.pack(side="left", fill="both", expand=True)
            log_scrollbar.pack(side="right", fill="y")
        
        # Log controls
        log_controls = ctk.CTkFrame(self.logs_tab) if CTK_AVAILABLE else ttk.Frame(self.logs_tab)
        log_controls.pack(fill="x", padx=10, pady=5)
        
        clear_btn = (ctk.CTkButton(log_controls, text="Clear Logs", command=self._clear_logs) 
                    if CTK_AVAILABLE else ttk.Button(log_controls, text="Clear Logs", command=self._clear_logs))
        clear_btn.pack(side="left", padx=5)
    
    def _create_logs_tab_standard(self):
        """Create logs tab content (standard version)"""
        self.log_text = tk.Text(self.logs_tab, wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(self.logs_tab, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        
        # Log controls
        log_controls = ttk.Frame(self.logs_tab)
        log_controls.pack(fill="x", padx=10, pady=5)
        
        clear_btn = ttk.Button(log_controls, text="Clear Logs", command=self._clear_logs)
        clear_btn.pack(side="left", padx=5)
    
    def _create_settings_tab(self):
        """Create settings tab content"""
        # Advanced settings
        if CTK_AVAILABLE:
            settings_scroll = ctk.CTkScrollableFrame(self.settings_tab)
            settings_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        else:
            settings_scroll = self.settings_tab
        
        # This would contain detailed settings configuration
        placeholder = (ctk.CTkLabel(settings_scroll, text="Advanced settings will be implemented here") 
                      if CTK_AVAILABLE else ttk.Label(settings_scroll, text="Advanced settings will be implemented here"))
        placeholder.pack(pady=20)
    
    def _create_settings_tab_standard(self):
        """Create settings tab content (standard version)"""
        placeholder = ttk.Label(self.settings_tab, text="Advanced settings will be implemented here")
        placeholder.pack(pady=20)
    
    def _setup_logging_handler(self):
        """Set up logging handler to display logs in GUI"""
        class GUILogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
            
            def emit(self, record):
                msg = self.format(record)
                # Schedule GUI update in main thread
                self.text_widget.after(0, lambda: self._append_log(msg))
            
            def _append_log(self, msg):
                try:
                    if CTK_AVAILABLE:
                        self.text_widget.insert("end", msg + "\n")
                        self.text_widget.see("end")
                    else:
                        self.text_widget.insert(tk.END, msg + "\n")
                        self.text_widget.see(tk.END)
                except:
                    pass  # Ignore errors if widget is destroyed
        
        # Add handler to root logger
        handler = GUILogHandler(self.log_text)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(handler)
    
    def _connect_device(self):
        """Connect to Android device"""
        try:
            self.status_var.set("Connecting...")
            
            # Initialize bot if not already done
            if self.bot is None:
                self.bot = RushRoyaleBot()
                self.automation = AutomationEngine(self.bot)
            
            # Connect to device
            success = self.bot.connect_device()
            
            if success:
                device_info = self.bot.get_device_info()
                self.device_var.set(f"Connected: {device_info.get('model', 'Unknown')}")
                self.status_var.set("Device connected")
                
                # Enable control buttons
                self.start_btn.configure(state="normal")
                self.automation_btn.configure(state="normal")
                self.connect_btn.configure(text="Reconnect")
            else:
                self.device_var.set("Connection failed")
                self.status_var.set("Ready")
                messagebox.showerror("Connection Error", "Failed to connect to device")
                
        except Exception as e:
            self.logger.error(f"Device connection error: {e}")
            self.status_var.set("Connection error")
            messagebox.showerror("Error", f"Connection error: {e}")
    
    def _start_bot(self):
        """Start bot operation"""
        try:
            if not self.bot or not self.bot.is_connected():
                messagebox.showerror("Error", "Please connect to device first")
                return
            
            self.running = True
            self.status_var.set("Bot running")
            
            # Update button states
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            
            # Start bot in separate thread
            bot_thread = threading.Thread(target=self._bot_worker, daemon=True)
            bot_thread.start()
            
        except Exception as e:
            self.logger.error(f"Bot start error: {e}")
            messagebox.showerror("Error", f"Failed to start bot: {e}")
    
    def _stop_bot(self):
        """Stop bot operation"""
        try:
            self.running = False
            self.automation_running = False
            
            if self.automation:
                self.automation.stop_automation()
            
            self.status_var.set("Stopping...")
            
            # Update button states
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.automation_btn.configure(text="Start Automation", state="normal")
            
            self.status_var.set("Bot stopped")
            
        except Exception as e:
            self.logger.error(f"Bot stop error: {e}")
    
    def _toggle_automation(self):
        """Toggle automation mode"""
        try:
            if not self.automation:
                messagebox.showerror("Error", "Automation system not initialized")
                return
            
            if not self.automation_running:
                # Start automation
                chapter = int(self.chapter_var.get())
                battle_type = self.battle_type_var.get().lower()
                max_battles = int(self.max_battles_entry.get())
                
                session_config = {
                    'battle_type': battle_type,
                    'chapter': chapter
                }
                
                # Update settings
                self.automation.update_settings({
                    'max_battles_per_session': max_battles
                })
                
                # Start automation in separate thread
                automation_thread = threading.Thread(
                    target=lambda: self.automation.start_automation(
                        tasks=['pve_farming', 'reward_collection', 'energy_management'],
                        session_config=session_config
                    ),
                    daemon=True
                )
                automation_thread.start()
                
                self.automation_running = True
                self.automation_btn.configure(text="Stop Automation")
                self.status_var.set("Automation running")
                
            else:
                # Stop automation
                self.automation.stop_automation()
                self.automation_running = False
                self.automation_btn.configure(text="Start Automation")
                self.status_var.set("Automation stopped")
                
        except Exception as e:
            self.logger.error(f"Automation toggle error: {e}")
            messagebox.showerror("Error", f"Automation error: {e}")
    
    def _bot_worker(self):
        """Bot worker thread"""
        try:
            while self.running:
                # Update status periodically
                self._update_status()
                time.sleep(5.0)
                
        except Exception as e:
            self.logger.error(f"Bot worker error: {e}")
    
    def _update_status(self):
        """Update status displays"""
        try:
            if self.automation and self.automation.running:
                # Get automation status
                status = self.automation.get_automation_status()
                
                # Update battle count
                battles = status.get('battles_completed', 0)
                self.battle_count_var.set(str(battles))
                
                # Update success rate
                failed = status.get('battles_failed', 0)
                if battles + failed > 0:
                    success_rate = (battles / (battles + failed)) * 100
                    self.success_rate_var.set(f"{success_rate:.1f}%")
                
                # Update performance metrics
                perf_report = self.automation.get_performance_report()
                self._update_performance_display(perf_report)
                
        except Exception as e:
            self.logger.debug(f"Status update error: {e}")
    
    def _update_performance_display(self, perf_report: Dict[str, Any]):
        """Update performance metrics display"""
        try:
            # Clear existing content
            if CTK_AVAILABLE:
                self.performance_text.delete("1.0", "end")
            else:
                self.performance_text.delete("1.0", tk.END)
            
            # Format performance report
            report_text = "Performance Report\n" + "=" * 20 + "\n\n"
            
            for key, value in perf_report.items():
                if isinstance(value, float):
                    report_text += f"{key.replace('_', ' ').title()}: {value:.2f}\n"
                else:
                    report_text += f"{key.replace('_', ' ').title()}: {value}\n"
            
            # Insert text
            if CTK_AVAILABLE:
                self.performance_text.insert("1.0", report_text)
            else:
                self.performance_text.insert("1.0", report_text)
                
        except Exception as e:
            self.logger.debug(f"Performance display update error: {e}")
    
    def _refresh_screenshot(self):
        """Refresh device screenshot"""
        try:
            if not self.bot or not self.bot.is_connected():
                messagebox.showwarning("Warning", "Please connect to device first")
                return
            
            # Get screenshot
            screenshot = self.bot.get_screenshot()
            if screenshot is not None:
                self.last_screenshot = screenshot
                self._display_screenshot(screenshot)
            else:
                messagebox.showerror("Error", "Failed to capture screenshot")
                
        except Exception as e:
            self.logger.error(f"Screenshot refresh error: {e}")
            messagebox.showerror("Error", f"Screenshot error: {e}")
    
    def _display_screenshot(self, screenshot):
        """Display screenshot in GUI"""
        try:
            # Convert OpenCV image to PIL
            screenshot_rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(screenshot_rgb)
            
            # Resize to fit display
            display_size = (400, 600)  # Adjust as needed
            pil_image.thumbnail(display_size, Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(pil_image)
            
            # Update label
            self.screen_label.configure(image=photo, text="")
            self.screen_label.image = photo  # Keep a reference
            
        except Exception as e:
            self.logger.error(f"Screenshot display error: {e}")
    
    def _save_screenshot(self):
        """Save current screenshot"""
        try:
            if self.last_screenshot is None:
                messagebox.showwarning("Warning", "No screenshot to save")
                return
            
            # Open file dialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
                title="Save Screenshot"
            )
            
            if filename:
                cv2.imwrite(filename, self.last_screenshot)
                messagebox.showinfo("Success", f"Screenshot saved to {filename}")
                
        except Exception as e:
            self.logger.error(f"Screenshot save error: {e}")
            messagebox.showerror("Error", f"Failed to save screenshot: {e}")
    
    def _clear_logs(self):
        """Clear log display"""
        try:
            if CTK_AVAILABLE:
                self.log_text.delete("1.0", "end")
            else:
                self.log_text.delete("1.0", tk.END)
                
        except Exception as e:
            self.logger.debug(f"Log clear error: {e}")
    
    def _on_closing(self):
        """Handle window closing"""
        try:
            if self.running or self.automation_running:
                if messagebox.askokcancel("Quit", "Bot is running. Do you want to quit?"):
                    self._stop_bot()
                    time.sleep(1.0)  # Give time for cleanup
                    self.root.destroy()
            else:
                self.root.destroy()
                
        except Exception as e:
            self.logger.error(f"Closing error: {e}")
            self.root.destroy()
    
    def run(self):
        """Start the GUI application"""
        try:
            self.logger.info("Starting GUI application")
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"GUI runtime error: {e}")


def main():
    """Main entry point for GUI"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run GUI
    app = ModernBotGUI()
    app.run()


if __name__ == "__main__":
    main()
