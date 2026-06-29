DASHBOARD_PYEOF
for lbl in Claude-glances Claude-proclog Claude-dashboard; do launchctl bootout "$DOMAIN/$lbl" 2>/dev/null || true; rm -f "$LA/$lbl.plist" 2>/dev/null || true; done
pkill -f "proc-logger.py" 2>/dev/null || true; pkill -f "dashboard-server.py" 2>/dev/null || true
for i in $(seq 1 20); do pids=$(lsof -ti tcp:8765 2>/dev/null || true); [ -z "$pids" ] && break; echo "$pids" | xargs kill -9 2>/dev/null || true; sleep 0.3; done
sleep 0.5
mkplist(){
cat > "$LA/$1.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
 <key>Label</key><string>$1</string>
 <key>ProgramArguments</key><array><string>/usr/bin/python3</string><string>$2</string></array>
 <key>RunAtLoad</key><true/><key>KeepAlive</key><true/><key>ThrottleInterval</key><integer>10</integer>
 <key>StandardOutPath</key><string>/tmp/$1.log</string><key>StandardErrorPath</key><string>/tmp/$1.log</string>
</dict></plist>
EOF
launchctl bootstrap "$DOMAIN" "$LA/$1.plist"; }
mkplist Claude-proclog   "$MON/proc-logger.py"
mkplist Claude-dashboard "$MON/dashboard-server.py"
for i in $(seq 1 15); do code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8765/dashboard.html" 2>/dev/null || echo 000); [ "$code" = "200" ] && break; launchctl kickstart -k "$DOMAIN/Claude-dashboard" 2>/dev/null || true; sleep 1; done
for i in $(seq 1 20); do [ -f "$GL/proc-log.csv" ] && break; sleep 1; done
ln -f "$GL/proc-log.csv" "$OUT/proc-log.csv" 2>/dev/null || true; ln -f "$GL/rollup-log.csv" "$OUT/rollup-log.csv" 2>/dev/null || true
open "http://localhost:8765/dashboard.html" 2>/dev/null || true
note "Installed - opening DANISCOPE"
say "DANISCOPE is installed and running. It opens in your browser now, updates every minute, and starts automatically when you log in. Bookmark the page."
