"""
Setup script for building PROpitashka Database Admin as a macOS application
"""
from setuptools import setup

APP = ['admin_of_bases.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['psycopg2'],
    'excludes': ['test', 'tests', 'setuptools'],
    'plist': {
        'CFBundleName': 'PROpitashka Admin',
        'CFBundleDisplayName': 'PROpitashka Database Admin',
        'CFBundleGetInfoString': "Администратор базы данных PROpitashka",
        'CFBundleIdentifier': "com.propitashka.admin",
        'CFBundleVersion': "1.0.0",
        'CFBundleShortVersionString': "1.0.0",
        'NSHumanReadableCopyright': "Copyright © 2025, PROpitashka Team"
    }
}

setup(
    name='PROpitashka Admin',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

