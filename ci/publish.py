"""Validate a complete run, sign with SDK APK v3, then activate Bunny indexes.

The prepare command has no network access. Deploy revalidates everything before
creating the client, preflights immutable paths, and never deletes remote files.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

from packages import (apk_dump, component, digest, public_release, recipe_kind,
                      validate_index)

PUBLIC_URL = 'https://openwrt.lochnair.net'
KEY_PATH = 'keys/lochnair-apk.pem'


def publication_rows(matrix):
    rows = matrix['include']
    if not rows:
        raise ValueError('Empty publication matrix')
    seen = set()
    versions = set()
    selected = []
    for row in rows:
        component(row['package_arch'])
        key = (row['version'], row['package_arch'])
        if key in seen:
            raise ValueError(f'Duplicate matrix row: {key}')
        seen.add(key)
        if public_release(row['version']):
            versions.add(row['version'])
            selected.append(row)
    if len(versions) != 1:
        raise ValueError('Publication requires exactly one complete 25.12 release matrix')
    return selected


def expected_sources(feed):
    return {str(path.relative_to(feed)): (digest(path), *recipe_kind(path))
            for path in feed.glob('**/Makefile') if '.git' not in path.parts}


def validate_artifacts(matrix, artifacts, feed, identity):
    sources = expected_sources(feed)
    if not sources:
        raise ValueError('No feed recipes')
    repositories = []
    for row in publication_rows(matrix):
        version, arch = row['version'], row['package_arch']
        directory = artifacts / f'repository-{version}-{arch}'
        report = json.loads((directory / 'report.json').read_text())
        for key in ('version', 'package_arch', 'target', 'image', 'rust'):
            if report[key] != row[key]:
                raise ValueError(f'Build metadata mismatch for {version}/{arch}: {key}')
        if any(report[key] != value for key, value in identity.items()):
            raise ValueError('Artifacts do not belong to this run/commit/attempt')
        if report['schema'] != 1 or report['format'] != 'apk' or report['complete'] is not True:
            raise ValueError('Incomplete or non-APK build report')
        actual_sources = {}
        expected = {}
        for recipe in report['recipes']:
            source = recipe['source']
            if source in actual_sources:
                raise ValueError('Duplicate recipe in build report')
            actual_sources[source] = (recipe['source_sha256'], recipe['kind'], recipe['rust'])
            if recipe['kind'] == 'target-specific':
                continue  # All mixed/kernel recipe outputs remain separate artifacts.
            if recipe['status'] not in ('built', 'skipped') or not recipe['packages']:
                raise ValueError(f'Failed/missing userspace recipe: {source}')
            built = 0
            for package in recipe['packages']:
                if package['status'] == 'skipped':
                    reason = package.get('reason')
                    if reason not in ('sdk-without-rust', 'kconfig-unavailable'):
                        raise ValueError('Unrecognized package exclusion')
                    if reason == 'sdk-without-rust' and (row['rust'] or not recipe['rust']):
                        raise ValueError('Invalid Rust exclusion')
                    continue
                if package['status'] != 'built' or recipe['status'] != 'built':
                    raise ValueError('Missing expected supported package')
                name, ver = component(package['name']), component(package['version'])
                filename = f'{name}-{ver}.apk'
                if filename != package['filename'] or filename in expected:
                    raise ValueError('Invalid or duplicate output filename')
                expected[filename] = (name, ver)
                built += 1
            if recipe['status'] == 'built' and not built:
                raise ValueError('Built recipe has no built outputs')
        if actual_sources != sources:
            raise ValueError('Recipe inventory differs from the checked-out local feed')
        files = report['files']
        if set(files) != set(expected):
            raise ValueError('Build file inventory differs from expected packages')
        allowed = {'report.json', *expected}
        if expected:
            allowed.add('packages.adb')
        if {p.name for p in directory.iterdir()} != allowed:
            raise ValueError(f'Unexpected or missing artifact files in {directory}')
        for path in directory.iterdir():
            if path.is_symlink() or not path.is_file():
                raise ValueError('Only regular files are allowed in repository artifacts')
        for filename in expected:
            if digest(directory / filename) != files[filename]:
                raise ValueError(f'Package checksum mismatch: {filename}')
        eligibility = 'ready' if expected else 'empty'
        if report['eligibility'] != eligibility:
            raise ValueError('Invalid architecture eligibility')
        if not expected:
            print(f'Intentionally excluding {arch}: no eligible userspace outputs')
            continue
        repositories.append((row, directory, expected))
    if not repositories:
        raise ValueError('No publishable architectures')
    return repositories


def verify_repository(apk, directory, expected, arch, keys=None):
    index = directory / 'packages.adb'
    if index.read_bytes()[:3] != b'ADB':
        raise ValueError('Not an APK v3 ADB index')
    # Inspect every package payload, not only the index's package metadata.
    subprocess.run([str(apk), 'verify', '--allow-untrusted',
                    *[str(directory / name) for name in sorted(expected)]], check=True)
    data = apk_dump(apk, index)
    validate_index(data, expected, arch)
    with tempfile.TemporaryDirectory(prefix='apk-check-') as temporary:
        root = Path(temporary)
        # Fresh index from the exact package bytes: compare embedded package hashes,
        # sizes, names, versions and architectures against the supplied index.
        regenerated = root / 'packages.adb'
        subprocess.run([str(apk), 'mkndx', '--allow-untrusted', '--output', str(regenerated),
                        *[str(directory / name) for name in sorted(expected)]], check=True)
        if apk_dump(apk, regenerated)['packages'] != data['packages']:
            raise ValueError('Index metadata/hashes do not match the package files')
        if keys is not None:
            subprocess.run([str(apk), 'verify', '--root', str(root), '--keys-dir', str(keys),
                            '--repositories-file', '/dev/null', str(index)], check=True)


def prepare(apk, repositories, destination, fingerprint):
    # Keep the secret out of every APK/OpenSSL child process environment.
    secret = os.environ.pop('APK_SIGNING_KEY', '')
    # Validate ALL unsigned repositories before creating or using a key file.
    for row, source, expected in repositories:
        verify_repository(apk, source, expected, row['package_arch'])
    if destination.exists():
        raise ValueError('Signing destination must be new')
    with tempfile.TemporaryDirectory(prefix='apk-sign-') as temporary:
        private = Path(temporary) / 'private.pem'
        keys = Path(temporary) / 'keys'
        keys.mkdir()
        public = keys / 'lochnair-apk.pem'
        if not secret:
            raise ValueError('Missing APK_SIGNING_KEY')
        fd = os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as output:
            output.write(secret)
        del secret
        subprocess.run(['openssl', 'pkey', '-in', str(private), '-pubout', '-out', str(public)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        check_public_key(public, fingerprint)
        for row, source, expected in repositories:
            directory = destination / '25.12' / row['package_arch']
            directory.mkdir(parents=True)
            for name in expected:
                shutil.copyfile(source / name, directory / name)
            subprocess.run([str(apk), 'mkndx', '--allow-untrusted', '--sign', str(private),
                            '--output', str(directory / 'packages.adb'),
                            *[str(directory / name) for name in sorted(expected)]], check=True)
            verify_repository(apk, directory, expected, row['package_arch'], keys)
        public_output = destination / KEY_PATH
        public_output.parent.mkdir(parents=True)
        shutil.copyfile(public, public_output)
    # The private key existed only outside the artifact tree and is now removed.


def check_public_key(public, fingerprint):
    if not re.fullmatch(r'[0-9a-f]{64}', fingerprint) or digest(public) != fingerprint:
        raise ValueError('Public key fingerprint does not match the persistent signing identity')
    text = public.read_text()
    if not text.startswith('-----BEGIN PUBLIC KEY-----') or 'PRIVATE' in text:
        raise ValueError('Expected a PEM public key')


def deployment_plan(apk, repositories, destination, fingerprint):
    public = destination / KEY_PATH
    check_public_key(public, fingerprint)
    packages = [public]
    indexes = []
    for row, source, expected in repositories:
        directory = destination / '25.12' / row['package_arch']
        if {p.name for p in directory.iterdir()} != {*expected, 'packages.adb'}:
            raise ValueError('Unexpected/missing files in signed architecture')
        for name in expected:
            if digest(directory / name) != digest(source / name):
                raise ValueError('Package changed after signing')
            packages.append(directory / name)
        verify_repository(apk, directory, expected, row['package_arch'], public.parent)
        indexes.append(directory / 'packages.adb')
    expected_paths = set(packages + indexes)
    actual_paths = {p for p in destination.rglob('*') if not p.is_dir()}
    if actual_paths != expected_paths or any(p.is_symlink() for p in destination.rglob('*')):
        raise ValueError('Unexpected files/symlinks in publication tree')
    # Snapshot bytes after ALL validation and before any remote request/write.
    return ([(p.relative_to(destination).as_posix(), p.read_bytes()) for p in packages],
            [(p.relative_to(destination).as_posix(), p.read_bytes()) for p in indexes])


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirect refused for authenticated Bunny request')


class Bunny:
    def __init__(self, endpoint, access_key):
        url = urllib.parse.urlsplit(endpoint)
        if (url.scheme != 'https' or url.netloc != 'storage.bunnycdn.com'
                or url.query or url.fragment):
            raise ValueError('Use the HTTPS Storage Zone endpoint from the Access page')
        component(url.path.strip('/'))
        if not access_key:
            raise ValueError('Missing Storage Zone access key')
        self.base = endpoint.rstrip('/') + '/'
        self.access_key = access_key
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, method, url, key=None, data=None, missing=False):
        headers = {'AccessKey': key} if key else {}
        if data is not None:
            headers.update({'Content-Type': 'application/octet-stream',
                            'Checksum': hashlib.sha256(data).hexdigest().upper()})
        request = urllib.request.Request(url, headers=headers, data=data, method=method)
        for attempt in range(4):
            try:
                with self.opener.open(request, timeout=60) as response:
                    return response.read()
            except urllib.error.HTTPError as error:
                code = error.code
                error.close()
                if code == 404 and missing:
                    return None
                if code not in (429, 500, 502, 503, 504) or attempt == 3:
                    raise ValueError(f'Bunny {method} failed (HTTP {code})') from None
            except (urllib.error.URLError, TimeoutError):
                if attempt == 3:
                    raise ValueError(f'Bunny {method} failed (transport error)') from None
            time.sleep(2 ** attempt)

    def get(self, path):
        return self.request('GET', self.base + urllib.parse.quote(path, safe='/'),
                            self.access_key, missing=True)

    def put(self, path, data):
        self.request('PUT', self.base + urllib.parse.quote(path, safe='/'), self.access_key, data)
        if self.get(path) != data:
            raise ValueError(f'Storage read-back mismatch: {path}')

    def verify_public(self, path, data):
        for attempt in range(4):
            if self.request('GET', f'{PUBLIC_URL}/{urllib.parse.quote(path, safe="/")}',
                            missing=True) == data:
                return
            if attempt < 3:
                time.sleep(2 ** attempt)
        raise ValueError(f'CDN read-back mismatch: {path}')


def deploy(plan, bunny):
    packages, indexes = plan
    uploads = []
    # Preflight EVERY immutable filename before the first PUT.
    for path, data in packages:
        previous = bunny.get(path)
        if previous is not None and previous != data:
            raise ValueError(f'Refusing to overwrite immutable file; bump version/release: {path}')
        if previous is None:
            uploads.append((path, data))
    # Read all index paths before writes too, so authentication/path failures fail early.
    changed = [(path, data) for path, data in indexes if bunny.get(path) != data]
    for path, data in uploads:
        bunny.put(path, data)
    for path, data in packages:
        bunny.verify_public(path, data)
    # No index becomes visible until ALL new packages and the key are available.
    for path, data in changed:
        bunny.put(path, data)
        # CDN indexes may remain cached until the configured short TTL expires.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'deploy'))
    parser.add_argument('--apk', required=True, type=Path)
    parser.add_argument('--matrix', required=True, type=Path)
    parser.add_argument('--artifacts', required=True, type=Path)
    parser.add_argument('--feed', default='.', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--identity', type=Path,
                        help='Verified identity of a complete source build for publication retries')
    args = parser.parse_args()
    identity = {'commit': os.environ['GITHUB_SHA'], 'run_id': os.environ['GITHUB_RUN_ID'],
                'run_attempt': os.environ['GITHUB_RUN_ATTEMPT']}
    if args.identity is not None:
        identity = json.loads(args.identity.read_text())
        if set(identity) != {'commit', 'run_id', 'run_attempt'}:
            raise ValueError('Invalid source build identity')
    repositories = validate_artifacts(json.loads(args.matrix.read_text()), args.artifacts.resolve(),
                                      args.feed.resolve(), identity)
    fingerprint = os.environ['APK_PUBLIC_KEY_SHA256']
    if args.command == 'prepare':
        prepare(args.apk.resolve(), repositories, args.output.resolve(), fingerprint)
    else:
        # Even a manually invoked deploy must finish local validation before remote IO.
        plan = deployment_plan(args.apk.resolve(), repositories, args.output.resolve(), fingerprint)
        bunny = Bunny(os.environ['BUNNY_STORAGE_ENDPOINT'],
                      os.environ['BUNNY_STORAGE_ACCESS_KEY'])
        deploy(plan, bunny)


if __name__ == '__main__':
    main()
