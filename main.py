import sys
import os

# Add the transcriber directory to the Python path
sys.path.append('/Users/jwink/Documents/GitHub/transcriber')

import json
import logging
import select
import argparse
import pygame as pg
from time import sleep, time
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController
import pyautogui as mouse
from pync import Notifier  # For Mac notifications
import subprocess
import asyncio
from listen import collect_audio_once, initialize_audio_stream, initialize_vad
from send_keys import send_keys, print_text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_PATH = 'config.json'
CURRENT_PROFILE_INDEX = 0
LAYOUT_PATH = 'layout__ps4.json'
MAPPINGS_PATH = 'mappings.json'

#memory

# Initialize controllers
keyboard = KeyboardController()
mouse = MouseController()
controller = None
is_inputs_paused = False

def load_json(file_path) -> dict | bool:
    try:
        with open(file_path, 'r') as file:
            contents = json.load(file)
            print(f"Loaded {file_path}")
            print(contents)
            return contents
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

def save_layout(layout, layout_path):
    save_json(layout, layout_path)

def create_human_friendly_mappings(config, layout, mappings):
    
    current_profile_name = config['current_profile']
    profiles = config['profiles']
    current_profile = next((p for p in profiles if p['name'] == current_profile_name), None)

    if not current_profile:
        print(f"Profile '{current_profile_name}' not found.")
        return

    mappings = current_profile.get('mappings', {})
    buttons_mapping = mappings.get('buttons', {})
    axes_mapping = mappings.get('axes', {})

    human_friendly_mappings = {
        "buttons": {},
        "axes": {}
    }

    for button_index, action in buttons_mapping.items():
        button_name = layout['buttons'].get(button_index, f"Button {button_index}")
        human_friendly_mappings['buttons'][button_name] = action

    for axis_index, action in axes_mapping.items():
        axis_name = layout['axes'].get(axis_index, f"Axis {axis_index}")
        human_friendly_mappings['axes'][axis_name] = action

    save_json(human_friendly_mappings, MAPPINGS_PATH)
    print(f"Human-friendly mappings saved to {MAPPINGS_PATH}")

def swap_to_next_profile():
    """
    Does a profile swap, updates the config, and sends a notification.
    """
    config = load_json(CONFIG_PATH)
    if not config:
        logging.error("Failed to load configuration.")
        return
    
    global CURRENT_PROFILE_INDEX
    print(CURRENT_PROFILE_INDEX)


    profiles = config['profiles']
    print('profiles', profiles)
    current_profile_index = config['current_profile_index']
    print('current_profile_index', current_profile_index)
    current_profile = config['current_profile']
    print('current_profile', current_profile)
    if not current_profile:
        logging.error("No current profile set.")
        return

    try:
        current_index = CURRENT_PROFILE_INDEX
        next_index = (current_index + 1) % len(profiles)
        config['current_profile_index'] = next_index
        config[current_profile] = profiles[next_index]['name']
        CURRENT_PROFILE_INDEX = next_index

        # print('profiles[next_index][name]', profiles[CURRENT_PROFILE_INDEX]['name'])
        # print(f"config[] {config['profiles'][CURRENT_PROFILE_INDEX]}")
        # print(f"CURRENT_PROFILE_KEY", CURRENT_PROFILE_INDEX)
        if save_config(config, CONFIG_PATH):
            Notifier.notify(f"Switched to profile: {profiles[CURRENT_PROFILE_INDEX]['name']}", title="Profile Switch")
            logging.info(f"Switched to profile: {profiles[CURRENT_PROFILE_INDEX]['name']}")
            
            # Get button and axis actions for the new profile
            new_profile = profiles[next_index]
            # button_actions = new_profile.get('mappings', {}).get('buttons', {})
            # axis_actions = new_profile.get('mappings', {}).get('axes', {})
            
            # Apply the new mappings
            # apply_new_mappings(config, button_actions, axis_actions)
        else:
            logging.error("Failed to save profile change.")
    except StopIteration:
        logging.error("Current profile not found.")

def apply_new_mappings(config, button_actions, axis_actions):
    """
    Apply new button and axis mappings.
    """
    logging.info(f'data: {button_actions} {axis_actions})')
    logging.info("New mappings applied.")
    # Update the current profile with the new mappings
    

    def set_profile_mappings(profile, button_actions, axis_actions):
        logging.info(f"Setting profile mappings for profile: {profile['name']}")
        for button_index, action in button_actions.items():
            action_name = action.get('name', f"Button {button_index}")
            action_value = action.get('action', 'No action')
            logging.info(f"Setting button action: {action_name} -> {action_value}")
            set_button_action(profile, button_index, action_value)
        for axis_index, action in axis_actions.items():
            action_name = action.get('name', f"Axis {axis_index}")
            action_value = action.get('action', 'No action')
            logging.info(f"Setting axis action: {action_name} -> {action_value}")
            set_axis_action(profile, axis_index, action_value)

    def set_button_action(profile, button_index, action):
        if 'mappings' not in profile:
            profile['mappings'] = {}
        if 'buttons' not in profile['mappings']:
            profile['mappings']['buttons'] = {}
        profile['mappings']['buttons'][str(button_index)] = {"action": action}
        logging.info(f"Button action set: {button_index} -> {action}")

    def set_axis_action(profile, axis_index, action):
        if 'mappings' not in profile:
            profile['mappings'] = {}
        if 'axes' not in profile['mappings']:
            profile['mappings']['axes'] = {}
        profile['mappings']['axes'][str(axis_index)] = {"action": action}
        logging.info(f"Axis action set: {axis_index} -> {action}")

    set_profile_mappings(config['profiles'][CURRENT_PROFILE_INDEX], button_actions, axis_actions)

