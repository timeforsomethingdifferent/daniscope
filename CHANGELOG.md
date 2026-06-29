# DANISCOPE — Changelog

## v2.2 — 29 Jun 2026
- Tidied the top bar back to a single row. The ⓘ next to each app in the Right now view already explains what it is, so the extra Look up tab was removed

## v2.1 — 29 Jun 2026
- Expanded the built-in plain-English app dictionary with many more popular apps - messengers, password managers, browsers, note-takers, dictation and meeting tools - so more of what is running gets a clear explanation

## v2.0 — 29 Jun 2026
- Major update to how DANISCOPE catches slowdowns. It now records detailed diagnostics in the background every few seconds (true memory pressure, compression, paging, disk activity and stuck processes), keeps a few hours of that history, and automatically saves a deep snapshot the moment it detects a stall - so a future slowdown is captured on its own, with nothing for you to press
- Releases are now built and published automatically from a single push

## v1.21 — 29 Jun 2026
- Releases are now built and published automatically - the installer is rebuilt from source and the download is updated for each new version

## v1.20 — 29 Jun 2026
- Renamed the data folder from ~/glances to ~/.daniscope (a leftover name); your history is migrated automatically and the dashboard URL is unchanged

## v1.19 — 28 Jun 2026
- Update check now reads a VERSION file in the GitHub repo, so a newer version is detected as soon as it is pushed

## v1.18 — 28 Jun 2026
- Opt-in update check: a red/green indicator in the top bar. Off by default. Turn it on in Settings and DANISCOPE pings GitHub once a week to see if there is a newer version - the only outbound connection, and it sends nothing about you

## v1.17 — 28 Jun 2026
- New Expand / Compress button: expand the charts into a wide, scrollable timeline you can slide across, or compress back to fit the screen
- Long-term history is now capped at 6 months

## v1.16 — 28 Jun 2026
- The range and scale button row now stays stuck below the nav bar when you scroll, so the controls are always reachable

## v1.15 — 28 Jun 2026
- One Full scale / Fit to data button at the top-right of each tab now expands all the memory charts on that tab to your full RAM at once, instead of a button per chart

## v1.14 — 28 Jun 2026
- Today tab now has 1h / 6h / 12h / 24h range buttons, matching Long-term
- Logging window locked to 24 hours

## v1.13 — 28 Jun 2026
- Long-term tab now has 7 days / 30 days / All range buttons; the charts and the trend roundup both update to whichever scope you pick

## v1.12 — 28 Jun 2026
- New roundup at the top of Long-term: a plain-English trend over your history showing whether memory use and pressure are climbing, easing or steady, plus the biggest mover

## v1.11 — 28 Jun 2026
- Removed the Directory tab from the nav (the dictionary still powers every plain-English explanation behind the scenes)
- Nav buttons no longer shift position when the Show/Hide gaps button appears or disappears

## v1.10 — 28 Jun 2026
- Header is now a sticky navigation bar: name and version on the left, tabs and settings on the right, staying in view as you scroll
- Moved the descriptive blurb into a new About button in Settings
- Show/Hide gaps button moved up beside the settings cog (appears on the Today tab)

## v1.9 — 28 Jun 2026
- New Hide gaps / Show gaps button at the top of Today: keep the real sleep/off gaps, or compress them out to see just the active periods

## v1.8 — 28 Jun 2026
- Today chart times now show every hour
- Hovering any chart shows the exact time at the top of the tooltip, on both Today and Long-term

## v1.7 — 28 Jun 2026
- Today chart times now sit on clean clock marks (on the hour / half hour, widening to every 2-3 hours across a full day) instead of arbitrary times

## v1.6 — 28 Jun 2026
- The dashboard no longer caches in your browser, so updates show on the next 60-second refresh without a hard reload

## v1.5 — 28 Jun 2026
- Tighter spacing between the chart ticks and their buttons

## v1.4 — 28 Jun 2026
- Times now show as AM/PM, and Long-term shows friendly dates instead of timestamps
- More breathing room (and a divider) under the Right-now-by-resource panel
- Chart buttons (hide-all and scale) now sit on their own row under the ticks, with consistent names: Full scale / Fit to data

## v1.3 — 28 Jun 2026
- Today charts now plot on real time, so a gap (sleep or computer off) shows as a real blank instead of a jump
- Today tab opens with a Right-now-by-resource breakdown (CPU, memory pressure, heat)
- Removed the Memory pressure tile from Right Now (it lives in the Today breakdown now)

## v1.2 — 28 Jun 2026
- New Directory tab: search every process running on your Mac and see what each one is
- Around 55 more plain-English process descriptions
- Corrected the duetexpertd description (it is the background-task scheduler, not a Siri process)
- Version history is now behind a button in Settings

## v1.1 — 28 Jun 2026
- Settings cog: header styles moved here, plus this changelog
- Your tab and scroll position now stay put when the page refreshes
- Peak is now an overall intensity score, not just CPU
- Tick-box legends with Deselect / Select all
- Full scale vs zoom toggle on the memory charts
- Version number added

## v1.0 — 27 Jun 2026
- First version: Right-now health verdict, Today and Long-term charts, plain-English explainers, and the slowdown/culprit engine
