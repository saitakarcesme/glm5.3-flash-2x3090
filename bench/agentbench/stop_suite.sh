#!/usr/bin/env bash
# Stop any running agent-suite drivers and pi runs (never matches its own process).
me=$$; parent=$PPID
for pat in "ab_round" "run_suite.sh" "bin/pi -p"; do
  for p in $(pgrep -f "$pat"); do [ "$p" != "$me" ] && [ "$p" != "$parent" ] && kill "$p" 2>/dev/null; done
done
sleep 1; pgrep -af "run_suite|bin/pi -p" | grep -v stop_suite || echo "suite stopped"