def normalize_joystick_value(value, min_val, max_val):
    if min_val == max_val:
        logging.error("Min == Max, cannot normalize.")
        return 0.0
    normalized = 2 * (value - min_val) / (max_val - min_val) - 1
    return restrict_joystic_value(normalized)

def restrict_joystic_value(value):
    """Restricts the joystick value to the range [-1, 1]."""
    return max(-1.0, min(1.0, value))

def normalize_trigger_value_to_1(value, min_val, max_val):
    """
    Normalize the trigger value to a range of [0, 1].
    """
    if min_val == max_val:
        logging.error("Min == Max, cannot normalize.")
        return 0.0
    normalized = (value - min_val) / (max_val - min_val)
    return restrict_trigger_value_to_1(normalized)

def restrict_trigger_value_to_1(value):
    """Restricts the trigger value to the range [0, 1]."""
    return max(0.0, min(1.0, value))

def apply_deadzone(value, deadzone):
    """
    Apply deadzone to the normalized axis value.
    """
    if abs(value) <= deadzone:
        return 0.0
    return value

# def get_current_axis_value(axis, controller, config):
#     """
#     Retrieve the current value of the specified axis from the active controller, 
#     normalize it based on calibration data, and apply a deadzone if configured.

#     Args:
#         axis (int): The index of the axis to retrieve the value for.
#         controller (pygame.joystick.Joystick): The active controller object.
#         config (dict): The configuration dictionary.

#     Returns:
#         float: The normalized and deadzone-adjusted value of the axis, or 0.0 if no active controller is found.

#     Raises:
#         KeyError: If the axis is not found in the configuration file.
#         ValueError: If the calibration data for the axis is invalid.
#     """
#     if controller:
#         pg.event.pump()  # Update the internal state of the joystick
#         raw_value = controller.get_axis(axis)
        
#         print('axis raw value', raw_value)
#         if config:
#             min_val = config['calibration']['axes'][str(axis)]['min']
#             max_val = config['calibration']['axes'][str(axis)]['max']
#             normalized = normalize_axis_value(raw_value, min_val, max_val)
#             deadzone = config['calibration']['deadzone'].get(str(axis), 0.0)
#             return apply_deadzone(normalized, deadzone)
#         else:
#             logging.error("Failed to load config for normalization.")
#             return raw_value
#     else:
#         logging.error("No active controller found. silly goose")
#         return 0.0

def calculate_axis_value(raw_value, axis, config):
    # print(f"Axis {axis} raw value: {raw_value}")
    #if axis is 4 or 5
    if config and str(axis) in config['calibration']['axes']:

        if axis in [4, 5]: #triggers
            min_val = -1.0
            max_val = 1.0
            deadzone = 0.0
            normalized = normalize_trigger_value_to_1(raw_value, min_val, max_val)
            return apply_deadzone(normalized, deadzone)        
        else: #joysticks
            min_val = config['calibration']['axes'][str(axis)]['min']
            max_val = config['calibration']['axes'][str(axis)]['max']
            deadzone = config['calibration']['deadzone'].get(str(axis), 0.1)
            normalized = normalize_joystick_value(raw_value, min_val, max_val)
            return apply_deadzone(normalized, deadzone)
    else:
        logging.error("Failed to find axis for normalization in config.")
        return raw_value

def calibrate_axes(config, controller):
    """
    Calibrates the axes based on user input and updates the configuration file.

    This function guides the user through the process of calibrating the axes of a controller.
    It prompts the user to move each axis to its minimum and maximum positions and records these values.
    Additionally, it allows the user to set a deadzone for each axis, with default values provided.

    The calibration data and deadzone values are then saved to the configuration file.

    Returns:
        None
    """
    if not config:
        print("Failed to load configuration.")
        return
    
    if not controller:
        print("No controller initialized.")
        return

    print("Starting calibration...")
    calibration_data = {}
    deadzone_data = {}

    for axis in config['calibration']['axes']:
        print(f"Calibrating axis {axis}. Move to minimum position and press Enter.")
        input()
        min_val = calculate_axis_value(int(axis), controller, config)
        print(f"Minimum value for axis {axis}: {min_val}")

        print(f"Move axis {axis} to maximum position and press Enter.")
        input()
        max_val = calculate_axis_value(int(axis), controller, config)
        print(f"Maximum value for axis {axis}: {max_val}")

        calibration_data[axis] = {"min": min_val, "max": max_val}
        deadzone = set_deadzone(axis)
        deadzone_data[axis] = deadzone

    config['calibration']['axes'] = calibration_data
    config['calibration']['deadzone'] = deadzone_data

    if save_config(config, CONFIG_PATH):
        print("Calibration successful and saved to config.json.")
    else:
        print("Failed to save calibration data.")

def calibrate_axis_no_ref(axis):
    """
    Calibrates a single axis by prompting the user to move it to its minimum and maximum positions.

    Args:
        axis (str): The axis identifier to calibrate.

    Returns:
        tuple: A tuple containing the minimum and maximum values for the axis.
    """
    print(f"Calibrating axis {axis}. Move to minimum position and press Enter.")
    input()
    min_val = calculate_axis_value(int(axis))
    print(f"Minimum value for axis {axis}: {min_val}")

    print(f"Move axis {axis} to maximum position and press Enter.")
    input()
    max_val = calculate_axis_value(int(axis))
    print(f"Maximum value for axis {axis}: {max_val}")

    return min_val, max_val

def set_deadzone(axis):
    """
    Sets the deadzone for a given axis, with a default value provided.

    Args:
        axis (str): The axis identifier to set the deadzone for.

    Returns:
        float: The deadzone value for the axis.
    """
    default_deadzone = 0.05 if axis in ['4', '5'] else 0.1
    deadzone = input(f"Enter deadzone for axis {axis} (default {default_deadzone}): ").strip()
    return float(deadzone) if deadzone else default_deadzone

