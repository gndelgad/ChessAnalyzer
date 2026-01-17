#!/usr/bin/env bash

set -e

echo "Downloading Stockfish (Linux x86_64 AVX2)..."

curl -L \
  https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-ubuntu-x86-64-avx2.tar \
  -o stockfish.tar

# Wait until the file exists and is fully downloaded
while [ ! -s stockfish.tar ]; do
  sleep 1
done

echo "Extracting Stockfish..."
tar -xf stockfish.tar


STOCKFISH_BIN="stockfish/stockfish-ubuntu-x86-64-avx2"


mv "$STOCKFISH_BIN" stockfish-bin
rm -r stockfish
mv stockfish-bin stockfish
chmod +x stockfish

echo "Stockfish installed successfully"
