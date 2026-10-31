"""Bounded process samples: command names only, never arguments or model thinking."""
import argparse,json,subprocess,time,os,signal
from pathlib import Path


def sample():
    result=subprocess.run(['ps','-eo','pid,ppid,pcpu,pmem,rss,etime,comm'],capture_output=True,text=True,timeout=5,check=True)
    rows=[line for line in result.stdout.splitlines()[1:] if any(name in line.split()[-1].lower() for name in ('ollama','llama','python'))]
    return {'epoch':round(time.time(),3),'process_columns':'pid ppid pcpu pmem rss_kib etime comm',
        'processes':rows[:32],'process_names_only':True}


def monitor(path,*,duration=2700):
    end=time.monotonic()+duration;records=[]
    while time.monotonic()<end:
        try:records.append(sample())
        except (OSError,subprocess.SubprocessError) as e:records.append({'error_type':type(e).__name__})
        while len(json.dumps(records).encode())>262144:records.pop(0)
        tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(records));tmp.replace(path)
        time.sleep(2)


def stop_owned(pids,*,grace=5):
    tracked={int(p) for p in pids if str(p).isdigit() and int(p)>1}
    tracked.discard(os.getpid());child_tracking=True
    try:
        rows=subprocess.check_output(['ps','-eo','pid,ppid'],text=True,stderr=subprocess.DEVNULL,timeout=5).splitlines()[1:]
        pairs=[tuple(map(int,row.split())) for row in rows]
        for _ in range(32):
            children={pid for pid,parent in pairs if parent in tracked and pid>1}
            if children<=tracked:break
            tracked|=children
    except (OSError,subprocess.SubprocessError,ValueError):child_tracking=False
    def live(pid):
        try:os.kill(pid,0)
        except ProcessLookupError:return False
        except PermissionError:return True
        try:
            value=Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')',1)[1].split()[0]
            return value!='Z'
        except FileNotFoundError:return True # missing proc metadata is not proof of termination
        except (OSError,IndexError):return True
    def send(sig):
        for pid in sorted(tracked,reverse=True):
            if live(pid):
                try:os.kill(pid,sig)
                except (ProcessLookupError,PermissionError):pass
    send(signal.SIGTERM);end=time.monotonic()+grace
    while any(live(pid) for pid in tracked) and time.monotonic()<end:time.sleep(.1)
    send(signal.SIGKILL);end=time.monotonic()+1
    while any(live(pid) for pid in tracked) and time.monotonic()<end:time.sleep(.1)
    return {'tracked_owned_pids':sorted(tracked),'all_stopped':not any(live(pid) for pid in tracked),
            'child_tracking_succeeded':child_tracking,'command_arguments_recorded':False}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--stop',action='store_true');a=p.parse_args()
    if a.stop:
        result=stop_owned([os.environ.get('A09_OLLAMA_PID',''),os.environ.get('A09_SAMPLER_PID','')])
        a.out.write_text(json.dumps(result,indent=2)+'\n')
    else:monitor(a.out)
