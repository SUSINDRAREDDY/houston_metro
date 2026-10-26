"""Capture bounded HPA telemetry while the separate load-test Job runs."""
import datetime,json,subprocess,time
from pathlib import Path
out=Path('deliverables/milestone5/evidence')
with (out/'scaling-observations.jsonl').open('a') as stream:
    for _ in range(30):
        result=subprocess.run(['kubectl','get','hpa','metroai','-n','metroai','-o','json'],capture_output=True,text=True,timeout=20)
        if result.returncode==0:
            data=json.loads(result.stdout)
            stream.write(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':data.get('status',{})})+'\n');stream.flush()
        time.sleep(10)
