import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from second_brain.config import Settings
from second_brain.dashboard import make_server


class DashboardHTTPTests(unittest.TestCase):
    def test_session_authorization_and_command_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            try:
                server, token = make_server(Settings(Path(folder)), port=0, token='test-session')
            except OSError as error:
                self.skipTest(f'Loopback server unavailable: {error}')
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{server.server_port}'
            try:
                with self.assertRaises(HTTPError) as error:
                    urlopen(base + '/api/snapshot', timeout=5)
                self.assertEqual(error.exception.code, 401)
                headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
                with urlopen(Request(base + '/api/command', data=json.dumps({'command': '/task Verify local capture'}).encode(), headers=headers), timeout=10) as response:
                    payload = json.load(response)
                self.assertEqual(payload['snapshot']['tasks'][0]['title'], 'Verify local capture')
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(base + '/api/command', data=b'{"command":"/sync push"}', headers=headers), timeout=5)
                self.assertEqual(error.exception.code, 400)
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(base + '/api/snapshot', headers={**headers, 'Origin': 'https://other.example'}), timeout=5)
                self.assertEqual(error.exception.code, 401)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
