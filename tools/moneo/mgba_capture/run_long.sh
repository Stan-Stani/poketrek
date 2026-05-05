#!/bin/bash
# Launch the long Korean LeafGreen capture in the background.
# Writes JSON to .moneo-artifacts/capture-long.json
set -e
cd "$(dirname "$0")/../../.."
ROM='Pocket Monsters - LeafGreen (Korean).gba'
OUT='.moneo-artifacts/capture-long.json'
FRAMES="${1:-108000}"
PRESS="${2:-A,A,START,A,A,A,DOWN,A}"
exec ./tools/moneo/mgba_capture/build/mgba_capture \
    --rom "$ROM" \
    --out "$OUT" \
    --frames "$FRAMES" \
    --press "$PRESS"
