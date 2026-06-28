# DANISCOPE

A friendly, plain-English live monitor for your Mac.

DANISCOPE watches your Mac quietly in the background and tells you, in plain language, when it is running slow and what is causing it — so you do not have to read CPU, RAM and swap figures and decode them yourself. Think of it as a translator for Activity Monitor.

## What it does

- A **Right now** verdict — green / amber / red — with the culprit named in plain English.
- **Today** and **Long-term** charts of CPU, memory and per-app usage, with trends.
- Plain-English explanations for hundreds of macOS processes (hover the ⓘ).
- Runs entirely on your own Mac. Nothing about you leaves your machine.

## Install

Download and run the installer. It is self-contained, needs no Homebrew, and runs in your own user account (no admin needed for the monitor itself). The dashboard opens at `http://localhost:8765/dashboard.html` and starts automatically when you log in.

## Privacy

DANISCOPE makes **no** outbound connections, with one exception you control: an **optional, off-by-default** weekly check to GitHub that asks only *"is there a newer version?"*. It sends nothing about you, and you can leave it off and check for updates yourself.

## Version

The current version is in [`VERSION`](VERSION). The full changelog lives in the app under **Settings → Version history**.
