"""Shared publication policy; OpenWrt remains the recipe/Kconfig authority."""

import hashlib
import json
import re
import subprocess


ARCH = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_+.-]*")
VERSION = re.compile(r"(24\.10|25\.12)\.\d+(?:-rc\d+)?")


def component(value):
    if not isinstance(value, str) or not ARCH.fullmatch(value) or '..' in value:
        raise ValueError(f"Unsafe path component: {value!r}")
    return value


def public_release(version):
    if not VERSION.fullmatch(version):
        raise ValueError(f"Unsupported OpenWrt release: {version}")
    return version.startswith('25.12.')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def recipe_kind(makefile):
    source = '\n'.join(line.split('#', 1)[0] for line in makefile.read_text().splitlines())
    source = source.replace('\\\n', ' ')
    # The entire mixed recipe is target-specific, including ipt-xt_tls.
    kernel = bool(re.search(r'\bkernel\.mk\b|\bKernelPackage\b', source))
    rust = bool(re.search(r'\brust/host\b|\brust-package\.mk\b|\bBuild/Compile/Cargo\b|\bRustBinPackage\b', source))
    return ('target-specific' if kernel else 'userspace'), rust


def package_metadata(text):
    """Read OpenWrt's evaluated .packageinfo, including multi-output recipes."""
    result = {}
    source = None
    package = None
    for line in text.splitlines():
        if line.startswith('Source-Makefile: '):
            source = line.split(': ', 1)[1]
            package = None
        elif line.startswith('Package: '):
            if source is None:
                raise ValueError('Package metadata without Source-Makefile')
            package = {'Package': line.split(': ', 1)[1]}
            result.setdefault(source, []).append(package)
        elif line == '@@':
            package = None  # Do not interpret description/config text as fields.
        elif package is not None and ': ' in line:
            key, value = line.split(': ', 1)
            package[key] = value
    return result


def apk_dump(apk, path):
    return json.loads(subprocess.check_output(
        [str(apk), 'adbdump', '--allow-untrusted', '--format', 'json', str(path)], text=True))


def validate_index(data, expected, arch):
    """Require one exact name/version/file per expected local userspace output."""
    packages = data.get('packages') if isinstance(data, dict) else None
    if not isinstance(packages, list) or not packages:
        raise ValueError('Missing or empty APK v3 package index')
    actual = {}
    for package in packages:
        name, version = package['name'], package['version']
        component(name)
        component(version)
        filename = f'{name}-{version}.apk'
        if filename in actual or name.startswith(('kmod-', 'kernel')):
            raise ValueError(f'Duplicate or kernel package in index: {name}')
        if package.get('arch') not in (arch, 'noarch'):
            raise ValueError(f'Wrong APK architecture: {package.get("arch")} (expected {arch})')
        # A helper tied to the kernel must never escape recipe classification.
        dependencies = package.get('depends', [])
        if not isinstance(dependencies, list):
            raise ValueError('Unexpected APK dependency metadata')
        for dependency in dependencies:
            dep = dependency.get('name', '') if isinstance(dependency, dict) else dependency
            if not isinstance(dep, str) or re.match(r'^(?:kernel(?:[<>=~]|$)|kmod-)', dep):
                raise ValueError(f'Kernel dependency in userspace index: {name}')
        actual[filename] = (name, version)
    if actual != expected:
        raise ValueError(f'APK index differs from expected outputs: {set(actual) ^ set(expected)}')
    return packages
