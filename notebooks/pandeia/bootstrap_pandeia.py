
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import os
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path


INSTALL_FILES = {'pandeia': {'version': 2026.1, 'data_url': ['https://stsci.box.com/shared/static/0qjvuqwkurhx1xd13i63j760cosep9wh.gz'], 'environment_variable': 'pandeia_refdata', 'install_path': '${HOME}/refdata/', 'data_path': 'pandeia_data-2026.1-roman'}}
OTHER_VARIABLES = {'CRDS_SERVER_URL': 'https://roman-crds.stsci.edu', 'CRDS_CONTEXT': 'roman_0041.pmap', 'CRDS_PATH': '${HOME}/crds_cache'}


def expand_vars(value: str) -> str:
    return os.path.expandvars(value)


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} -> {dest}")
    urllib.request.urlretrieve(url, dest)


def is_supported_archive(path: Path) -> bool:
    suffixes = "".join(path.suffixes).lower()
    return (
        suffixes.endswith(".tar")
        or suffixes.endswith(".tgz")
        or suffixes.endswith(".tar.gz")
        or suffixes.endswith(".gz")
    )


def extract_archive(archive_path: Path, extract_to: Path) -> None:
    print(f"Extracting {archive_path} -> {extract_to}")
    extract_to.mkdir(parents=True, exist_ok=True)

    # Try tar first regardless of filename extension.
    # This handles files like "...something.gz" that are actually tar.gz archives.
    try:
        with tarfile.open(archive_path, "r:*") as tf:
            tf.extractall(path=extract_to)
        return
    except tarfile.ReadError:
        pass

    # Fall back to plain gzip single-file extraction
    suffixes = "".join(archive_path.suffixes).lower()
    if suffixes.endswith(".gz"):
        output_path = extract_to / archive_path.stem
        with gzip.open(archive_path, "rb") as src, open(output_path, "wb") as dst:
            shutil.copyfileobj(src, dst)
        return

    raise RuntimeError(f"Unsupported archive format: {archive_path}")


def ensure_dataset(name: str, spec: dict[str, object], resolved_env: dict[str, str]) -> None:
    install_path = Path(expand_vars(str(spec["install_path"]))).expanduser()
    data_path = str(spec["data_path"])
    env_var = str(spec["environment_variable"])
    urls = list(spec["data_url"])

    final_path = install_path / data_path
    install_path.mkdir(parents=True, exist_ok=True)

    if final_path.exists():
        print(f"[skip] {name} already present at {final_path}")
    else:
        with tempfile.TemporaryDirectory(dir=str(install_path)) as tmpdir:
            tmpdir_path = Path(tmpdir)
            downloads_dir = tmpdir_path / "downloads"
            downloads_dir.mkdir(parents=True, exist_ok=True)

            for idx, url in enumerate(urls, start=1):
                filename = Path(url).name or f"{name}_{idx}.download"
                archive_path = downloads_dir / filename

                download_file(url, archive_path)

                if not is_supported_archive(archive_path):
                    raise RuntimeError(f"Downloaded file is not a supported archive: {archive_path}")

                extract_archive(archive_path, install_path)

        if not final_path.exists():
            # Helpful debug output
            print(f"Expected final path was not created: {final_path}")
            print(f"Contents of install path {install_path}:")
            for child in sorted(install_path.iterdir()):
                print(f" - {child}")
            raise RuntimeError(
                f"{name} data downloaded but expected directory not found: {final_path}"
            )

        print(f"Installed {name} into {final_path}")

    resolved_env[env_var] = str(final_path)
    os.environ[env_var] = str(final_path)
    print(f"Set {env_var}={final_path}")


def set_other_variables(resolved_env: dict[str, str]) -> None:
    for key, value in OTHER_VARIABLES.items():
        expanded = expand_vars(str(value))
        resolved_env[key] = expanded
        os.environ[key] = expanded
        print(f"Set {key}={expanded}")


def write_env_file(env_path: Path, env_map: dict[str, str]) -> None:
    env_path.parent.mkdir(parents=True, exist_ok=True)

    with env_path.open("w", encoding="utf-8") as f:
        for key, value in env_map.items():
            f.write(f"{key}={value}\n")

    print(f"Wrote environment file: {env_path}")


def bootstrap(write_env_file_path: str | None = None) -> None:
    resolved_env: dict[str, str] = {}

    set_other_variables(resolved_env)

    for dataset_name, dataset_spec in INSTALL_FILES.items():
        ensure_dataset(dataset_name, dataset_spec, resolved_env)

    if write_env_file_path:
        write_env_file(Path(write_env_file_path), resolved_env)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-env-file", default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    bootstrap(args.write_env_file)
