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
#if [ ! -d "$pandeia_refdata/pandeia_data" ]; then
#  wget https://stsci.box.com/v/pandeia-data-v2025p9-roman -O /tmp/pandeia_data.zip
#  unzip /tmp/pandeia_data.zip -d "$pandeia_refdata"
#  rm /tmp/pandeia_data.zip
#fi

# Download STIPS reference data if not already present
if [ ! -d "$HOME/.stips_data" ]; then
  wget https://stsci.box.com/shared/static/8y3g2y7z9t5g6h6f5j4k3l2m1n0op9q8.zip -O /tmp/stips_data.zip
  unzip /tmp/stips_data.zip -d "$HOME/.stips_data"
  rm /tmp/stips_data.zip
fi  



echo "Roman notebook environment variables set successfully!"
echo "Variables will be available in subsequent GitHub Actions steps."
