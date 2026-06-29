#!/usr/bin/env python3
# Raw capture every 10s (last ~24h) + compact rollup every 5min (months)
# + rich detail buffer every 10s (last few hours) + automatic deep capture when
# a stall is detected. All no-admin. Every addition is wrapped so it can never
# break the core logging.
import psutil, time, os, datetime, subprocess, re
RAW  = os.path.expanduser("~/.daniscope/proc-log.csv")
ROLL = os.path.expanduser("~/.daniscope/rollup-log.csv")
DETAIL = os.path.expanduser("~/.daniscope/detail-log.csv")
RAW_MAX, ROLL_MAX = 150000, 500000
CPU_MIN, MEM_MIN = 0.3, 75.0
DETAIL_HOURS = 3                      # how much rich history to keep
TRIGGER_GAP  = 600                    # min seconds between auto-captures
STALL_PERSIST = 3                     # consecutive bad samples (~30s) before a capture
CORES = psutil.cpu_count(logical=True) or 8
os.makedirs(os.path.dirname(RAW), exist_ok=True)
if not os.path.exists(RAW):  open(RAW,"w").write("timestamp,command,cpu_pct,mem_mb\n")
if not os.path.exists(ROLL): open(ROLL,"w").write("timestamp,key,cpu_pct,mem_mb\n")
DETAIL_HEADER=("timestamp,mempress,cpu_total,load1,load5,mem_used_mb,swap_used_mb,"
  "compressor_pages,pageins,pageouts,swapins,swapouts,decompressions,"
  "disk_read_mb,disk_write_mb,stuck_count,windowserver_cpu,kernel_task_cpu,event\n")
if not os.path.exists(DETAIL): open(DETAIL,"w").write(DETAIL_HEADER)

def trim(path,maxn):
    try:
        ls=open(path).readlines()
        if len(ls)>maxn:
            keep=[ls[0]]+ls[-(maxn-1):]
            with open(path,"r+") as f: f.seek(0); f.writelines(keep); f.truncate()
    except Exception: pass