def initialize_pygame():
    """
    Initializes the Pygame library and detects connected controllers.

    This function initializes the Pygame library and its joystick module. It then checks for connected 
    controllers and initializes each detected controller. If no controllers are detected, a warning 
    message is logged.

    Returns:
        bool | pg.joystick.Joystick | list[pg.joystick.Joystick]: False if no controllers are detected, 
        a single controller if one controller is detected, or a list of controllers if multiple controllers are detected.
    """
    pg.init()
    pg.joystick.init()
    controller_count = pg.joystick.get_count()
    if controller_count == 0:
        logging.warning("No controllers detected. Please connect a controller.")
        return False
    if controller_count == 1:
        controller = pg.joystick.Joystick(0)
        controller = initialize_controller(controller)
        logging.info(f"Initialized controller in init_pygame: {controller.get_name()}")
        return controller
    else:
        logging.info(f"{controller_count} controller(s) detected.")
        controllers = []
        for i in range(controller_count):
            controller += pg.joystick.Joystick(i)
            initialize_controller(controller)
            controllers += controller
        return controllers

def initialize_controller(controller):
    """
    Initialize the given controller and set it as the active controller.

    This function sets the provided controller as the active controller,
    initializes it, and logs the initialization with the controller's name.

    Args:
        controller: An instance of a controller object that has `init` and `get_name` methods.

    Returns:
        None
    """
    controller.init()
    logging.info(f"Initialize_controller: {controller.get_name()}")
    return controller

def handle_controller_events(data, config):
    """
    Handle and process controller events based on the provided data.

    This function processes various types of controller events such as 
    axis motion, button presses, and connection events. It updates the 
    state of connected controllers, pressed buttons, released buttons, 
    and axis values accordingly.

    Args:
        data (dict): A dictionary containing the following keys:
            - events (list): List of controller events to process.
            - accepted_events (list): List of event types that are accepted.
            - pressed_buttons (list): List of currently pressed buttons.
            - released_buttons (list): List of buttons that were released.
            - axis_values (dict): Dictionary of current axis values.
            - connected_controllers (list): List of connected controller indices.
            - held_buttons (list): List of buttons that are being held down.

    Returns:
        None
    """
    events = data['events']
    accepted_events = data['accepted_events']
    pressed_buttons = data['pressed_buttons']
    released_buttons = data['released_buttons']
    axis_values = data['axis_values']
    connected_controllers = data['connected_controllers']
    held_buttons = data['held_buttons']

    if not config:
        logging.error("Failed to load config.")
        return

    for event in events:
        if event.type not in accepted_events:
            if event.type == pg.JOYDEVICEADDED:
                logging.info(f"Controller {event.guid} connected.")
                connected_controllers.append(f"{len(connected_controllers)}: {event.guid}")
            elif event.type == pg.JOYDEVICEREMOVED:
                #check to see what controller no longer exists in pg.joysticks
                controller_count = pg.joystick.get_count()
                # for i in range(controller_count):
                #     print('pg.joystick.Joystick(i)', pg.joystick.Joystick(i))
                #     temp_controller_list.append(pg.joystick.Joystick(i).get_guid())
                if len(connected_controllers) != controller_count and controller_count > 0:
                    logging.info("A controller disconnected.")
                    #we could then listen for inputs in listener and be able to tell what controllers are still transmitting inputs
                elif controller_count == 0:
                    logging.info("All controllers disconnected.")
                    connected_controllers.clear()
            else:
                logging.info(f"Unknown event type: {event.type}")
        else:
            #there are so many joy events lol
            if event.type == pg.JOYAXISMOTION:
                axis = event.axis
                evalue = event.value
                value = calculate_axis_value(evalue, axis, config)
                # print('event: axis & value & evalue', axis, value, evalue)
                if axis not in [4,5]:                   
                    logging.debug("i disabled joysticks, see line 378. there was agross error going on")
                    continue
                # print('axis in axis_values', axis in axis_values)
                min_val = config['calibration']['axes'][str(axis)]['min']                
                max_val = config['calibration']['axes'][str(axis)]['max']
                # print('min & max', min_val, max_val)
                if value > min_val:
                    axis_values[axis] = value
                if value == min_val:
                    print('value is at min value')
                    if axis in axis_values:
                        print('axis in axis_values')
                        del axis_values[axis]
                else:
                    #update value
                    # print('before', axis_values)
                    axis_values[axis] = value
            elif event.type == pg.JOYBUTTONDOWN:
                if event.button not in pressed_buttons and event.button not in held_buttons:
                    pressed_buttons.append(event.button)
            elif event.type == pg.JOYBUTTONUP:
                if event.button in held_buttons:
                    released_buttons.append(event.button)
                    held_buttons.remove(event.button)
            elif event.type == pg.JOYHATMOTION:
                # Handle hat motion if needed
                pass

from collections import deque

# Smoothing parameters
SMOOTHING_WINDOW_SIZE = 5
mouse_movements = deque(maxlen=SMOOTHING_WINDOW_SIZE)

def smooth_mouse_move(dx, dy):
    mouse_movements.append((dx, dy))
    avg_dx = sum(m[0] for m in mouse_movements) / len(mouse_movements)
    avg_dy = sum(m[1] for m in mouse_movements) / len(mouse_movements)
    mouse.move(avg_dx, avg_dy)

