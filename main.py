from tkinter import messagebox, PhotoImage, Menu, BooleanVar, Tk, BOTH, filedialog
import os
from typing import Optional
import logging
from utils import get_resource_path, get_user_data_path
from configuration import Configuration
from constants import DEFAULT_APP_SETTINGS
from zone_control import ZoneControlFrame

class IrrigationApp:
    def __init__(self, icon: Optional[str] = "assets/icon", app_name: Optional[str] = "ValveControl 2000", app_author: Optional[str] = "GyB" ):
        self.icon = get_resource_path(icon)
        self.app_name = app_name
        self.app_author = app_author
        app_settings_file = get_user_data_path(self.app_name, self.app_author, 'settings.json')
        log_file = get_user_data_path(self.app_name, self.app_author, 'debug.log')
        self.log_file = log_file

        # Set up logging
        # To file
        logging.basicConfig(
            filename = log_file,
            level = logging.DEBUG,
            format = '%(asctime)s %(levelname)s %(filename)s: %(message)s',
            datefmt ='%H:%M:%S'
        )
        # and console
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(filename)s: %(message)s'))
        logging.getLogger('').addHandler(console)

        self.logger = logging.getLogger(__name__)

        # Create main window
        self.root = Tk()
        self.root.title("ValveControl 2000")
        self.root.minsize(700, 700)
        self.setup_window_icon()

        # Initialize configuration and load app settings
        self.config = Configuration(app_settings_file)
        success, error_message = self.config.load_app_settings()

        # Available languages and their short codes
        self.languages = self.config.languages

        # Set up localization
        self.current_language = self.config.app_settings.language
        self.change_language(self.current_language)

        # Setup the default menu
        self.update_language_vars()
        self.create_menu()

        # Display error message if the app settings can not be loaded
        if not success:
            messagebox.showerror(
                self._("Error"),
                self._("Could not load app settings: {}").format(error_message)
            )

        # Load last used config file
        if self.config.app_settings.last_config_file:
            success, error_message = self.config.load_zone_config(self.config.app_settings.last_config_file)
            if not success:
                messagebox.showerror(
                    self._("Error"),
                    self._("Could not load zone config: {}").format(error_message)
                )

        # Set up window geometry and content
        self.apply_window_geometry()
        self.create_window()

    def setup_window_icon(self):
        """Handle window icon setting for various OSes"""
        try:
            if os.path.exists(f"{self.icon}.ico"):
                self.root.iconbitmap(f"{self.icon}.ico")

            # Fallback for OS like MacOS
            if os.path.exists(f"{self.icon}.png"):
                icon_image = PhotoImage(file=f"{self.icon}.png")
                self.root.iconphoto(True, icon_image)
        except Exception as e:
            self.logger.debug(self._("Warning: Could not set application icon: {}").format(e))

    def apply_window_geometry(self):
        """Apply window geometry from app settings"""
        try:
            self.root.geometry(self.config.app_settings.window_geometry)
        except Exception:
            self.root.geometry(DEFAULT_APP_SETTINGS['window_geometry'])

    def update_language_vars(self):
        """Update language variables to reflect current selection"""
        self.language_vars = {}
        for lang in self.languages:
            self.language_vars[lang] = BooleanVar(value=lang == self.current_language)

    def create_menu(self):
        """Create application menu bar"""
        self.menubar = Menu(self.root)
        self.root.config(menu=self.menubar)

        # File menu
        self.file_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=self._("File"), menu=self.file_menu)
        self.file_menu.add_command(label=self._("Open zone config"), command=self.open_zone_config)
        self.file_menu.add_command(label=self._("Save zone config"), command=self.save_zone_config)
        self.file_menu.add_command(label=self._("Save zone config as..."), command=self.save_zone_config_as)
        self.file_menu.add_separator()
        self.file_menu.add_command(label=self._("Exit"), command=self.on_closing)

        # Language menu
        self.language_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=self._("Language"), menu=self.language_menu)

        for language in self.languages.keys():
            self.language_menu.add_checkbutton(
                label=language,
                command=lambda l=language: self.change_language(l),
                variable=self.language_vars[language]
            )

    def create_main_content(self):
        """Create main application content"""
        self.zone_control = ZoneControlFrame(self.root, self.config, self._, self.ngettext)
        self.zone_control.pack(fill=BOTH, expand=True)

    def create_window(self):
        """Create main window"""
        # Remove existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()

        # (Re)Create content
        self.update_language_vars()
        self.create_menu()
        self.create_main_content()

    def save_zone_config(self):
        """Save current zone config"""
        success, error = self.config.save_zone_config()
        if success:
            messagebox.showinfo(
                self._("Success"),
                self._("Zone config saved successfully")
            )
        else:
            if error == "No file specified":
                self.save_zone_config_as()
            else:
                messagebox.showerror(
                    self._("Error"),
                    self._("Could not save zone config: {}").format(error)
                )

    def save_zone_config_as(self):
        """Save current zone config to a new file"""
        initial_dir = self.config.app_settings.last_config_directory
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=initial_dir,
            title=self._("Save zone config as")
        )

        if filename:
            self.config.update_last_config_directory(filename)
            success, error = self.config.save_zone_config(filename)

            if success:
                messagebox.showinfo(
                    self._("Success"),
                    self._("Zone config saved successfully")
                )
                # Refresh the UI to show the new configuration file path
                self.zone_control.refresh_ui()
            else:
                messagebox.showerror(
                    self._("Error"),
                    self._("Could not save zone config: {}").format(error)
                )

    def open_zone_config(self):
        """Open and load a zone config file"""
        initial_dir = self.config.app_settings.last_config_directory
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=initial_dir,
            title=self._("Open zone config")
        )

        if filename:
            self.config.update_last_config_directory(filename)
            success, error_message = self.config.load_zone_config(filename)

            if success:
                messagebox.showinfo(
                    self._("Success"),
                    self._("Zone config loaded successfully")
                )
                self.zone_control.refresh_ui()
            else:
                messagebox.showerror(
                    self._("Error"),
                    self._("Could not load zone config: {}").format(error_message)
                )

    def change_language(self, new_language):
        """Change application language"""
        self._, self.ngettext = self.config.change_language(new_language)
        self.current_language = new_language
        self.create_window()
        self.config.save_app_settings()

    def on_closing(self):
        """Handle window closing event"""
        if self.config.has_unsaved_changes():
            answer = messagebox.askyesnocancel(
                self._("Unsaved Changes"),
                self._("There are unsaved changes to the zone configuration. Would you like to save them?")
            )

            if answer is None:  # Cancel
                return
            elif answer:  # Yes
                if self.config.current_zone_config_file:
                    success, error = self.config.save_zone_config()
                    if not success:
                        messagebox.showerror(
                            self._("Error"),
                            self._("Could not save zone config: {}").format(error)
                        )
                        return
                else:
                    self.save_zone_config_as()
                    if self.config.has_unsaved_changes():  # User cancelled save dialog
                        return

        # Update window geometry in settings before saving
        self.config.app_settings.window_geometry = self.root.geometry()
        self.config.save_app_settings()
        self.root.quit()

    def loop(self):
        """Start the application main loop"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

if __name__ == "__main__":
    app = IrrigationApp()
    app.loop()