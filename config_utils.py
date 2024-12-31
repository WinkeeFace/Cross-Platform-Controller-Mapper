import json
import logging

CONFIG_PATH = 'config.json'
CURRENT_PROFILE_KEY = 'current_profile'
LAYOUT_PATH = 'layout__ps4.json'
MAPPINGS_PATH = 'mappings.json'

def load_json(file_path) -> dict | bool:
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"Failed to load {file_path}: {e}")
        return False

def save_json(data, file_path):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def save_config(config, config_path) -> bool:
    try:
        with open(config_path, 'w') as file:
            json.dump(config, file, indent=4)
        return True
    except Exception as e:
        logging.error(f"Failed to save config: {e}")
        return False