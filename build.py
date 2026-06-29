#!/usr/bin/env python3
"""
DANISCOPE installer builder + release-notes generator.

Single source of truth:
  - VERSION                     -> the version string, e.g. "1.21"
  - claude-dashboard-server.py  -> holds the CHANGELOG array (the "why" for each
                                   version). Everything user-facing is drawn from it:
                                   the in-app Version history, the GitHub release
                                   notes, the commit message, and CHANGELOG.md.

Modes:
  python build.py                 build dist/DANISCOPE-Installer.zip AND write
                                  dist/RELEASE_NOTES.md (used as the GitHub release body)
  python build.py --commit-msg    print a git commit message for the latest version
  python build.py --changelog     print a full CHANGELOG.md (all versions)

Build runs on a plain Linux runner (no macOS needed): the .app is just a folder
structure wrapping a shell script.
"""
import os, re, sys, json, zipfile

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


def version():
    v = read("VERSION").strip()
    if not v:
        sys.exit("build: VERSION file is empty")
    return v


def changelog():
    """Parse the CHANGELOG array out of the dashboard source (each entry is JSON)."""
    out, inside = [], False
    for ln in read("claude-dashboard-server.py").splitlines():
        s = ln.strip()
        if not inside:
            if s.startswith("CHANGELOG"):
                inside = True
            continue
        if s.startswith("]"):
            break
        s = s.rstrip(",")
        if s.startswith("{") and s.endswith("}"):
            try:
                out.append(json.loads(s))
            except Exception:
                pass
    return out


def build_installer(ver):
    proc = read("claude-proc-logger.py")
    dash = read("claude-dashboard-server.py")
    dash, n = re.subn(r'VERSION="[^"]*"', 'VERSION="%s"' % ver, dash, count=1)
    if n != 1:
        sys.exit('build: expected exactly one VERSION="..." in dashboard source, found %d' % n)
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


def latest_entry(ver):
    cl = changelog()
    if cl:
        return cl[0]
    return {"v": ver, "d": "", "notes": ["Maintenance release."]}


def release_notes_md(ver):
    e = latest_entry(ver)
    head = "### What's new in v%s%s" % (e.get("v", ver), (" — " + e["d"]) if e.get("d") else "")
    bullets = "\n".join("- " + n for n in e.get("notes", []))
    install = ("\n\n---\n**Install:** download `DANISCOPE-Installer.zip` below, unzip, "
               "then right-click the app and choose **Open** (first time only, past the "
               "unidentified-developer warning).")
    return head + "\n\n" + bullets + install + "\n"


def commit_msg(ver):
    e = latest_entry(ver)
    title = "DANISCOPE v%s" % ver
    bullets = "\n".join("- " + n for n in e.get("notes", []))
    return title + "\n\n" + bullets + "\n"


def changelog_md():
    lines = ["# DANISCOPE — Changelog", ""]
    for e in changelog():
        lines.append("## v%s%s" % (e.get("v", "?"), (" — " + e["d"]) if e.get("d") else ""))
        for n in e.get("notes", []):
            lines.append("- " + n)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    ver = version()
    if arg == "--commit-msg":
        sys.stdout.write(commit_msg(ver)); return
    if arg == "--changelog":
        sys.stdout.write(changelog_md()); return
    if arg:
        sys.exit("build: unknown argument %r" % arg)
    installer_text = build_installer(ver)
    zip_path = write_zip(installer_text, ver)
    os.makedirs(DIST, exist_ok=True)
    with open(os.path.join(DIST, "RELEASE_NOTES.md"), "w", encoding="utf-8") as f:
        f.write(release_notes_md(ver))
    print("built %s for v%s (installer %d bytes) + dist/RELEASE_NOTES.md"
          % (zip_path, ver, len(installer_text.encode("utf-8"))))


if __name__ == "__main__":
    main()
