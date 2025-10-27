#!/usr/bin/env python3
"""
ndd_streaming.py — low-RAM installer for reference data tarballs.

Key features:
- Streams HTTP responses straight into tarfile (mode="r|*") to avoid RAM spikes
- Path traversal guard while extracting tar members
- Retries + timeouts for reliability
- Honors pre-existing env vars to skip downloads (notebooks can set & reuse)
- Expands ${HOME} and other env vars in install paths
"""

import os
import io
import tarfile
import yaml
import requests
from typing import Dict, Any, Iterable, Optional
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


DEFAULT_DEPS = (
    "https://raw.githubusercontent.com/spacetelescope/roman_notebooks/"
    "refs/heads/main/refdata_dependencies.yaml"
)

# -------- HTTP utils (retries + timeouts) -------- #

def _requests_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


# -------- tar safety (prevent path traversal) -------- #

def _safe_members(members: Iterable[tarfile.TarInfo]) -> Iterable[tarfile.TarInfo]:
    """
    Yield only safe members (no absolute paths, no '..' escapes).
    """
    for m in members:
        # Normalize member path
        name = m.name
        norm = os.path.normpath(name).lstrip(os.sep)
        if norm.startswith("..") or os.path.isabs(name):
            # Skip unsafe member
            continue
        # rewrite name to normalized relative path
        m.name = norm
        yield m


# -------- core installer -------- #

def _expand_install_path(path_template: str) -> str:
    # Expand ${HOME} and $VARS, then expanduser (~)
    path = os.path.expandvars(path_template.replace("${HOME}", os.environ.get("HOME", "")))
    path = os.path.expanduser(path)
    return path


def _already_installed(final_path: str) -> bool:
    # Consider installed if directory exists and is non-empty
    return os.path.isdir(final_path) and any(True for _ in os.scandir(final_path))


def _stream_extract_tar_from_url(url: str, dest_dir: str, session: requests.Session, timeout: int = 300) -> None:
    """
    Open URL with streaming and feed directly to tarfile in streaming mode (r|*),
    so we never hold the entire tar in memory or on disk.
    """
    with session.get(url, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()
        # tarfile can read a file-like object; resp.raw is a urllib3 HTTPResponse
        # Use streaming mode to avoid seeking requirements.
        with tarfile.open(fileobj=resp.raw, mode="r|*") as tar:
            tar.extractall(path=dest_dir, members=_safe_members(tar))


def install_files(
    dependencies: str = DEFAULT_DEPS,
    verbose: bool = False
) -> Dict[str, Dict[str, Any]]:
    """
    Retrieve ancillary reference data files needed for specific packages (e.g., synphot, STIPS).
    - Streams tarballs to avoid RAM blowups on CI runners.
    - Returns a dict: {ENV_VAR: {"path": <final_path>, "pre_installed": bool}}

    If the YAML path exists locally, it is read from disk; otherwise it's treated as a URL.
    The YAML schema is the same as in the roman_notebooks repo (install_files section).
    """
    session = _requests_session()

    # --- Load YAML (small; safe to read into memory) ---
    if os.path.exists(dependencies):
        if verbose:
            print(f"[ndd] Using local YAML: {dependencies}")
        with open(dependencies, "r") as f:
            yf = yaml.safe_load(f)["install_files"]
    else:
        if verbose:
            print(f"[ndd] Fetching YAML: {dependencies}")
        r = session.get(dependencies, timeout=60)
        r.raise_for_status()
        yf = yaml.safe_load(r.content)["install_files"]

    result: Dict[str, Dict[str, Any]] = {}

    for package, cfg in yf.items():
        envvar: str = cfg["environment_variable"]
        data_urls = cfg["data_url"]
        install_path = _expand_install_path(cfg["install_path"])
        final_path = os.path.join(install_path, cfg["data_path"])

        # If env var is already set and not a sentinel, prefer it
        pre_set = os.environ.get(envvar)
        if pre_set and pre_set != "***unset***":
            if verbose:
                print(f"[ndd] Found existing {package} path via ${envvar} = {pre_set}")
            result[envvar] = {"path": pre_set, "pre_installed": True}
            continue

        # If env not set but final_path already populated, treat as pre-installed
        if _already_installed(final_path):
            if verbose:
                print(f"[ndd] {package} appears installed at {final_path} (env not set).")
            os.makedirs(install_path, exist_ok=True)
            os.environ[envvar] = final_path
            result[envvar] = {"path": final_path, "pre_installed": True}
            continue

        # Otherwise, perform a streaming install
        if verbose:
            print(f"[ndd] Installing {package} → {install_path}")
            print(f"[ndd]   Will set ${envvar} to {final_path}")
            print(f"[ndd]   {len(data_urls)} file(s) to download...")

        os.makedirs(install_path, exist_ok=True)

        for i, url in enumerate(data_urls, start=1):
            if verbose:
                print(f"[ndd]     ({i}/{len(data_urls)}) {url}")
            try:
                _stream_extract_tar_from_url(url, install_path, session=session)
            except tarfile.ReadError:
                # Some servers require full buffering; fallback: chunk to temp file, then open
                if verbose:
                    print("        Streamed tar read failed; falling back to temp file...")
                import tempfile
                with session.get(url, stream=True, timeout=300) as resp:
                    resp.raise_for_status()
                    with tempfile.NamedTemporaryFile(delete=False) as tmp:
                        for chunk in resp.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                tmp.write(chunk)
                        tmp_path = tmp.name
                try:
                    with tarfile.open(tmp_path, mode="r:*") as tar:
                        tar.extractall(path=install_path, members=_safe_members(tar))
                finally:
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

        # Export env var for current process (useful inside notebooks/CI)
        os.environ[envvar] = final_path

        if verbose:
            print(f"[ndd]   Set: export {envvar}='{final_path}'")

        result[envvar] = {"path": final_path, "pre_installed": False}

    return result


# -------- CLI / quick test -------- #

if __name__ == "__main__":
    # Run with: python ndd_streaming.py
    out = install_files(verbose=True)
    print("\nReference data paths set to:")
    for k, v in out.items():
        print(f"  {k} = {v['path']}  (pre_installed={v['pre_installed']})")

