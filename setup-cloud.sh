#!/usr/bin/env bash
set -euo pipefail
cd /workspace/SpeechA/proyecto/MRS_Speech_Analytics_v3.6.19_Revision
export UV_CACHE_DIR=/workspace/.cache/uv
export UV_PYTHON_INSTALL_DIR=/workspace/.runtimes/python
export UV_PYTHON_BIN_DIR=/workspace/.runtimes/bin
export PIP_CACHE_DIR=/workspace/.cache/pip
uv python install 3.10.22
if [ ! -x /workspace/SpeechA/.venv/bin/python ]; then
  uv venv --python /workspace/.runtimes/python/cpython-3.10-linux-x86_64-gnu/bin/python3.10 /workspace/SpeechA/.venv
fi
/workspace/SpeechA/.venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 10)'
uv pip install --python /workspace/SpeechA/.venv/bin/python -r requirements-dev.txt -c constraints-tested.txt
/workspace/SpeechA/.venv/bin/python -m ensurepip --upgrade
/workspace/SpeechA/.venv/bin/python -c 'import openpyxl, av, imageio_ffmpeg; from faster_whisper import WhisperModel; from app.services.analytics_service import AnalyticsService; print("Development dependencies available")'
