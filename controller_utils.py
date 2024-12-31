import logging
import pygame as pg
import os
from calibration_utils import calculate_axis_value
from config_utils import save_json, load_json, CONFIG_PATH, CURRENT_PROFILE_KEY

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
    if (controller_count == 0):
        logging.warning("No controllers detected. Please connect a controller.")
        return False
    if (controller_count == 1):
        controller = pg.joystick.Joystick(0)
        controller = initialize_controller(controller)
        logging.info(f"Initialized controller in init_pygame: {controller.get_name()}")
        return controller
    else:
        logging.info(f"{controller_count} controller(s) detected.")
        controllers = []
        for i in range(controller_count):
            controller = pg.joystick.Joystick(i)
            initialize_controller(controller)
            controllers.append(controller)
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
                logging.info(f"Controller <{event.guid}> connected.")
                connected_controllers.append(event.device_index)
            elif event.type == pg.JOYDEVICEREMOVED:
                logging.info(f"Controller {event.instance_id} disconnected.")
                connected_controllers.remove(event.instance_id)
            else:
                logging.info(f"Unknown event type: {event.type}")
        else:
            #there are so many joy events lol
            if event.type == pg.JOYAXISMOTION:
                axis = event.axis
                value = event.value
                value = calculate_axis_value(value, axis, config)
                # print('axis & value & evalue', axis, value, value)
                # print('axis_values', axis_values)
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
                    # print('after', axis_values)
                # sleep(1.5)
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

def listen():
    """
    Listen for controller inputs, identify the button or axis, and prompt the user to name it.
    Save the mappings to ./layout/<controller_name>.json.
    """
    layout = {
        "axes": {},
        "buttons": {}
    }

    if not initialize_pygame():
        return

    controller = pg.joystick.Joystick(0)
    initialize_controller(controller)
    
    # Get controller name and set layout file path
    controller_name = controller.get_name().replace(" ", "_")
    layout_dir = os.path.join(os.getcwd(), 'layout')
    os.makedirs(layout_dir, exist_ok=True)
    layout_file_path = os.path.join(layout_dir, f"{controller_name}.json")

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
    
    # Save the layout using save_json
    save_json(layout, layout_file_path)
    print(f"Controller input mapping completed and saved to {layout_file_path}.")