def execute_script_in_venv(script_name, *args):
    print(f"Executing script: {script_name} with args: {args}")
    tscribe_path = os.getenv("tscribe")
    print(f"tscribe_path: {tscribe_path}")
    if not tscribe_path:
        print("TSCRIBE environment variable is not set.")
        return {"status": "error", "message": "TSCRIBE environment variable is not set."}
    
    cd_command = f"cd {tscribe_path}"
    venv_activate = f"source {os.path.join('venv', 'bin', 'activate')}"
    script_path = os.path.join(tscribe_path, script_name)
    print(f"script_path: {script_path}")
    
    try:
        # Combine commands into one shell run
        args_str = " ".join(args)
        full_command = f"{cd_command} && {venv_activate} && chmod +x {script_path} && python3.12 {script_path} {args_str}"
        print(f"Executing command: {full_command}")
        result = subprocess.run(full_command, shell=True, capture_output=True, text=True, check=True)
        
        print(f"Command output: {result.stdout.strip()}")
        print(f"Command error: {result.stderr.strip()}")
        return {
            "status": "success",
            "output": result.stdout.strip(),
            "error": result.stderr.strip()
        }
    except subprocess.CalledProcessError as e:
        print(f"Script execution failed: {e}")
        print(f"Error output: {e.stderr.strip()}")
        return {
            "status": "error",
            "message": f"Script execution failed: {e}",
            "output": e.stdout.strip(),
            "error": e.stderr.strip()
        }

async def listen_once_locally():
    p, stream = initialize_audio_stream()
    vad = initialize_vad()

    print("Recording audio once...")
    audio_bytes = await collect_audio_once(stream, vad, silence_threshold=15)
    # Replace remote call with local processing below:
    transcription = local_transcribe(audio_bytes)  # implement locally
    send_keys(transcription)  # or send_keys(transcription)
    p.terminate()

def local_transcribe(audio_bytes):
    # Insert or copy logic from client.py's send_audio_to_api() but do local processing
    # e.g. call a local library or script to transcribe
    return "transcribed text"

def execute_action(action, value, config):
    """
    Executes a specified action based on the provided action name and value.

    Parameters:
    action (str): The name of the action to execute. This can be a mouse action, 
                  keyboard action, or a custom action defined in the action_map.
    value (any): The value associated with the action. This can be a boolean, 
                 float, or any other type depending on the action.
    config (dict): The configuration dictionary containing settings and mappings.

    Returns:
    None
    """
    """
    Executes a specified action based on the provided action name and value.
    Parameters:
    action (str): The name of the action to execute. This can be a mouse action, 
                  keyboard action, or a custom action defined in the action_map.
    value (any): The value associated with the action. This can be a boolean, 
                 float, or any other type depending on the action.
    Supported Actions:
    - "MouseScrollUp": Scrolls the mouse up.
    - "MouseScrollDown": Scrolls the mouse down.
    - "MouseScrollLeft": Scrolls the mouse left.
    - "MouseScrollRight": Scrolls the mouse right.
    - "MouseMove": Moves the mouse to a specified position.
    - "SwapProfile": Swaps to the next profile.
    - "ArrowKeysHorizontal": Handles horizontal arrow key presses based on the value.
    - "ArrowKeysVertical": Handles vertical arrow key presses based on the value.
    - "TestLog": Logs the provided value for testing purposes.
    - "Key.<key_name>": Presses or releases a specified keyboard key.
    - "Button.<button_name>": Presses or releases a specified mouse button.
    If the action is not recognized, a warning is logged.
    Returns:
    None
    """

    speed = config.get('calibration', {}).get('mouse_speed', 1.0)  # Get speed from config
    speed = 30
    action_map = {
        "MouseMoveVertical": lambda v: smooth_mouse_move(0, v * speed) if v else None,
        "MouseMoveHorizontal": lambda v: smooth_mouse_move(v * speed, 0) if v else None,
        "MouseScrollUp": lambda v: mouse.scroll(1) if v else None,
        "MouseScrollDown": lambda v: mouse.scroll(-1) if v else None,
        "MouseScrollLeft": lambda v: mouse.hscroll(-1) if v else None,
        "MouseScrollRight": lambda v: mouse.hscroll(1) if v else None,
        "MouseMove": lambda v: smooth_mouse_move(v[0] * speed, v[1] * speed) if v and isinstance(v, (list, tuple)) and len(v) == 2 else None,
        "SwapProfile": lambda v: swap_to_next_profile() if v else None,
        "ArrowKeysHorizontal": lambda v: handle_arrow_keys_horizontal(v),
        "ArrowKeysVertical": lambda v: handle_arrow_keys_vertical(v),
        "TestLog": lambda v: test_log(v),
        "PauseInputs": lambda v: toggle_pause_inputs() if v else None,
        "ExecuteScript": lambda v: execute_script_in_venv("client.py", "--once", "--st", "80") if v else None,
        "ListenOnceLocally": lambda v: listen_once_locally() if v else None,
        "": lambda v: None
    }
        # "Macro": lambda v: execute_macro(v) if v else None,
    print('value', value)
    print('action', action)
    def test_log(v):
        print(f"Test Log: value={v}")

    def parse_and_execute_combination(action):
        """
        Parse a combination action string and execute the corresponding key presses/releases.
        The combination action string should contain key names separated by '+'.
        Example: "Key.ctrl+Key.alt+Key.delete"
        """
        
        keys = action.split('+')
        for key in keys:
            key = key.strip()
            if key.startswith("Key."):
                key_name = key.split(".")[1]
                keyboard.press(getattr(Key, key_name))
            elif key.startswith("Button."):
                button_name = key.split(".")[1]
                mouse.press(getattr(Button, button_name))
            elif len(key) == 1:
                keyboard.press(key.lower())
            else:
                try:
                    keyboard.press(getattr(Key, key))
                except AttributeError:
                    logging.warning(f"Unknown key/button in combination: {key}")

        # Release keys/buttons after pressing them
        for key in reversed(keys):
            key = key.strip()
            if key.startswith("Key."):
                key_name = key.split(".")[1]
                keyboard.release(getattr(Key, key_name))
            elif key.startswith("Button."):
                button_name = key.split(".")[1]
                mouse.release(getattr(Button, button_name))
            elif len(key) == 1:
                keyboard.release(key.lower())
            else:
                try:
                    keyboard.release(getattr(Key, key))
                except AttributeError:
                    logging.warning(f"Unknown key/button in combination: {key}")


        def handle_arrow_keys_horizontal(v):
            if v > 0.5:
                keyboard.press(Key.right)
                keyboard.release(Key.left)
            elif v < -0.5:
                keyboard.press(Key.left)
                keyboard.release(Key.right)
            else:
                keyboard.release(Key.left)
                keyboard.release(Key.right)

        def handle_arrow_keys_vertical(v):
            if v > 0.5:
                keyboard.press(Key.down)
                keyboard.release(Key.up)
            elif v < -0.5:
                keyboard.press(Key.up)
                keyboard.release(Key.down)
            else:
                keyboard.release(Key.up)
                keyboard.release(Key.down)

        def handle_special_key(pynput_key, v):
            if v:
                keyboard.press(pynput_key)
            else:
                keyboard.release(pynput_key)

        # Check if the action is a Key or Button
        if action.startswith("Key."):
            key = getattr(Key, action.split(".")[1])
            handle_special_key(key, value)
        elif action.startswith("Button."):
            button = getattr(Button, action.split(".")[1])
            if value:
                mouse.press(button)
                print('mouse press')
            else:
                mouse.release(button)
                print('mouse release')
        else:
            if '+' in action:
                try:
                    parse_and_execute_combination(action)
                except Exception as e:
                    logging.error(f"Error executing combination action '{action}': {e}")
                return
            else:
                func = action_map.get(action)
            # print('func', func)
                if func:
                    # print('func', func, value)
                    func(value)
                else:
                    logging.warning(f"No action mapped for '{action}'.")

