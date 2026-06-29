#!/usr/bin/env python3
# Raw capture every 10s (last ~7h) + compact rollup every 5min (months).
import psutil, time, os, datetime
RAW  = os.path.expanduser("~/.daniscope/proc-log.csv")
ROLL = os.path.expanduser("~/.daniscope/rollup-log.csv")
RAW_MAX, ROLL_MAX = 150000, 500000
CPU_MIN, MEM_MIN = 0.3, 75.0
os.makedirs(os.path.dirname(RAW), exist_ok=True)
if not os.path.exists(RAW):  open(RAW,"w").write("timestamp,command,cpu_pct,mem_mb\n")
if not os.path.exists(ROLL): open(ROLL,"w").write("timestamp,key,cpu_pct,mem_mb\n")
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
cache={}
psutil.cpu_percent(None)
for p in psutil.process_iter():
    try: p.cpu_percent(None); cache[p.pid]=p
    except Exception: pass
cyc=0
while True:
    time.sleep(10); cyc+=1
    ts=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows=[]; seen=set(); allp=[]
    for pid in psutil.pids():
        seen.add(pid)
        try:
            pr=cache.get(pid)
            if pr is None:
                pr=psutil.Process(pid); pr.cpu_percent(None); cache[pid]=pr; continue
            cpu=pr.cpu_percent(None); mem=pr.memory_info().rss/1048576; nm=pr.name().replace(","," ")
            allp.append((cpu,nm,mem))
            if cpu>CPU_MIN or mem>MEM_MIN: rows.append((round(cpu,1),nm,round(mem,1)))
        except Exception: cache.pop(pid,None)
    for pid in list(cache):
        if pid not in seen: cache.pop(pid,None)
    syscpu=psutil.cpu_percent(None); vm=psutil.virtual_memory(); sw=psutil.swap_memory()
    try: load1=os.getloadavg()[0]
    except Exception: load1=0
    out=["%s,SYSTEM.cpu_total,%.1f,\n"%(ts,syscpu),
         "%s,SYSTEM.mem_used_mb,,%.0f\n"%(ts,vm.used/1048576),
         "%s,SYSTEM.swap_used_mb,,%.0f\n"%(ts,sw.used/1048576),
         "%s,SYSTEM.load1,%.2f,\n"%(ts,load1)]
    rows.sort(reverse=True)
    out+=["%s,%s,%s,%s\n"%(ts,n,c,m) for c,n,m in rows]
    try: open(RAW,"a").write("".join(out))
    except Exception: pass
    if cyc%30==0:
        trim_age(RAW,24,400000)
        grp={}
        for cpu,nm,mem in allp:
            g=nm.split(" Helper")[0]
            c0,m0=grp.get(g,(0.0,0.0)); grp[g]=(c0+cpu,m0+mem)
        kt=0.0
        for cpu,nm,mem in allp:
            if 'kernel_task' in nm: kt=cpu
        rb=["%s,SYSTEM.cpu_total,%.1f,\n"%(ts,syscpu),
            "%s,SYSTEM.mem_used_mb,,%.0f\n"%(ts,vm.used/1048576),
            "%s,SYSTEM.swap_used_mb,,%.0f\n"%(ts,sw.used/1048576),
            "%s,SYSTEM.load1,%.2f,\n"%(ts,load1),
            "%s,kernel_task,%.1f,\n"%(ts,kt)]
        for g,(c,m) in sorted(grp.items(),key=lambda x:x[1][1],reverse=True)[:8]:
            rb.append("%s,app.%s,%.1f,%.0f\n"%(ts,g.replace(",", " "),c,m))
        try: open(ROLL,"a").write("".join(rb)); trim_age(ROLL,4392,ROLL_MAX)
        except Exception: pass
