import logging
from pync import Notifier
from config_utils import load_json, save_json, CONFIG_PATH, CURRENT_PROFILE_KEY, MAPPINGS_PATH

def swap_to_next_profile():
    """
    Does a profile swap, updates the config, and sends a notification.
    """
    config = load_json(CONFIG_PATH)
    if not config:
        logging.error("Failed to load configuration.")
        return

    profiles = config.get('profiles', [])
    current_profile = config.get(CURRENT_PROFILE_KEY)
    if not current_profile:
        logging.error("No current profile set.")
        return

    try:
        current_index = next(i for i, p in enumerate(profiles) if p['name'] == current_profile)
        next_index = (current_index + 1) % len(profiles)
        config[CURRENT_PROFILE_KEY] = profiles[next_index]['name']
        if save_config(config, CONFIG_PATH):
            Notifier.notify(f"Switched to profile: {profiles[next_index]['name']}", title="Profile Switch")
            logging.info(f"Switched to profile: {profiles[next_index]['name']}")
        else:
            logging.error("Failed to save profile change.")
    except StopIteration:
        logging.error("Current profile not found.")

def create_human_friendly_mappings(config, layout, mappings):
    current_profile_name = config.get('current_profile')
    profiles = config.get('profiles', [])
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

def list_mappings(layouts):
    """
    Lists the current controller mappings from the configuration files.
    """
    config = load_json(CONFIG_PATH)
    if not config:
        print("Failed to load configuration.")
        return

    current_profile = config.get(CURRENT_PROFILE_KEY)
    if not current_profile:
        print("No current profile set.")
        return

    profile = next((p for p in config['profiles'] if p['name'] == current_profile), None)
    if not profile:
        print(f"Profile '{current_profile}' not found.")
        return

    for controller_name, layout in layouts.items():
        print(f"\nController: {controller_name}")
        print("Button Mappings:")
        for button, action in layout.get('buttons', {}).items():
            print(f"Button {button}: {action}")
        print("Axis Mappings:")
        for axis, action in layout.get('axes', {}).items():
            print(f"Axis {axis}: {action}")
    print("Mappings listed successfully.")

def add_mapping(buttons=None, axes=None, action=None):
    config = load_json(CONFIG_PATH)
    if not config:
        print("Failed to load configuration.")
        return

    current_profile = config.get(CURRENT_PROFILE_KEY)
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

    current_profile = config.get(CURRENT_PROFILE_KEY)
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

    current_profile = config.get(CURRENT_PROFILE_KEY)
    if not current_profile:
        print("No current profile set.")
        return

    profile = next((p for p in config['profiles'] if p['name'] == current_profile), None)
    if not profile:
        print(f"Profile '{current_profile}' not found.")
        return

    print(f"\nMapping Buttons and Axes for Profile: '{current_profile}'\n")

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

def execute_profile_actions(data, config, controller):
    """
    Executes actions based on the current profile and input data.
    This function processes input data to execute corresponding actions defined in the current profile.
    It handles button presses, button holds, button releases, and axis movements. The function also
    includes placeholders for handling combo actions.
    Args:
        data (dict): A dictionary containing input data with the following keys:
            - 'held_buttons' (set): A set of buttons that are currently held down.
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

    current_profile = config.get(CURRENT_PROFILE_KEY)
    if not current_profile:
        logging.error("No current profile set.")
        return

    profile = next((p for p in config['profiles'] if p['name'] == current_profile), None)
    if not profile:
        logging.error(f"Profile '{current_profile}' not found.")
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
                action = profile['mappings']['buttons'].get(str(button))
                if action:
                    print('action pressed', action)
                    execute_action(action, 1, config)
                    data['held_buttons'].add(button)
                    data['pressed_buttons'].remove(button)

    #if held we don't want to do but we want to know it's still there, fine
    #if pressed we want to do it once
    #if released we want to do it once

    #we need to make sure that we check to see if the button is held, if it is we don't want to do anything

    if data['released_buttons']:
        for button in data['released_buttons']:
            action = profile['mappings']['buttons'].get(str(button))
            if action:
                print('action released', action)
                execute_action(action, 0, config)
                data['released_buttons'].remove(button)
    # Execute axis actions
    if data['axis_values']:
        #TODO: here, idk if it actually factors in min and max properly to get a range then it can calc a % of 100% and then apply deadzone
        zero_axes = []
        # print('skip_axes', data['skip_axes'])
        for axis, value in data['axis_values'].items():
            if value == 0:
                zero_axes.append(axis)
            elif axis not in data['skip_axes']:
                action = profile['mappings']['axes'].get(str(axis))
                if action and value != 0:
                    # print('mock execute action', action, value)
                    execute_action(action, value, config)
                if axis in [4, 5]:
                    data['skip_axes'].add(axis)
        if zero_axes:
            for axis in zero_axes:
                data['axis_values'].pop(axis)
                if axis in data['skip_axes']:
                    execute_action(profile['mappings']['axes'].get(str(axis)), 0, config)
                    data['skip_axes'].remove(axis)

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