def toggle_pause_inputs():
    """
    Toggles the state of input processing (pause/resume).
    """
    global is_inputs_paused
    is_inputs_paused = not is_inputs_paused
    state = "paused" if is_inputs_paused else "resumed"
    Notifier.notify(f"Inputs {state}.", title="Input State Change")
    logging.info(f"Inputs {state}.")

def get_button_action(profile, button_index):
    return profile['mappings']['buttons'].get(str(button_index), {}).get("action")

def get_axis_action(profile, axis_index):
    return profile['mappings']['axes'].get(str(axis_index), {}).get("action")

def execute_profile_actions(data, config, controller):
    """
    Executes actions based on the current profile and input data.
    This function processes input data to execute corresponding actions defined in the current profile.
    It handles button presses, button holds, button releases, and axis movements. The function also
    includes placeholders for handling combo actions.
        logging.debug(f'func: {func}')
        logging.debug(f'value: {value}')
        logging.debug(f'action: {action}')
            - 'pressed_buttons' (set): A set of buttons that were pressed.
            - 'released_buttons' (set): A set of buttons that were released.
            - 'axis_values' (dict): A dictionary mapping axis identifiers to their current values.
    Returns:
        None
    """
    # TODO: Add logic to handle combo actions. Ensure that individual button presses do not trigger other events
    # if they are part of a combo. Implement a delay to check for combos before executing single button actions.
    if not config:
        logging.error("Failed to load configuration.")
        return
    global CURRENT_PROFILE_INDEX
    profile = config['profiles'][CURRENT_PROFILE_INDEX]
    if not profile:
        logging.error("No current profile set.")
        return

    if not controller:
        return
    
    # Example of reading each axis value
    # axes_config = config['calibration']['axes']
    # axis_values = {}
    # for axis_key in axes_config.keys():
    #     val = get_current_axis_value(int(axis_key), controller, config)
    #     axis_values[axis_key] = val
    #     # Do something with val, e.g. call execute_action if tagged in config:
    #     mapped_action = config['profiles'][0]['mappings']['axes'].get(axis_key)
    #     if mapped_action:
    #         execute_action(mapped_action, val)

    # Execute button actions TODO: i need some logic to make sure when i go to combo it doesn't trigger other events. like maybe a delay to see if combo otherwise just send key press. so probably if combo else press idk
    if data['held_buttons']:
        for button in data['held_buttons']:
            action = profile['mappings']['buttons'].get(str(button))
            # if action:
            #     logging.info(f"Action held: {action}")
    
    if data['pressed_buttons']:
        for button in data['pressed_buttons']:
            mapped_action = get_button_action(profile, button)
            if mapped_action:
                execute_action(mapped_action, 1, config)
                data['held_buttons'].add(button)
                data['pressed_buttons'].remove(button)

    if data['released_buttons']:
        for button in data['released_buttons']:
            mapped_action = get_button_action(profile, button)
            if mapped_action:
                execute_action(mapped_action, 0, config)
                data['released_buttons'].remove(button)

    if data['axis_values']:
        print
        print('Debug: Axis values detected:', data['axis_values'])
        capturedAxisValues = data['axis_values'].copy()
        for axis, value in capturedAxisValues.items():
            print(f'Debug: Processing axis {axis} with current value {value} and previous value {data["axis_value_previous"][axis]}')
            
            # If the last value is not zero and the current value is not zero, then process the actions below
            if data['axis_value_previous'][axis] != 0.0 and value != 0.0:
                print(f'Debug: Axis {axis} has non-zero previous and current values')
                if data['skip_axes'][axis] != axis and value != 0.0:
                    mapped_action = get_axis_action(profile, int(axis))
                    if mapped_action:
                        print(f'Debug: Executing action for axis {axis} with value {value}')
                        execute_action(mapped_action, value, config)
                    if axis in [4, 5]:
                        print(f'Debug: Marking axis {axis} to be skipped')
                        data['skip_axes'][axis] = axis
            elif value == 0.0 and data['axis_value_previous'][axis] != 0.0:
                action = get_axis_action(profile, int(axis))
                if action:
                    print(f'Debug: Executing action for axis {axis} with value 0 (release)')
                    execute_action(action, 0, config)
                    data['skip_axes'][axis] = None
                    print(f'Debug: Axis {axis} reset - {data["skip_axes"]}')
                    data['axis_values'].pop(axis)  # this is why we are using the captured value, so we can modify on the loop without having to do another loop.
                    print(f'Debug: Axis {axis} removed - {data["axis_values"]}')
            elif value == 0.0 and data['axis_value_previous'][axis] == 0.0:
                data['axis_value_previous'][axis] = None
                return
            data['axis_value_previous'][axis] = value


    #TODO: add in combos
    # Execute combo actions
    # if data['pressed_buttons'] or data['held_buttons']:
    #     for combo in profile['combos']:
    #         if all(button in held_buttons for button in combo['buttons']):
    #             action = combo['action']
    #             execute_action(action, 1)
    #         else:
    #             action = combo['action']
    #             execute_action(action, 0)

