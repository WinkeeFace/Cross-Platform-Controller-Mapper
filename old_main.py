import json
import logging
import argparse
from time import sleep, time
import pygame as pg
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController
import sys
from pync import Notifier  # For Mac notifications
import select

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize controllers
keyboard = KeyboardController()
mouse = MouseController()
active_controller = None

CONFIG_PATH = 'config.json'
CURRENT_PROFILE_KEY = 'current_profile'
LAYOUT_PATH = 'layout__ps4.json'
config, layout, profile = {}, {}, {}

previous_axis_values, previous_button_values, previous_hat_values = [], [], []

def spinner(text, pattern_id):
    spinner = [
        ['|', '/', '-', '\\'], #0
        ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'], #1
        ['◜', '◠', '◝', '◞', '◡', '◟'], #2
        ['◐', '◓', '◑', '◒'], #3
        ['▖', '▘', '▝', '▗'], #4
        ['◢', '◣', '◤', '◥'], #5
        ['◰', '◳', '◲', '◱'], #6
        ['◴', '◷', '◶', '◵'], #7
        ['◡', '⊙', '◠', '⊙'], #8
        ['⠁', '⠂', '⠄', '⡀', '⢀', '⠠', '⠐', '⠈'], #9
        ['-', '\\', '|', '/'], #10
        ['←', '↖', '↑', '↗', '→', '↘', '↓', '↙'], #11
        ['▉', '▊', '▋', '▌', '▍', '▎', '▏'], #12
        ['▉', '▊', '▋', '▌', '▍', '▎', '▏', '▎', '▍', '▌', '▋', '▊'],#13
        ['▖', '▘', '▝', '▗'], #14
        ['.', 'o', 'O', '@', '*'], #15
        ['|', '||', '|||', '||||', '|||||', '||||||', '|||||||', '||||||||', '|||||||||', '||||||||||'], #16
        ['▁', '▃', '▄', '▅', '▆', '▇', '█', '▇', '▆', '▅', '▄', '▃'], #17
        ['▉', '▊', '▋', '▌', '▍', '▎', '▏', '▎', '▍', '▌', '▋', '▊'] #18
    ]

    colors = [
        '\033[38;5;196m',  # Red
        '\033[38;5;202m',  # Red-Orange
        '\033[38;5;208m',  # Orange
        '\033[38;5;214m',  # Yellow-Orange
        '\033[38;5;220m',  # Yellow
        '\033[38;5;226m',  # Yellow-Green
        '\033[38;5;190m',  # Green-Yellow
        '\033[38;5;154m',  # Green
        '\033[38;5;118m',  # Green-Cyan
        '\033[38;5;82m',   # Cyan
        '\033[38;5;51m',   # Cyan-Blue
        '\033[38;5;45m',   # Blue
        '\033[38;5;39m',   # Blue-Indigo
        '\033[38;5;93m',   # Indigo
        '\033[38;5;129m',  # Indigo-Violet
        '\033[38;5;165m',  # Violet
        '\033[38;5;201m',  # Red-Violet
        '\033[38;5;196m',  # Red
        '\033[38;5;202m',  # Red-Orange
        '\033[38;5;208m',  # Orange
        '\033[38;5;214m',  # Yellow-Orange
        '\033[38;5;220m',  # Yellow
        '\033[38;5;226m',  # Yellow-Green
        '\033[38;5;190m',  # Green-Yellow
        '\033[38;5;154m',  # Green
        '\033[38;5;118m',  # Green-Cyan
        '\033[38;5;82m',   # Cyan
        '\033[38;5;51m',   # Cyan-Blue
        '\033[38;5;45m',   # Blue
        '\033[38;5;39m',   # Blue-Indigo
        '\033[38;5;93m',   # Indigo
        '\033[38;5;129m',  # Indigo-Violet
        '\033[38;5;165m',  # Violet
        '\033[38;5;201m'   # Red-Violet
    ]

    # colors.append('\033[0m')  # Reset
    spinner_index = 0
    color_index = 0

    while True:
        try:
            sys.stdout.write(f"\rWaiting for {text}.. {colors[color_index]}{spinner[pattern_id][spinner_index]}\033[0m")
            sys.stdout.flush()
            spinner_index = (spinner_index + 1) % len(spinner[pattern_id])
            color_index = (color_index + 1) % len(colors)
            sleep(0.4)
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                spinner_index = 0
                input()
                pattern_id = int(input("Enter new spinner pattern ID (0-18): "))
        except KeyboardInterrupt:
            print(f"\nStopped waiting for {text}.")
            break

