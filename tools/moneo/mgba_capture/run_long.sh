#!/bin/bash
# Launch the long Korean LeafGreen capture in the background.
# Writes JSON to .moneo-artifacts/capture-long.json
set -e
cd "$(dirname "$0")/../../.."
ROM='Pocket Monsters - LeafGreen (Korean).gba'
OUT='.moneo-artifacts/capture-long.json'
FRAMES="${1:-108000}"
PRESS="${2:-A,A,A,A,B,A,A,A,A,A}"
STATE="${3:-}"
EXTRA=""
if [ -n "$STATE" ]; then
    EXTRA="--state $STATE"
fi
exec ./tools/moneo/mgba_capture/build/mgba_capture \
    --rom "$ROM" \
    --out "$OUT" \
    --frames "$FRAMES" \
    --press "$PRESS" \
    $EXTRA