def check_controller(config, layout, mappings, controller): #TODO: this has too much responsibility I feel 
    """
    Initializes the Pygame library and checks for connected controllers. If controllers are detected,
    it initializes each controller and listens for input events. The function processes controller
    input events and executes corresponding profile actions.

    Global Variables:
    - active_controller: The currently active controller.

    The function performs the following steps:
    1. For each detected controller:
        a. Initializes the controller.
        b. Logs the initialization of the controller.
        c. Sets up a data dictionary to store controller input events and states.
        d. Continuously listens for controller input events and processes them.
        e. Executes profile actions based on the input events.
        f. Handles KeyboardInterrupt to stop monitoring when interrupted by the user.

    Note:
    - The function uses the `logging` module to log information and warnings.
    - The function uses the `sleep` function to introduce delays between processing input events.
    """
    
    if controller:
        logging.info(f"Initialized Controller {controller}: {controller.get_name()}")
        global CURRENT_PROFILE_INDEX
        data = {
            'accepted_events': [pg.JOYAXISMOTION, pg.JOYBUTTONDOWN, pg.JOYBUTTONUP, pg.JOYHATMOTION],
            'pressed_buttons': [],
            'released_buttons': [],
            'axis_values': {},
            'connected_controllers': [],
            'events': [],
            'profile': config.get('current_profile_index'),
            'skip_axes': {index: None for index in range(6)},
            'held_buttons': set(),
            'axis_value_previous': {index: None for index in range(6)}
        }
        first = True
        while True or first:
            try:
                listen_for_controller_input(data, config)
                if data['pressed_buttons'] or data['held_buttons']:
                    execute_profile_actions(data, config, controller)
                    # sleep(0.1)
                if data['released_buttons']:
                    execute_profile_actions(data, config, controller)
                    # sleep(0.1)
                if data['axis_values']: #TODO this is pretty broken right now, im trying to get min and max to read properly otherwise it's just broken. might need to change how we calc value (% of 100%) and then apply deadzone
                    execute_profile_actions(data, config, controller)
                data['events'].clear()
                # sleep(0.1)
                if first:
                    first = False
            except KeyboardInterrupt:
                logging.info("Controller monitoring stopped by user.")
                break

def listen_for_controller_input(data, config):
    """
    Listens for controller input events and processes them.

    This function pumps the event queue to update the internal state of the event system,
    retrieves all the events from the queue, and stores them in the provided data dictionary.
    If there are any events, it calls the handle_controller_events function to process them.

    Args:
        data (dict): A dictionary to store the events. The events are stored under the key 'events'.

    Returns:
        None
    """
    pg.event.pump()
    data['events'] = pg.event.get()
    if data['events']:
        handle_controller_events(data, config)

def normalize_axis_value_0_to_1(value, min_val, max_val):
    if min_val == max_val:
        return 0.0
    return (value - min_val) / (max_val - min_val)

def normalize_axis_value_neg_1_to_1(value, min_val, max_val):
    if min_val == max_val:
        return 0.0
    # First map to [0,1], then scale to [-1,1].
    normalized_0_1 = (value - min_val) / (max_val - min_val)
    return normalized_0_1 * 2 - 1

def list_mappings():
    """
    Lists the current controller mappings from the configuration file.

    This function loads the configuration from a JSON file specified by CONFIG_PATH.
    It retrieves the current profile and prints the button and axis mappings for that profile.
    If the configuration or the current profile is not found, appropriate error messages are printed.

    Returns:
        None
    """
    config = load_json(CONFIG_PATH)
    if not config:
        print("Failed to load configuration.")
        return
    global CURRENT_PROFILE_INDEX
    current_profile = config.get('current_profile_index')
    if not current_profile:
        print("No current profile set.")
        return
    profile = next((p for p in config['profiles'] if p['name'] == current_profile), None)
    if not profile:
        print(f"Profile '{current_profile}' not found.")
        return

    print(f"Profile: {current_profile}")
    print("Button Mappings:")
    for button, action in profile['mappings']['buttons'].items():
        print(f"Button {button}: {action}")
    print("Axis Mappings:")
    for axis, action in profile['mappings']['axes'].items():
        print(f"Axis {axis}: {action}")
    print("Mappings printed successfully.")

def add_mapping(buttons=None, axes=None, action=None):
    config = load_json(CONFIG_PATH)
    if not config:
        print("Failed to load configuration.")
        return
    global CURRENT_PROFILE_INDEX
    current_profile = config.get('current_profile_index')
    if not current_profile:
        print("No current profile set.")
        return

    profile = next((p for p in config['profiles'] if p['name'] == current_profile), None)
    if not profile:
        print(f"Profile '{current_profile}' not found.")
        return

    if buttons:
        for button in buttons:
            profile['mappings']['buttons'][str(button)] = action
            print(f"Mapped Button {button} to action '{action}'.")

    if axes:
        for axis in axes:
            profile['mappings']['axes'][str(axis)] = action
            print(f"Mapped Axis {axis} to action '{action}'.")

    if save_config(config, CONFIG_PATH):
        print("Mappings updated successfully.")
    else:
        print("Failed to save mappings.")

