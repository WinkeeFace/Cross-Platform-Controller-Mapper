# test_main.py

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import main

import main

class TestMain(unittest.TestCase):

    @patch('main.load_json')
    def test_load_json(self, mock_load_json):
        mock_load_json.return_value = {'key': 'value'}
        result = main.load_json('config.json')
        self.assertEqual(result, {'key': 'value'})

    @patch('main.KeyboardController')
    def test_execute_action_keyboard(self, mock_keyboard):
        main.execute_action('Key.ctrl', True)
        mock_keyboard().press.assert_called_with(main.Key.ctrl)
        main.execute_action('Key.ctrl', False)
        mock_keyboard().release.assert_called_with(main.Key.ctrl)

    @patch('main.MouseController')
    def test_execute_action_mouse(self, mock_mouse):
        main.execute_action('Button.left', True)
        mock_mouse().press.assert_called_with(main.Button.left)
        main.execute_action('Button.left', False)
        mock_mouse().release.assert_called_with(main.Button.left)

    @patch('main.swap_to_next_profile')
    def test_swap_to_next_profile(self, mock_swap):
        main.swap_to_next_profile()
        mock_swap.assert_called_once()
    
    @patch('main.pg.event.pump')
    def test_get_current_axis_value_no_controller(self, mock_pump):
        result = main.calculate_axis_value(0, None, {})
        self.assertEqual(result, 0.0)

    @patch('main.pg.event.pump')
    def test_get_current_axis_value_no_calibration(self, mock_pump):
        mock_controller = MagicMock()
        mock_controller.get_axis.return_value = 0.5
        result = main.calculate_axis_value(0, mock_controller, None)
        self.assertEqual(result, 0.5)
        mock_controller.get_axis.assert_called_once_with(0)

    @patch('main.normalize_axis_value', return_value=0.25)
    @patch('main.apply_deadzone', return_value=0.25)
    @patch('main.pg.event.pump')
    def test_get_current_axis_value_with_calibration(self, mock_pump, mock_apply_deadzone, mock_normalize):
        mock_controller = MagicMock()
        mock_controller.get_axis.return_value = 0.75
        config = {
            'calibration': {
                'axes': {
                    '0': {
                        'min': -1.0,
                        'max': 1.0
                    }
                },
                'deadzone': {}
            }
        }
        result = main.calculate_axis_value(0, mock_controller, config)
        self.assertEqual(result, 0.25)
        mock_normalize.assert_called_once_with(0.75, -1.0, 1.0)
        mock_apply_deadzone.assert_called_once_with(0.25, 0.0)

    @patch('main.pg.event.pump')
    def test_get_current_axis_value_with_deadzone(self, mock_pump):
        mock_controller = MagicMock()
        mock_controller.get_axis.return_value = 0.5
        config = {
            'calibration': {
                'axes': {
                    '1': {
                        'min': -0.99228098269979,
                        'max': 0.9297543250524951
                    }
                },
                'deadzone': {
                    '1': 0.1
                }
            }
        }
        result = main.calculate_axis_value(1, mock_controller, config)
        expected_normalized_value = main.normalize_joystick_value(0.5, -0.99228098269979, 0.9297543250524951)
        expected_value = main.apply_deadzone(expected_normalized_value, 0.1)
        self.assertEqual(result, expected_value)

    @patch('builtins.input', side_effect=['-1.0', '1.0'])
    @patch('main.get_current_axis_value', return_value=-1.0)
    def test_calibrate_axis_no_ref(self, mock_get_current_axis_value, mock_input):
        result = main.calibrate_axis_no_ref('0')
        mock_input.assert_any_call("Move axis 0 to maximum position and press Enter.")
        self.assertEqual(result, (-1.0, 1.0))
    
    @patch('builtins.input', return_value='')
    def test_set_deadzone_default(self, mock_input):
        deadzone = main.set_deadzone('1')
        self.assertEqual(deadzone, 0.05)
    
    @patch('builtins.input', return_value='0.2')
    def test_set_deadzone_custom(self, mock_input):
        deadzone = main.set_deadzone('0')
        self.assertEqual(deadzone, 0.2)
    
    @patch('main.pg.joystick.get_count', return_value=2)
    @patch('main.pg.joystick.Joystick')
    @patch('main.logging.warning')
    def test_initialize_pygame_multiple_controllers(self, mock_logging_warning, mock_joystick, mock_get_count):
        controllers = [MagicMock(), MagicMock()]
        mock_joystick.side_effect = controllers
        result = main.initialize_pygame()
        self.assertEqual(result, controllers)
    
    @patch('main.pg.joystick.get_count', return_value=0)
    @patch('main.logging.warning')
    def test_initialize_pygame_no_controllers(self, mock_logging_warning, mock_get_count):
        result = main.initialize_pygame()
        mock_logging_warning.assert_called_with("No controllers detected.")
        self.assertFalse(result)
    
    @patch('main.load_json', return_value={'current_profile': 'Default', 'profiles': []})
    @patch('main.Notifier.notify')
    def test_swap_to_next_profile_no_profiles(self, mock_notify, mock_load_json):
        main.swap_to_next_profile()
        mock_notify.assert_called_with("No profiles available to swap.")

if __name__ == '__main__':
    unittest.main()