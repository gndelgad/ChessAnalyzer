#!/usr/bin/env bash

set -e

echo "Downloading Stockfish..."
curl -L https://stockfishchess.org/files/stockfish_15.1_linux_x64_avx2.zip -o stockfish.zip

unzip stockfish.zip
mv stockfish_15.1_linux_x64_avx2/stockfish stockfish
chmod +x stockfish

echo "Stockfish ready."
