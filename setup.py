"""
Setup script for building the ValveControl 2000 application.
"""
from setuptools import setup

APP = ['main.py']
DATA_FILES = [
    'assets',
    'locales'
]
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'assets/icon.icns',
    'plist': {
        'CFBundleName': 'ValveControl 2000',
        'CFBundleDisplayName': 'ValveControl 2000',
        'CFBundleGetInfoString': 'Irrigation System Control',
        'CFBundleIdentifier': 'hu.gyb.ValveControl 2000',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'NSHumanReadableCopyright': 'Copyright © 2024 Balazs Gyarmati'
    },
    'packages': ['tkinter'],
    'resources': ['assets', 'locales'],
    'includes': ['constants', 'configuration', 'utils', 'zone_control']
}

setup(
    app=APP,
    name='ValveControl 2000',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)