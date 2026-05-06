#!/usr/bin/env bash
# Run capture against every saveN.ss0 in the repo with a diverse walk/talk press script.
set -e
cd "$(dirname "$0")/../.."

PRESS="A,A,A,A,A,A,DOWN,DOWN,A,A,B,RIGHT,RIGHT,A,A,B,UP,UP,A,A,B,LEFT,LEFT,A,A,B,DOWN,RIGHT,A,UP,LEFT,A,B,A,A,B,A,A,B,DOWN,DOWN,DOWN,A,A,UP,UP,UP,A,A,RIGHT,RIGHT,RIGHT,A,A,LEFT,LEFT,LEFT,A,A,A,B,A,DOWN,A,UP,A,RIGHT,A,LEFT,A,B"

PIDS=()
for n in 2 3 4 5 6; do
  rm -rf ".moneo-artifacts/dumps/fb-save$n"
  mkdir -p ".moneo-artifacts/dumps/fb-save$n"
  nohup ./tools/moneo/mgba_capture/build/mgba_capture \
    --rom "Pocket Monsters - LeafGreen (Korean).gba" \
    --state "save$n.ss0" \
    --out ".moneo-artifacts/capture-save$n.json" \
    --frames 60000 \
    --press "$PRESS" \
    --dump-fb-dir ".moneo-artifacts/dumps/fb-save$n" \
    --dump-fb-every 60 \
    >"/tmp/cap-save$n.out" 2>"/tmp/cap-save$n.err" &
  PIDS+=($!)
  echo "save$n PID=$!"
done

for p in "${PIDS[@]}"; do wait "$p" || true; done
echo "ALL DONE"
for n in 2 3 4 5 6; do
  printf 'save%s: ' "$n"
  tail -1 "/tmp/cap-save$n.err"
done
