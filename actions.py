import logging
import pyautogui as mouse
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController
from profile_utils import swap_to_next_profile
from config_utils import CONFIG_PATH, load_json
from pync import Notifier

keyboard = KeyboardController()
mouse_controller = MouseController()

def smooth_mouse_move(x, y):
    # Placeholder function for mouse movement
    mouse.moveRel(x, y)

def execute_action(action, value, config):
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
        "": lambda v: None
    }
    print('action', action)
    def test_log(v):
        print(f"Test Log: value={v}")

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
            mouse_controller.press(button)
        else:
            mouse_controller.release(button)
    else:
        func = action_map.get(action)
        if func:
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