def remove_mapping(buttons=None, axes=None):
    """
    Remove button and/or axis mappings from the current profile in the configuration.

    This function loads the current configuration, identifies the current profile,
    and removes the specified button and/or axis mappings from the profile. The updated
    configuration is then saved back to the configuration file.

    Args:
        buttons (list, optional): A list of button identifiers to remove from the mappings.
        axes (list, optional): A list of axis identifiers to remove from the mappings.

    Returns:
        None
    """
    config = load_json(CONFIG_PATH)
    if not config:
        print("Failed to load configuration.")
        return
    global CURRENT_PROFILE_INDEX
    current_profile = config.get('current_profile_index')
    if not current_profile:
        print("No current profile set.")
        return

    profile = next((p for p in config['profiles'] if p['name'] == current_profile), None)
    if not profile:
        print(f"Profile '{current_profile}' not found.")
        return

    if buttons:
        for button in buttons:
            if str(button) in profile['mappings']['buttons']:
                del profile['mappings']['buttons'][str(button)]
                print(f"Removed mapping for Button {button}.")
            else:
                print(f"No mapping found for Button {button}.")

    if axes:
        for axis in axes:
            if str(axis) in profile['mappings']['axes']:
                del profile['mappings']['axes'][str(axis)]
                print(f"Removed mapping for Axis {axis}.")
            else:
                print(f"No mapping found for Axis {axis}.")

    if save_config(config, CONFIG_PATH):
        print("Mappings updated successfully.")
    else:
        print("Failed to save mappings.")

def map_buttons_to_action():
    """
        This function loads the current configuration and profile, initializes the controller, and waits for user input to map
        controller buttons or axes to specific actions. The user can press a controller button or move an axis to detect the input,
        and then bind it to a keyboard key or mouse action. The mappings are saved back to the configuration file.

        Steps:
        1. Load the configuration from the specified path.
        2. Retrieve the current profile from the configuration.
        3. Initialize the controller and wait for user input.
        4. Detect controller button presses or axis movements.
        5. Bind the detected input to a keyboard key or mouse action.
        6. Save the updated mappings to the configuration file.

        Returns:
            None

    Interactively map controller buttons and axes to actions by detecting inputs and allowing keyboard or mouse binding.
    """
    config = load_json(CONFIG_PATH)
    if not config:
        print("Failed to load configuration.")
        return
    global CURRENT_PROFILE_INDEX
    current_profile_index = config.get('current_profile_index')
    if not current_profile_index:
        print("No current profile set.")
        return

    profile = config['profiles'][current_profile_index]
    print(f"Current Profile: {profile['name']}")
    # profile_name = profile.get('name')
    # if not profile_name:
    #     print(f"Profile '{profile_name}' not found.")
    #     return

    print(f"\nMapping Buttons and Axes for Profile: '{profile}'\n")

    pg.init()
    pg.joystick.init()
    controller_count = pg.joystick.get_count()
    if controller_count == 0:
        print("No controllers detected.")
        return

    controller = pg.joystick.Joystick(0)
    controller.init()

    while True:
        choice = input("Press a controller button or move an axis to map, or type 'done' to finish: ").strip().lower()

        if choice == 'done':
            break

        detected_input = None
        input_type = None

        print("Waiting for controller input...")
        while detected_input is None:
            for event in pg.event.get():
                if event.type == pg.JOYBUTTONDOWN:
                    detected_input = event.button
                    input_type = 'button'
                    break
                elif event.type == pg.JOYAXISMOTION:
                    detected_input = event.axis
                    input_type = 'axis'
                    break

        if input_type == 'button':
            print(f"Detected Button {detected_input}. Press a key or move the mouse to bind the action.")
        elif input_type == 'axis':
            print(f"Detected Axis {detected_input}. Press a key or move the mouse to bind the action.")

        action = None
        while action is None:
            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    key_name = pg.key.name(event.key)
                    action = f"Key.{key_name}"
                    break
                elif event.type == pg.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        action = "Button.left"
                    elif event.button == 2:
                        action = "Button.middle"
                    elif event.button == 3:
                        action = "Button.right"
                    break
                elif event.type == pg.MOUSEMOTION:
                    action = "MouseMove"
                    break

        if input_type == 'button':
            profile['mappings']['buttons'][str(detected_input)] = action
            print(f"Mapped Button {detected_input} to action '{action}'.\n")
        elif input_type == 'axis':
            profile['mappings']['axes'][str(detected_input)] = action
            print(f"Mapped Axis {detected_input} to action '{action}'.\n")

    if save_config(config, CONFIG_PATH):
        print("Mappings updated successfully.\n")
    else:
        print("Failed to save mappings.\n")

def listen():
    """
    Listen for controller inputs, identify the button or axis, and prompt the user to name it.
    Save the mappings to layout__ps4.json.
    """
    layout = {
        "axes": {},
        "buttons": {}
    }

    if not initialize_pygame():
        return

    controller = pg.joystick.Joystick(0)
    initialize_controller(controller)

    print("Starting controller input listening...")
    print("Press a button or move an axis on the controller to identify it.")

    while True:
        detected_input = None
        input_type = None

        print("Waiting for controller input... (type 'done' to finish)")
        while detected_input is None:
            for event in pg.event.get():
                if event.type == pg.JOYBUTTONDOWN:
                    detected_input = event.button
                    input_type = 'button'
                    break
                elif event.type == pg.JOYAXISMOTION:
                    detected_input = event.axis
                    input_type = 'axis'
                    break

        if detected_input is None:
            break

        if input_type == 'button':
            print(f"Detected Button {detected_input}.")
        elif input_type == 'axis':
            print(f"Detected Axis {detected_input}.")

        name = input("Enter a name for this input (or type 'skip' to skip): ").strip()
        if name.lower() == 'done':
            break
        elif name.lower() == 'skip':
            continue

        if input_type == 'button':
            layout["buttons"][str(detected_input)] = name
        elif input_type == 'axis':
            layout["axes"][str(detected_input)] = name

        print(f"Mapped {input_type.capitalize()} {detected_input} to '{name}'.\n")

    with open(LAYOUT_PATH, 'w') as f:
        json.dump(layout, f, indent=4)

    print("Controller input mapping completed and saved to layout__ps4.json.")