def load_json(config_path) -> dict | bool:
    try:
        with open(config_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        return False

def save_config(config, config_path) -> bool:
    try:
        with open(config_path, 'w') as file:
            json.dump(config, file, indent=4)
        return True
    except Exception as e:
        logging.error(f"Failed to save config: {e}")
        return False

def initialize_pygame():
    pg.init()
    pg.joystick.init()
    controller_count = pg.joystick.get_count()
    if (controller_count == 0):
        logging.warning("No controller detected. Please connect a controller.")
        return None
    elif (controller_count == 1):
        logging.info("1 controller detected.")
        controller = pg.joystick.Joystick(0)
        controller.init()
        return controller
    else:
        for i in range(controller_count):
            pg.joystick.Joystick(i).init()
        return pg.joystick.Joystick(0)

def initialize_controller(controller):
    global active_controller
    active_controller = controller
    active_controller.init()
    logging.info(f"Initialized controller: {active_controller.get_name()}")

def check_controller():
    controller_count = pg.joystick.get_count()
    print(f"Detected {controller_count} controller(s).")
    if controller_count == 0:
        print("No controllers detected.")
    else:
        for i in range(controller_count):
            controller = pg.joystick.Joystick(i)
            initialize_controller(controller)
            print(f"Controller {i}: {controller.get_name()}")

            print(f"Controller properties for {controller.get_name()}:")
            print("  ID:", controller.get_id())
            for attr in dir(controller):
                if not attr.startswith('_') and not callable(getattr(controller, attr)):
                    try:
                        print(f"  {attr}: {getattr(controller, attr)}")
                    except Exception as e:
                        print(f"  {attr}: Error retrieving value ({e})")

            previous_axis_values = [controller.get_axis(axis) for axis in range(controller.get_numaxes())]
            previous_button_values = [controller.get_button(button) for button in range(controller.get_numbuttons())]
            previous_hat_values = [controller.get_hat(hat) for hat in range(controller.get_numhats())]

            data = {
                'accepted_events': [pg.JOYAXISMOTION, pg.JOYBUTTONDOWN, pg.JOYBUTTONUP, pg.JOYHATMOTION],
                'pressed_buttons': [],
                'axis_values': {},
                'connected_controllers': [],
                'events': []
            }
            first = True
            while data['connected_controllers'] or first:
                try:
                    pg.event.pump()
                    data['events'] = pg.event.get()
                    if data['events']:
                        event_response(data)
                        if data['pressed_buttons']:
                            sleep(0.2)
                            print(f"Pressed buttons: {data['pressed_buttons']}")
                        
                        if data['axis_values']:
                            print(f"Axis values: {data['axis_values']}")

                        # Execute actions based on profile mappings
                        for button in data['pressed_buttons']:
                            action = profile['mappings'].get(str(button))
                            if action:
                                execute_action(action, 1)  # Button pressed

                        for axis, value in data['axis_values'].items():
                            action = profile['mappings'].get(str(axis))
                            if action:
                                execute_action(action, value)

                    data['events'].clear()
                    sleep(0.1)
                    if first:
                        first = False
                except KeyboardInterrupt:
                    print("Stopped streaming controller values.")
                    break
                finally:
                    if controller_count == 0:
                        break

def execute_action(action, value):
    if action == "MouseLeftClick":
        if value:
            mouse.press(Button.left)
        else:
            mouse.release(Button.left)
    elif action == "MouseRightClick":
        if value:
            mouse.press(Button.right)
        else:
            mouse.release(Button.right)
    elif action == "MouseMiddleClick":
        if value:
            mouse.press(Button.middle)
        else:
            mouse.release(Button.middle)
    elif action == "SwapProfile":
        if value:
            swap_to_next_profile()
    elif action == "ArrowKeysHorizontal":
        if value > 0.5:
            keyboard.press(Key.right)
            keyboard.release(Key.left)
        elif value < -0.5:
            keyboard.press(Key.left)
            keyboard.release(Key.right)
        else:
            keyboard.release(Key.left)
            keyboard.release(Key.right)
    elif action == "ArrowKeysVertical":
        if value > 0.5:
            keyboard.press(Key.down)
            keyboard.release(Key.up)
        elif value < -0.5:
            keyboard.press(Key.up)
            keyboard.release(Key.down)
        else:
            keyboard.release(Key.up)
            keyboard.release(Key.down)
    elif action in ["Option", "Command", "Control", "Shift"]:
        key_map = {
            "Option": Key.alt,
            "Command": Key.cmd,
            "Control": Key.ctrl,
            "Shift": Key.shift
        }
        key_to_press = key_map.get(action)
        if key_to_press:
            if value:
                keyboard.press(key_to_press)
            else:
                keyboard.release(key_to_press)
    else:
        # Handle other keys
        if value:
            keyboard.press(action)
        else:
            keyboard.release(action)         
            
#TODO: this allows multi controller support™️
def log_event_joy(event):
    print(f"Controller event detected from controller {event.joy}.")

def event_response(data):

    events = data['events']
    accepted_events = data['accepted_events']
    pressed_buttons = data['pressed_buttons']
    axis_values = data['axis_values']

    connected_controllers = data['connected_controllers']

    for event in events:
        if (event.type not in accepted_events):
            if (event.type == pg.JOYDEVICEADDED):
                print(f"Controller <{event.guid}> connected.")
                connected_controllers.append(event.device_index)
            elif (event.type == pg.JOYDEVICEREMOVED):
                print(event)
                # print(f"Controller <{event.device_index}> disconnected.")
                connected_controllers.remove(event.instance_id)
            else:
                print("Unknown event type.")
                print(event)
                continue
        else: #accepted event type
            
            if (event.type == pg.JOYAXISMOTION):
                axis_values[event.axis] = event.value
            elif (event.type == pg.JOYBUTTONDOWN):
                pressed_buttons.append(event.button)
            elif (event.type == pg.JOYBUTTONUP):
                if (event.button in pressed_buttons):
                    pressed_buttons.remove(event.button)
                else:
                    print("Button not found in pressed buttons.")
            elif (event.type == pg.JOYHATMOTION):
                print("Hat motion detected.")
                print(event.hat, event.value)
            # log_event_joy(event) #TODO: shows we can log events from specific controllers thus binding actions to a specific controller

def map_buttons_to_action():
    print("Press the controller button(s) you want to map. Press Enter when done.")
    pressed_buttons = set()

    while True:
        pressed_buttons = listen_for_controller_input(pressed_buttons)
        if pressed_buttons:
            print(f"Detected buttons: {' + '.join(map(str, pressed_buttons))}")
            break
        sleep(0.1)

    buttons = list(pressed_buttons)

    print("Now, type the key name you want to map to and press Enter.")
    action = input("Key name: ").strip()

    if not action:
        print("No key name entered. Mapping aborted.")
        return

    print(f"Map {' + '.join(map(str, buttons))} to {action}? (y/n)")
    choice = input().lower()
    if (choice != 'y'):
        print("Mapping aborted.")
        return

    add_mapping([str(b) for b in buttons], action)

def listen_for_controller_input(pressed_buttons):
    pg.event.pump()
    for event in pg.event.get():
        if (event.type == pg.JOYBUTTONDOWN):
            button = event.button
            pressed_buttons.add(button)
            logging.debug(f"Button pressed: {button}")
        elif (event.type == pg.JOYBUTTONUP):
            button = event.button
            if (button in pressed_buttons):
                pressed_buttons.remove(button)
                logging.debug(f"Button released: {button}")
    return pressed_buttons

def add_mapping(buttons, action):
    profile_name = config[CURRENT_PROFILE_KEY]
    profile = next((p for p in config['profiles'] if p['name'] == profile_name), None)
    if profile:
        for button in buttons:
            profile['mappings'][button] = action
        save_config(config, CONFIG_PATH)
        print(f"Mapping added: {buttons} -> {action}")
    else:
        print(f"Profile {profile_name} not found.")

def remove_mapping(buttons):
    profile_name = config[CURRENT_PROFILE_KEY]
    profile = next((p for p in config['profiles'] if p['name'] == profile_name), None)
    if profile:
        for button in buttons:
            if (button in profile['mappings']):
                del profile['mappings'][button]
        save_config(config, CONFIG_PATH)
        print(f"Mapping removed: {buttons}")
    else:
        print(f"Profile {profile_name} not found.")

def list_mappings():
    profile_name = config[CURRENT_PROFILE_KEY]
    profile = next((p for p in config['profiles'] if p['name'] == profile_name), None)
    if profile:
        print(f"Mappings for profile {profile_name}:")
        for button, action in profile['mappings'].items():
            print(f"  {button}: {action}")
    else:
        print(f"Profile {profile_name} not found.")

def normalize_axis_value(value, min_val, max_val):
    """
    Normalize the axis value to a range between -1 and 1 based on the min and max values.
    """
    if min_val == max_val:
        logging.error("Min and max values are the same. Cannot normalize.")
        return 0.0
    normalized_value = 2 * (value - min_val) / (max_val - min_val) - 1
    return normalized_value

def get_current_axis_value(axis):
    if active_controller:
        pg.event.pump()  # Update the internal state of the joystick
        raw_value = active_controller.get_axis(axis)
        config = load_json(CONFIG_PATH)
        if config:
            min_val = config['calibration']['axes'][str(axis)]['min']
            max_val = config['calibration']['axes'][str(axis)]['max']
            return normalize_axis_value(raw_value, min_val, max_val)
        else:
            logging.error("Failed to load config for normalization.")
            return raw_value
    else:
        logging.error("No active controller found.")
        return 0.0

def calibrate_axes():
    config = load_json(CONFIG_PATH)
    if not config:
        print("Failed to load configuration.")
        return

    print("Starting calibration...")
    calibration_data = {}
    for axis in config['calibration']['axes']:
        print(f"Calibrating axis {axis}. Move to minimum position and press Enter.")
        input()
        min_val = get_current_axis_value(int(axis))
        print(f"Minimum value for axis {axis}: {min_val}")

        print(f"Move axis {axis} to maximum position and press Enter.")
        input()
        max_val = get_current_axis_value(int(axis))
        print(f"Maximum value for axis {axis}: {max_val}")

        calibration_data[axis] = {"min": min_val, "max": max_val}

    config['calibration']['axes'] = calibration_data
    if save_config(config, CONFIG_PATH):
        print("Calibration successful and saved to config.json.")
    else:
        print("Failed to save calibration data.")

# Rest of the code remains the same
def run_parser():
    parser = argparse.ArgumentParser(description="Controller Mapper")
    subparsers = parser.add_subparsers(dest='command', required=True)

    subparsers.add_parser('run', help='Start the controller mapper')
    subparsers.add_parser('list', help='List all current mappings')
    add_parser = subparsers.add_parser('add', help='Add a new mapping')
    add_parser.add_argument('-b', '--buttons', nargs='+', required=True, help='Buttons to map')
    add_parser.add_argument('-a', '--action', required=True, help='Action to perform')
    remove_parser = subparsers.add_parser('remove', help='Remove an existing mapping')
    remove_parser.add_argument('-b', '--buttons', nargs='+', required=True, help='Buttons to remove')
    subparsers.add_parser('map', help='Interactively map controller buttons to actions')
    subparsers.add_parser('check', help='Check for connected controllers')
    switch_parser = subparsers.add_parser('switch', help='Switch to a different profile')
    switch_parser.add_argument('profile_name', help='Name of the profile to switch to')
    subparsers.add_parser('listen', help='Listen and print all controller inputs')
    subparsers.add_parser('spinner', help='Test the spinner')
    calibrate_parser = subparsers.add_parser('calibrate', help='Calibrate controller axes')

    args = parser.parse_args()

    if (args.command == 'run'):
        run_mapper()
    elif (args.command == 'list'):
        list_mappings()
    elif (args.command == 'add'):
        add_mapping(args.buttons, args.action)
    elif (args.command == 'remove'):
        remove_mapping(args.buttons)
    elif (args.command == 'map'):
        map_buttons_to_action()
    elif (args.command == 'check'):
        check_controller()
    elif (args.command == 'switch'):
        switch_profile(args.profile_name)
    elif (args.command == 'spinner'):
        spinner_id = int(input("Enter spinner pattern ID (0-18): "))
        spinner("spinner", spinner_id)
    elif args.command == 'calibrate':
        calibrate_axes()
    # elif args.command == 'listen':
    #     listen_controller()
    else:
        logging.error("Unknown command.")
        parser.print_help()

def switch_profile(profile_name):
    global config
    profile = next((p for p in config['profiles'] if p['name'] == profile_name), None)
    if profile:
        config[CURRENT_PROFILE_KEY] = profile_name
        save_config(config, CONFIG_PATH)
        print(f"Switched to profile: {profile_name}")
    else:
        print(f"Profile {profile_name} not found.")

def run_menu():
    commands = {
        'r': 'run',
        'l': 'list',
        'a': 'add',
        're': 'remove',
        'm': 'map',
        'c': 'check',
        's': 'switch',
        'li': 'listen'
    }

    while True:
        print("\nController Mapper Menu:")
        print("  r  - Run the controller mapper")
        print("  l  - List all current mappings")
        print("  a  - Add a new mapping")
        print("  re - Remove an existing mapping")
        print("  m  - Interactively map controller buttons to actions")
        print("  c  - Check for connected controllers")
        print("  s  - Switch to a different profile")
        print("  li - Listen and print all controller inputs")
        print("  q  - Quit")

        choice = input("Enter your choice: ").strip().lower()

        if (choice == 'q'):
            break
        elif (choice in commands):
            command = commands[choice]
            if (command == 'run'):
                run_mapper(active_controller)
            elif (command == 'list'):
                list_mappings()
            elif (command == 'add'):
                map_buttons_to_action()
            elif (command == 'remove'):
                buttons = input("Enter buttons to remove (space-separated): ").strip().split()
                remove_mapping(buttons)
            elif (command == 'map'):
                map_buttons_to_action()
            elif (command == 'check'):
                check_controller()
            elif (command == 'switch'):
                profile_name = input("Enter profile name to switch to: ").strip()
                switch_profile(profile_name)
            # elif command == 'listen':
            #     listen_controller()
        else:
            print("Invalid choice. Please try again.")
        
def build_profile(config):
    
    profile_name = config.get(CURRENT_PROFILE_KEY)
    if not profile_name:
        logging.error(f"Current profile key '{CURRENT_PROFILE_KEY}' not found in config.")
        return

    profile = next((p for p in config['profiles'] if p['name'] == profile_name), None)
    if not profile:
        logging.error(f"Profile {profile_name} not found.")
        return

    # Log current profile and mappings
    logging.info(f"Loaded profile: {profile_name}")
    logging.info("Mappings:")
    for button, action in profile['mappings'].items():
        logging.info(f"  {button}: {action}")

    return profile

    # mappings = profile['mappings'] #TODO: utilize this to map the controller inputs to the actions

def get_controller_data(controller):
    
    axis_list = simplify_for_loop(controller.get_numaxes(), controller.get_axis)
    button_list = simplify_for_loop(controller.get_numbuttons(), controller.get_button)
    hat_list = simplify_for_loop(controller.get_numhats(), controller.get_hat)

    return axis_list, button_list, hat_list
    
def simplify_for_loop(length, array): #TODO: remove items we don't use by looking at the config
    cleaned_list = []
    for index in range(length):
        value = array(index)
        cleaned_list.append((index, value))
    return cleaned_list

def detect_changes(resulting_elements, previous_values):

    # current_values = [ resulting_elements[element_id] for element_id in range(len(resulting_elements))] 

    changed_values = []

    for element_id in range(len(previous_values)):
        current_value = resulting_elements[element_id]
        if (current_value != previous_values[element_id]):
            print(f"Element ID: {element_id}")
            print(f"Current value: {current_value}")
            print(f"Previous value: {previous_values[element_id]}")
            # Update the previous value
            previous_values[element_id] = current_value
            changed_values.append((element_id, current_value))

    #what am i really doing here?
    #im checking to see if the current value is different from the previous value
    #if it is, then we need to update the previous value to the current value and then return the element index and the current value
    #if it isn't, then we just return None

    #loop through, based on len of each list, and compare the current value to the previous value at index
    
    return changed_values

def run_mapper(controller):    
    if not controller:
        logging.error("No controller available.")
        return

    current_axis_values, current_button_values, current_hat_values = get_controller_data(controller)

    print(f"Current axis values: {current_axis_values}")
    print(f"Current button values: {current_button_values}")
    print(f"Current hat values: {current_hat_values}")

    changed_axis, changed_button, changed_hat = None, None, None
    
    #TODO: make modular (no globals here)
    global previous_axis_values, previous_button_values, previous_hat_values 
    
    while True:
        try:
            pg.event.pump()
            for event in pg.event.get():
                print(event)

            # Update and check axes
            changed_axises = detect_changes(current_axis_values, previous_axis_values)
            
            # Update and check buttons
            changed_buttons = detect_changes(current_button_values, previous_button_values)

            # Update and check hats
            changed_hats = detect_changes(current_hat_values, previous_hat_values)

            #Okay so now I need to come up with a way to check to see if any combos have been pressed which I guess we can grab that from the profile mappings property. Once we have that we can just iterate through that list and do a quick check to see if any of those happened and will just check to see a water my combo mappings, if any, civil, probably at a keyword in their config that just wraps the combo string or list in a wrapper of some kind. This should allow us to search for that specific wrapper and then check the combination inside. I'm liking the comma separated value idea. The list inside of the wrapper because this way we can actually combo more than two or three things at the same time. Which also means we cannot just straight execute an action but rather we should create a pending action that we then we can validate to make sure we don't do anything. We don't want to. And that's when we can possibly do the combo check but I think the combo check should be different just looking to see a are these specific buttons pressed down, which shouldn't be too bad because all the axes and buttons have indexes associated with them so we don't need to remember the name of the button or any that we just need to look at Haywood's this index and their associated value.

            # Execute actions
            if changed_axises:
                print("Changed axises detected.")
                # execute_action()
            if changed_buttons:
                print("Changed buttons detected.")
                # execute_action()
            if changed_hats:
                print("Changed hats detected.")
                # execute_action()

            previous_axis_values, previous_button_values, previous_hat_values = current_axis_values, current_button_values, current_hat_values

            #check for combos by looking at 1's and 0's
            # if ANY of the values are 1, then we need to check if any of the other values are 1
            


            sleep(0.2) #trying to slow down the loop to see if it helps with the CPU usage
        except KeyboardInterrupt:
            logging.info("Controller Mapper stopped by user.")
            break

    #we need to make sure there aren't combos pressed somehow. this seems to be my main running loop. which i'd rather pass back up to main.
    
    outbound_data = (changed_axis, changed_button, changed_hat), (previous_axis_values, previous_button_values, previous_hat_values)

    return outbound_data

def execute_action(action, value):
    if action == "MouseLeftClick":
        if value:
            mouse.press(Button.left)
        else:
            mouse.release(Button.left)
    elif action == "MouseRightClick":
        if value:
            mouse.press(Button.right)
        else:
            mouse.release(Button.right)
    elif action == "MouseMiddleClick":
        if value:
            mouse.press(Button.middle)
        else:
            mouse.release(Button.middle)
    elif action == "SwapProfile":
        if value:
            swap_to_next_profile()
    elif action == "ArrowKeysHorizontal":
        if value > 0.5:
            keyboard.press(Key.right)
            keyboard.release(Key.left)
        elif value < -0.5:
            keyboard.press(Key.left)
            keyboard.release(Key.right)
        else:
            keyboard.release(Key.left)
            keyboard.release(Key.right)
    elif action == "ArrowKeysVertical":
        if value > 0.5:
            keyboard.press(Key.down)
            keyboard.release(Key.up)
        elif value < -0.5:
            keyboard.press(Key.up)
            keyboard.release(Key.down)
        else:
            keyboard.release(Key.up)
            keyboard.release(Key.down)
    elif action in ["Option", "Command", "Control", "Shift"]:
        key_map = {
            "Option": "option",
            "Command": "command",
            "Control": "control",
            "Shift": "shift"
        }
        key_to_press = key_map.get(action)
        if key_to_press:
            if value:
                keyboard.press(key_to_press)
            else:
                keyboard.release(key_to_press)
    else:
        # Handle other keys
        if value:
            keyboard.press(action)
        else:
            keyboard.release(action)

def swap_to_next_profile():
    global config
    profiles = config['profiles']
    current_profile_name = config[CURRENT_PROFILE_KEY]
    current_index = next((index for (index, d) in enumerate(profiles) if d["name"] == current_profile_name), None)
    if current_index is not None:
        next_index = (current_index + 1) % len(profiles)
        next_profile = profiles[next_index]
        next_profile_name = next_profile['name']
        config[CURRENT_PROFILE_KEY] = next_profile_name
        save_config(config, CONFIG_PATH)
        logging.info(f"Switched to profile: {next_profile_name}")
        # Display notification
        Notifier.notify(f"Switched to profile: {next_profile_name}", title="Controller Mapper")
    else:
        logging.error("Current profile not found in profiles list.")

def main():
    global config, layout, profile
    global previous_axis_values, previous_button_values, previous_hat_values


    controller = initialize_pygame()
    if controller:
        initialize_controller(controller)
    config = load_json(CONFIG_PATH)
    layout = load_json(LAYOUT_PATH)

    if not config:
        logging.error("Failed to load config.")
        return
    
    if not layout:
        logging.error("Failed to load layout.")
        return
    
    profile = build_profile(config)

    if not profile:
        logging.error("Failed to build profile.")
        return
    
    
    previous_axis_values, previous_button_values, previous_hat_values = get_controller_data(controller)

    # run_parser()
    if run_parser():
            run_mapper(controller)
            print("Controller Mapper started.")

if __name__ == "__main__":
    main()