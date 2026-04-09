import os
import requests
import tarfile
import yaml
from pathlib import Path


def install_files(dependencies=None, verbose=True, packages=None):
    """
    PURPOSE
    -------
    Retrieve ancillary reference data files needed for specific Python packages:
        - pandeia
        - STIPS
        - STPSF
        - synphot
    
    This code checks for each package that the appropriate environment variable exists 
    and, if not, it downloads the reference data to the path indicated in the YAML 
    instructions and returns instructions to the user for how to set the variables.
    
    INPUTS
    ------
    dependencies (str): A URL or local path to the YAML definition file for the data 
    dependencies. The code will first check for the existence of the file locally, and 
    if it does not exist then it will assume the input is a URL. The default is the URL 
    of the file on the roman_notebooks GitHub repository. The YAML file should have the 
    following format:
            
        package_name:  # Name of the package
            version:  # Package version number for documentation
            data_url:  # URL for each tarball to pull (can provide multiple, e.g., synphot)
                - URL_1
                ...
                - URL_N
            environment_variable:  # Environment variable to check or set up (e.g., PYSYN_CDBS)
            install_path:  # Parent directory under which to install the reference data
            data_path:  # Name of the folder that the reference data exists in
                
        The variable data_path is appended to install_path to give the final path to the reference
        data in the file system.

    verbose (bool): Print messages to the standard out. Default is False.
    
    packages (None, list, str): List of packages for which to install reference data. This can
    be a list of string package names, a comma separated string of package names, or None. If None, 
    then install package reference data for all packages in the dependencies file. Default None.
        
    RETURNS
    -------
    results (dict): A dictionary for each environment variable with the value equal to the final
        path to which the variable should be set.
    """
    
    # Looks for the data dependencies file in local repository
    DEPENDENCIES_PATH = Path(__file__).parent.parent / "refdata_dependencies.yaml"

    # Check if dependencies is a local file. If not, retrieve it from the GitHub repo.
    # This allows us to not have to maintain a copy in every notebook folder.
    if not dependencies:
        dependencies = DEPENDENCIES_PATH
        if os.path.exists(dependencies):
            with open(dependencies, 'r') as f:
                yf = yaml.safe_load(f)['install_files']
        else:
            dependencies = 'https://raw.githubusercontent.com/spacetelescope/roman_notebooks/refs/heads/main/refdata_dependencies.yaml'
            req = requests.get(dependencies, allow_redirects=True)
            yf = yaml.safe_load(req.content)['install_files']
    else:
        print("file with package data information not found")

    # If only installing certain packages, check that now and limit the dictionary to
    # just those package keys.
    if packages:
        if isinstance(packages, str):
            packages = packages.split(',')

        keys = yf.keys()
        skips = [k  for k in keys if k not in packages]
        for s in skips:
            _ = yf.pop(s)

    # Loop over packages defined in the dependencies dictionary.
    home = os.environ.get('HOME', os.path.expanduser('~'))
    result = {}
    for package in yf.keys():
        envvar = yf[package]['environment_variable']
        try:
            test = os.environ[envvar]
            if test == '***unset***':
                raise KeyError('UNSET PATH')
            if verbose:
                print(f"Found {package} path {os.environ[envvar]}")
            result[envvar] = {'path': os.environ[envvar], 'pre_installed': True}
        except KeyError:
            if verbose:
                print(f"Did not find {package} data in environment, setting it up...")

            # Get the path where the data should be installed. Resolve any environment variables.
            env_path = yf[package]['install_path']
            tmp_path = env_path.split('/')
            tmp_path = [home if '${HOME}' in tp else tp for tp in tmp_path]
            final_path = '/'.join(tmp_path)

            # Check if path directory structure exists. If not, make it.
            if not os.path.isdir(final_path):
                os.makedirs(final_path)

            # Download the tarball from the URL in the YAML file and extract the files.
            tot_files = len(yf[package]['data_url'])
            if verbose:
                print(f"\tDownloading and uncompressing file...")
                print(f"\tFound {tot_files} data URL(s) to download and install...")
            for i, url in enumerate(yf[package]['data_url']):
                if verbose:
                    print(f"\tWorking on file {i+1} out of {tot_files}")
                req = requests.get(url, allow_redirects=True)
                file_name = url.split('/')[-1]
                with open(file_name, 'wb') as download_file:
                    download_file.write(req.content)
                with tarfile.open(file_name) as tarball:
                    members = tarball.getmembers()
                    tarball.extractall(path=final_path, members=members, filter='data')
                os.remove(file_name)

            # Messages to the user
            if verbose:
                print(f"\tUpdate environment variable with the following:")
                print(f"\t\texport {yf[package]['environment_variable']}='{os.path.join(final_path, yf[package]['data_path'])}'")
            result[envvar] = {'path': os.path.join(final_path, yf[package]['data_path']), 'pre_installed': False}

    # Return the environment variables and paths to the user as a dictionary so that they
    # can be set programmatically.
    return result

def _load_yaml(dependencies=None):
    """Load the refdata_dependencies YAML from a local path or URL."""
    DEPENDENCIES_PATH = Path(__file__).parent.parent / "refdata_dependencies.yaml"
    if not dependencies:
        dependencies = DEPENDENCIES_PATH
    if os.path.exists(dependencies):
        with open(dependencies, 'r') as f:
            return yaml.safe_load(f)
    else:
        if not dependencies or dependencies == DEPENDENCIES_PATH:
            dependencies = 'https://raw.githubusercontent.com/spacetelescope/roman_notebooks/refs/heads/main/refdata_dependencies.yaml'
        req = requests.get(dependencies, allow_redirects=True)
        return yaml.safe_load(req.content)


def setup_env(result, dependencies=None, verbose=True):
    # Update environment variables (if necessary) and print reference data paths
    print('Reference data paths set to:')
    for k, v in result.items():
        if not v['pre_installed']:
            os.environ[k] = v['path']
        print(f"\t{k} = {v['path']}")

    # Also apply other_variables from the YAML (e.g. CRDS env vars)
    yf = _load_yaml(dependencies)
    other = yf.get('other_variables', {})
    home = os.environ.get('HOME', os.path.expanduser('~'))
    for key, value in other.items():
        value = str(value).replace('${HOME}', home)
        if key not in os.environ:
            os.environ[key] = value
            if verbose:
                print(f"\t{key} = {value}")
        elif verbose:
            print(f"\t{key} = {os.environ[key]} (pre-set, not overwritten)")


if __name__ == 'main':
    
    install_files()
