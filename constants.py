from typing import Dict, Any

DEFAULT_ZONE_CONFIG: Dict[str, Any] = {
    'zones': [
        {
            'name': 'Water pump',
            'enabled': True,
            'master_zone': -1,
            'is_master': True
        },
        {
            'name': 'Lawn',
            'enabled': True,
            'master_zone': 0,
            'is_master': False
        }
    ],
    'general': {
        'open_master_automatically': True,
        'close_master_automatically': True,
        'close_dependent_automatically': True
    },
    'mqtt': {
        'enabled': False,
        'broker': 'localhost',
        'port': 1883,
        'username': '',
        'password': '',
        'client_id': 'valvecontrol2000',
        'topic_prefix': 'irrigation',
        'use_tls': False,
        'ca_cert_path': '',
        'status_update_interval': 30
    }
}

DEFAULT_APP_SETTINGS: Dict = {
    'language': 'English',
    'window_geometry': '500x400+100+100',
    'last_config_directory': None,  # Will be set to home directory in code
    'last_config_file': 'irrigation_zone_config.json'
}

SUPPORTED_LANGUAGES = {
    'English': 'en',
    'Magyar': 'hu'
}