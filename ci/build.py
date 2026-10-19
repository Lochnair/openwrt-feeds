"""Build installed feed recipes and stage unsigned userspace repositories."""

import gzip
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


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


def is_rust_recipe(makefile):
    source = "\n".join(line.split("#", 1)[0] for line in makefile.read_text().splitlines())
    source = source.replace("\\\n", " ")
    return bool(re.search(r"\brust/host\b|\brust-package\.mk\b|\bBuild/Compile/Cargo\b|\bRustBinPackage\b",
                          source))


def compile_packages(sdk, packages, summary, rust=True):
    failed = []
    results = []
    for package in packages:
        if not rust and is_rust_recipe(sdk / "package/feeds/lochnair" / package / "Makefile"):
            reason = "SKIPPED (Rust recipe; official SDK has no prebuilt Rust toolchain)"
            print(f"{package}: {reason}", flush=True)
            results.append(f"| {package} | {reason} |\n")
            continue
        target = f"package/feeds/lochnair/{package}/compile"
        print(f"::group::Build {package}", flush=True)
        result = subprocess.run(["make", target], cwd=sdk)
        status = "passed"
        if result.returncode:
            print(f"Retrying {package} with verbose diagnostics", flush=True)
            result = subprocess.run(["make", target, "V=sc", "-j1"], cwd=sdk)
            status = "passed on verbose retry"
        if result.returncode:
            failed.append(package)
            status = "FAILED"
            print(f"::error title=Package build failed::{package}", flush=True)
        results.append(f"| {package} | {status} |\n")
        print("::endgroup::", flush=True)
    with summary.open("a") as output:
        output.write("## Package builds\n\n| Recipe | Result |\n| --- | --- |\n")
        output.writelines(results)
    return failed


def collect_packages(sdk, output, version, arch, target):
    repository = output / "repositories" / version / arch
    specific = output / "target-specific" / version / target
    targets = sdk / "bin/targets"
    if targets.is_dir():
        # Preserve original board/subtarget paths, separate from repositories.
        shutil.copytree(targets, output / "target-specific" / version, dirs_exist_ok=True)
    source = sdk / "bin/packages" / arch / "lochnair"
    count = 0
    for package in sorted(source.glob("*")):
        if package.suffix not in (".ipk", ".apk"):
            continue
        # Never follow a feed symlink into bin/targets (or any other directory).
        if (package.is_symlink() or not package.is_file()
                or targets.resolve() in package.resolve().parents):
            raise ValueError(f"Expected a regular package file: {package}")
        destination = repository
        if package.name.startswith(("kmod-", "kernel_", "kernel-")):
            destination = specific / "packages"
        else:
            count += 1
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(package, destination / package.name)
    if not count:
        raise ValueError(f"No userspace packages found in {source}")
    return repository


def generate_repository(sdk, repository):
    # Use the SDK's effective package format, including explicit older releases.
    apk = "CONFIG_USE_APK=y" in (sdk / ".config").read_text().splitlines()
    expected, unexpected = (".apk", ".ipk") if apk else (".ipk", ".apk")
    if list(repository.glob(f"*{unexpected}")) or not list(repository.glob(f"*{expected}")):
        raise ValueError(f"Repository packages do not match SDK format {expected}")
    env = dict(os.environ)
    env["PATH"] = str(sdk / "staging_dir/host/bin") + os.pathsep + env["PATH"]
    env["MKHASH"] = str(sdk / "staging_dir/host/bin/mkhash")
    if apk:
        subprocess.run([str(sdk / "staging_dir/host/bin/apk"), "mkndx",
                        "--root", str(sdk), "--keys-dir", str(sdk), "--allow-untrusted",
                        "--output", "packages.adb",
                        *[p.name for p in sorted(repository.glob("*.apk"))]],
                       cwd=repository, env=env, check=True)
        if not (repository / "packages.adb").stat().st_size:
            raise ValueError("Empty APK index")
    else:
        manifest = subprocess.check_output([str(sdk / "scripts/ipkg-make-index.sh"), "."],
                                           cwd=repository, env=env)
        indexed = sum(line.startswith(b"Package: ") for line in manifest.splitlines())
        if indexed != len(list(repository.glob("*.ipk"))):
            raise ValueError("opkg index did not include every staged package")
        (repository / "Packages.manifest").write_bytes(manifest)
        packages = b"\n".join(line for line in manifest.split(b"\n") if not line.startswith(
            (b"Maintainer:", b"LicenseFiles:", b"Source:", b"SourceName:",
             b"Require-User:", b"SourceDateEpoch:")))
        (repository / "Packages").write_bytes(packages)
        (repository / "Packages.gz").write_bytes(gzip.compress(packages, mtime=0))


def main():
    sdk = Path.cwd()
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    if sys.argv[1] == "build":
        initialize_feeds(sdk, workspace / "feed")
        packages = discover_packages(sdk)
        print(f"Discovered recipes: {', '.join(packages)}", flush=True)
        failed = compile_packages(sdk, packages, Path(os.environ["GITHUB_STEP_SUMMARY"]),
                                  rust=os.environ.get("SDK_HAS_RUST", "true") == "true")
        return int(bool(failed))
    if sys.argv[1] == "repository":
        repository = collect_packages(sdk, workspace / "output", os.environ["OPENWRT_VERSION"],
                                      os.environ["PACKAGE_ARCH"], os.environ["SDK_TARGET"])
        generate_repository(sdk, repository)
        return 0
    raise ValueError(f"Unknown command: {sys.argv[1]}")


if __name__ == "__main__":
    sys.exit(main())
