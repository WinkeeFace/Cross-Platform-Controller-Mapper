import unittest
from unittest.mock import patch, mock_open, MagicMock
import old_main
import pygame as pg
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController
import json

class TestControllerMapper(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pg.init()

    @patch('main.pg.event.get')
    def test_listen_for_controller_input(self, mock_event_get):
        
        # Create mock events for button press and release
        mock_event_press = MagicMock(type=pg.JOYBUTTONDOWN, button=0)
        mock_event_release = MagicMock(type=pg.JOYBUTTONUP, button=0)

        # Mock event.get() to return the mock events in sequence
        mock_event_get.side_effect = [
            [mock_event_press],    # First call returns button press event
            [mock_event_release],  # Second call returns button release event
        ]

        pressed_buttons = set()

        # First call - Button pressed
        pressed_buttons = old_main.listen_for_controller_input(pressed_buttons)
        self.assertIn(0, pressed_buttons)

        # Second call - Button released
        pressed_buttons = old_main.listen_for_controller_input(pressed_buttons)
        self.assertNotIn(0, pressed_buttons)

    @patch('main.keyboard')
    def test_execute_action_keyboard(self, mock_keyboard):
        # Test pressing and releasing a modifier key (e.g., 'Option')
        old_main.execute_action('Option', True)
        mock_keyboard.press.assert_called_with('option')
        
        old_main.execute_action('Option', False)
        mock_keyboard.release.assert_called_with('option')

    @patch('main.mouse')
    def test_execute_action_mouse_click(self, mock_mouse):
        # Test mouse left click press and release
        old_main.execute_action('MouseLeftClick', True)
        mock_mouse.press.assert_called_with(Button.left)
        
        old_main.execute_action('MouseLeftClick', False)
        mock_mouse.release.assert_called_with(Button.left)

    @patch('main.keyboard')
    def test_execute_action_arrow_keys_horizontal(self, mock_keyboard):
        # Simulate joystick moving right
        old_main.execute_action('ArrowKeysHorizontal', 1.0)
        mock_keyboard.press.assert_called_with(Key.right)
        mock_keyboard.release.assert_called_with(Key.left)
        
        # Reset mock between calls
        mock_keyboard.reset_mock()
        
        # Simulate joystick moving to neutral
        old_main.execute_action('ArrowKeysHorizontal', 0.0)
        mock_keyboard.release.assert_any_call(Key.left)
        mock_keyboard.release.assert_any_call(Key.right)

    @patch('main.Notifier')
    @patch('main.save_config')
    @patch('main.logging')
    def test_swap_to_next_profile(self, mock_logging, mock_save_config, mock_notifier):
        # Setup test config
        old_main.config = {
            "current_profile": "Profile1",
            "profiles": [
                {"name": "Profile1", "mappings": {}},
                {"name": "Profile2", "mappings": {}},
                {"name": "Profile3", "mappings": {}}
            ]
        }

        # Call the function
        old_main.swap_to_next_profile()

        # Verify the current profile has been updated
        self.assertEqual(old_main.config["current_profile"], "Profile2")

        # Verify that save_config was called
        mock_save_config.assert_called_with(old_main.config, old_main.CONFIG_PATH)

        # Verify that a notification was sent
        mock_notifier.notify.assert_called_with("Switched to profile: Profile2", title="Controller Mapper")

    @patch('builtins.open', new_callable=mock_open, read_data=json.dumps({
        "profiles": [{"name": "MyProfile", "device": "XboxController", "mappings": {"ButtonA": "KeySpace"}}]
    }))
    def test_load_config(self, mock_file):
        config = old_main.load_json('config.json')
        expected_config = {
            "profiles": [{"name": "MyProfile", "device": "XboxController", "mappings": {"ButtonA": "KeySpace"}}]
        }
        self.assertEqual(config, expected_config)
        mock_file.assert_called_with('config.json', 'r')

    @patch('builtins.open', new_callable=mock_open)
    def test_save_config(self, mock_file):
        config = {"profiles": [{"name": "MyProfile", "device": "XboxController", "mappings": {"ButtonA": "KeySpace"}}]}
        old_main.save_config(config, 'config.json')
        mock_file.assert_called_with('config.json', 'w')
        handle = mock_file()
        written_data = ''.join(call.args[0] for call in handle.write.call_args_list)
        expected_data = json.dumps(config, indent=4)
        self.assertEqual(written_data, expected_data)

    @patch('main.execute_action')
    @patch('main.pg.event.pump')
    @patch('main.initialize_controller')
    @patch('main.initialize_pygame')
    def test_run_mapper(self, mock_initialize_pygame, mock_initialize_controller, mock_event_pump, mock_execute_action):
        # Mock controller
        mock_controller = MagicMock()
        mock_controller.get_numaxes.return_value = 2
        mock_controller.get_numbuttons.return_value = 5
        mock_controller.get_numhats.return_value = 1
        mock_controller.get_axis.return_value = 0.0  # Always return 0.0
        mock_controller.get_hat.return_value = (0, 0)

        # Define get_button to simulate a button press on Button 1
        button_states = [
            [0, 0, 0, 0, 0],  # Initial state
            [0, 1, 0, 0, 0],  # Button 1 pressed
        ]

        def get_button_side_effect(button_index):
            state = button_states[get_button_side_effect.call_count]
            if button_index == mock_controller.get_numbuttons.return_value - 1:
                get_button_side_effect.call_count = min(get_button_side_effect.call_count + 1, len(button_states) - 1)
            return state[button_index]

        get_button_side_effect.call_count = 0
        mock_controller.get_button.side_effect = get_button_side_effect

        mock_initialize_pygame.return_value = mock_controller
        mock_initialize_controller.return_value = None

        # Mock configuration
        with patch('main.load_json') as mock_load_json:
            mock_load_json.return_value = {
                "current_profile": "Default",
                "profiles": [
                    {
                        "name": "Default",
                        "device": "TestController",
                        "mappings": {
                            "Button 1": "SwapProfile"
                        }
                    },
                    {
                        "name": "Gaming",
                        "device": "TestController",
                        "mappings": {}
                    }
                ]
            }
            # Mock swap_to_next_profile to prevent changing global state during test
            with patch('main.swap_to_next_profile') as mock_swap_profile:
                # Run the mapper function
                old_main.run_mapper(mock_controller)

                # Check that execute_action was called with 'SwapProfile'
                mock_execute_action.assert_any_call("SwapProfile", 1)

                # Verify that swap_to_next_profile was called
                mock_swap_profile.assert_called_once()

    @unittest.mock.patch('sys.argv', ['main.py', 'run'])
    @patch('main.run_parser')
    def test_main(self, mock_run_parser):
        old_main.main()
        mock_run_parser.assert_called_once()

if __name__ == '__main__':
    unittest.main()
