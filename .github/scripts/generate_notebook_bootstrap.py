#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
NOTEBOOKS_DIR = REPO_ROOT / "notebooks"
REFDATA_SPEC_PATH = REPO_ROOT / "refdata_dependencies.yaml"

PACKAGE_TO_REFDATA = {
    "stpsf": ["stpsf"],
    "stsynphot": ["synphot"],
    "synphot": ["synphot"],
    "pandeia": ["pandeia"],
    "pandeia-engine": ["pandeia"],
    "stips": ["stips"],
}


BOOTSTRAP_TEMPLATE = r'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import os
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path


INSTALL_FILES = {install_files!r}
OTHER_VARIABLES = {other_variables!r}


def expand_vars(value: str) -> str:
    return os.path.expandvars(value)


def is_supported_archive(path: Path) -> bool:
    suffixes = "".join(path.suffixes).lower()
    return (
        suffixes.endswith(".tar")
        or suffixes.endswith(".tgz")
        or suffixes.endswith(".tar.gz")
        or suffixes.endswith(".gz")
    )


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {{url}} -> {{dest}}")
    urllib.request.urlretrieve(url, dest)


def extract_archive(archive_path: Path, extract_to: Path) -> None:
    print(f"Extracting {{archive_path}} -> {{extract_to}}")
    extract_to.mkdir(parents=True, exist_ok=True)

    suffixes = "".join(archive_path.suffixes).lower()

    if suffixes.endswith(".tar") or suffixes.endswith(".tgz") or suffixes.endswith(".tar.gz"):
        with tarfile.open(archive_path, "r:*") as tf:
            tf.extractall(path=extract_to)
        return

    if suffixes.endswith(".gz") and not suffixes.endswith(".tar.gz"):
        output_path = extract_to / archive_path.stem
        with gzip.open(archive_path, "rb") as src, open(output_path, "wb") as dst:
            shutil.copyfileobj(src, dst)
        return

    raise RuntimeError(f"Unsupported archive format: {{archive_path}}")


def ensure_dataset(name: str, spec: dict[str, object], resolved_env: dict[str, str]) -> None:
    install_path = Path(expand_vars(str(spec["install_path"]))).expanduser()
    data_path = str(spec["data_path"])
    env_var = str(spec["environment_variable"])
    urls = list(spec["data_url"])

    final_path = install_path / data_path
    install_path.mkdir(parents=True, exist_ok=True)

    if final_path.exists():
        print(f"[skip] {{name}} already present at {{final_path}}")
    else:
        with tempfile.TemporaryDirectory(dir=str(install_path)) as tmpdir:
            tmpdir_path = Path(tmpdir)
            downloads_dir = tmpdir_path / "downloads"
            staging_dir = tmpdir_path / "extract"
            downloads_dir.mkdir(parents=True, exist_ok=True)
            staging_dir.mkdir(parents=True, exist_ok=True)

            for idx, url in enumerate(urls, start=1):
                filename = Path(url).name or f"{name}_{idx}.download"
                archive_path = downloads_dir / filename
                download_file(url, archive_path)

                if not is_supported_archive(archive_path):
                    raise RuntimeError(f"Downloaded file is not a supported archive: {{archive_path}}")

                extract_archive(archive_path, staging_dir)

            if not final_path.exists():
                print(f"Installed {{name}} into {{install_path}}")

    resolved_env[env_var] = str(final_path)
    os.environ[env_var] = str(final_path)
    print(f"Set {{env_var}}={{final_path}}")


def set_other_variables(resolved_env: dict[str, str]) -> None:
    for key, value in OTHER_VARIABLES.items():
        expanded = expand_vars(str(value))
        resolved_env[key] = expanded
        os.environ[key] = expanded
        print(f"Set {{key}}={{expanded}}")


def write_env_file(env_path: Path, env_map: dict[str, str]) -> None:
    env_path.parent.mkdir(parents=True, exist_ok=True)
    with env_path.open("w", encoding="utf-8") as f:
        for key, value in env_map.items():
            f.write(f"{{key}}={{value}}\\n")
    print(f"Wrote environment file: {{env_path}}")


def bootstrap(write_env_file_path: str | None = None) -> None:
    resolved_env: dict[str, str] = {}
    set_other_variables(resolved_env)

    for dataset_name, dataset_spec in INSTALL_FILES.items():
        ensure_dataset(dataset_name, dataset_spec, resolved_env)

    if write_env_file_path:
        write_env_file(Path(write_env_file_path), resolved_env)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-env-file",
        default=None,
        help="Optional path to write KEY=VALUE environment variables"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        bootstrap(write_env_file_path=args.write_env_file)
    except Exception as exc:
        print(f"Bootstrap failed: {{exc}}", file=sys.stderr)
        raise
