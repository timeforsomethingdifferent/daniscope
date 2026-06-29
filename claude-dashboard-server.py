#!/usr/bin/env python3
import os, json, csv, collections, time, threading, datetime, re
import http.server, socketserver
try: import psutil
except Exception: psutil=None
GL=os.path.expanduser("~/.daniscope")
RAW=os.path.join(GL,"proc-log.csv"); ROLL=os.path.join(GL,"rollup-log.csv")
HTML=os.path.join(GL,"dashboard.html"); PORT=8765; VERSION="2.1"
CURATED={
 'kernel_task':'The macOS kernel. High here is your Mac deliberately throttling to shed heat, it is the symptom of a hot chip, not the cause. Lighten the load or improve airflow and it drops.',
 'windowserver':'Draws everything on screen. Rises with more displays, higher resolution and refresh rates, screen sharing, and lots of on-screen video or animation. Running multiple or high-resolution external displays is a common reason it sits higher.',
 'coreaudiod':'macOS Core Audio, the system sound engine. Mild use is normal whenever audio plays. Constantly high usually points to one specific audio app or device, such as a per-app audio tool or a USB headset/DAC.',
 'arkaudiod':'Audio processing for a connected device, often a per-app audio router (such as SoundSource) or a USB headset/DAC. Quick test: quit the audio-routing app; if this drops or disappears that is the source; if it stays, it is the headset/DAC driver.',
 'arcaudiod':'Audio processing for a connected device, usually a per-app audio router (such as SoundSource) or a USB headset/DAC. Test: quit the audio-routing app and watch this; if it falls then that app was driving it; if not, it is the headset/DAC.',
 'soundsource':'SoundSource by Rogue Amoeba, per-app volume and audio routing. It keeps an audio engine running in the background, which can also appear as a separate audio process.',
 'duetexpertd':"Part of Apple's background-activity scheduler (CoreDuet / DuetActivityScheduler). It learns your usage patterns to decide WHEN to run background tasks, so they disrupt you least and save battery, and it feeds some on-device predictions. It runs regardless of whether Siri is on. NOT the Duet Display app. Brief spikes are normal and settle on their own.",
 'virtualization':"macOS's virtual-machine engine. It only runs when something needs a VM. If you have no VM apps (Docker, Parallels, UTM), this is almost always macOS itself: recent versions run some on-device Apple Intelligence and security work inside lightweight secure VMs, which is why it can spike overnight while everything else is idle. Not something you installed, and not malware.",
 'vtdecoder':'Hardware video decoding. Spikes when video plays, a call, a YouTube tab, screen sharing, and drops the moment the video stops. Normal.',
 'vtencoder':'Hardware video encoding. Runs when recording or sharing your screen, or on a video call. Stops when the recording or call ends.',
 'mds_stores':'Spotlight search building its index. Spikes after a macOS update, big file changes, or a new drive, then settles. Safe to leave, it finishes on its own.',
 'mdworker':'Spotlight indexing a batch of files. Temporary, it stops once caught up.',
 'mds':'Spotlight search indexing. Temporary spikes after big file changes.',
 'photoanalysisd':'Photos scanning your library for faces, scenes and search. Runs after you import photos, then stops. Plugging into power lets it finish faster.',
 'mediaanalysisd':'Analysing photos and videos for search. Temporary, ends when done.',
 'corespotlightd':'Spotlight indexing app content. Temporary.',
 'spotlight':'Spotlight search.',
 'bird':'iCloud Drive syncing. High usually means a large sync, many files changed or a fresh sign-in. Settles once caught up.',
 'cloudd':'iCloud sync. High points to a big upload or download in progress; it calms down when finished.',
 'nsurlsessiond':'Background downloads and uploads for iCloud, the App Store and apps. High means something large is transferring. Temporary.',
 'backupd':'Time Machine running a backup. Heavy while it runs, especially the first one or after big changes, then stops.',
 'launchd':'The master macOS process that starts and supervises everything else. Almost never the real problem itself.',
 'continuitycaptureagent':'Using an iPhone as a webcam via Continuity Camera. This carries a known CPU cost; a dedicated USB webcam avoids it.',
 'transcode':'Converting a finished recording, e.g. Zoom processing a local recording after a call. Heavy but temporary, it ends when the conversion finishes.',
 'insync':'Insync syncing files to Google Drive. CPU spikes when many files change, idle the rest of the time.',
 'willow voice':'Willow Voice dictation. Keeps a speech model in memory (~2GB) so it can transcribe instantly.',
 'stats':'Stats, the menu-bar system monitor. Tiny and constant, it is measuring everything else.',
 'aldente':'AlDente, the battery charge-limit app. Negligible load.',
 'little snitch':'Little Snitch network firewall. Light background load watching connections.',
 'webkit':'A Safari web page or web app running in the background. A single heavy tab (video, a web app) can push this high, check which site.',
 'brave browser':'Brave. Each tab and extension is its own process, so a heavy web app (Canva, Google Docs, video) or a runaway extension can spike CPU or eat memory. The tab title usually names the culprit.',
 'zoom':'Zoom. CPU climbs with camera on, screen share, and more people on screen. After a call, a Zoom Transcode process can run briefly to process a local recording.',
 'fathom':'Fathom meeting notetaker, recording or processing a call.',
 'notion':'Notion notes and calendar.',
 'whatsapp':'WhatsApp messaging.',
 'claude':'Claude desktop app.',
 'loom':"Loom screen recorder. CPU and GPU climb while you record; helper processes handle the capture and the upload afterwards.",
 'descript':"Descript audio and video editor. Heavy while editing, transcribing, exporting or uploading; quiet otherwise.",
 'replayd':"macOS screen-recording engine. Runs whenever something records your screen (Loom, QuickTime, the screenshot tool).",
 'screencapture':"The macOS screenshot and screen-recording tool. Spikes only while you capture.",
 'roboform':"RoboForm password manager.",
 '1password':"1Password password manager.",
 'onepassword':"1Password password manager.",
 'chrome':"Google Chrome. Each tab and extension is its own process, so a heavy tab or a runaway extension can spike CPU or memory.",
 'slack':"Slack chat. A web-app-based client; can hold a lot of memory with several workspaces open.",
 'spotify':"Spotify music player.",
 'figma':"Figma design app. GPU- and memory-heavy with large files.",
 'dropbox':"Dropbox file sync. CPU spikes when lots of files change, idle otherwise.",
 'onedrive':"Microsoft OneDrive file sync.",
 'drivefs':"Google Drive file sync (Drive for desktop).",
 'obsidian':"Obsidian notes app.",
 'cleanshot':"CleanShot X screenshot tool. Spikes only while capturing.",
 'paste':"Paste clipboard manager. Spikes only when you copy or open it.",
 'raycast':"Raycast launcher and productivity tool.",
 'grammarly':"Grammarly. Watches text fields across your browser and apps, which can be a steady background cost.",
 'monogram':"Monogram Creator - software for the Monogram physical control deck. If the hardware is not connected, it can be quit.",
 'docker':"Docker - runs Linux containers inside a virtual machine. Can use a lot of CPU and memory while containers run.",
 'parallels':"Parallels - runs Windows or Linux in a virtual machine.",
 'microsoft':"A Microsoft Office app (Word, Excel, Outlook, and so on).",
 'contactsd':"Keeps your Contacts indexed and synced. Brief activity when contacts change.",
 'identityservicesd':"Handles iMessage, FaceTime and Apple ID identity. Occasional spikes when messaging or signing in.",
 'apsd':"Apple Push Notification client - keeps one connection open so notifications (Messages, Mail, apps) arrive.",
 'rapportd':"Powers Continuity and Handoff between your Apple devices - AirDrop, unlocking with your Watch, iPhone-as-webcam.",
 'sharingd':"AirDrop, Handoff, Continuity and the shared clipboard.",
 'trustd':"Checks security certificates when apps connect to the internet. Brief spikes while verifying.",
 'syspolicyd':"Gatekeeper - checks that apps are safe to open. Spikes the first time you open a newly downloaded app.",
 'tccd':"The privacy gatekeeper - controls which apps may use your camera, mic and files, and shows the permission prompts.",
 'powerd':"Manages sleep, wake and power. A core system process.",
 'cfprefsd':"Manages app preference (settings) files. Tiny and constant.",
 'mdnsresponder':"Handles DNS name lookups and discovery of nearby devices (AirPrint, AirPlay, Bonjour).",
 'bluetoothd':"Manages your Bluetooth devices - mouse, keyboard, headphones.",
 'fseventsd':"Watches the file system for changes so apps and backups know what changed. Tiny.",
 'revisiond':"macOS document version history (the auto-save / Versions feature).",
 'dasd':"Apple's background-task scheduler - decides when to run dozens of background jobs (like Time Machine) so they least disrupt you. Works with duetexpertd.",
 'coreduetd':"Part of Apple's CoreDuet system that learns usage patterns to schedule background work efficiently. Sibling of duetexpertd.",
 'suggestd':"Builds on-device suggestions from Mail and Messages (names, events, contacts). Brief background work.",
 'knowledge':"Apple's on-device usage store that powers Screen Time and suggestions.",
 'biome':"Apple's on-device learning store (Biome) that feeds suggestions. Background, low impact.",
 'intelligenceplatform':"Runs Apple's on-device AI models. Spikes overnight or after updates while it processes, then settles.",
 'assistantd':"Siri's main process. Stays idle if you do not use Siri.",
 'corespeechd':"On-device speech recognition for dictation and Hey Siri (if enabled).",
 'searchparty':"The Find My network - helps locate your devices over Bluetooth.",
 'softwareupdated':"Checks for and downloads macOS updates.",
 'appstoreagent':"App Store background updates.",
 'commerce':"App Store purchases and downloads.",
 'akd':"Apple ID authentication helper.",
 'secd':"Syncs your Keychain (saved passwords) via iCloud.",
 'thermalmonitord':"Watches temperature and triggers throttling if the Mac gets too hot.",
 'airportd':"Manages your Wi-Fi connection.",
 'logd':"Collects system logs. Tiny and constant.",
 'notification':"Notification Center - shows your notifications. If it balloons in memory, quit and relaunch it.",
 'controlcenter':"The menu-bar Control Center and its icons.",
 'windowmanager':"Runs Stage Manager and window tiling.",
 'dock':"The Dock, Mission Control and Launchpad.",
 'finder':"The macOS file manager and desktop.",
 'loginwindow':"Manages your login session.",
 'telegram':"Telegram messenger.",
 'signal':"Signal private messenger.",
 'discord':"Discord chat and voice. Electron-based; can hold a lot of memory.",
 'messenger':"Facebook Messenger.",
 'teams':"Microsoft Teams chat and meetings. Memory-heavy with several teams open.",
 'skype':"Skype calls and chat.",
 'wechat':"WeChat messenger.",
 'viber':"Viber messenger.",
 'bitwarden':"Bitwarden password manager.",
 'dashlane':"Dashlane password manager.",
 'lastpass':"LastPass password manager.",
 'keepass':"KeePass / KeePassXC password manager.",
 'nordpass':"NordPass password manager.",
 'enpass':"Enpass password manager.",
 'keeper':"Keeper password manager.",
 'proton':"A Proton app (Pass, Mail, VPN or Drive).",
 'superwhisper':"superwhisper voice dictation. Keeps a speech model in memory for instant transcription.",
 'macwhisper':"MacWhisper transcription app.",
 'wispr':"Wispr Flow voice dictation.",
 'aqua':"Aqua Voice dictation.",
 'dragon':"Dragon dictation (speech-to-text).",
 'otter':"Otter.ai meeting transcription and notes.",
 'granola':"Granola AI meeting notetaker.",
 'fireflies':"Fireflies.ai meeting notetaker.",
 'krisp':"Krisp noise cancellation and meeting notes.",
 'avoma':"Avoma meeting assistant and notetaker.",
 'sembly':"Sembly AI meeting notetaker.",
 'tldv':"tl;dv meeting recorder and notetaker.",
 'firefox':"Mozilla Firefox. Each tab and extension is its own process; a heavy tab can spike CPU or memory.",
 'microsoft edge':"Microsoft Edge browser. Chromium-based; each tab is its own process.",
 'vivaldi':"Vivaldi browser.",
 'opera':"Opera browser.",
 'safari':"Apple Safari. A heavy tab or web app can push CPU and memory up; the tab title usually names it.",
 'chatgpt':"ChatGPT desktop app.",
 'perplexity':"Perplexity AI app.",
 'ollama':"Ollama - runs AI models locally. Can be CPU/GPU and memory heavy while a model runs.",
 'lm studio':"LM Studio - runs AI models locally. Heavy while a model is loaded.",
 'copilot':"Microsoft / GitHub Copilot AI assistant.",
 'evernote':"Evernote notes app.",
 'bear':"Bear notes app.",
 'craft':"Craft docs and notes app.",
 'logseq':"Logseq notes app.",
 'things':"Things task manager.",
 'todoist':"Todoist task manager.",
 'omnifocus':"OmniFocus task manager.",
 'asana':"Asana project management.",
 'trello':"Trello boards.",
 'linear':"Linear issue tracker.",
 'clickup':"ClickUp project management.",
 'outlook':"Microsoft Outlook email and calendar.",
 'thunderbird':"Mozilla Thunderbird email.",
 'mimestream':"Mimestream email client for Gmail.",
 'superhuman':"Superhuman email client.",
 'mailspring':"Mailspring email client.",
 'airmail':"Airmail email client.",
 'spark':"Spark email client.",
 'pcloud':"pCloud file sync.",
 'nextcloud':"Nextcloud file sync.",
 'tresorit':"Tresorit encrypted file sync.",
 'mega':"MEGA cloud file sync.",
 'screenflow':"ScreenFlow screen recorder and editor.",
 'camtasia':"Camtasia screen recorder and editor.",
 'screen studio':"Screen Studio screen recorder.",
 'riverside':"Riverside recording studio.",
 'quicktime':"Apple QuickTime player and screen recorder.",
 'photoshop':"Adobe Photoshop. GPU- and memory-heavy with large files.",
 'illustrator':"Adobe Illustrator.",
 'premiere':"Adobe Premiere Pro video editor. Very heavy while editing or exporting.",
 'after effects':"Adobe After Effects motion graphics. Very heavy while rendering.",
 'lightroom':"Adobe Lightroom photo editor.",
 'sketch':"Sketch design app.",
 'affinity':"An Affinity app (Photo, Designer or Publisher).",
 'pixelmator':"Pixelmator image editor.",
 'final cut':"Final Cut Pro video editor. Heavy while editing or exporting.",
 'davinci':"DaVinci Resolve video editor. GPU- and memory-heavy.",
 'blender':"Blender 3D. Very CPU- and GPU-heavy while rendering.",
 'xcode':"Apple Xcode developer tools. Heavy while building or indexing.",
 'iterm':"iTerm2 terminal.",
 'warp':"Warp terminal.",
 'sublime':"Sublime Text editor.",
 'jetbrains':"A JetBrains IDE (IntelliJ, PyCharm, and so on). Memory-heavy while indexing.",
 'android studio':"Android Studio IDE. Memory-heavy while building.",
 'postman':"Postman API client.",
 'tableplus':"TablePlus database client.",
 'vlc':"VLC media player.",
 'iina':"IINA media player.",
 'spotify':"Spotify music player.",
 'tidal':"TIDAL music player.",
 'alfred':"Alfred launcher and productivity tool.",
 'bartender':"Bartender - tidies your menu-bar icons.",
 'rectangle':"Rectangle window manager.",
 'bettertouchtool':"BetterTouchTool input and automation tool.",
 'hazel':"Hazel automated file organiser.",
 'karabiner':"Karabiner-Elements keyboard customiser.",
 'cleanmymac':"CleanMyMac maintenance app.",
}
ROLL_ALIAS={"brave":"Brave Browser","claude":"Claude","notion":"Notion Calendar","fathom":"Fathom","zoom":"zoom.us","safari":"Safari","audio":"coreaudiod"}
CHANGELOG=[
 {"v":"2.1","d":"29 Jun 2026","notes":["Expanded the built-in plain-English app dictionary with many more popular apps - messengers, password managers, browsers, note-takers, dictation and meeting tools - so more of what is running gets a clear explanation","Brought back the Look up tab: search everything running on your Mac and read a plain-English explanation of each item"]},
 {"v":"2.0","d":"29 Jun 2026","notes":["Major update to how DANISCOPE catches slowdowns. It now records detailed diagnostics in the background every few seconds (true memory pressure, compression, paging, disk activity and stuck processes), keeps a few hours of that history, and automatically saves a deep snapshot the moment it detects a stall - so a future slowdown is captured on its own, with nothing for you to press","Releases are now built and published automatically from a single push"]},
 {"v":"1.21","d":"29 Jun 2026","notes":["Releases are now built and published automatically - the installer is rebuilt from source and the download is updated for each new version"]},
 {"v":"1.20","d":"29 Jun 2026","notes":["Renamed the data folder from ~/glances to ~/.daniscope (a leftover name); your history is migrated automatically and the dashboard URL is unchanged"]},
 {"v":"1.19","d":"28 Jun 2026","notes":["Update check now reads a VERSION file in the GitHub repo, so a newer version is detected as soon as it is pushed"]},
 {"v":"1.18","d":"28 Jun 2026","notes":["Opt-in update check: a red/green indicator in the top bar. Off by default. Turn it on in Settings and DANISCOPE pings GitHub once a week to see if there is a newer version - the only outbound connection, and it sends nothing about you"]},
 {"v":"1.17","d":"28 Jun 2026","notes":["New Expand / Compress button: expand the charts into a wide, scrollable timeline you can slide across, or compress back to fit the screen","Long-term history is now capped at 6 months"]},
 {"v":"1.16","d":"28 Jun 2026","notes":["The range and scale button row now stays stuck below the nav bar when you scroll, so the controls are always reachable"]},
 {"v":"1.15","d":"28 Jun 2026","notes":["One Full scale / Fit to data button at the top-right of each tab now expands all the memory charts on that tab to your full RAM at once, instead of a button per chart"]},
 {"v":"1.14","d":"28 Jun 2026","notes":["Today tab now has 1h / 6h / 12h / 24h range buttons, matching Long-term","Logging window locked to 24 hours"]},
 {"v":"1.13","d":"28 Jun 2026","notes":["Long-term tab now has 7 days / 30 days / All range buttons; the charts and the trend roundup both update to whichever scope you pick"]},
 {"v":"1.12","d":"28 Jun 2026","notes":["New roundup at the top of Long-term: a plain-English trend over your history showing whether memory use and pressure are climbing, easing or steady, plus the biggest mover"]},
 {"v":"1.11","d":"28 Jun 2026","notes":["Removed the Directory tab from the nav (the dictionary still powers every plain-English explanation behind the scenes)","Nav buttons no longer shift position when the Show/Hide gaps button appears or disappears"]},
 {"v":"1.10","d":"28 Jun 2026","notes":["Header is now a sticky navigation bar: name and version on the left, tabs and settings on the right, staying in view as you scroll","Moved the descriptive blurb into a new About button in Settings","Show/Hide gaps button moved up beside the settings cog (appears on the Today tab)"]},
 {"v":"1.9","d":"28 Jun 2026","notes":["New Hide gaps / Show gaps button at the top of Today: keep the real sleep/off gaps, or compress them out to see just the active periods"]},
 {"v":"1.8","d":"28 Jun 2026","notes":["Today chart times now show every hour","Hovering any chart shows the exact time at the top of the tooltip, on both Today and Long-term"]},
 {"v":"1.7","d":"28 Jun 2026","notes":["Today chart times now sit on clean clock marks (on the hour / half hour, widening to every 2-3 hours across a full day) instead of arbitrary times"]},
 {"v":"1.6","d":"28 Jun 2026","notes":["The dashboard no longer caches in your browser, so updates show on the next 60-second refresh without a hard reload"]},
 {"v":"1.5","d":"28 Jun 2026","notes":["Tighter spacing between the chart ticks and their buttons"]},
 {"v":"1.4","d":"28 Jun 2026","notes":["Times now show as AM/PM, and Long-term shows friendly dates instead of timestamps","More breathing room (and a divider) under the Right-now-by-resource panel","Chart buttons (hide-all and scale) now sit on their own row under the ticks, with consistent names: Full scale / Fit to data"]},
 {"v":"1.3","d":"28 Jun 2026","notes":["Today charts now plot on real time, so a gap (sleep or computer off) shows as a real blank instead of a jump","Today tab opens with a Right-now-by-resource breakdown (CPU, memory pressure, heat)","Removed the Memory pressure tile from Right Now (it lives in the Today breakdown now)"]},
 {"v":"1.2","d":"28 Jun 2026","notes":["New Directory tab: search every process running on your Mac and see what each one is","Around 55 more plain-English process descriptions","Corrected the duetexpertd description (it is the background-task scheduler, not a Siri process)","Version history is now behind a button in Settings"]},
 {"v":"1.1","d":"28 Jun 2026","notes":["Settings cog: header styles moved here, plus this changelog","Your tab and scroll position now stay put when the page refreshes","Peak is now an overall intensity score, not just CPU","Tick-box legends with Deselect / Select all","Full scale vs zoom toggle on the memory charts","Version number added"]},
 {"v":"1.0","d":"27 Jun 2026","notes":["First version: Right-now health verdict, Today and Long-term charts, plain-English explainers, and the slowdown/culprit engine"]},
]
def f(x):
    try: return float(x)
    except: return 0.0
