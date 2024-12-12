import os
import sys
from typing import Optional, Tuple, Callable
from appdirs import user_data_dir
import gettext

def get_workdir() -> str:
    """Get the application's workdir path."""
    frozen = getattr(sys, 'frozen', False)

    if not frozen:
        # Not frozen (=not an .exe or .app)
        # using regular python interpreter
       return os.path.dirname(os.path.abspath(__file__))

    elif frozen in ('dll', 'console_exe', 'windows_exe'):
        # Windows app created by py2exe
        return os.path.dirname(sys.executable)

    elif frozen in ('macosx_app',):
        # Mac OS app created by py2app
        return os.getenv('RESOURCEPATH', os.path.join(os.path.dirname(sys.executable), '..', 'Resources'))

def ensure_directory_exists(path: str) -> None:
    """Create a directory if it doesn't exist"""
    os.makedirs(os.path.dirname(path), exist_ok=True)

def get_resource_path(filename: str, subdirectory: Optional[str] = None) -> str:
    """Get full path for a resource file for the application"""
    base_path = get_workdir()

    if subdirectory:
        return os.path.join(base_path, subdirectory, filename)
    return os.path.join(base_path, filename)

def get_user_data_path(app_name: str, app_author: str, filename: str, subdirectory: Optional[str] = None, roaming: Optional[bool] = True) -> str:
    """Get the path for storing the various user related data"""
    base_path = os.path.dirname(os.path.abspath(__file__))

    # If running from a bundle, use system path for user data
    if getattr(sys, 'frozen', False):
        base_path = user_data_dir(app_name, app_author, roaming=roaming)

    if subdirectory:
        base_path = os.path.join(base_path, subdirectory)

    ensure_directory_exists(base_path)
    return os.path.join(base_path, filename)

class LocalizationManager:
    def __init__(self):
        self._current_language: str = 'en'
        self._translation: gettext.NullTranslations = gettext.NullTranslations()

    def setup_locale(self, language: str) -> Tuple[Callable, Callable]:
        """Setup localization for the specified language"""
        self._current_language = language
        locale_dir = get_resource_path('locales')

        try:
            self._translation = gettext.translation(
                'messages',
                locale_dir,
                languages=[language]
            )
            self._translation.install()
        except FileNotFoundError:
            # If the requested language is not found, fall back to English
            self._translation = gettext.NullTranslations()
            gettext.install('messages')

        return self._translation.gettext, self._translation.ngettext

    @property
    def current_language(self) -> str:
        """Get the currently active language"""
        return self._current_language

    def gettext(self, message: str) -> str:
        """Translate a message"""
        return self._translation.gettext(message)

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        """Translate singular/plural message"""
        return self._translation.ngettext(singular, plural, n)

# Global instance
localization = LocalizationManager()