"""Exercise the real image without using or printing any user's credentials."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid


def docker(*args):
    result = subprocess.run(['docker', *args], text=True, capture_output=True)
    if result.returncode:
        # Docker arguments include only paths, names and image tags, not secrets.
        raise RuntimeError(f'Docker {args[0]} failed: {result.stderr.strip()}')
    return result.stdout.strip()


def request(url, path='/', username=None, password=None, payload=None):
    headers = {}
    if username is not None:
        credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()
        headers['Authorization'] = 'Basic ' + credentials
    if payload is not None:
        headers['Content-Type'] = 'application/json'
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url + path, data=body, headers=headers,
                                 method='PUT' if payload is not None else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def verify(image):
    name = 'syncclipboard-test-' + uuid.uuid4().hex[:12]
    password = secrets.token_hex(24) + '"\\end'
    username = 'ci_test'
    with tempfile.TemporaryDirectory(prefix='syncclipboard-ha-') as directory:
        data = Path(directory)
        options = data / 'options.json'

        def write_options(value):
            options.write_text(json.dumps({'username': username, 'password': value}), encoding='utf-8')
            os.chmod(options, 0o600)

        def remove():
            subprocess.run(['docker', 'rm', '-f', name], capture_output=True)

        def start():
            docker('run', '-d', '--name', name, '-p', '127.0.0.1::5033',
                   '-v', f'{data}:/data', image)
            port = docker('port', name, '5033/tcp').splitlines()[0]
            return 'http://' + port

        def wait_ready(url):
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                try:
                    if request(url)[0] == 401:
                        return
                except (OSError, TimeoutError):
                    pass
                if docker('inspect', '-f', '{{.State.Running}}', name) != 'true':
                    raise RuntimeError('Candidate container exited before becoming ready')
                time.sleep(1)
            raise TimeoutError('Candidate did not become ready within 90 seconds')

        try:
            write_options('')
            docker('run', '-d', '--name', name, '-v', f'{data}:/data', image)
            for _ in range(30):
                if docker('inspect', '-f', '{{.State.Running}}', name) == 'false':
                    break
                time.sleep(1)
            require(docker('inspect', '-f', '{{.State.ExitCode}}', name) != '0',
                    'Empty password must fail startup')
            require(docker('inspect', '-f', '{{.State.Running}}', name) == 'false',
                    'Empty-password container must stop')
            remove()

            write_options(password)
            url = start()
            wait_ready(url)
            require(request(url)[0] == 401, 'Unauthenticated request must return 401')
            require(request(url, username=username, password='wrong')[0] == 401,
                    'Wrong credentials must return 401')
            require(request(url, username=username, password=password)[0] == 200,
                    'Correct credentials must succeed')
            status, body = request(url, '/api/version', username, password)
            version = body.decode().strip().strip('"')
            require(status == 200 and re.fullmatch(r'[0-9A-Za-z.+-]{1,64}', version),
                    'Server must return a valid version')
            text = 'Home Assistant SyncClipboard persistence test: 剪贴板同步'
            profile = {'type': 'Text', 'hash': hashlib.sha256(text.encode()).hexdigest().upper(),
                       'text': text, 'hasData': False, 'dataName': '', 'size': 0}
            require(request(url, '/SyncClipboard.json', username, password, profile)[0] == 200,
                    'Clipboard PUT must succeed')
            status, body = request(url, '/SyncClipboard.json', username, password)
            require(status == 200 and json.loads(body)['text'] == text, 'Text must read back exactly')
            remove()
            url = start()
            wait_ready(url)
            status, body = request(url, '/SyncClipboard.json', username, password)
            require(status == 200 and json.loads(body)['text'] == text,
                    'Clipboard must survive container replacement with the same data volume')
            print('PASS: startup, authentication, Unicode round-trip and persistent volume')
            return {'passed': True, 'server_version': version}
        finally:
            remove()
            # The app runs as root like the HA container; restore ownership of
            # this isolated test volume before the runner deletes its temp dir.
            docker('run', '--rm', '--user', '0:0', '--network', 'none',
                   '--entrypoint', 'chown', '-v', f'{data}:/data', image,
                   '-R', f'{os.getuid()}:{os.getgid()}', '/data')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', required=True)
    parser.add_argument('--result', type=Path, default=Path('verification.json'))
    arguments = parser.parse_args()
    result = verify(arguments.image)
    arguments.result.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
