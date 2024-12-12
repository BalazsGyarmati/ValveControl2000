import json
import os
from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass, asdict
import hashlib
import re
from constants import SUPPORTED_LANGUAGES, DEFAULT_ZONE_CONFIG, DEFAULT_APP_SETTINGS
from utils import ensure_directory_exists, localization

@dataclass
class AppSettings:
    language: str
    window_geometry: str
    last_config_directory: str
    last_config_file: str

    def validate(self) -> bool:
        return (
            isinstance(self.language, str) and
            isinstance(self.window_geometry, str) and
            re.match(r'^\d+x\d+\+\d+\+\d+$', self.window_geometry) and
            isinstance(self.last_config_directory, str),
            isinstance(self.last_config_file, str)
        )

    def __dict__(self) -> Dict:
        return asdict(self)

    def to_json(self) -> Dict:
        return self.__dict__()

@dataclass
class ZoneConfig:
    zones: List[Dict]
    general: Dict
    mqtt: Dict

    def validate_zone(self, zone) -> bool:
        return (
            isinstance(zone.get('name', None), str) and
            isinstance(zone.get('enabled', None), bool) and
            isinstance(zone.get('master_zone', None), int) and
            isinstance(zone.get('is_master', None), bool) and
            zone.get('master_zone', 0) > -2 and
            zone.get('master_zone', 0) < 8
        )

    def validate(self) -> bool:
        mqtt_valid = (
            isinstance(self.mqtt, dict) and
            isinstance(self.mqtt.get('enabled', False), bool) and
            # Only validate other MQTT fields if enabled is True
            (not self.mqtt.get('enabled', False) or (
                isinstance(self.mqtt.get('broker', ''), str) and
                isinstance(self.mqtt.get('port', 0), int) and
                isinstance(self.mqtt.get('username', ''), str) and
                isinstance(self.mqtt.get('password', ''), str) and
                isinstance(self.mqtt.get('client_id', ''), str) and
                isinstance(self.mqtt.get('topic_prefix', ''), str) and
                isinstance(self.mqtt.get('use_tls', False), bool) and
                isinstance(self.mqtt.get('ca_cert_path', ''), str) and
                isinstance(self.mqtt.get('status_update_interval', 0), int)
            ))
        )

        return (
            isinstance(self.general.get('open_master_automatically', None), bool) and
            all(self.validate_zone(zone) for zone in self.zones) and
            len(self.zones) < 9 and
            mqtt_valid
        )

    def __dict__(self) -> Dict:
        return asdict(self)

    def to_json(self) -> Dict:
        return self.__dict__()

class Configuration:
    def __init__(self, app_settings_file: str):
        self.app_settings_file = app_settings_file
        self.app_settings = AppSettings(**DEFAULT_APP_SETTINGS.copy())
        self.zone_config = ZoneConfig(**DEFAULT_ZONE_CONFIG.copy())
        self.current_zone_config_file: Optional[str] = None
        self.last_saved_hash: Optional[str] = None

        # Available languages and their short codes
        self.languages = SUPPORTED_LANGUAGES

        # Set up localization
        self.current_language = self.app_settings.language
        self._, self.ngettext = localization.setup_locale(self.languages[self.current_language])

    def _calculate_zone_config_hash(self) -> str:
        config_json = json.dumps(self.zone_config.to_json(), sort_keys=True)
        return hashlib.sha256(config_json.encode()).hexdigest()

    def has_unsaved_changes(self) -> bool:
        return self.last_saved_hash != self._calculate_zone_config_hash()

    def load_app_settings(self) -> AppSettings:
        """Load and validate app related settings from JSON file"""
        new_app_settings = DEFAULT_APP_SETTINGS.copy()
        new_app_settings['last_config_directory'] = os.path.expanduser('~')
        new_app_settings['last_config_file'] = None

        self.app_settings = AppSettings(**new_app_settings)

        try:
            if os.path.exists(self.app_settings_file):
                with open(self.app_settings_file, 'r', encoding='utf-8') as f:
                    loaded_app_settings = json.load(f)
                    new_app_settings.update(loaded_app_settings)

            # Validate app settings, before overwriting
            new_app_settings = AppSettings(**new_app_settings)
            if new_app_settings.validate():
                self.app_settings = new_app_settings
                return True, None
            else:
                return False, self._("Invalid app settings format")
        except json.JSONDecodeError:
            return False, self._("Invalid JSON file for app settings")
        except Exception as e:
            return False, self._("Warning: Could not load app settings: {}").format(e)

    def save_app_settings(self) -> Tuple[bool, Optional[str]]:
        """Save current app settings to JSON file"""
        try:
            ensure_directory_exists(self.app_settings_file)

            with open(self.app_settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.app_settings.to_json(), f, indent=4, ensure_ascii=False)
            return True, None
        except Exception as e:
            return False, str(e)

    def change_language(self, new_language):
        """Change application language"""
        if new_language != self.current_language:
            self.current_language = new_language
            self.app_settings.language = new_language
            self._, self.ngettext = localization.setup_locale(self.languages[new_language])
            self.save_app_settings()
        return self._, self.ngettext

    def save_zone_config(self, filename: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        try:
            target_file = filename or self.current_zone_config_file
            if not target_file:
                return False, self._("No file specified")

            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(self.zone_config.to_json(), f, indent=4, ensure_ascii=False)

            self.current_zone_config_file = target_file
            self.app_settings.last_config_file = target_file
            self.last_saved_hash = self._calculate_zone_config_hash()
            self.save_app_settings()
            return True, None
        except Exception as e:
            return False, str(e)

    def load_zone_config(self, filename: str) -> Tuple[bool, Optional[str]]:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                zone_config_json = json.load(f)

            # Validate zone config structure, before overwriting
            new_zone_config = ZoneConfig(**zone_config_json)
            if new_zone_config.validate():
                self.zone_config = new_zone_config
                self.current_zone_config_file = filename
                self.app_settings.last_config_file = filename
                self.last_saved_hash = self._calculate_zone_config_hash()
                self.save_app_settings()
                return True, None
            else:
                return False, self._("Invalid zone config format")
        except json.JSONDecodeError:
            return False, self._("Invalid JSON file for zone config")
        except Exception as e:
            return False, str(e)

    def update_last_config_directory(self, path: str):
        """Update last used config directory in settings"""
        self.app_settings.last_config_directory = os.path.dirname(path)
        self.save_app_settings()