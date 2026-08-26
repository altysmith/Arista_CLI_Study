#!/bin/zsh

cd "$(dirname "$0")" || exit 1
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"

python_candidates=(
  /opt/homebrew/bin/python3
  /usr/local/bin/python3
  python3
  python
  "$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
)

for candidate in "${python_candidates[@]}"; do
  if [[ "$candidate" == */* ]]; then
    [[ -x "$candidate" ]] || continue
    python_cmd="$candidate"
  else
    python_cmd="$(command -v "$candidate" 2>/dev/null)" || continue
  fi

  if "$python_cmd" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' 2>/dev/null; then
    "$python_cmd" -m arista_sim.web
    exit_code=$?
    if (( exit_code != 0 )) && [[ -t 0 ]]; then
      read -k 1 "?The browser lab exited with an error. Press any key to close..."
      print
    fi
    exit "$exit_code"
  fi
done

print "Python 3.11 or newer was not found."
print "Install it from https://www.python.org/downloads/ and try again."
if [[ -t 0 ]]; then
  read -k 1 "?Press any key to close..."
  print
fi
exit 1