'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--notebook-name",
        required=True,
        help="Notebook filename, e.g. example.ipynb",
    )
    return parser.parse_args()


def normalize_requirement_name(line: str) -> str | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    line = line.split("#", 1)[0].strip()
    line = re.split(r"[<>=!~]", line, maxsplit=1)[0].strip()
    line = line.split("[", 1)[0].strip()

    if not line:
        return None

    return line.lower().replace("_", "-")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping at top level in {path}")
    return data


def find_notebook_by_name(notebook_name: str) -> Path:
    matches = sorted(NOTEBOOKS_DIR.rglob(notebook_name))

    if not matches:
        raise FileNotFoundError(
            f"Notebook '{notebook_name}' was not found under {NOTEBOOKS_DIR}"
        )

    if len(matches) > 1:
        match_list = "\n".join(str(p.relative_to(REPO_ROOT)) for p in matches)
        raise RuntimeError(
            f"Notebook name '{notebook_name}' is ambiguous. Multiple matches found:\n{match_list}"
        )

    return matches[0]


def load_requirements(requirements_path: Path) -> list[str]:
    packages: list[str] = []
    for raw_line in requirements_path.read_text(encoding="utf-8").splitlines():
        pkg = normalize_requirement_name(raw_line)
        if pkg:
            packages.append(pkg)
    return packages


def infer_refdata_keys(packages: list[str]) -> list[str]:
    inferred: list[str] = []
    for pkg in packages:
        for key in PACKAGE_TO_REFDATA.get(pkg, []):
            if key not in inferred:
                inferred.append(key)
    return inferred


def build_manifest(refdata_spec: dict[str, Any], selected_keys: list[str]) -> dict[str, Any]:
    install_files = refdata_spec.get("install_files", {})
    other_variables = refdata_spec.get("other_variables", {})

    if not isinstance(install_files, dict):
        raise ValueError("install_files must be a mapping")
    if not isinstance(other_variables, dict):
        raise ValueError("other_variables must be a mapping")

    selected_install_files: dict[str, Any] = {}
    missing: list[str] = []

    for key in selected_keys:
        if key in install_files:
            selected_install_files[key] = install_files[key]
        else:
            missing.append(key)

    if missing:
        raise KeyError(f"Missing refdata spec entries for inferred keys: {missing}")

    return {
        "install_files": selected_install_files,
        "other_variables": other_variables,
    }


def write_outputs(notebook_path: Path, manifest: dict[str, Any]) -> tuple[Path, Path]:
    notebook_dir = notebook_path.parent
    notebook_stem = notebook_path.stem

    manifest_path = notebook_dir / f"{notebook_stem}.refdata.yml"
    bootstrap_path = notebook_dir / f"bootstrap_{notebook_stem}.py"

    with manifest_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, sort_keys=False)

    bootstrap_code = BOOTSTRAP_TEMPLATE.format(
        install_files=manifest["install_files"],
        other_variables=manifest["other_variables"],
    )
    bootstrap_path.write_text(bootstrap_code, encoding="utf-8")
    bootstrap_path.chmod(0o755)

    return manifest_path, bootstrap_path


def main() -> None:
    args = parse_args()

    if not NOTEBOOKS_DIR.exists():
        raise FileNotFoundError(f"Expected notebooks directory at {NOTEBOOKS_DIR}")

    if not REFDATA_SPEC_PATH.exists():
        raise FileNotFoundError(f"Expected refdata spec at {REFDATA_SPEC_PATH}")

    notebook_path = find_notebook_by_name(args.notebook_name)
    notebook_dir = notebook_path.parent
    requirements_path = notebook_dir / "requirements.txt"

    if not requirements_path.exists():
        raise FileNotFoundError(
            f"No requirements.txt found in notebook directory: {notebook_dir}"
        )

    packages = load_requirements(requirements_path)
    refdata_keys = infer_refdata_keys(packages)
    refdata_spec = load_yaml(REFDATA_SPEC_PATH)
    manifest = build_manifest(refdata_spec, refdata_keys)
    manifest_path, bootstrap_path = write_outputs(notebook_path, manifest)

    print(f"Notebook found: {notebook_path.relative_to(REPO_ROOT)}")
    print(f"Requirements found: {requirements_path.relative_to(REPO_ROOT)}")
    print(f"Detected packages: {packages}")
    print(f"Inferred refdata keys: {refdata_keys}")
    print(f"Wrote manifest: {manifest_path.relative_to(REPO_ROOT)}")
    print(f"Wrote bootstrap: {bootstrap_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