def log_controller_inputs():
    """
    Listen for controller inputs and log the button presses based on the mappings in layout__ps4.json.
    """
    layout = load_json(LAYOUT_PATH)
    if not layout:
        print("Failed to load layout.")
        return

    if not initialize_pygame():
        return

    controller = pg.joystick.Joystick(0)
    initialize_controller(controller)

    print("Starting to log controller inputs...")

    while True:
        for event in pg.event.get():
            if event.type == pg.JOYBUTTONDOWN:
                button = str(event.button)
                if button in layout["buttons"]:
                    logging.info(f"Button {button} pressed: {layout['buttons'][button]}")
            elif event.type == pg.JOYBUTTONUP:
                button = str(event.button)
                if button in layout["buttons"]:
                    logging.info(f"Button {button} released: {layout['buttons'][button]}")
            elif event.type == pg.JOYAXISMOTION:
                axis = str(event.axis)
                if axis in layout["axes"]:
                    value = event.value
                    logging.info(f"Axis {axis} moved to {value}: {layout['axes'][axis]}")

        sleep(0.1)

def run(config, layout, mappings, controller):
    """
    Initializes the pygame library and checks for connected controllers.
    This function first attempts to initialize the pygame library. If the 
    initialization fails, the function returns immediately. If the initialization 
    is successful, it proceeds to check for connected controllers.
    """
    print(controller, 'controller')
    if not controller:
        print("No controller found")
        return
    
    check_controller(config, layout, mappings, controller)

# def preload():
#     """
#     Preload the configuration and layout files.
#     """
#     config = load_json(CONFIG_PATH)
#     layout = load_json(LAYOUT_PATH)
#     mappings = load_json(MAPPINGS_PATH)
#     controller = initialize_pygame()
#     print('controller', controller)  # Ensure controller is correctly initialized

#     if not config:
#         logging.error("Failed to load configuration.")
#     if not layout:
#         logging.error("Failed to load layout.")
#     if not mappings:
#         logging.error("Failed to load mappings.")
#     if not controller:
#         logging.error("Failed to initialize controller.")
#     return config, layout, mappings, controller

def preload():
    config = load_json(CONFIG_PATH)
    layout = load_json(LAYOUT_PATH)
    mappings = load_json(MAPPINGS_PATH)
    global CURRENT_PROFILE_INDEX
    CURRENT_PROFILE_INDEX = config['current_profile_index']
    print('CURRENT_PROFILE_INDEX', CURRENT_PROFILE_INDEX)
    print('config', config)   

    pg_controller = initialize_pygame()
    if isinstance(pg_controller, list) and pg_controller:
        # Take the first controller if multiple
        controller_obj = initialize_controller(pg_controller[0])
    elif pg_controller:
        # Single controller returned
        controller_obj = initialize_controller(pg_controller)
    else:
        controller_obj = None

    return config, layout, mappings, controller_obj

def run_parser():

    config, layout, mappings, controller = preload()
    
    parser = argparse.ArgumentParser(description="Controller Mapper")
    subparsers = parser.add_subparsers(dest='command', required=True)

    subparsers.add_parser('run', help='Start the controller mapper')
    subparsers.add_parser('list', help='List all current mappings')
    add_parser = subparsers.add_parser('add', help='Add a new mapping')
    add_parser.add_argument('-b', '--buttons', nargs='+', help='Buttons to map')
    add_parser.add_argument('-a', '--action', help='Action to perform')
    remove_parser = subparsers.add_parser('remove', help='Remove an existing mapping')
    remove_parser.add_argument('-b', '--buttons', nargs='+', help='Buttons to remove')
    subparsers.add_parser('map', help='Interactively map controller buttons to actions')
    subparsers.add_parser('check', help='Check for connected controllers')
    switch_parser = subparsers.add_parser('switch', help='Switch to a different profile')
    switch_parser.add_argument('profile_name', help='Name of the profile to switch to')
    subparsers.add_parser('calibrate', help='Calibrate controller axes')
    subparsers.add_parser('listen', help='Listen for controller inputs and map them')
    subparsers.add_parser('log', help='Log controller inputs based on layout__ps4.json')
    subparsers.add_parser('human', help='Create human-friendly mappings')

    args = parser.parse_args()

    if args.command == 'run':
        run(config, layout, mappings, controller)
    elif args.command == 'list':
        list_mappings() #TODO: convert to main_data
    elif args.command == 'add':
        if args.buttons and args.action:
            add_mapping(buttons=args.buttons, action=args.action)
        else:
            print("Please provide buttons and action to add mapping.")
    elif args.command == 'remove':
        if args.buttons:
            remove_mapping(buttons=args.buttons)
        else:
            print("Please provide buttons to remove mapping.")
    elif args.command == 'map':
        map_buttons_to_action()
    elif args.command == 'check':
        check_controller()
    elif args.command == 'switch':
        swap_to_next_profile()
    elif args.command == 'calibrate':
        calibrate_axes(config, controller)
    elif args.command == 'listen':
        listen()
    elif args.command == 'log':
        log_controller_inputs()
    elif args.command == 'human':
        create_human_friendly_mappings()
    else:
        print("Unknown command.")

if __name__ == "__main__":
    run_parser()