def read_csv(path):
    S=collections.OrderedDict()
    try:
        for r in csv.reader(open(path)):
            if len(r)<4 or r[0]=="timestamp": continue
            S.setdefault(r[0],[]).append((r[1],r[2],r[3]))
    except Exception: pass
    return S
def appname(c):
    i=c.find(' Helper')
    if i>0: c=c[:i]
    return c
def owner(path):
    if not path: return None
    if path.startswith(('/System/','/usr/','/sbin/','/bin/')) or '/Library/Apple/' in path: return 'Apple / macOS'
    m=re.search(r'/([^/]+)\.app/',path)
    if m: return m.group(1)
    return path
def live_paths():
    m={}
    if not psutil: return m
    for p in psutil.process_iter(['name']):
        nm=p.info.get('name')
        if not nm or nm in m: continue
        try: m[nm]=p.exe()
        except Exception: m[nm]=''
    return m
def explain(name,paths):
    key=(name or '').lower()
    for k,v in CURATED.items():
        if k in key: return v
    p=paths.get(name,''); o=owner(p)
    if o=='Apple / macOS':
        return 'A built-in macOS system process'+((' ('+p+')') if p else '')+'. These are normally light; a brief spike after waking, updating or syncing is normal and settles on its own. If it stays high, note the exact name and it can be looked into specifically.'
    if o and o!=p:
        return 'Part of '+o+'. If it is high, that app is doing work in the background, quitting or restarting the app clears it.'
    if p:
        return 'Runs from '+p+'. Not a recognised app; if it is consistently high, that path tells you where it lives.'
    return 'A background process named '+(name or '?')+'.'
