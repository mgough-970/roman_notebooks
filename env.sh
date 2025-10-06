#!/bin/bash
# Environment variables extracted from environment.yml
# This script sets up Roman notebook environment variables for GitHub Actions

# Set variables for current session AND future steps
export CRDS_SERVER_URL="https://roman-crds.stsci.edu"
export CRDS_PATH="${HOME}/.crds_cache"
export CRDS_CONTEXT="roman_0027.pmap"
export PYSYN_CDBS="${HOME}/.synphot_data"
export AWS_DEFAULT_REGION="us-east-1"
export OMP_NUM_THREADS="4"
export MKL_NUM_THREADS="4"
export NUMBA_NUM_THREADS="4"
export CRDS_AUTO_UPDATE_CONTEXT="false"
export CRDS_VERBOSITY="50"
export pandeia_refdata=${HOME}/data/pandeia
export STIPS_DATA_DIR="${HOME}/.stips_data"


# For GitHub Actions: Also set variables for subsequent steps
if [ -n "$GITHUB_ENV" ]; then
  echo "CRDS_SERVER_URL=${CRDS_SERVER_URL}" >> $GITHUB_ENV
  echo "CRDS_PATH=${CRDS_PATH}" >> $GITHUB_ENV
  echo "CRDS_CONTEXT=${CRDS_CONTEXT}" >> $GITHUB_ENV
  echo "PYSYN_CDBS=${PYSYN_CDBS}" >> $GITHUB_ENV
  echo "AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}" >> $GITHUB_ENV
  echo "OMP_NUM_THREADS=${OMP_NUM_THREADS}" >> $GITHUB_ENV
  echo "MKL_NUM_THREADS=${MKL_NUM_THREADS}" >> $GITHUB_ENV
  echo "NUMBA_NUM_THREADS=${NUMBA_NUM_THREADS}" >> $GITHUB_ENV
  echo "CRDS_AUTO_UPDATE_CONTEXT=${CRDS_AUTO_UPDATE_CONTEXT}" >> $GITHUB_ENV
  echo "CRDS_VERBOSITY=${CRDS_VERBOSITY}" >> $GITHUB_ENV
  echo "pandeia_refdata=${pandeia_refdata}" >> $GITHUB_ENV
  echo "STIPS_DATA_DIR=${STIPS_DATA_DIR}" >> $GITHUB_ENV
fi

# Create necessary directories
mkdir -p "$CRDS_PATH"
mkdir -p "$PYSYN_CDBS"
mkdir -p "$pandeia_refdata"

# Get the data
# Download Pandeia reference data if not already present
if [ ! -d "$pandeia_refdata/pandeia_data" ]; then
  wget "https://public.boxcloud.com/d/1/b1!s0CvRLNMMZ-5SBibFl1L_T3Tn0wNobZt9JzeerayOyk3IkvbT3bSHSvm5_Cs7wO4F0d9yzs6W0ce4EmdYn8CuwyA-zZxnKx6zO0Ggm1IR_ejDuVotP7FRa26Zz-eBZ2aDBpZ48rsmZBo1z05Tj8Ct-B2WNg40xEu7rnD4420_-M3UlMIacdnJw8zNVVB0k5usbf9-mEcNSZDu1bMdXdSBs_kYp8IM-TTvu3o_ppWhKN8AA_YdhbUepD8Ois49dn4KX8yifoUopIPSpSAh5L2U5bRLZgXh2FGboq--xGizdaIuk1pzmFgTLdbF7F6sJGzjIYeq-U23XClM_yi9jKf5v2YeGa7f35rBRB2zyaeaWLbrNYdp9y6B83B6R5gyj1PjggOlBsRP9mcac7j3w6E8ufTOlsHARhP3X0iyoDRRlp7rjqacbB8XfsSvOs_sPpx546RsZJJbz-se7zhyUqoHsjXDrEXo6DmVBy8EUElb9_tL27efO6FYIcKq55F9ZYo1PhvqSUS132E4leHDhrrykuqBe-BOFxj2B6ebIgSqfiSn3g8sV0eiblLMnDt1i9RJXBAvYoemZBt7vx6Qv3nFtHVtb6XCWMyxJgmKOao1IUf5pKtqnKcBc1nj6b6xql-4aOG62HTAXICqrsHD5o7kups2tIuccJeJH48BoRQWrVMs_Zhjs6HTaZ0z3v_ElIhpOB_tdUL9HQ4kfuXUheey5wHdLHbT402qpu8QkJIO4ptw_7ejiMwou7w3T_ZmCAYZ4FWqy1-vJ8RrQqLmkDfSEozWECzIr9ASQ1eVI-i0Ag22Pe-bXelOvrkWV1LlcQ-k7gftDJSqd6zXoK00_ltGPSaLuuf6O3FF9eaplpuysXZSr6NonQotRQr36wVbjmnKkl0Ku9T-2pvhaPYM6y0M3qIEWRv733_T4DUQQ051nDsqSw2vsJynOxpzntFPzVx101TJVWwjmv9q2vrsZ71R9o9JtvYPttfFh8Yb2lxHzysVzl5IYbuQPQ7b8AZA9OjUotmp7dtZ5B8QEzkYb7DeKIx3Z13kU3JVBCrqi7H1xt24PkYksns56z43o--K4p7UU6ZQ0u4jH4bDCW3heeivISzdV1xN_MjUVI5w_AkCOESmU0D15ZsTPdqpg1UZ9CUOGrBZlkUQFqBPE2zUXPab5CZrXxDnKsYEArLhznCsQNnpQo3CNGy7GbHJ7mD5lYW8-DhDyhX4Vc7g6wuB9ImAsJJ-daHiFCws0kTYU_1vaBDcbxsTan2aZyg-3AF5pRgnNhTRknNghK9IYPa9zGLUTDuyqI5OIS8uuiQQjMF3pQDmhU5AAt7d6ItxkfQYC3jY-O_OXoPzOmniQIR5Oec54M6am8xodg5e6Rk9MGU7MX-7JhNPbo1ceFPtcSqll6wgyvxRhE72lHYE9o_opKuiH1cx9Uw5KyEsH1XX0xFFfiQZTQaAJt6eoFq-rxVBg../download" -O /tmp/pandeia_data.zip
  mkdir "$pandeia_refdata"
  tar zxvf /tmp/pandeia_data.zip "$pandeia_refdata"
  #rm /tmp/pandeia_data.zip
fi

# Download STIPS reference data if not already present
# Note: Need to get proper direct download URL for STIPS data as well
if [ ! -d "$HOME/.stips_data" ]; then
  echo "STIPS data download URL needs to be updated with proper Box direct download link"
  # wget https://stsci.box.com/shared/static/8y3g2y7z9t5g6h6f5j4k3l2m1n0op9q8.zip -O /tmp/stips_data.zip
  # unzip /tmp/stips_data.zip -d "$HOME/.stips_data"
  # rm /tmp/stips_data.zip
fi  



echo "Roman notebook environment variables set successfully!"
echo "Variables will be available in subsequent GitHub Actions steps."
