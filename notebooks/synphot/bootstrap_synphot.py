
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


INSTALL_FILES = {'synphot': {'version': '1.6.0', 'data_url': ['https://archive.stsci.edu/hlsps/reference-atlases/hlsp_reference-atlases_hst_multi_everything_multi_v18_sed.tar', 'https://archive.stsci.edu/hlsps/reference-atlases/hlsp_reference-atlases_hst_multi_star-galaxy-models_multi_v3_synphot2.tar', 'https://archive.stsci.edu/hlsps/reference-atlases/hlsp_reference-atlases_hst_multi_castelli-kurucz-2004-atlas_multi_v2_synphot3.tar', 'https://archive.stsci.edu/hlsps/reference-atlases/hlsp_reference-atlases_hst_multi_kurucz-1993-atlas_multi_v2_synphot4.tar', 'https://archive.stsci.edu/hlsps/reference-atlases/hlsp_reference-atlases_hst_multi_pheonix-models_multi_v3_synphot5.tar', 'https://archive.stsci.edu/hlsps/reference-atlases/hlsp_reference-atlases_hst_multi_calibration-spectra_multi_v13_synphot6.tar', 'https://archive.stsci.edu/hlsps/reference-atlases/hlsp_reference-atlases_jwst_multi_etc-models_multi_v1_synphot7.tar', 'https://archive.stsci.edu/hlsps/reference-atlases/hlsp_reference-atlases_hst_multi_modewave_multi_v1_synphot8.tar', 'https://archive.stsci.edu/hlsps/reference-atlases/hlsp_reference-atlases_hst_multi_other-spectra_multi_v2_sed.tar'], 'environment_variable': 'PYSYN_CDBS', 'install_path': '${HOME}/refdata/', 'data_path': 'grp/redcat/trds/'}, 'stpsf': {'version': '2.1.0', 'data_url': ['https://stsci.box.com/shared/static/kqfolg2bfzqc4mjkgmujo06d3iaymahv.gz'], 'environment_variable': 'STPSF_PATH', 'install_path': '${HOME}/refdata/', 'data_path': 'stpsf-data'}}
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
