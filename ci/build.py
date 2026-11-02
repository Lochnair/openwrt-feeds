"""Full SDK builds with fail-closed userspace publication metadata."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

from packages import (apk_dump, component, digest, package_metadata, public_release,
                      recipe_kind, validate_index, write_json)


def discover_packages(sdk):
    # Let OpenWrt identify recipes, including nested recipes and multi-output ones.
    packages = sorted(path.name for path in (sdk / "package/feeds/lochnair").iterdir()
                      if (path / "Makefile").is_file())
    if not packages:
        raise ValueError("No installed lochnair feed recipes found")
    return packages


def initialize_feeds(sdk, feed):
    # Respect an SDK's feeds.conf if present; otherwise retain its default feeds.
    config = sdk / "feeds.conf"
    if not config.exists():
        shutil.copyfile(sdk / "feeds.conf.default", config)
    with config.open("a") as output:
        output.write(f"\nsrc-link lochnair {feed}\n")
    subprocess.run(["./scripts/feeds", "update", "-a"], cwd=sdk, check=True)
    # This installs the local recipes AND their recursive upstream dependencies.
    subprocess.run(["./scripts/feeds", "install", "-a", "-p", "lochnair"], cwd=sdk, check=True)
    if (sdk / ".config").exists():
        subprocess.run(
            [
                "sed", "-i",
                "s/^CONFIG_RUST_SCCACHE=y$/# CONFIG_RUST_SCCACHE is not set/",
                ".config",
            ],
            cwd=sdk,
            check=True,
        )
    subprocess.run(["make", "defconfig"], cwd=sdk, check=True)


def build_plan(sdk, feed, packages, rust):
    metadata = package_metadata((sdk / 'tmp/.packageinfo').read_text())
    recipes = []
    for name in packages:
        makefile = sdk / 'package/feeds/lochnair' / name / 'Makefile'
        kind, needs_rust = recipe_kind(makefile)
        outputs = metadata.get(f'package/feeds/lochnair/{name}/Makefile')
        if not outputs:
            raise ValueError(f'No evaluated package metadata for {name}')
        recipe = {'name': name, 'kind': kind, 'rust': needs_rust,
                  'source': str(makefile.resolve().relative_to(feed.resolve())),
                  'source_sha256': digest(makefile), 'status': 'pending', 'packages': []}
        for output in outputs:
            if output.get('Build-Only') == '1':
                continue
            # None of this feed's userspace outputs currently use ABI suffixes.
            # Fail closed rather than guess a future library's binary filename.
            if kind == 'userspace' and output.get('ABI-Version'):
                raise ValueError(f'ABI-suffixed output needs explicit support: {name}')
            # Kernel DUMP metadata contains <LINUX_VERSION>, resolved only at build time.
            # It is diagnostic metadata, never a public repository filename.
            version = (component(output['Version']) if kind == 'userspace'
                       else output['Version'])
            package = {'name': component(output['Package']),
                       'version': version, 'status': 'pending',
                       'depends': output.get('Depends', ''),
                       'menu_depends': output.get('Menu-Depends', '')}
            if needs_rust and not rust:
                package.update(status='skipped', reason='sdk-without-rust')
            recipe['packages'].append(package)
        if not recipe['packages']:
            raise ValueError(f'No binary outputs for {name}')
        recipes.append(recipe)
    # Explicitly request every variant before Kconfig evaluates architecture support.
    with (sdk / '.config').open('a') as config:
        for recipe in recipes:
            for package in recipe['packages']:
                if package['status'] == 'pending':
                    config.write(f'\nCONFIG_PACKAGE_{package["name"]}=m\n')
    subprocess.run(['make', 'defconfig'], cwd=sdk, check=True)
    selected = set((sdk / '.config').read_text().splitlines())
    for recipe in recipes:
        for package in recipe['packages']:
            if package['status'] != 'pending':
                continue
            symbol = f'CONFIG_PACKAGE_{package["name"]}'
            if not ({f'{symbol}=m', f'{symbol}=y'} & selected):
                package.update(status='skipped', reason='kconfig-unavailable')
        if all(p['status'] == 'skipped' for p in recipe['packages']):
            recipe.update(status='skipped', reason='all-outputs-intentionally-unsupported')
    return recipes


def compile_packages(sdk, report, report_path, summary):
    results = []
    for recipe in report['recipes']:
        name = recipe['name']
        if recipe['status'] == 'skipped':
            results.append(f'| {name} | skipped (see report.json for reasons) |\n')
            continue
        print(f'::group::Build {name}', flush=True)
        target = f'package/feeds/lochnair/{name}/compile'
        result = subprocess.run(['make', target], cwd=sdk)
        status = 'passed'
        if result.returncode:
            print(f'Retrying {name} with verbose diagnostics', flush=True)
            result = subprocess.run(['make', target, 'V=sc', '-j1'], cwd=sdk)
            status = 'passed on verbose retry'
        recipe['status'] = 'failed' if result.returncode else 'built'
        if result.returncode:
            status = 'FAILED'
            level = 'warning' if recipe['kind'] == 'target-specific' else 'error'
            print(f'::{level} title=Package build failed::{name}', flush=True)
        for package in recipe['packages']:
            if package['status'] == 'pending':
                package['status'] = recipe['status']
        write_json(report_path, report)
        results.append(f'| {name} | {status} |\n')
        print('::endgroup::', flush=True)
    with summary.open('a') as output:
        output.write('## Package builds\n\n| Recipe | Result |\n| --- | --- |\n')
        output.writelines(results)


def collect_packages(sdk, output, report):
    version, arch, target = report['version'], report['package_arch'], report['target']
    repository = output / 'repositories' / version / arch
    specific = output / 'target-specific' / version / target / 'packages'
    targets = sdk / 'bin/targets'
    report['target_specific_errors'] = []
    if targets.is_dir():
        try:
            shutil.copytree(targets, output / 'target-specific' / version,
                            dirs_exist_ok=True, symlinks=True)
        except (OSError, shutil.Error) as error:
            report['target_specific_errors'].append(str(error))
            print('::warning::Could not collect all target-specific diagnostics', flush=True)
    source = sdk / 'bin/packages' / arch / 'lochnair'
    expected = {}
    target_packages = {}
    for recipe in report['recipes']:
        for package in recipe['packages']:
            if recipe['kind'] == 'target-specific':
                target_packages[package['name']] = (recipe, package)
                continue
            name, ver = package['name'], package['version']
            filename = (f'{name}-{ver}.apk' if report['format'] == 'apk'
                        else f'{name}_{ver}_{arch}.ipk')
            package['filename'] = filename
            expected[filename] = (recipe, package)
    report['files'] = {}
    for path in sorted(source.glob('*')):
        if path.suffix not in ('.apk', '.ipk'):
            continue
        entry = expected.get(path.name)
        if entry is None:
            # Match known target outputs by name, not their unresolved DUMP version.
            separator = '-' if path.suffix == '.apk' else '_'
            entry = next((target_packages[name] for name in sorted(
                target_packages, key=len, reverse=True)
                if path.name.startswith(name + separator)), None)
        if entry is None:
            raise ValueError(f'Unexpected local feed output: {path.name}')
        recipe, package = entry
        if path.is_symlink() or not path.is_file() or targets.resolve() in path.resolve().parents:
            if recipe['kind'] == 'target-specific':
                report['target_specific_errors'].append(f'Not a regular target artifact: {path.name}')
                continue
            raise ValueError(f'Expected regular local feed output: {path}')
        destination = specific if recipe['kind'] == 'target-specific' else repository
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination / path.name)
        if recipe['kind'] == 'userspace':
            if package['status'] != 'built':
                raise ValueError(f'Output present for unsuccessful/skipped package: {path.name}')
            report['files'][path.name] = digest(path)
    for filename, (recipe, package) in expected.items():
        if package['status'] == 'built' and not (source / filename).is_file():
            package.update(status='failed', reason='missing-output-after-success')
            recipe['status'] = 'failed'
    eligible = [r for r in report['recipes'] if r['kind'] == 'userspace']
    failed = any(r['status'] not in ('built', 'skipped') for r in eligible)
    report['eligibility'] = ('failed' if failed else 'ready' if report['files'] else 'empty')
    report['complete'] = not failed
    return repository


def generate_repository(sdk, repository, report):
    if report['format'] != 'apk' or not report['files']:
        return  # 24.10 is downloadable raw IPKs only, never an IPK repository.
    apk = sdk / 'staging_dir/host/bin/apk'
    files = sorted(report['files'])
    subprocess.run([str(apk), 'verify', '--allow-untrusted', *files],
                   cwd=repository, check=True)
    subprocess.run([str(apk), 'mkndx', '--root', str(sdk), '--keys-dir', str(sdk),
                    '--allow-untrusted', '--output', 'packages.adb', *files],
                   cwd=repository, check=True)
    expected = {p['filename']: (p['name'], p['version']) for r in report['recipes']
                if r['kind'] == 'userspace' for p in r['packages'] if p['status'] == 'built'}
    validate_index(apk_dump(apk, repository / 'packages.adb'), expected, report['package_arch'])


def main():
    sdk = Path.cwd()
    workspace = Path(os.environ['GITHUB_WORKSPACE'])
    version, arch, target = (os.environ[k] for k in ('OPENWRT_VERSION', 'PACKAGE_ARCH', 'SDK_TARGET'))
    public_release(version)
    component(arch)
    if len(target.split('/')) != 2:
        raise ValueError('Expected board/subtarget')
    for part in target.split('/'):
        component(part)
    report_path = workspace / 'output/repositories' / version / arch / 'report.json'
    if sys.argv[1] == 'build':
        initialize_feeds(sdk, workspace / 'feed')
        packages = discover_packages(sdk)
        recipes = build_plan(sdk, workspace / 'feed', packages,
                             os.environ.get('SDK_HAS_RUST', 'true') == 'true')
        config = (sdk / '.config').read_text().splitlines()
        if f'CONFIG_TARGET_ARCH_PACKAGES="{arch}"' not in config:
            raise ValueError('SDK target package architecture differs from matrix')
        apk = 'CONFIG_USE_APK=y' in config
        if apk != public_release(version):
            raise ValueError('SDK package format does not match release policy')
        report = {'schema': 1, 'version': version, 'package_arch': arch, 'target': target,
                  'image': os.environ['SDK_IMAGE'], 'rust': os.environ['SDK_HAS_RUST'] == 'true',
                  'commit': os.environ['GITHUB_SHA'], 'run_id': os.environ['GITHUB_RUN_ID'],
                  'run_attempt': os.environ['GITHUB_RUN_ATTEMPT'],
                  'format': 'apk' if apk else 'ipk', 'complete': False, 'recipes': recipes}
        write_json(report_path, report)
        compile_packages(sdk, report, report_path, Path(os.environ['GITHUB_STEP_SUMMARY']))
        # Kernel failures are diagnostic only. Collection checks every expected output.
        return int(any(r['status'] == 'failed' and r['kind'] == 'userspace' for r in recipes))
    if sys.argv[1] == 'repository':
        import json
        report = json.loads(report_path.read_text())
        try:
            repository = collect_packages(sdk, workspace / 'output', report)
            generate_repository(sdk, repository, report)
        except Exception:
            report.update(complete=False, eligibility='failed')
            raise
        finally:
            write_json(report_path, report)
        return int(not report['complete'])
    raise ValueError(f'Unknown command: {sys.argv[1]}')


if __name__ == '__main__':
    sys.exit(main())
