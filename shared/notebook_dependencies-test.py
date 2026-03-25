import os
import tarfile
import tempfile
from urllib.parse import urlparse

import requests
import yaml


def _download_file_stream(url, destination, chunk_size=1024 * 1024, verbose=True):
    """
    Stream a remote file to disk in chunks instead of loading it all into memory.
    """
    if verbose:
        print(f"\tStreaming download: {url}")
        print(f"\tSaving to: {destination}")

    with requests.get(url, stream=True, allow_redirects=True, timeout=(30, 300)) as response:
        response.raise_for_status()

        with open(destination, "wb") as fh:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:  # filter out keep-alive chunks
                    fh.write(chunk)


def _load_yaml(dependencies):
    """
    Load the dependency YAML from either a local file or a URL.
    """
    if os.path.exists(dependencies):
        with open(dependencies, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)["install_files"]

    with requests.get(dependencies, stream=True, allow_redirects=True, timeout=(30, 120)) as response:
        response.raise_for_status()
        return yaml.safe_load(response.text)["install_files"]


def install_files(
    dependencies="https://raw.githubusercontent.com/mgough-970/roman_notebooks/refs/heads/main/refdata_dependencies.yaml",
    verbose=True,
    packages=None,
):
    """
    PURPOSE
    -------
    Retrieve ancillary reference data files needed for specific Python packages:
        - pandeia
        - STIPS
        - STPSF
        - synphot

    This code checks for each package that the appropriate environment variable exists
    and, if not, downloads the reference data to the path indicated in the YAML
    instructions and returns instructions to the user for how to set the variables.

    INPUTS
    ------
    dependencies (str): A URL or local path to the YAML definition file for the data
    dependencies.

    verbose (bool): Print messages to stdout.

    packages (None, list, str): List of packages for which to install reference data.
        Can be a list of package names, a comma-separated string, or None.

    RETURNS
    -------
    result (dict): A dictionary keyed by environment variable name, with path info.
    """
    yf = _load_yaml(dependencies)

    if packages:
        if isinstance(packages, str):
            packages = [p.strip() for p in packages.split(",") if p.strip()]

        keys = list(yf.keys())
        skips = [k for k in keys if k not in packages]
        for s in skips:
            yf.pop(s, None)

    home = os.environ["HOME"]
    result = {}

    for package, config in yf.items():
        envvar = config["environment_variable"]

        try:
            existing = os.environ[envvar]
            if existing == "***unset***":
                raise KeyError("UNSET PATH")

            if verbose:
                print(f"Found {package} path {existing}")

            result[envvar] = {"path": existing, "pre_installed": True}
            continue

        except KeyError:
            if verbose:
                print(f"Did not find {package} data in environment, setting it up...")

        env_path = config["install_path"]
        path_parts = env_path.split("/")
        path_parts = [home if "${HOME}" in part else part for part in path_parts]
        final_path = "/".join(path_parts)

        os.makedirs(final_path, exist_ok=True)

        urls = config["data_url"]
        total_files = len(urls)

        if verbose:
            print("\tDownloading and uncompressing file...")
            print(f"\tFound {total_files} data URL(s) to download and install...")

        for i, url in enumerate(urls, start=1):
            if verbose:
                print(f"\tWorking on file {i} out of {total_files}")

            parsed = urlparse(url)
            raw_name = os.path.basename(parsed.path) or f"download_{i}.tar.gz"

            # Write archive to a temp file inside the install path.
            with tempfile.NamedTemporaryFile(
                dir=final_path,
                prefix="download_",
                suffix=f"_{raw_name}",
                delete=False,
            ) as tmp:
                archive_path = tmp.name

            try:
                _download_file_stream(url, archive_path, verbose=verbose)

                with tarfile.open(archive_path, mode="r:*") as tarball:
                    tarball.extractall(path=final_path, filter=None)

            finally:
                if os.path.exists(archive_path):
                    os.remove(archive_path)

        installed_data_path = os.path.join(final_path, config["data_path"])

        if verbose:
            print("\tUpdate environment variable with the following:")
            print(f"\t\texport {envvar}='{installed_data_path}'")

        result[envvar] = {"path": installed_data_path, "pre_installed": False}

    return result


def setup_env(result):
    """
    Update environment variables (if necessary) and print reference data paths.
    """
    print("Reference data paths set to:")
    for k, v in result.items():
        if not v["pre_installed"]:
            os.environ[k] = v["path"]
        print(f"\t{k} = {v['path']}")


if __name__ == "__main__":
    install_files()