def trim_age(path,hours,maxn):
    try:
        ls=open(path).readlines()
        if len(ls)<2: return
        cut=(datetime.datetime.now()-datetime.timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        keep=[ls[0]]+[ln for ln in ls[1:] if ln[:19]>=cut]
        if len(keep)>maxn: keep=[keep[0]]+keep[-(maxn-1):]
        with open(path,"r+") as fp: fp.seek(0); fp.writelines(keep); fp.truncate()
    except Exception: pass

# ---- no-admin system probes (all guarded + timeout so they can't hang us) ----
def sh(cmd,timeout=4):
    try: return subprocess.run(cmd,capture_output=True,text=True,timeout=timeout).stdout
    except Exception: return ""
def get_vmstat():
    d={}
    for line in sh(["vm_stat"]).splitlines():
        m=re.match(r'(.+?):\s+([0-9]+)\.?\s*$',line)
        if m: d[m.group(1).strip()]=int(m.group(2))
    return d
def get_mempress():
    o=sh(["sysctl","-n","kern.memorystatus_vm_pressure_level"]).strip()
    try: return int(o)
    except Exception: return ""
def get_stuck():
    o=sh(["ps","-axo","stat="])
    if not o: return ""
    return sum(1 for t in o.split() if "U" in t)
def cap_dir():
    # auto-captures go to the project's diagnostics/ if the setup command recorded
    # the path; otherwise into ~/.daniscope/diagnostics. Either way they persist.
    try:
        pp=open(os.path.expanduser("~/.claude-monitor/project-path")).read().strip()
        if pp: d=os.path.join(pp,"diagnostics")
        else: raise ValueError
    except Exception:
        d=os.path.expanduser("~/.daniscope/diagnostics")
    try: os.makedirs(d,exist_ok=True)
    except Exception: pass
    return d

last_trigger=0.0
def deep_capture(reasons,busiest):
    """On a detected stall: write a rich snapshot + a 3s stack sample. No admin."""
    global last_trigger
    now=time.time()
    if now-last_trigger < TRIGGER_GAP: return ""
    last_trigger=now
    d=cap_dir(); stamp=datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    rep=os.path.join(d,"auto-slow-%s.txt"%stamp)
    try:
        with open(rep,"w") as f:
            f.write("DANISCOPE auto-capture %s\nreasons: %s\n\n"%(stamp,", ".join(reasons)))
            f.write("== memory_pressure ==\n"+ "".join(sh(["memory_pressure"]).splitlines(keepends=True)[-6:]))
            f.write("\n== vm_stat ==\n"+sh(["vm_stat"]))
            f.write("\n== top by cpu ==\n"+sh(["top","-l","1","-n","15","-o","cpu","-stats","pid,command,cpu,mem,state"],timeout=8))
            f.write("\n== stuck/uninterruptible ==\n")
            ps=sh(["ps","-axo","pid,stat,%cpu,%mem,comm"])
            f.write("\n".join(l for l in ps.splitlines() if l.split()[1:2] and "U" in l.split()[1]) or "(none)")
        if busiest:
            subprocess.run(["sample",str(busiest),"3","-file",os.path.join(d,"auto-sample-%s.txt"%stamp)],
                           capture_output=True,timeout=12)
    except Exception: pass
    return os.path.basename(rep)

cache={}
prev_vm={}
bad_streak=0
psutil.cpu_percent(None)
for p in psutil.process_iter():
    try: p.cpu_percent(None); cache[p.pid]=p
    except Exception: pass
cyc=0
while True:
    time.sleep(10); cyc+=1
    ts=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows=[]; seen=set(); allp=[]; best=(0.0,None,"")
    for pid in psutil.pids():
        seen.add(pid)
        try:
            pr=cache.get(pid)
            if pr is None:
                pr=psutil.Process(pid); pr.cpu_percent(None); cache[pid]=pr; continue
            cpu=pr.cpu_percent(None); mem=pr.memory_info().rss/1048576; nm=pr.name().replace(","," ")
            allp.append((cpu,nm,mem))
            if cpu>best[0] and "kernel_task" not in nm: best=(cpu,pid,nm)
            if cpu>CPU_MIN or mem>MEM_MIN: rows.append((round(cpu,1),nm,round(mem,1)))
        except Exception: cache.pop(pid,None)
    for pid in list(cache):
        if pid not in seen: cache.pop(pid,None)
    syscpu=psutil.cpu_percent(None); vm=psutil.virtual_memory(); sw=psutil.swap_memory()
    try: la=os.getloadavg(); load1,load5=la[0],la[1]
    except Exception: load1=load5=0
    out=["%s,SYSTEM.cpu_total,%.1f,\n"%(ts,syscpu),
         "%s,SYSTEM.mem_used_mb,,%.0f\n"%(ts,vm.used/1048576),
         "%s,SYSTEM.swap_used_mb,,%.0f\n"%(ts,sw.used/1048576),
         "%s,SYSTEM.load1,%.2f,\n"%(ts,load1)]
    rows.sort(reverse=True)
    out+=["%s,%s,%s,%s\n"%(ts,n,c,m) for c,n,m in rows]
    try: open(RAW,"a").write("".join(out))
    except Exception: pass

    # ---- rich detail buffer + auto-capture (all guarded) ----
    try:
        mp=get_mempress(); vmd=get_vmstat(); stuck=get_stuck()
        ws=kt=0.0
        for cpu,nm,mem in allp:
            if nm=="WindowServer": ws=cpu
            elif "kernel_task" in nm: kt=cpu
        try:
            dio=psutil.disk_io_counters(); drd=dio.read_bytes/1048576; dwr=dio.write_bytes/1048576
        except Exception: drd=dwr=""
        g=lambda k: vmd.get(k,"")
        # decide if this looks like a stall (GUESSED thresholds - tune with data)
        reasons=[]
        if isinstance(mp,int) and mp>=4: reasons.append("memory pressure critical")
        if isinstance(stuck,int) and stuck>=1: reasons.append("%d stuck process(es)"%stuck)
        if load1>=CORES and syscpu<50: reasons.append("load %.1f vs %d cores, CPU %.0f%%"%(load1,CORES,syscpu))
        if prev_vm:
            dpo=g("Pageouts")-prev_vm.get("Pageouts",0) if isinstance(g("Pageouts"),int) else 0
            dso=g("Swapouts")-prev_vm.get("Swapouts",0) if isinstance(g("Swapouts"),int) else 0
            if dso>0 or (isinstance(dpo,int) and dpo>30000): reasons.append("paging out")
        bad_streak = bad_streak+1 if reasons else 0
        event=""
        if reasons and bad_streak>=STALL_PERSIST:
            fn=deep_capture(reasons,best[1])
            event=("CAPTURED:"+fn) if fn else "stall(%s)"%(";".join(reasons))
        elif reasons:
            event="watch(%s)"%(";".join(reasons))
        prev_vm=vmd if vmd else prev_vm
        drow=("%s,%s,%.1f,%.2f,%.2f,%.0f,%.0f,%s,%s,%s,%s,%s,%s,%s,%s,%s,%.1f,%.1f,%s\n"%(
            ts,mp,syscpu,load1,load5,vm.used/1048576,sw.used/1048576,
            g("Pages occupied by compressor"),g("Pageins"),g("Pageouts"),
            g("Swapins"),g("Swapouts"),g("Decompressions"),
            (round(drd,1) if drd!="" else ""),(round(dwr,1) if dwr!="" else ""),
            stuck,ws,kt,event))
        open(DETAIL,"a").write(drow)
    except Exception: pass

    if cyc%30==0:
        trim_age(RAW,24,400000)
        trim_age(DETAIL,DETAIL_HOURS,100000)
        grp={}
        for cpu,nm,mem in allp:
            gname=nm.split(" Helper")[0]
            c0,m0=grp.get(gname,(0.0,0.0)); grp[gname]=(c0+cpu,m0+mem)
        kt=0.0
        for cpu,nm,mem in allp:
            if 'kernel_task' in nm: kt=cpu
        rb=["%s,SYSTEM.cpu_total,%.1f,\n"%(ts,syscpu),
            "%s,SYSTEM.mem_used_mb,,%.0f\n"%(ts,vm.used/1048576),
            "%s,SYSTEM.swap_used_mb,,%.0f\n"%(ts,sw.used/1048576),
            "%s,SYSTEM.load1,%.2f,\n"%(ts,load1),
            "%s,kernel_task,%.1f,\n"%(ts,kt)]
        for gname,(c,m) in sorted(grp.items(),key=lambda x:x[1][1],reverse=True)[:8]:
            rb.append("%s,app.%s,%.1f,%.0f\n"%(ts,gname.replace(",", " "),c,m))
        try: open(ROLL,"a").write("".join(rb)); trim_age(ROLL,4392,ROLL_MAX)
        except Exception: pass
