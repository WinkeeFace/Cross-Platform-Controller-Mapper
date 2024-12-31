import json
import logging
import sys
import select
import argparse
import pygame as pg
from time import sleep, time
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController
import pyautogui as mouse
from pync import Notifier  # For Mac notifications
from config_utils import load_json, save_json, save_config, CONFIG_PATH, CURRENT_PROFILE_KEY, LAYOUT_PATH, MAPPINGS_PATH
from controller_utils import (initialize_pygame, initialize_controller,
                              handle_controller_events, normalize_axis_value_0_to_1,
                              normalize_axis_value_neg_1_to_1, listen)
from actions import execute_action, toggle_pause_inputs
from calibration_utils import calibrate_axes, set_deadzone  # etc
from profile_utils import (swap_to_next_profile, create_human_friendly_mappings,
                           list_mappings, add_mapping, remove_mapping,
                           map_buttons_to_action, execute_profile_actions)
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize controllers
keyboard = KeyboardController()
mouse = MouseController()
controller = None
is_inputs_paused = False

def save_layout(layout, layout_path):
    save_json(layout, layout_path)

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

def check_controller(config, layout, mappings, controller): #TODO: this has too much responsiblility I feel 
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
        print(controller, 'controller')

        logging.info(f"Initialized Controller {controller}: {controller.get_name()}")

        data = {
            'accepted_events': [pg.JOYAXISMOTION, pg.JOYBUTTONDOWN, pg.JOYBUTTONUP, pg.JOYHATMOTION],
            'pressed_buttons': [],
            'released_buttons': [],
            'axis_values': {},
            'connected_controllers': [controller.get_instance_id()],
            'events': [],
            'profile': config.get(CURRENT_PROFILE_KEY),
            'skip_axes': set(),
            'held_buttons': set()
        }
        first = True
        while data['connected_controllers'] or first:
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

def listen_for_controller_events(controller):
    """
    returns event list so we can do stuff with it
    """
    pg.event.pump()
    return pg.event.get()

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

def preload():
    config = load_json(CONFIG_PATH)
    layout_dir = os.path.join(os.getcwd(), 'layout')
    layouts = {}

    if os.path.exists(layout_dir):
        for file in os.listdir(layout_dir):
            if file.endswith('.json'):
                controller_name = os.path.splitext(file)[0]
                layout_path = os.path.join(layout_dir, file)
                layouts[controller_name] = load_json(layout_path)
    else:
        logging.warning(f"Layout directory {layout_dir} does not exist.")

    mappings = load_json(MAPPINGS_PATH)

    pg_controller = initialize_pygame()
    if isinstance(pg_controller, list) and pg_controller:
        # Take the first controller if multiple
        controller_obj = initialize_controller(pg_controller[0])
    elif pg_controller:
        # Single controller returned
        controller_obj = initialize_controller(pg_controller)
    else:
        controller_obj = None

    return config, layouts, mappings, controller_obj

def run_parser():

    config, layouts, mappings, controller = preload()
    
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
        run(config, layouts, mappings, controller)
    elif args.command == 'list':
        list_mappings(layouts)  # Update to handle multiple layouts
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
        check_controller(config, layouts, mappings, controller)
    elif args.command == 'switch':
        swap_to_next_profile()
    elif args.command == 'calibrate':
        calibrate_axes(config, controller)
    elif args.command == 'listen':
        listen()
    elif args.command == 'log':
        log_controller_inputs()
    elif args.command == 'human':
        create_human_friendly_mappings(config, layouts, mappings)
    else:
        print("Unknown command.")

if __name__ == "__main__":
    run_parser()