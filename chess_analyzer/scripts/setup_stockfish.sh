#!/usr/bin/env bash

set -e

echo "Downloading Stockfish (Linux x86_64 AVX2)..."

curl -L \
  https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-ubuntu-x86-64-avx2.tar \
  -o stockfish.tar

echo "Extracting Stockfish..."
tar -xf stockfish.tar

# Find the stockfish binary inside the extracted folder
STOCKFISH_BIN=$(find . -type f -name "stockfish" | head -n 1)

if [ -z "$STOCKFISH_BIN" ]; then
  echo "Stockfish binary not found!"
  exit 1
fi

echo "Found Stockfish at $STOCKFISH_BIN"

mv "$STOCKFISH_BIN" stockfish
chmod +x stockfish

echo "Stockfish installed successfully"
