#!/usr/bin/env bash

set -e

#echo "Updating certificates..."

#apt-get update && apt-get install -y ca-certificates
#update-ca-certificates

echo "=== Checking OpenSSL Version ==="
openssl version

#echo "=== Checking CA Certificates ==="
# List CA certificates (optional)
#ls -l /etc/ssl/certs/ | head -n 10
#echo ""

echo "=== Testing connection to Chess.com API ==="
# Run curl in verbose mode, capturing both stdout and stderr
curl_output=$(curl -v https://api.chess.com/pub/player/magnuscarlsen 2>&1)
echo "$curl_output"

echo "Downloading Stockfish (Linux x86_64 AVX2)..."

curl -L \
  https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-ubuntu-x86-64-avx2.tar \
  -o stockfish.tar

# Wait until the file exists and is fully downloaded
#while [ ! -s stockfish.tar ]; do
#  sleep 1
#done

echo "Extracting Stockfish..."
tar -xf stockfish.tar


STOCKFISH_BIN="stockfish/stockfish-ubuntu-x86-64-avx2"


mv "$STOCKFISH_BIN" stockfish-bin
rm -r stockfish
mv stockfish-bin stockfish
chmod +x stockfish

echo "Stockfish installed successfully"