def sysd(pl): return {c:(f(a) if ('cpu' in c or 'load' in c) else f(b)) for c,a,b in pl if c.startswith("SYSTEM")}
def procs_of(pl): return [(f(c),cmd,f(m)) for cmd,c,m in pl if not cmd.startswith("SYSTEM")]
def slow_flag(pl):
    sd=sysd(pl); pr=procs_of(pl)
    if not pr: return None
    cpu=sd.get("SYSTEM.cpu_total",0); swap=sd.get("SYSTEM.swap_used_mb",0); kt=0.0
    for c,n,m in pr:
        if 'kernel_task' in n: kt=c
    if swap>1500:
        b=max(pr,key=lambda x:x[2]); return ('Memory',b[1],str(round(b[2]/1024,1))+'GB RAM ('+str(round(swap))+'MB swap)')
    if kt>20:
        b=max(pr,key=lambda x:x[0]); return ('Heat',b[1],'chip throttling, heaviest load '+str(round(b[0]))+'%')
    if cpu>85:
        b=max(pr,key=lambda x:x[0]); return ('CPU',b[1],str(round(b[0]))+'% CPU')
    return None
def pressure(swap): return "None" if swap<300 else ("Low" if swap<1500 else "High")
def level_info(pl):
    sd=sysd(pl); pr=procs_of(pl)
    cpu=sd.get("SYSTEM.cpu_total",0); swap=sd.get("SYSTEM.swap_used_mb",0); kt=0.0
    for c,n,m in pr:
        if 'kernel_task' in n: kt=c
    fl=slow_flag(pl)
    if fl:
        return {"lvl":3,"name":"RED","head":"Slow right now","sub":"A culprit is bogging you down. Clear the item below and it lifts.","culprit":fl[1],"det":fl[2],"type":fl[0]}
    if pr and (swap>500 or kt>8 or cpu>70):
        if swap>500:
            b=max(pr,key=lambda x:x[2]); typ="Memory"; det=str(round(b[2]/1024,1))+"GB RAM"
        elif kt>8:
            b=max(pr,key=lambda x:x[0]); typ="Heat"; det="chip warming, heaviest "+str(round(b[0]))+"%"
        else:
            b=max(pr,key=lambda x:x[0]); typ="CPU"; det=str(round(b[0]))+"% CPU"
        return {"lvl":2,"name":"AMBER","head":"Working hard","sub":"Something heavy is running. It is not hurting you yet, but you are close.","culprit":b[1],"det":det,"type":typ}
    return {"lvl":1,"name":"GREEN","head":"Running fine","sub":"Nothing is slowing you down. No throttling, no swap, CPU has headroom.","culprit":None,"det":None,"type":None}
def detect(raw):
    flags=[]
    for t,pl in raw.items():
        fl=slow_flag(pl)
        if fl: flags.append((t,)+fl)
    ev=[]
    for t,typ,cul,det in flags:
        if ev:
            l=ev[-1]
            gap=(datetime.datetime.strptime(t,"%Y-%m-%d %H:%M:%S")-datetime.datetime.strptime(l['_lt'],"%Y-%m-%d %H:%M:%S")).total_seconds()
            if gap<=180 and typ==l['type']:
                l['end']=t[11:16]; l['_lt']=t; l['det']=det
                l['culs'][cul]=l['culs'].get(cul,0)+1; continue
        ev.append({'start':t[11:16],'end':t[11:16],'type':typ,'det':det,'_lt':t,'culs':{cul:1}})
    out=[]
    for e in ev:
        out.append({'start':e['start'],'end':e['end'],'type':e['type'],'culprit':max(e['culs'],key=e['culs'].get),'det':e['det']})
    return out[-8:]
def strain(cpu,swap,kt):
    parts=sorted([(min(100.0,cpu),"CPU"),(min(100.0,swap/20.0),"Memory"),(min(100.0,kt*4.0),"Heat")],reverse=True)
    return parts[0]
def busiest(raw):
    best=None
    for t,pl in raw.items():
        sd=sysd(pl); pr=procs_of(pl)
        if not pr: continue
        cpu=sd.get("SYSTEM.cpu_total",0); swap=sd.get("SYSTEM.swap_used_mb",0); kt=0.0
        for c,nn,mm in pr:
            if 'kernel_task' in nn: kt=c
        sc,typ=strain(cpu,swap,kt)
        if best is None or sc>best['score']:
            b=max(pr,key=lambda x:x[2]) if typ=="Memory" else max(pr,key=lambda x:x[0])
            best={'t':t[11:16],'score':round(sc),'type':typ,'cul':b[1]}
    return best
def build_directory(paths):
    if not psutil: return []
    g={}
    try:
        for pr in psutil.process_iter(['name','memory_info']):
            nm=pr.info.get('name')
            if not nm: continue
            k=appname(nm)
            try: mem=pr.info['memory_info'].rss/1048576.0
            except Exception: mem=0.0
            e=g.setdefault(k,[0.0,0]); e[0]+=mem; e[1]+=1
    except Exception: pass
    out=[]
    for k,(mem,cnt) in g.items():
        pth=paths.get(k,''); o=owner(pth)
        cat='apple' if o=='Apple / macOS' else ('app' if (o and o!=pth) else 'other')
        out.append({'n':k,'mem':round(mem),'c':cnt,'cat':cat,'info':explain(k,paths)})
    out.sort(key=lambda x:x['mem'],reverse=True)
    return out
