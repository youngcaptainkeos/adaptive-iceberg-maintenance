"""User-authorized failure notifications; never change the failed run's status."""
import json,urllib.request
from pathlib import Path
from datetime import datetime,timezone

def notify_failure(label,detail,receipt):
    record={'label':label,'failure_detail':detail,'attempted_utc':datetime.now(timezone.utc).isoformat()}
    try:
        cfg=json.loads((Path(__file__).resolve().parents[2]/'docs/experiment_protocols/failure_notifications.json').read_text())
        request=urllib.request.Request(cfg['topic_url'],data=(label+'\n'+detail).encode(),method='POST',
                                       headers={'Title':'Capstone run failed','Tags':'warning'})
        with urllib.request.urlopen(request,timeout=cfg['timeout_seconds']) as response:
            record.update(status='notification_delivered',http_status=response.status,response=json.load(response))
    except Exception as exc:record.update(status='notification_delivery_failed',error=str(exc))
    try:
        with Path(receipt).open('x') as stream:json.dump(record,stream,indent=2);stream.write('\n')
    except Exception as exc:print('Could not persist notification receipt: '+str(exc),flush=True)
    print(json.dumps(record),flush=True)
    return record
