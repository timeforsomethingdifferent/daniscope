#!/bin/bash
mkdir -p "$HOME/Documents/Mac-monitor"
exec >> "$HOME/Documents/Mac-monitor/install-log.txt" 2>&1
set -uo pipefail
MON="$HOME/.claude-monitor"; GL="$HOME/.daniscope"; LA="$HOME/Library/LaunchAgents"
OUT="$HOME/Documents/Mac-monitor"; DOMAIN="gui/$(id -u)"; PY=/usr/bin/python3
mkdir -p "$MON" "$GL" "$LA" "$OUT"
if [ -d "$HOME/glances" ]; then [ -f "$GL/proc-log.csv" ] || cp "$HOME/glances/proc-log.csv" "$GL/" 2>/dev/null || true; [ -f "$GL/rollup-log.csv" ] || cp "$HOME/glances/rollup-log.csv" "$GL/" 2>/dev/null || true; fi
say(){ osascript -e "display dialog \"$1\" buttons {\"OK\"} default button 1 with title \"DANISCOPE\"" >/dev/null 2>&1 || true; }
note(){ osascript -e "display notification \"$1\" with title \"DANISCOPE\"" >/dev/null 2>&1 || true; }
note "Installing DANISCOPE..."
if ! $PY --version >/dev/null 2>&1; then
  say "DANISCOPE needs Apple Command Line Tools (they include Python). A system installer will pop up - click Install, wait, then open DANISCOPE Installer again."
  xcode-select --install >/dev/null 2>&1 || true; exit 0
fi
if ! $PY -c "import psutil" >/dev/null 2>&1; then
  $PY -m pip --version >/dev/null 2>&1 || $PY -m ensurepip --user >/dev/null 2>&1 || true
  $PY -m pip install --user psutil >/dev/null 2>&1 || $PY -m pip install --user --break-system-packages psutil >/dev/null 2>&1 || true
fi
if ! $PY -c "import psutil" >/dev/null 2>&1; then
  say "Could not install a needed component (psutil). Check your internet connection and open DANISCOPE Installer again."; exit 1
fi
rm -f "$MON/proc-logger.py" "$MON/dashboard-server.py" 2>/dev/null || true
cat > "$MON/proc-logger.py" <<'PROCLOGGER_PYEOF'
