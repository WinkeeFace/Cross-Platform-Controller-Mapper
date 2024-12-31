import logging
from config_utils import load_json, save_config, CONFIG_PATH

def calculate_axis_value(raw_value, axis, config):
    if config and str(axis) in config['calibration']['axes']:
        if axis in [4, 5]:  # triggers
            min_val = -1.0
            max_val = 1.0
            deadzone = 0.0
            normalized = normalize_trigger_value_to_1(raw_value, min_val, max_val)
            return apply_deadzone(normalized, deadzone)
        else:  # joysticks
            min_val = config['calibration']['axes'][str(axis)]['min']
            max_val = config['calibration']['axes'][str(axis)]['max']
            deadzone = config['calibration']['deadzone'].get(str(axis), 0.1)
            normalized = normalize_joystick_value(raw_value, min_val, max_val)
            return apply_deadzone(normalized, deadzone)
    else:
        logging.error("Failed to find axis for normalization in config.")
        return raw_value

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