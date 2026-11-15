#!/usr/bin/env bash
# One-time setup per machine: Python packages, the Kokoro voice model, and the brand font.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; CACHE="$HERE/.cache"; mkdir -p "$CACHE"
pip install -q kokoro-onnx soundfile numpy pillow cairosvg onnx --break-system-packages 2>/dev/null || pip install -q kokoro-onnx soundfile numpy pillow cairosvg onnx
command -v ffmpeg >/dev/null || { echo "ffmpeg is required"; exit 1; }
REL=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
[ -s "$CACHE/kokoro.onnx" ] || curl -sSL -o "$CACHE/kokoro.onnx" "$REL/kokoro-v1.0.onnx"
[ -s "$CACHE/voices.bin" ]  || curl -sSL -o "$CACHE/voices.bin"  "$REL/voices-v1.0.bin"
# Same model with its per-phoneme durations exposed as an output, for lip-sync in story Reels
[ -s "$CACHE/kokoro-timed.onnx" ] || python3 "$HERE/expose_durations.py" "$CACHE/kokoro.onnx" "$CACHE/kokoro-timed.onnx"
if [ ! -d "$CACHE/fonts/package" ]; then
  mkdir -p "$CACHE/fonts" && (cd "$CACHE/fonts" && npm pack -q @fontsource/plus-jakarta-sans >/dev/null && tar xzf ./*.tgz)
fi
echo "setup ok"