def compute_trend(ls,rollseries,rt):
    if len(ls)<4: return None
    def _ha(vals):
        vals=[v for v in vals if v is not None]
        if not vals: return (0.0,0.0)
        h=max(1,len(vals)//2)
        return (sum(vals[:h])/h, sum(vals[h:])/max(1,len(vals)-h))
    mfa,mla=_ha([r["memg"] for r in ls]); mpct=((mla-mfa)/mfa*100) if mfa>0 else 0
    mdir="up" if mpct>5 else ("down" if mpct<-5 else "flat")
    sfa,sla=_ha([r["swap"] for r in ls])
    grow=None
    for i,gnm in enumerate(rollseries["names"]):
        ga,gl=_ha(rollseries["data"][i]); dlt=gl-ga
        if grow is None or abs(dlt)>abs(grow[1]): grow=(gnm,dlt)
    try:
        d0=datetime.datetime.strptime(rt[0],"%Y-%m-%d %H:%M:%S"); d1=datetime.datetime.strptime(rt[-1],"%Y-%m-%d %H:%M:%S"); days=max(1,(d1-d0).days)
    except Exception: days=1
    rows=[{"k":"Memory in use","dir":mdir,"detail":"%.1f to %.1f GB"%(mfa,mla)}]
    if sfa<300 and sla<300:
        rows.append({"k":"Memory pressure","dir":"flat","detail":"low the whole time"})
    else:
        sdir="up" if sla>sfa+200 else ("down" if sla<sfa-200 else "flat")
        rows.append({"k":"Memory pressure","dir":sdir,"detail":"swap %d to %d MB"%(round(sfa),round(sla))})
    if grow and abs(grow[1])>0.05:
        rows.append({"k":"Biggest mover","dir":("up" if grow[1]>0 else "down"),"detail":"%s %s%.1f GB"%(grow[0],"+" if grow[1]>=0 else "",grow[1])})
    return {"days":days,"rows":rows,"verdict":("heavier" if mdir=="up" else ("lighter" if mdir=="down" else "steady"))}
def rollup_view(roll,days):
    rt=list(roll.keys())
    if days is not None and rt:
        try:
            last=datetime.datetime.strptime(rt[-1],"%Y-%m-%d %H:%M:%S"); cut=last-datetime.timedelta(days=days)
            rt=[t for t in rt if datetime.datetime.strptime(t,"%Y-%m-%d %H:%M:%S")>=cut]
        except Exception: pass
    if not rt: return {"roll":[],"rollseries":{"names":[],"data":[]},"trend":None}
    if len(rt)>250:
        stp=max(1,len(rt)//250); rt=[rt[i] for i in range(0,len(rt),stp)]
    ls=[]; approws=[]; apppeak={}
    for t in rt:
        smem=ssw=0.0; apps={}
        for c,a,b in roll[t]:
            if c=="SYSTEM.mem_used_mb": smem=f(b)
            elif c=="SYSTEM.swap_used_mb": ssw=f(b)
            elif c.startswith("app."):
                nmk=c[4:]; nmk=ROLL_ALIAS.get(nmk,nmk); apps[nmk]=apps.get(nmk,0)+f(b)
        for nmk,v in apps.items(): apppeak[nmk]=max(apppeak.get(nmk,0),v)
        dt=datetime.datetime.strptime(t,"%Y-%m-%d %H:%M:%S")
        ls.append({"t":dt.strftime("%b %-d"),"ft":dt.strftime("%b %-d, %-I:%M %p"),"memg":round(smem/1024,1),"swap":round(ssw)})
        approws.append(apps)
    topL=sorted(apppeak,key=apppeak.get,reverse=True)[:6]
    rollseries={"names":topL,"data":[[round(a.get(n,0)/1024,2) for a in approws] for n in topL]}
    return {"roll":ls,"rollseries":rollseries,"trend":compute_trend(ls,rollseries,rt)}
def build_data():
    raw=read_csv(RAW); roll=read_csv(ROLL); rts=list(raw.keys()); paths=live_paths()
    ram=(round(psutil.virtual_memory().total/1024**3) if psutil else 36)
    latest={}; li={"lvl":1}
    if rts:
        pl=raw[rts[-1]]; sd=sysd(pl); pr=sorted(procs_of(pl),reverse=True)
        li=level_info(pl); swap=sd.get("SYSTEM.swap_used_mb",0); cpun=sd.get("SYSTEM.cpu_total",0); ktn=0.0
        for _c,_n,_m in procs_of(pl):
            if 'kernel_task' in _n: ktn=_c
        latest={"cpu":round(sd.get("SYSTEM.cpu_total",0)),"memg":round(sd.get("SYSTEM.mem_used_mb",0)/1024,1),
                "swap":round(swap),"load":round(sd.get("SYSTEM.load1",0),1),"ts":rts[-1][11:16],
                "level":li,"pressure":pressure(swap),"comp":{"cpu":round(min(100,cpun)),"mem":round(min(100,swap/20.0)),"heat":round(min(100,ktn*4))},
                "topcpu":[[round(c,1),n,round(m)] for c,n,m in pr[:6]],
                "topmem":[[round(c,1),n,round(m)] for c,n,m in sorted(pr,key=lambda x:x[2],reverse=True)[:6]]}
    events=detect(raw); bz=busiest(raw)
    names=set()
    for p in latest.get("topcpu",[])+latest.get("topmem",[]): names.add(p[1])
    for e in events: names.add(e['culprit'])
    if li.get("culprit"): names.add(li["culprit"])
    if bz: names.add(bz['cul'])
    catalog={n:explain(n,paths) for n in names}
    rs=[]; pts=[]
    if rts:
        _ps=lambda x: datetime.datetime.strptime(x,"%Y-%m-%d %H:%M:%S")
        tend=_ps(rts[-1]); tcut=tend-datetime.timedelta(hours=24)
        widx=[i for i,t in enumerate(rts) if _ps(t)>=tcut]
        traw0=_ps(rts[widx[0]]); BMIN=5
        t0=traw0.replace(second=0,microsecond=0); t0=t0-datetime.timedelta(minutes=t0.minute%BMIN)
        total_min=(tend-t0).total_seconds()/60.0; NB=max(1,int(total_min//BMIN)+1)
        span_h=total_min/60.0
        tickmin=60
        bs=[[] for _ in range(NB)]
        for i in widx:
            bi=int((_ps(rts[i])-t0).total_seconds()/60.0//BMIN)
            if 0<=bi<NB: bs[bi].append(rts[i])
        for bi in range(NB):
            bt=t0+datetime.timedelta(minutes=bi*BMIN)
            label=bt.strftime("%-I %p") if ((bt.hour*60+bt.minute)%tickmin==0) else ""; ft=bt.strftime("%-I:%M %p")
            if bs[bi]:
                t=bs[bi][-1]; pl=raw[t]; sd=sysd(pl)
                rs.append({"t":label,"ft":ft,"cpu":round(sd.get("SYSTEM.cpu_total",0)),"memg":round(sd.get("SYSTEM.mem_used_mb",0)/1024,1),"swap":round(sd.get("SYSTEM.swap_used_mb",0))})
                grp={}
                for cmd,cpu,mem in pl:
                    if cmd.startswith("SYSTEM"): continue
                    g=appname(cmd); grp[g]=grp.get(g,0)+f(mem)
                pts.append(grp)
            else:
                rs.append({"t":label,"ft":ft,"cpu":None,"memg":None,"swap":None}); pts.append(None)
    peak={}
    for grp in pts:
        if not grp: continue
        for g,v in grp.items(): peak[g]=max(peak.get(g,0),v)
    topapps=sorted(peak,key=peak.get,reverse=True)[:5]
    memseries={"names":topapps,"labels":[r["t"] for r in rs],
               "data":[[(round(grp.get(g,0)/1024,2) if grp else None) for grp in pts] for g in topapps]}
    views={"7":rollup_view(roll,7),"30":rollup_view(roll,30),"all":rollup_view(roll,None)}
    directory=build_directory(paths)
    return {"total_ram_gb":ram,"updated":datetime.datetime.now().strftime("%H:%M:%S"),"latest":latest,
            "events":events,"busiest":bz,"catalog":catalog,"raw":rs,"memseries":memseries,"changelog":CHANGELOG,"directory":directory,"views":views}
TEMPLATE=r"""<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="60"><meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><meta http-equiv="Pragma" content="no-cache"><meta http-equiv="Expires" content="0"><title>DANISCOPE</title><link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCI+CjxyZWN0IHdpZHRoPSI2NCIgaGVpZ2h0PSI2NCIgcng9IjEzIiBmaWxsPSIjMWYyNDMwIi8+CjxwYXRoIGQ9Ik0zMiA4YzEyIDAgMTkgOSAxOSAyMiAwIDE1LTggMjUtMTkgMjVTMTMgNDUgMTMgMzBDMTMgMTcgMjAgOCAzMiA4eiIgZmlsbD0iI2Y0YjYzZSIgc3Ryb2tlPSIjNGEzMzE4IiBzdHJva2Utd2lkdGg9IjMiLz4KPGNpcmNsZSBjeD0iMTMuNSIgY3k9IjMzIiByPSI0IiBmaWxsPSIjZjRiNjNlIiBzdHJva2U9IiM0YTMzMTgiIHN0cm9rZS13aWR0aD0iMi41Ii8+CjxjaXJjbGUgY3g9IjUwLjUiIGN5PSIzMyIgcj0iNCIgZmlsbD0iI2Y0YjYzZSIgc3Ryb2tlPSIjNGEzMzE4IiBzdHJva2Utd2lkdGg9IjIuNSIvPgo8cGF0aCBkPSJNMTYgMzBjMCAxNyA3IDI1IDE2IDI1czE2LTggMTYtMjVjLTMgNi04IDktMTYgOXMtMTMtMy0xNi05eiIgZmlsbD0iIzVhM2ExZiIgc3Ryb2tlPSIjM2EyNTEyIiBzdHJva2Utd2lkdGg9IjIiLz4KPHBhdGggZD0iTTIxIDI3YzIuNS0yLjQgNi41LTIuNCA5IDAiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzRhMzMxOCIgc3Ryb2tlLXdpZHRoPSIyLjYiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8cGF0aCBkPSJNMzQgMjdjMi41LTIuNCA2LjUtMi40IDkgMCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNGEzMzE4IiBzdHJva2Utd2lkdGg9IjIuNiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+CjxlbGxpcHNlIGN4PSIyNS41IiBjeT0iMzEuNSIgcng9IjMuMiIgcnk9IjMuNyIgZmlsbD0iI2ZmZiIvPgo8ZWxsaXBzZSBjeD0iMzguNSIgY3k9IjMxLjUiIHJ4PSIzLjIiIHJ5PSIzLjciIGZpbGw9IiNmZmYiLz4KPGNpcmNsZSBjeD0iMjYiIGN5PSIzMiIgcj0iMS45IiBmaWxsPSIjNGU3ZDNmIi8+PGNpcmNsZSBjeD0iMzkiIGN5PSIzMiIgcj0iMS45IiBmaWxsPSIjNGU3ZDNmIi8+CjxjaXJjbGUgY3g9IjI2LjMiIGN5PSIzMS43IiByPSIuNyIgZmlsbD0iIzFhMWExOCIvPjxjaXJjbGUgY3g9IjM5LjMiIGN5PSIzMS43IiByPSIuNyIgZmlsbD0iIzFhMWExOCIvPgo8cGF0aCBkPSJNMzIgMzNjLTEgMy0yIDQuNS0zLjIgNS41IDEuMiAxIDMuNSAxIDQuNiAwIiBmaWxsPSJub25lIiBzdHJva2U9IiM0YTMzMTgiIHN0cm9rZS13aWR0aD0iMS43IiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KPGcgZmlsbD0iI2EwNmUzNCI+PGNpcmNsZSBjeD0iMjIiIGN5PSIzNSIgcj0iLjciLz48Y2lyY2xlIGN4PSIyNC41IiBjeT0iMzciIHI9Ii43Ii8+PGNpcmNsZSBjeD0iMjAuNSIgY3k9IjM3LjUiIHI9Ii42Ii8+PGNpcmNsZSBjeD0iNDIiIGN5PSIzNSIgcj0iLjciLz48Y2lyY2xlIGN4PSIzOS41IiBjeT0iMzciIHI9Ii43Ii8+PGNpcmNsZSBjeD0iNDMuNSIgY3k9IjM3LjUiIHI9Ii42Ii8+PC9nPgo8L3N2Zz4=">
<style>
body{font-family:-apple-system,Helvetica,Arial,sans-serif;background:#f6f6f4;color:#1a1a18;margin:0;padding:24px}
.wrap{max-width:860px;margin:0 auto;position:relative}h1{font-size:20px;font-weight:500;margin:0 0 2px}
.sub{color:#76756f;font-size:13px;margin:0 0 18px}.tabs{display:flex;gap:8px;flex-wrap:wrap}
.tab{padding:8px 16px;border:1px solid #e2e1da;border-radius:8px;background:#fff;cursor:pointer;font-size:14px}
.tab.on{background:#1a1a18;color:#fff;border-color:#1a1a18}
.switch{display:flex;gap:6px;align-items:center;font-size:12px;color:#76756f;margin:0 0 14px}
.sbtn{border:1px solid #e2e1da;background:#fff;color:#46453f;padding:6px 13px;border-radius:7px;cursor:pointer;font-size:12.5px}
.sbtn.on{background:#1a1a18;color:#fff;border-color:#1a1a18}
.verdict{border-radius:12px;padding:16px 20px;margin:0 0 8px;border:1px solid}
.headline{font-size:21px;font-weight:600;margin:0}.subl{font-size:14px;margin:4px 0 0;opacity:.85}
.tiles{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:14px 0 0}
.tile{background:#fff;border:1px solid #e6e5de;border-radius:10px;padding:11px 13px}
.tile .k{font-size:11px;color:#9a9994;margin:0 0 5px;text-transform:uppercase;letter-spacing:.03em}
.tile .v{font-size:19px;font-weight:600}.tile .v small{font-size:12px;font-weight:400;color:#76756f}
.panel{background:#fff;border:1px solid #e2e1da;border-radius:10px;padding:14px 18px;margin:14px 0 0}
.ev{display:flex;gap:10px;align-items:baseline;padding:8px 0;border-bottom:1px solid #efeee8;font-size:14px}
.tag{font-size:11px;padding:2px 8px;border-radius:6px;flex:none;font-weight:600}
.chk{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;border-radius:50%;color:#fff;font-size:12px;margin-right:6px;vertical-align:-3px;background:#52a02a}
.row{padding:6px 0;border-bottom:1px solid #efeee8;font-size:14px}.rowtop{display:flex;justify-content:space-between}
.eye{position:relative;cursor:help;color:#9a9994;margin-left:5px;font-size:13px}.eye:hover{color:#1a1a18}
.tip{display:none;position:absolute;bottom:20px;left:50%;transform:translateX(-50%);width:250px;background:#1a1a18;color:#f4f3ef;font-size:12px;line-height:1.5;font-weight:400;padding:9px 11px;border-radius:8px;box-shadow:0 8px 22px rgba(0,0,0,.25);z-index:60;text-align:left;white-space:normal;overflow-wrap:anywhere;word-break:break-word}
.tipR{left:auto;right:-2px;transform:none}.tipL{left:-2px;right:auto;transform:none}.eye:hover .tip{display:block}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:16px}.chart{position:relative;height:160px;margin:0 0 22px}
.lg{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:12px;color:#76756f;margin:0 0 6px}.lgi{display:inline-flex;align-items:center;gap:6px;cursor:pointer;user-select:none}.lgi.off{opacity:.6}.lgi input{display:none}.swbox{width:15px;height:15px;border-radius:4px;border:1.5px solid;display:inline-flex;align-items:center;justify-content:center;color:#fff;font-size:10px;font-weight:800;line-height:1}.lgi.off .swbox{background:transparent!important;color:transparent}.lgbtn{border:1px solid #d8d7d0;background:#fff;color:#5b5a54;font-size:11px;padding:3px 10px;border-radius:6px;cursor:pointer}.lgbtn:hover{background:#f0efe9}
.sw{width:10px;height:10px;border-radius:2px;display:inline-block;margin-right:4px;vertical-align:-1px}
.muted{color:#76756f;font-size:13px;margin:0 0 4px}.hide{display:none}.h{font-weight:600;font-size:15px;margin:0 0 8px}
.cog{background:none;border:none;font-size:20px;color:#9a9994;cursor:pointer;line-height:1;padding:4px}.cog:hover{color:#1a1a18}.modal{position:fixed;inset:0;background:rgba(20,22,28,.45);display:flex;align-items:center;justify-content:center;z-index:200}.modal.hide{display:none}.mbox{background:#fff;border-radius:14px;width:380px;max-width:90vw;box-shadow:0 20px 60px rgba(0,0,0,.3);overflow:hidden}.mhd{display:flex;justify-content:space-between;align-items:center;padding:13px 18px;border-bottom:1px solid #eee;font-weight:600;font-size:15px}.mhd span{cursor:pointer;color:#9a9994}.mhd span:hover{color:#1a1a18}.mb{padding:16px 18px}.mlbl{font-size:12px;color:#76756f;text-transform:uppercase;letter-spacing:.04em;margin:0 0 9px}.mb .switch{flex-wrap:wrap}.cl{max-height:240px;overflow:auto;font-size:13px}.clv{font-weight:600;margin:10px 0 3px}.cld{color:#9a9994;font-weight:400;font-size:12px}.cln{margin:0 0 6px;padding-left:18px;color:#46453f}.cln li{margin:2px 0;line-height:1.4}.dirq{width:100%;box-sizing:border-box;padding:9px 12px;border:1px solid #e2e1da;border-radius:8px;font-size:14px;margin:10px 0 4px;background:#fff}.dirhd{font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:#9a9994;margin:18px 0 4px}.dirhc{color:#bdbcb5;font-weight:500;margin-left:5px}.dirrow{display:flex;justify-content:space-between;gap:12px;padding:9px 0;border-bottom:1px solid #efeee8}.dirL{min-width:0}.dirn{font-size:14px;font-weight:500}.dirx{color:#9a9994;font-weight:400;font-size:12px}.note2{font-size:12px;color:#76756f;line-height:1.45;margin-top:2px}.dirM{color:#46453f;font-size:13px;white-space:nowrap}.comp{display:flex;gap:16px;margin:6px 0 2px}.cbar{flex:1;min-width:0}.cl2{font-size:12px;color:#76756f;display:flex;justify-content:space-between;margin-bottom:4px}.ctrack{height:8px;background:#eceae3;border-radius:5px;overflow:hidden}.cfill{height:100%;border-radius:5px}.tdivider{height:1px;background:#e7e6df;margin:16px 0 22px}.lgbreak{flex-basis:100%;height:0}.lg .lgbtn{margin-top:2px}.todayctl{margin:0 0 12px}.nav{position:sticky;top:0;z-index:100;background:#f6f6f4;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px 0;margin:0 0 18px;border-bottom:1px solid #e7e6df;flex-wrap:wrap}.brandtop{font-size:20px;font-weight:500}.bver{font-size:12px;color:#9a9994;font-weight:500;margin-left:3px}.bsub{color:#76756f;font-size:12px;margin-top:3px}.navr{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.invis{visibility:hidden}.trow{display:flex;align-items:baseline;gap:10px;padding:7px 0;border-bottom:1px solid #efeee8;font-size:14px}.tar{font-size:12px;flex:none;width:14px}.tk{font-weight:500;min-width:130px}.td{color:#76756f}.rsel{display:flex;gap:6px;margin:0 0 8px;position:sticky;top:64px;z-index:90;background:#f6f6f4;padding:6px 0}.rbtn,.tbtn{padding:5px 12px;border:1px solid #e2e1da;border-radius:7px;background:#fff;cursor:pointer;font-size:12.5px;color:#46453f}.rbtn.on,.tbtn.on{background:#1a1a18;color:#fff;border-color:#1a1a18}.cwrap{overflow-x:auto;overflow-y:hidden}.expanded .chart{width:2400px}.updind{border:none;cursor:pointer;font-size:12px;font-weight:600;padding:4px 9px;border-radius:7px}.updind.red{color:#8a2020;background:#fbe6e6}.updind.green{color:#2c5810;background:#e9f3dc}.updind.amber{color:#7a4408;background:#faedd6}.updopt{display:flex;align-items:center;gap:7px;font-size:13.5px;cursor:pointer}.updopt input{accent-color:#1a1a18}.updexp{font-size:12.5px;color:#76756f;line-height:1.5;margin:8px 0}</style></head><body><div class="wrap">
<header class="nav"><div class="brand"><div class="brandtop" style="display:flex;align-items:center;gap:10px"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="28" height="28" style="border-radius:6px;flex:none"><rect width="64" height="64" rx="13" fill="#1f2430"/><path d="M32 8c12 0 19 9 19 22 0 15-8 25-19 25S13 45 13 30C13 17 20 8 32 8z" fill="#f4b63e" stroke="#4a3318" stroke-width="3"/><circle cx="13.5" cy="33" r="4" fill="#f4b63e" stroke="#4a3318" stroke-width="2.5"/><circle cx="50.5" cy="33" r="4" fill="#f4b63e" stroke="#4a3318" stroke-width="2.5"/><path d="M16 30c0 17 7 25 16 25s16-8 16-25c-3 6-8 9-16 9s-13-3-16-9z" fill="#5a3a1f" stroke="#3a2512" stroke-width="2"/><path d="M21 27c2.5-2.4 6.5-2.4 9 0" fill="none" stroke="#4a3318" stroke-width="2.6" stroke-linecap="round"/><path d="M34 27c2.5-2.4 6.5-2.4 9 0" fill="none" stroke="#4a3318" stroke-width="2.6" stroke-linecap="round"/><ellipse cx="25.5" cy="31.5" rx="3.2" ry="3.7" fill="#fff"/><ellipse cx="38.5" cy="31.5" rx="3.2" ry="3.7" fill="#fff"/><circle cx="26" cy="32" r="1.9" fill="#4e7d3f"/><circle cx="39" cy="32" r="1.9" fill="#4e7d3f"/><circle cx="26.3" cy="31.7" r=".7" fill="#1a1a18"/><circle cx="39.3" cy="31.7" r=".7" fill="#1a1a18"/><path d="M32 33c-1 3-2 4.5-3.2 5.5 1.2 1 3.5 1 4.6 0" fill="none" stroke="#4a3318" stroke-width="1.7" stroke-linecap="round"/><g fill="#a06e34"><circle cx="22" cy="35" r=".7"/><circle cx="24.5" cy="37" r=".7"/><circle cx="20.5" cy="37.5" r=".6"/><circle cx="42" cy="35" r=".7"/><circle cx="39.5" cy="37" r=".7"/><circle cx="43.5" cy="37.5" r=".6"/></g></svg><span class="bname">DANISCOPE</span><span class="bver">v__VER__</span></div><div class="bsub">updated __UPDATED__ &middot; hover the &#9432; to learn what something is</div></div>
<div class="navr"><div class="tabs"><div class="tab on" data-t="now">Right now</div><div class="tab" data-t="today">Today</div><div class="tab" data-t="long">Long-term</div><div class="tab" data-t="dir">Look up</div></div><button id="gapbtn" class="lgbtn navgap invis"></button><button id="updind" class="updind"></button><button id="cog" class="cog" title="Settings">&#9881;</button></div></header>
<div id="settings" class="modal hide"><div class="mbox"><div class="mhd">Settings<span id="setx">&#10005;</span></div><div class="mb"><div class="mlbl">Header style</div><div class="switch"><button class="sbtn" data-s="light">Traffic light</button><button class="sbtn" data-s="defcon">DEFCON blocks</button><button class="sbtn" data-s="gauge">Gauge</button></div><button id="vhbtn" class="lgbtn" style="margin-top:20px">Version history</button><div id="changelog" class="cl hide"></div><button id="aboutbtn" class="lgbtn" style="margin-top:10px">About</button><div id="aboutbox" class="cl hide"><p style="margin:6px 0;line-height:1.5">DANISCOPE shows what your Mac is doing, live, in plain English. A small logger records resource use every 10 seconds in the background, and this page reads it and refreshes every 60 seconds. Hover the &#9432; next to anything to learn what it is. Everything stays on your Mac &mdash; nothing is sent anywhere.</p></div><div class="mlbl" style="margin-top:18px">Updates</div><label class="updopt"><input type="checkbox" id="updchk"> Check for updates weekly</label><p class="updexp">If you tick this, DANISCOPE pings GitHub once a week to ask one thing: is there a newer version? If there is, you will see a note here &mdash; installing is always your choice. This is the only connection this software makes from your Mac to the outside, and it sends nothing about you. Untick it anytime and just check for updates yourself.</p><div id="updavail" class="hide" style="margin-top:6px"><a href="https://github.com/timeforsomethingdifferent/Daniscope/releases/latest" target="_blank" style="color:#1f3d79">Download the latest version</a></div></div></div></div><div id="now"></div>
<div id="today" class="hide"><div class="rsel" id="trsel"><button class="tbtn" data-tr="1">1 hour</button><button class="tbtn" data-tr="6">6 hours</button><button class="tbtn" data-tr="12">12 hours</button><button class="tbtn" data-tr="24">24 hours</button><button id="tscale" class="tbtn" style="margin-left:auto"></button><button id="texp" class="tbtn"></button></div><div id="todayroundup"></div><div class="tdivider"></div>
<div class="muted">Total CPU used across the whole Mac (%)</div><div class="cwrap"><div class="chart"><canvas id="c1"></canvas></div></div>
<div class="muted">Total memory in use, and swap. Swap on the floor means no memory pressure.</div>
<div class="lg" id="lg2"></div><div class="cwrap"><div class="chart"><canvas id="c2"></canvas></div></div>
<div class="muted">Memory per app (GB) &mdash; today's 5 biggest, whoever they are. <span style="color:#9a9994;display:block;margin-top:3px">Scaled to the apps themselves, not your <span class="ramn"></span>GB of RAM &mdash; a tall line here does <b>not</b> mean the Mac is full.</span></div>
<div class="lg" id="lg3"></div><div class="cwrap"><div class="chart"><canvas id="c3"></canvas></div></div></div>
<div id="long" class="hide"><div class="rsel"><button class="rbtn" data-r="7">7 days</button><button class="rbtn" data-r="30">30 days</button><button class="rbtn" data-r="all">All</button><button id="lscale" class="rbtn" style="margin-left:auto"></button><button id="lexp" class="rbtn"></button></div><div id="longroundup"></div><div class="tdivider"></div>

<div class="muted">Memory by app over days (GB) &mdash; biggest apps over the period. <span style="color:#9a9994;display:block;margin-top:3px">Scaled to the apps themselves, not your <span class="ramn"></span>GB of RAM &mdash; a tall line here does <b>not</b> mean the Mac is full.</span></div><div class="lg" id="lg4"></div><div class="cwrap"><div class="chart"><canvas id="c4"></canvas></div></div>

<div class="muted">System memory + swap over days</div><div class="lg" id="lg5"></div><div class="cwrap"><div class="chart"><canvas id="c5"></canvas></div></div></div><div id="dir" class="hide"><div class="muted">Everything running on your Mac right now, grouped by app. Search to look anything up.</div><input id="dirq" class="dirq" placeholder="Search processes..."><div id="dirlist"></div></div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
var D=/*DATA*/;var L=D.latest||{};var CAT=D.catalog||{};var RAM=D.total_ram_gb||36;
document.querySelectorAll(".ramn").forEach(function(e){e.textContent=RAM;});
function esc(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
function nm(n,al){var info=CAT[n];if(!info)return esc(n);var c='tip'+(al==='r'?' tipR':(al==='l'?' tipL':''));return esc(n)+'<span class="eye">&#9432;<span class="'+c+'">'+esc(info)+'</span></span>';}
function proc(n,right,al){return '<div class="row"><div class="rowtop"><span>'+nm(n,al)+'</span><span class="muted" style="margin:0">'+right+'</span></div></div>';}
var LV=L.level||{lvl:1,name:'GREEN',head:'Running fine',sub:'',culprit:null,det:null,type:null};
var EV=D.events||[],BZ=D.busiest,PRz=L.pressure||'None';
var CL={1:{bg:'#e9f3dc',bd:'#bcd994',fg:'#2c5810',dot:'#52a02a'},2:{bg:'#faedd6',bd:'#ecc78f',fg:'#7a4408',dot:'#dd8a1c'},3:{bg:'#fbe6e6',bd:'#f1b0b0',fg:'#8a2020',dot:'#d83b3b'}};
var TG={Memory:{bg:'#faeeda',fg:'#633806'},Heat:{bg:'#fcebeb',fg:'#791f1f'},CPU:{bg:'#e7eefb',fg:'#1f3d79'}};
function curLine(){if(LV.lvl===1||!LV.culprit)return '';var t=LV.type||'CPU';var tg=TG[t]||TG.CPU;return '<div style="margin-top:9px;font-size:14px"><span class="tag" style="background:'+tg.bg+';color:'+tg.fg+'">'+t+'</span> Right now: '+nm(LV.culprit,'l')+' &mdash; '+esc(LV.det)+'</div>';}
function tilesBlock(){var c=CL[LV.lvl];var n=EV.length;var pk=BZ||{score:0,t:'—',cul:'—'};var lab="Peak intensity today";
 return '<div class="tiles"><div class="tile"><div class="k">Slowdowns today</div><div class="v" style="color:'+(n?CL[3].dot:c.dot)+'">'+n+'</div></div>'+
 '<div class="tile"><div class="k">'+lab+'</div><div class="v">'+pk.score+'%<small> &middot; '+pk.t+'</small></div><div class="muted" style="margin:3px 0 0;font-size:12px">'+nm(pk.cul,'l')+'</div></div>'+
 '</div>';
}
function listBlock(){var h='<div class="panel"><div class="h">What slowed you down today</div>';
 if(EV.length){h+=EV.map(function(e){var tg=TG[e.type]||TG.CPU;var w=e.start===e.end?e.start:e.start+'–'+e.end;return '<div class="ev"><span class="tag" style="background:'+tg.bg+';color:'+tg.fg+'">'+e.type+'</span><span>'+w+'</span><span>'+nm(e.culprit,'l')+' &middot; '+esc(e.det)+'</span></div>';}).join('');}
 else{h+='<div class="muted" style="font-size:14px"><span class="chk">&#10003;</span>No slowdowns today. Your Mac stayed healthy.</div>';}
 if(BZ){h+='<div class="muted" style="border-top:1px dashed #ddd;padding-top:9px;margin-top:11px;font-size:13px">Busiest moment (separate from the above): <b>'+BZ.score+'% intensity</b> at '+BZ.t+', '+nm(BZ.cul,'l')+'. '+(EV.length?'':'Not a slowdown, just the heaviest point of the day.')+'</div>';}
 return h+'</div>';
}
function heroLight(){var s=LV,c=CL[s.lvl];var lamp=function(l){var on=s.lvl===l;return '<div style="width:26px;height:26px;border-radius:50%;margin:5px auto;background:'+(on?CL[l].dot:'#3a3a38')+';box-shadow:'+(on?'0 0 12px '+CL[l].dot:'none')+'"></div>';};
 return '<div class="verdict" style="background:'+c.bg+';border-color:'+c.bd+'"><div style="display:flex;gap:18px;align-items:center"><div style="background:#222;border-radius:11px;padding:7px 6px">'+lamp(3)+lamp(2)+lamp(1)+'</div><div><div style="font-size:12px;letter-spacing:.06em;color:'+c.fg+';font-weight:700">LEVEL '+s.lvl+' OF 3 &middot; '+s.name+'</div><div class="headline" style="color:'+c.fg+'">'+s.head+'</div><div class="subl">'+s.sub+'</div>'+curLine()+'</div></div></div>'+tilesBlock();
}
function heroDefcon(){var s=LV;var blk=function(l){var on=s.lvl===l;var c=CL[l];return '<div style="flex:1;text-align:center;padding:13px 0;border-radius:9px;background:'+(on?c.bg:'#f0efe9')+';border:1.5px solid '+(on?c.bd:'#e6e5de')+';opacity:'+(on?1:.5)+'"><div style="font-size:22px;font-weight:700;color:'+(on?c.fg:'#a8a7a1')+'">'+l+'</div><div style="font-size:11px;font-weight:600;color:'+(on?c.fg:'#a8a7a1')+'">'+['','GREEN','AMBER','RED'][l]+'</div></div>';};
 return '<div class="verdict" style="background:#fff;border-color:#e2e1da"><div style="font-size:12px;color:#9a9994;letter-spacing:.05em;font-weight:600;margin-bottom:8px">STATUS LEVEL</div><div style="display:flex;gap:8px">'+blk(1)+blk(2)+blk(3)+'</div><div class="headline" style="margin-top:14px;color:'+CL[s.lvl].fg+'">'+s.head+'</div><div class="subl">'+s.sub+'</div>'+curLine()+'</div>'+listBlock();
}
function heroGauge(){var s=LV,c=CL[s.lvl];var ang={1:150,2:90,3:30}[s.lvl];var r=ang*Math.PI/180;var nx=100+70*Math.cos(r),ny=100-70*Math.sin(r);
 return '<div class="verdict" style="background:'+c.bg+';border-color:'+c.bd+'"><div style="display:flex;gap:20px;align-items:center;flex-wrap:wrap"><svg width="190" height="112" viewBox="0 0 200 118"><path d="M10,100 A90,90 0 0 1 55,22.06" fill="none" stroke="'+CL[1].dot+'" stroke-width="15" stroke-linecap="round"/><path d="M58,20.5 A90,90 0 0 1 142,20.5" fill="none" stroke="'+CL[2].dot+'" stroke-width="15"/><path d="M145,22.06 A90,90 0 0 1 190,100" fill="none" stroke="'+CL[3].dot+'" stroke-width="15" stroke-linecap="round"/><line x1="100" y1="100" x2="'+nx.toFixed(1)+'" y2="'+ny.toFixed(1)+'" stroke="#1a1a18" stroke-width="4" stroke-linecap="round"/><circle cx="100" cy="100" r="7" fill="#1a1a18"/></svg><div><div style="font-size:30px;font-weight:700;color:'+c.fg+';line-height:1">'+s.lvl+' &middot; '+s.name+'</div><div class="headline" style="margin-top:5px;color:'+c.fg+'">'+s.head+'</div><div class="subl">'+s.sub+'</div>'+curLine()+'</div></div></div>'+tilesBlock();
}
var STY={light:heroLight,defcon:heroDefcon,gauge:heroGauge},SNAME={light:'Traffic light',defcon:'DEFCON blocks',gauge:'Gauge'};
function paint(st){try{localStorage.setItem('hdrstyle',st);}catch(e){}document.querySelectorAll('.sbtn').forEach(function(b){b.classList.toggle('on',b.dataset.s===st);});document.getElementById('hero').innerHTML=STY[st]();}
var saved='light';try{saved=localStorage.getItem('hdrstyle')||'light';}catch(e){}
var cols='<div class="cols"><div><div class="muted">Top CPU now</div>'+(L.topcpu||[]).slice(0,5).map(function(p){return proc(p[1],p[0]+'%','l');}).join('')+'</div><div><div class="muted">Biggest memory now</div>'+(L.topmem||[]).slice(0,5).map(function(p){return proc(p[1],(p[2]/1024).toFixed(1)+' GB','r');}).join('')+'</div></div>';
document.getElementById('now').innerHTML='<div id="hero"></div>'+cols;
document.querySelectorAll('.sbtn').forEach(function(b){b.onclick=function(){paint(b.dataset.s);};});
paint(saved);
function showTab(id){document.querySelectorAll('.tab').forEach(function(x){x.classList.toggle('on',x.dataset.t===id)});['now','today','long','dir'].forEach(function(t){document.getElementById(t).classList.toggle('hide',t!==id)});try{localStorage.setItem('tab',id)}catch(e){}var _gb2=document.getElementById('gapbtn');if(_gb2)_gb2.classList.toggle('invis',id!=='today');window.dispatchEvent(new Event('resize'))}
document.querySelectorAll('.tab').forEach(function(t){t.onclick=function(){showTab(t.dataset.t)}});
var _st='now';try{_st=localStorage.getItem('tab')||'now'}catch(e){}showTab(_st);
var cog=document.getElementById('cog'),_set=document.getElementById('settings');if(cog){cog.onclick=function(){_set.classList.remove('hide')};document.getElementById('setx').onclick=function(){_set.classList.add('hide')};_set.onclick=function(e){if(e.target===_set)_set.classList.add('hide')};}
window.addEventListener('beforeunload',function(){try{localStorage.setItem('scroll',window.scrollY)}catch(e){}});
var _cl=D.changelog||[],_cle=document.getElementById('changelog');if(_cle){_cle.innerHTML=_cl.map(function(c){return '<div class="clv">v'+c.v+' <span class="cld">'+c.d+'</span></div><ul class="cln">'+c.notes.map(function(x){return '<li>'+esc(x)+'</li>'}).join('')+'</ul>';}).join('');}var _vh=document.getElementById('vhbtn');if(_vh){_vh.onclick=function(){document.getElementById('changelog').classList.toggle('hide')}}var _ab=document.getElementById('aboutbtn');if(_ab){_ab.onclick=function(){document.getElementById('aboutbox').classList.toggle('hide')}}var DIR=D.directory||[];function renderDir(q){q=(q||'').toLowerCase();var G={app:'Your apps',apple:'Apple / macOS system',other:'Other'};var html='';['app','apple','other'].forEach(function(cat){var items=DIR.filter(function(x){return x.cat===cat&&(x.n.toLowerCase().indexOf(q)>=0||(x.info||'').toLowerCase().indexOf(q)>=0)});if(!items.length)return;html+='<div class="dirhd">'+G[cat]+'<span class="dirhc">'+items.length+'</span></div>';html+=items.map(function(x){var mem=x.mem>=1024?(x.mem/1024).toFixed(1)+' GB':x.mem+' MB';return '<div class="dirrow"><div class="dirL"><div class="dirn">'+esc(x.n)+(x.c>1?' <span class="dirx">x'+x.c+'</span>':'')+'</div><div class="note2">'+esc(x.info||'')+'</div></div><div class="dirM">'+mem+'</div></div>';}).join('');});document.getElementById('dirlist').innerHTML=html||'<div class="muted" style="margin-top:14px">No matches.</div>';}var _dq=document.getElementById('dirq');if(_dq){_dq.oninput=function(){renderDir(this.value)};renderDir('');}var CP=L.comp||{cpu:0,mem:0,heat:0},_tr=document.getElementById('todayroundup');if(_tr){function _bar(lbl,v){var col=v>=85?CL[3].dot:(v>=60?CL[2].dot:CL[1].dot);return '<div class="cbar"><div class="cl2"><span>'+lbl+'</span><b>'+v+'</b></div><div class="ctrack"><div class="cfill" style="width:'+Math.min(100,v)+'%;background:'+col+'"></div></div></div>';}_tr.innerHTML='<div class="panel"><div class="h">Right now, by resource</div><div class="comp">'+_bar('CPU',CP.cpu)+_bar('Memory pressure',CP.mem)+_bar('Heat',CP.heat)+'</div><div class="muted" style="margin-top:9px;font-size:13px">Your overall status is the worst of these three. Right now you are '+(LV.name||'GREEN')+'.</div></div>';}
function mk(id,labels,dss,ymax,leg,cticks,fl){var _c=new Chart(document.getElementById(id),{type:'line',data:{labels:labels,datasets:dss},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:!!leg,position:'top',align:'start',labels:{usePointStyle:true,pointStyle:'rectRounded',boxWidth:8,boxHeight:8,padding:14,font:{size:11},color:'#5b5a54'}},tooltip:{usePointStyle:true,padding:10,boxPadding:4,titleColor:'#fff',bodyColor:'#eee',backgroundColor:'rgba(26,26,24,.95)',callbacks:{title:function(it){var _ch=it[0]&&it[0].chart;return (_ch&&_ch.$fl&&it.length)?_ch.$fl[it[0].dataIndex]:''}}}},elements:{point:{radius:0,hoverRadius:4,hitRadius:8}},hover:{mode:'index',intersect:false},scales:{x:(cticks?{ticks:{autoSkip:false,color:'#999',font:{size:10},maxRotation:0},grid:{display:false,drawTicks:false}}:{ticks:{maxTicksLimit:7,color:'#999',font:{size:10}},grid:{display:false}}),y:{beginAtZero:true,max:ymax,ticks:{color:'#999',font:{size:10}},grid:{color:'rgba(0,0,0,.06)'}}}}});_c.$fl=fl;return _c;}
function legend(ch,elid){var el=document.getElementById(elid);if(!el)return;el.innerHTML=ch.data.datasets.map(function(d,i){return '<label class="lgi"><input type="checkbox" data-i="'+i+'" checked><span class="swbox" style="background:'+d.borderColor+';border-color:'+d.borderColor+'">&#10003;</span>'+esc(d.label||'')+'</label>';}).join('')+'<div class="lgbreak"></div><button class="lgbtn" type="button"></button>';function setvis(cb,on){ch.setDatasetVisibility(+cb.dataset.i,on);cb.checked=on;cb.parentElement.classList.toggle("off",!on);}var btn=el.querySelector(".lgbtn");function sync(){var any=Array.prototype.some.call(el.querySelectorAll("input"),function(c){return c.checked;});btn.textContent=any?"Deselect all":"Select all";}el.querySelectorAll("input").forEach(function(cb){cb.onchange=function(){setvis(cb,cb.checked);ch.update();sync();};});btn.onclick=function(){var any=Array.prototype.some.call(el.querySelectorAll("input"),function(c){return c.checked;});var t=!any;el.querySelectorAll("input").forEach(function(cb){setvis(cb,t);});ch.update();sync();};sync();}
function scaleBtn(ch,elid,full,startFull){var el=document.getElementById(elid);if(!el)return;var key='scale_'+elid,st=null;try{st=localStorage.getItem(key);}catch(e){}var isFull=(st==null)?startFull:(st==='1');var b=document.createElement('button');b.className='lgbtn';b.type='button';function apply(){ch.options.scales.y.max=isFull?full:undefined;ch.update();b.textContent=isFull?'Fit to data':'Full scale';}b.onclick=function(){isFull=!isFull;try{localStorage.setItem(key,isFull?'1':'0');}catch(e){}apply();};el.appendChild(b);apply();}
var Rfull=D.raw||[],MSfull=D.memseries||{names:[],labels:[],data:[]},PAL=['#D85A30','#7F77DD','#1D9E75','#E0A100','#3FA7C4','#C2569B'];
var KMAP={'1':12,'6':72,'12':144,'24':1000000000};
var TRANGE='24';try{TRANGE=localStorage.getItem('trange')||'24'}catch(e){}
var gapsOn=true;try{gapsOn=(localStorage.getItem('gaps')||'1')==='1'}catch(e){}
var Trl,TFL,Gcpu,Gmemg,Gswap,MSc,Tmask,TlabC,TflC;
function loadTR(r){var k=KMAP[r]||1000000000,st=Math.max(0,Rfull.length-k);var R=Rfull.slice(st);Trl=R.map(function(x){return x.t});TFL=R.map(function(x){return x.ft});Gcpu=R.map(function(x){return x.cpu});Gmemg=R.map(function(x){return x.memg});Gswap=R.map(function(x){return x.swap==null?null:+(x.swap/1024).toFixed(2)});MSc={names:MSfull.names,labels:MSfull.labels.slice(st),data:MSfull.data.map(function(a){return a.slice(st)})};Tmask=[];R.forEach(function(x,i){if(x.cpu!=null)Tmask.push(i)});var Rc=Tmask.map(function(i){return R[i]}),s2=Math.max(1,Math.floor(Rc.length/8));TlabC=Rc.map(function(x,i){return (i%s2===0)?x.ft:''});TflC=Rc.map(function(x){return x.ft})}
function Tcmp(a){return Tmask.map(function(i){return a[i]})}
loadTR(TRANGE);
var c1c=mk('c1',Trl,[{label:'CPU %',data:Gcpu,borderColor:'#378ADD',backgroundColor:'rgba(55,138,221,.1)',fill:true,tension:.3,borderWidth:2}],undefined,false,true,TFL);
var c2c=mk('c2',Trl,[{label:'Memory GB',data:Gmemg,borderColor:'#1D9E75',backgroundColor:'rgba(29,158,117,.1)',fill:true,tension:.3,borderWidth:2},{label:'Swap GB',data:Gswap,borderColor:'#E24B4A',borderDash:[4,3],tension:.3,borderWidth:2}],RAM,false,true,TFL);legend(c2c,'lg2');
var c3c=mk('c3',MSc.labels,MSc.names.map(function(n,i){return {label:n,data:MSc.data[i],borderColor:PAL[i%PAL.length],tension:.3,borderWidth:2};}),undefined,false,true,TFL);legend(c3c,'lg3');
var VIEWS=D.views||{},LRANGE='all';try{LRANGE=localStorage.getItem('lrange')||'all'}catch(e){}
function _lv(){return VIEWS[LRANGE]||{roll:[],rollseries:{names:[],data:[]},trend:null}}
function _lds(v){return v.rollseries.names.map(function(n,i){return {label:n,data:v.rollseries.data[i],borderColor:PAL[i%PAL.length],tension:.3,borderWidth:2};})}
var _V0=_lv();
var c4c=mk('c4',_V0.roll.map(function(x){return x.t}),_lds(_V0),undefined,false,false,_V0.roll.map(function(x){return x.ft}));legend(c4c,'lg4');
var c5c=mk('c5',_V0.roll.map(function(x){return x.t}),[{label:'Memory GB',data:_V0.roll.map(function(x){return x.memg}),borderColor:'#378ADD',tension:.3,borderWidth:2},{label:'Swap GB',data:_V0.roll.map(function(x){return +(x.swap/1024).toFixed(2)}),borderColor:'#E24B4A',borderDash:[4,3],tension:.3,borderWidth:2}],RAM,false,false,_V0.roll.map(function(x){return x.ft}));legend(c5c,'lg5');
function setRange(r){LRANGE=r;try{localStorage.setItem('lrange',r)}catch(e){}var v=_lv();var ll=v.roll.map(function(x){return x.t}),lfl=v.roll.map(function(x){return x.ft});c4c.data.labels=ll;c4c.data.datasets=_lds(v);c4c.$fl=lfl;c4c.update();legend(c4c,'lg4');c5c.data.labels=ll;c5c.data.datasets[0].data=v.roll.map(function(x){return x.memg});c5c.data.datasets[1].data=v.roll.map(function(x){return +(x.swap/1024).toFixed(2)});c5c.$fl=lfl;c5c.update();renderTrend(v.trend);document.querySelectorAll('.rbtn').forEach(function(b){b.classList.toggle('on',b.dataset.r===r)})}
function applyToday(){var on=gapsOn,lab=on?Trl:TlabC,fl=on?TFL:TflC;c1c.data.labels=lab;c1c.data.datasets[0].data=on?Gcpu:Tcmp(Gcpu);c1c.$fl=fl;c1c.update();c2c.data.labels=lab;c2c.data.datasets[0].data=on?Gmemg:Tcmp(Gmemg);c2c.data.datasets[1].data=on?Gswap:Tcmp(Gswap);c2c.$fl=fl;c2c.update();c3c.data.labels=lab;c3c.data.datasets=MSc.names.map(function(n,i){return {label:n,data:on?MSc.data[i]:Tcmp(MSc.data[i]),borderColor:PAL[i%PAL.length],tension:.3,borderWidth:2}});c3c.$fl=fl;c3c.update();legend(c3c,'lg3')}
function setGaps(on){gapsOn=on;try{localStorage.setItem('gaps',on?'1':'0')}catch(e){}applyToday();var b=document.getElementById('gapbtn');if(b)b.textContent=on?'Hide gaps':'Show gaps'}
function setTR(r){TRANGE=r;try{localStorage.setItem('trange',r)}catch(e){}loadTR(r);applyToday();document.querySelectorAll('.tbtn').forEach(function(b){b.classList.toggle('on',b.dataset.tr===r)})}
document.querySelectorAll('.tbtn').forEach(function(b){b.onclick=function(){setTR(b.dataset.tr)}});
var _gb=document.getElementById('gapbtn');if(_gb){_gb.onclick=function(){setGaps(!gapsOn)}}
setTR(TRANGE);var _gbt=document.getElementById('gapbtn');if(_gbt)_gbt.textContent=gapsOn?'Hide gaps':'Show gaps';
function renderTrend(TR){var _lr=document.getElementById('longroundup');if(!_lr)return;if(!TR){_lr.innerHTML='<div class="panel"><div class="muted" style="font-size:14px">Not enough history yet for a trend &mdash; it needs a day or two of data. Check back soon.</div></div>';return;}var _arr=function(d){return d==='up'?'\u25B2':(d==='down'?'\u25BC':'\u2192');},_acol=function(d){return d==='up'?CL[2].dot:(d==='down'?CL[1].dot:'#9a9994');},_vp={heavier:'a bit heavier than it was',lighter:'a bit lighter than it was',steady:'about the same as it was'};_lr.innerHTML='<div class="panel"><div class="h">Over the last '+TR.days+' day'+(TR.days===1?'':'s')+'</div>'+TR.rows.map(function(r){return '<div class="trow"><span class="tar" style="color:'+_acol(r.dir)+'">'+_arr(r.dir)+'</span><span class="tk">'+esc(r.k)+'</span><span class="td">'+esc(r.detail)+'</span></div>';}).join('')+'<div class="muted" style="margin-top:8px;font-size:13px">Overall, your Mac is running '+_vp[TR.verdict]+'.</div></div>';}
document.querySelectorAll('.rbtn').forEach(function(b){b.onclick=function(){setRange(b.dataset.r)}});setRange(LRANGE);
var tFull=false;try{tFull=localStorage.getItem('tscale')==='1'}catch(e){}function setTScale(full){tFull=full;try{localStorage.setItem('tscale',full?'1':'0')}catch(e){}c2c.options.scales.y.max=full?RAM:undefined;c2c.update();c3c.options.scales.y.max=full?RAM:undefined;c3c.update();var b=document.getElementById('tscale');if(b)b.textContent=full?'Fit to data':'Full scale'}var _ts=document.getElementById('tscale');if(_ts){_ts.onclick=function(){setTScale(!tFull)}}setTScale(tFull);
var lFull=false;try{lFull=localStorage.getItem('lscale')==='1'}catch(e){}function setLScale(full){lFull=full;try{localStorage.setItem('lscale',full?'1':'0')}catch(e){}c4c.options.scales.y.max=full?RAM:undefined;c4c.update();c5c.options.scales.y.max=full?RAM:undefined;c5c.update();var b=document.getElementById('lscale');if(b)b.textContent=full?'Fit to data':'Full scale'}var _ls=document.getElementById('lscale');if(_ls){_ls.onclick=function(){setLScale(!lFull)}}setLScale(lFull);
function _stick(){var nv=document.querySelector('.nav');if(!nv)return;var h=nv.offsetHeight;document.querySelectorAll('.rsel').forEach(function(el){el.style.top=h+'px'})}_stick();window.addEventListener('resize',_stick);
var tExp=false;try{tExp=localStorage.getItem('texp')==='1'}catch(e){}function setTExp(on){tExp=on;try{localStorage.setItem('texp',on?'1':'0')}catch(e){}document.getElementById('today').classList.toggle('expanded',on);[c1c,c2c,c3c].forEach(function(c){c.resize()});var b=document.getElementById('texp');if(b)b.textContent=on?'Compress':'Expand'}var _te=document.getElementById('texp');if(_te){_te.onclick=function(){setTExp(!tExp)}}setTExp(tExp);
var lExp=false;try{lExp=localStorage.getItem('lexp')==='1'}catch(e){}function setLExp(on){lExp=on;try{localStorage.setItem('lexp',on?'1':'0')}catch(e){}document.getElementById('long').classList.toggle('expanded',on);[c4c,c5c].forEach(function(c){c.resize()});var b=document.getElementById('lexp');if(b)b.textContent=on?'Compress':'Expand'}var _le=document.getElementById('lexp');if(_le){_le.onclick=function(){setLExp(!lExp)}}setLExp(lExp);
var CURVER='__VER__';function vgt(a,b){a=String(a).replace(/^v/i,'').split('.').map(Number);b=String(b).replace(/^v/i,'').split('.').map(Number);for(var i=0;i<Math.max(a.length,b.length);i++){var x=a[i]||0,y=b[i]||0;if(x!==y)return x>y}return false}
function updRender(){var en=false;try{en=localStorage.getItem('updchk')==='1'}catch(e){}var latest='';try{latest=localStorage.getItem('updlatest')||''}catch(e){}var avail=en&&latest&&vgt(latest,CURVER);var ind=document.getElementById('updind');var cb=document.getElementById('updchk');if(cb)cb.checked=en;if(ind){if(!en){ind.className='updind red';ind.textContent='\u25CF Updates off'}else if(avail){ind.className='updind amber';ind.textContent='\u25CF Update available'}else{ind.className='updind green';ind.textContent='\u25CF Up to date'}}var ua=document.getElementById('updavail');if(ua)ua.classList.toggle('hide',!avail)}
function updCheck(){var en=false;try{en=localStorage.getItem('updchk')==='1'}catch(e){}if(!en)return;var last=0;try{last=+(localStorage.getItem('updlast')||0)}catch(e){}if(Date.now()-last<561600000)return;fetch('https://api.github.com/repos/timeforsomethingdifferent/Daniscope/contents/VERSION?ref=main').then(function(r){return r.json()}).then(function(j){if(j&&j.content){var v=atob(j.content.replace(/\s/g,'')).trim();try{localStorage.setItem('updlatest',v);localStorage.setItem('updlast',String(Date.now()))}catch(e){}updRender()}}).catch(function(){})}
var _ui=document.getElementById('updind');if(_ui)_ui.onclick=function(){var st=document.getElementById('settings');if(st)st.classList.remove('hide')};var _uc=document.getElementById('updchk');if(_uc)_uc.onchange=function(){try{localStorage.setItem('updchk',this.checked?'1':'0')}catch(e){}if(this.checked){try{localStorage.removeItem('updlast')}catch(e){}updCheck()}updRender()};updRender();updCheck();
try{var _sy=parseInt(localStorage.getItem('scroll')||'0',10);if(_sy)window.scrollTo(0,_sy)}catch(e){}
</script></body></html>"""
def write_html():
    d=build_data()
    open(HTML+".tmp","w").write(TEMPLATE.replace("/*DATA*/",json.dumps(d)).replace("__UPDATED__",d["updated"]).replace("__VER__",VERSION))
    os.replace(HTML+".tmp",HTML)
class Reuse(socketserver.TCPServer):
    allow_reuse_address=True
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*a,**k): super().__init__(*a,directory=GL,**k)
    def end_headers(self):
        self.send_header("Cache-Control","no-store, no-cache, must-revalidate, max-age=0"); self.send_header("Pragma","no-cache"); self.send_header("Expires","0")
        super().end_headers()
    def log_message(self,*a): pass
def serve():
    for _ in range(60):
        try:
            Reuse(("127.0.0.1",PORT),H).serve_forever(); return
        except OSError:
            time.sleep(1)
if __name__=="__main__":
    try: write_html()
    except Exception: pass
    threading.Thread(target=serve,daemon=True).start()
    while True:
        time.sleep(60)
        try: write_html()
        except Exception: pass
