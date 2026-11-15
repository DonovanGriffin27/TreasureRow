#!/usr/bin/env bash
# Noah Higgs
# Starts Treasure Row on http://127.0.0.1:5001 and opens it in the browser.
# Double-click this file in Finder, or run it from Terminal.

cd "$(dirname "$0")" || exit 1
PORT="${PORT:-5001}"

if [ ! -x venv/bin/python ] || [ ! -f .env ]; then
  echo "Treasure Row is not installed yet. Running the installer first..."
  bash ./install.sh || { echo "Install did not finish. Fix the message above and try again."; exit 1; }
fi

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT is already in use. Close the other copy of Treasure Row (or the program using that port) and try again."
  exit 1
fi

# open the browser once the app answers (gives up after about 20 seconds)
(
  for _ in $(seq 1 40); do
    if curl -s -o /dev/null "http://127.0.0.1:$PORT/health"; then
      command -v open >/dev/null 2>&1 && open "http://127.0.0.1:$PORT"
      break
    fi
    sleep 0.5
  done
) &

echo "Starting Treasure Row at http://127.0.0.1:$PORT  (press Control+C to stop)"
exec venv/bin/python -m flask --app app run --port "$PORT"
