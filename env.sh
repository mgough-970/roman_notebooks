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
fi

# Create necessary directories
mkdir -p "$CRDS_PATH"
mkdir -p "$PYSYN_CDBS"

echo "Roman notebook environment variables set successfully!"
echo "Variables will be available in subsequent GitHub Actions steps."
