#!/usr/bin/env python3
"""
DANISCOPE installer builder.

Single source of truth = the VERSION file. This script regenerates the
self-contained macOS installer (.app) and zips it to dist/DANISCOPE-Installer.zip,
ready to attach to a GitHub release. Runs on a plain Linux runner (no macOS needed)
because the .app is just a folder structure wrapping a shell script.

Inputs (repo root):
  VERSION                       -> version string, e.g. "1.20"
  claude-proc-logger.py         -> logger source, embedded into the installer
  claude-dashboard-server.py    -> dashboard source, embedded into the installer
  build/prologue.sh             -> installer head (ends with the proc heredoc opener)
  build/middle.sh               -> closes proc heredoc + opens dashboard heredoc
  build/epilogue.sh             -> closes dashboard heredoc + the rest of the installer

Output:
  dist/DANISCOPE-Installer.zip
"""
import os, re, sys, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
APP  = "DANISCOPE Installer.app"

INFO_PLIST = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
 <key>CFBundleName</key><string>DANISCOPE Installer</string><key>CFBundleDisplayName</key><string>DANISCOPE Installer</string>
 <key>CFBundleIdentifier</key><string>com.daniscope.installer</string><key>CFBundleVersion</key><string>{ver}</string>
 <key>CFBundleShortVersionString</key><string>{ver}</string><key>CFBundleExecutable</key><string>installer</string>
 <key>CFBundlePackageType</key><string>APPL</string><key>LSMinimumSystemVersion</key><string>10.15</string><key>NSHighResolutionCapable</key><true/>
</dict></plist>'''


def read(path):
    with open(os.path.join(ROOT, path), "r", encoding="utf-8") as f:
        return f.read()


def build_installer(ver):
    proc = read("claude-proc-logger.py")
    dash = read("claude-dashboard-server.py")

    # Inject the canonical version into the embedded dashboard so the running
    # app's self-version always matches the VERSION file (drives the update chip).
    dash, n = re.subn(r'VERSION="[^"]*"', 'VERSION="%s"' % ver, dash, count=1)
    if n != 1:
        sys.exit('build: expected exactly one VERSION="..." in dashboard source, found %d' % n)

    # Heredoc safety: a body line equal to the closing marker would break the install.
    for marker, body, name in (("PROCLOGGER_PYEOF", proc, "proc-logger"),
                               ("DASHBOARD_PYEOF", dash, "dashboard-server")):
        if any(line == marker for line in body.splitlines()):
            sys.exit("build: %s contains a line equal to heredoc marker %s" % (name, marker))

    return read("build/prologue.sh") + proc + read("build/middle.sh") + dash + read("build/epilogue.sh")


def write_zip(installer_text, ver):
    os.makedirs(DIST, exist_ok=True)
    zip_path = os.path.join(DIST, "DANISCOPE-Installer.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)

    def entry(name, mode):
        zi = zipfile.ZipInfo(name)
        zi.external_attr = (mode & 0xFFFF) << 16
        zi.compress_type = zipfile.ZIP_DEFLATED
        return zi

    with zipfile.ZipFile(zip_path, "w") as z:
        for d in (APP + "/", APP + "/Contents/", APP + "/Contents/MacOS/"):
            z.writestr(entry(d, 0o040755), "")
        z.writestr(entry(APP + "/Contents/MacOS/installer", 0o100755), installer_text)
        z.writestr(entry(APP + "/Contents/Info.plist", 0o100644), INFO_PLIST.format(ver=ver))
    return zip_path


def main():
    ver = read("VERSION").strip()
    if not ver:
        sys.exit("build: VERSION file is empty")
    installer_text = build_installer(ver)
    zip_path = write_zip(installer_text, ver)
    print("built %s for v%s (installer %d bytes)" % (zip_path, ver, len(installer_text.encode("utf-8"))))


if __name__ == "__main__":
    main()
