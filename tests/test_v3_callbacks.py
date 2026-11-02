from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from second_brain.bot import process_update
from second_brain.config import Settings
from second_brain.state import State


class CallbackTests(unittest.TestCase):
    def test_callback_uses_clicking_user_and_acknowledges_once(self):
        with tempfile.TemporaryDirectory() as folder:
            settings = Settings(Path(folder), allowed_user=42)
            state = State(Path(folder) / 'state.sqlite')
            commands, transport = Mock(), Mock()
            commands.callback.return_value = 'Task marked done'
            update = {'update_id': 1, 'callback_query': {'id': 'callback1', 'from': {'id': 42}, 'message': {'from': {'id': 999}, 'chat': {'id': 42, 'type': 'private'}}, 'data': 'task:done:T-abc'}}
            try:
                process_update(update, settings, transport, commands, state)
                process_update(update, settings, transport, commands, state)
                transport.call.assert_called_once_with('answerCallbackQuery', {'callback_query_id': 'callback1'})
                commands.callback.assert_called_once_with('task:done:T-abc')
                self.assertEqual(state.counts(), {'done': 1})
            finally:
                state.close()

    def test_unauthorized_click_cannot_mutate_workspace(self):
        with tempfile.TemporaryDirectory() as folder:
            settings = Settings(Path(folder), allowed_user=42)
            state = State(Path(folder) / 'state.sqlite')
            commands, transport = Mock(), Mock()
            update = {'update_id': 1, 'callback_query': {'id': 'callback1', 'from': {'id': 99}, 'message': {'chat': {'id': 42, 'type': 'private'}}, 'data': 'plan:approve:P-abc:1'}}
            try:
                process_update(update, settings, transport, commands, state)
                commands.callback.assert_not_called()
                transport.call.assert_not_called()
                self.assertEqual(state.counts(), {'ignored': 1})
            finally:
                state.close()


if __name__ == '__main__':
    unittest.main()
