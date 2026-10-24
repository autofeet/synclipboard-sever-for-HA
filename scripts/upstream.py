"""Prepare a candidate update; the workflow must verify it before committing."""
import argparse
import json
from pathlib import Path
import re
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
DIGEST = re.compile(r'sha256:[0-9a-f]{64}')


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def verification_due(root, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        record = json.loads((root / 'maintenance.json').read_text(encoding='utf-8'))
        last = datetime.fromisoformat(record['last_verified'])
        return now - last >= timedelta(days=28) or last > now
    except (OSError, ValueError, KeyError, TypeError):
        return True


def prepare(root, digest):
    if not DIGEST.fullmatch(digest):
        raise ValueError('Invalid upstream digest')
    app = root / 'syncclipboard_server'
    lock_path = root / 'upstream.json'
    lock = json.loads(lock_path.read_text(encoding='utf-8'))
    if digest == lock['digest']:
        return False
    config_path = app / 'config.json'
    config = json.loads(config_path.read_text(encoding='utf-8'))
    if not re.fullmatch(r'\d+\.\d+\.\d+', config['version']):
        raise ValueError('Unsupported application version')
    major, minor, patch = map(int, config['version'].split('.'))
    config['version'] = f'{major}.{minor}.{patch + 1}'
    dockerfile = app / 'Dockerfile'
    text = dockerfile.read_text(encoding='utf-8')
    old = 'FROM jericx/syncclipboard-server@' + lock['digest']
    if text.count(old) != 1 or not text.startswith(old + '\n'):
        raise ValueError('Dockerfile and lock do not match')
    # Finish all checks before changing candidate files.
    dockerfile.write_text(text.replace(old, 'FROM jericx/syncclipboard-server@' + digest, 1), encoding='utf-8')
    write_json(config_path, config)
    lock['digest'] = digest
    lock['version'] = None  # Filled only after the image reports its version.
    write_json(lock_path, lock)
    return True


def record_verification(root, result_path):
    result = json.loads(result_path.read_text(encoding='utf-8'))
    version = result['server_version']
    if result.get('passed') is not True or not re.fullmatch(r'[0-9A-Za-z.+-]{1,64}', version):
        raise ValueError('Missing successful verification result')
    lock_path = root / 'upstream.json'
    lock = json.loads(lock_path.read_text(encoding='utf-8'))
    lock['version'] = version
    write_json(lock_path, lock)
    write_json(root / 'maintenance.json', {'last_verified': datetime.now(timezone.utc).isoformat(),
                                         'digest': lock['digest'], 'server_version': version})
    app = root / 'syncclipboard_server'
    config = json.loads((app / 'config.json').read_text(encoding='utf-8'))
    changelog = app / 'CHANGELOG.md'
    text = changelog.read_text(encoding='utf-8')
    heading = f"## {config['version']}\n"
    if heading not in text:
        text = text.replace('# Changelog\n', f"# Changelog\n\n{heading}\n- Update upstream to {version} ({lock['digest']}).\n- Passed startup, authentication, text round-trip and container-replacement persistence checks.\n", 1)
        changelog.write_text(text, encoding='utf-8')


def latest_digest():
    request = urllib.request.Request(
        'https://hub.docker.com/v2/repositories/jericx/syncclipboard-server/tags/latest',
        headers={'User-Agent': 'SyncClipboard-HA-maintenance'})
    with urllib.request.urlopen(request, timeout=30) as response:
        tag = json.load(response)
    digest = tag['digest']
    if not DIGEST.fullmatch(digest):
        raise ValueError('Invalid registry digest')
    if not any(image.get('architecture') == 'amd64' and image.get('os') == 'linux' for image in tag['images']):
        raise ValueError('Upstream tag has no linux/amd64 image')
    return digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['check', 'prepare', 'record', 'due'])
    parser.add_argument('--digest')
    parser.add_argument('--result', type=Path)
    args = parser.parse_args()
    if args.action == 'check':
        print(latest_digest())
    elif args.action == 'due':
        print('true' if verification_due(ROOT) else 'false')
    elif args.action == 'prepare':
        print('changed' if prepare(ROOT, args.digest or '') else 'unchanged')
    else:
        if not args.result:
            parser.error('--result is required')
        record_verification(ROOT, args.result)


if __name__ == '__main__':
    main()
