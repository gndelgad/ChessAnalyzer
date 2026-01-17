#!/usr/bin/env bash

set -e

echo "Downloading Stockfish (Linux x86_64 AVX2)..."

curl -L \
  https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-ubuntu-x86-64-avx2.tar \
  -o stockfish.tar

echo "Extracting Stockfish..."
tar -xf stockfish.tar

# The extracted binary is named: stockfish-ubuntu-x86-64-avx2
mv stockfish-ubuntu-x86-64-avx2 stockfish

chmod +x stockfish

echo "Stockfish installed successfully"
