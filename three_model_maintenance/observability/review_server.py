"""Read-only review dashboard from actual process/REST and saved event evidence."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import html
from http.server import BaseHTTPRequestHandler,HTTPServer
import json
from pathlib import Path
import subprocess
import urllib.request


class EventSummary:
    def __init__(self,path):
        self.path=path;self.offset=0;self.counts=Counter();self.states={};self.latencies=[];self.layouts=[];self.terminal=False

    def read(self):
        if self.path.exists():
            with self.path.open() as stream:
                stream.seek(self.offset)
                while True:
                    start=stream.tell();line=stream.readline()
                    if not line or not line.endswith('\n'):stream.seek(start);break
                    r=json.loads(line);kind=r['kind'];self.counts[kind]+=1
                    if kind=='queue_transition':self.states[r['source']['source_query_id']]=r['state']
                    if kind=='statement_completed' and r['role']=='trace_query':self.latencies.append(r['client_elapsed_ns']/1e6)
                    if kind in ('common_horizon_initial_state','common_horizon_final_state'):self.layouts.append(dict(phase=kind,state=r['file_state']))
                    if kind=='terminal_engine_archive_checkpoint' and r['terminal']:self.terminal=True
                self.offset=stream.tell()
        return dict(event_counts=dict(self.counts),queue_states=dict(Counter(self.states.values())),
            completed_query_service_ms=self.latencies,layouts=self.layouts,terminal_archive_captured=self.terminal)


def run(protocol):
    cfg=json.loads(protocol.read_text());out=Path(cfg['evidence_directory']);out.mkdir(parents=True,exist_ok=True)
    summary=EventSummary(Path(cfg['episode_directory'])/'events.jsonl')
    def snapshot():
        now=datetime.now(timezone.utc);campaign=Path(cfg['campaign_directory'])
        result=campaign/'result.json';progress=campaign/'progress.json'
        state=json.loads((result if result.exists() else progress).read_text()) if result.exists() or progress.exists() else None
        error=None;active=None
        try:
            with urllib.request.urlopen(cfg['spark_jobs_url'],timeout=cfg['rest_timeout_seconds']) as response:active=json.load(response)
        except Exception as exc:error=str(exc)
        processes=subprocess.check_output(['ps','-eo','pid,ppid,etime,stat,args'],text=True)
        processes='\n'.join(line for line in processes.splitlines() if any(s in line for s in ('SparkSubmit','three_model_maintenance','run_with_failure_alert')))
        data=dict(observed_utc=now.isoformat(),hostname=subprocess.check_output(['hostname'],text=True).strip(),
            campaign_id=cfg['campaign_id'],campaign_evidence='historical_saved' if result.exists() else 'current_progress_unaccepted',
            campaign=state,live_spark_running_jobs=active,live_spark_error=error,live_processes=processes,
            measured=summary.read(),model_status='No SF10 fitted/calibrated model or scheduling benefit accepted')
        cap=Path(cfg['historical_compaction_file'])
        data['separate_historical_compaction']=dict(source=str(cap),evidence=json.loads(cap.read_text()) if cap.exists() else None)
        name=now.strftime('%Y%m%dT%H%M%S_%fZ')+'.json';(out/name).write_text(json.dumps(data,indent=2)+'\n')
        data['snapshot_file']=name
        return data
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ('/','/api/status','/processes','/audit'):
                self.send_error(404);return
            data=snapshot()
            if self.path=='/api/status':body=json.dumps(data).encode();mime='application/json'
            elif self.path in ('/processes','/audit'):
                title='LIVE remote process listing' if self.path=='/processes' else 'HISTORICAL saved campaign audit status — not accepted'
                value=data['live_processes'] if self.path=='/processes' else json.dumps(data['campaign'],indent=2)
                body=('<html><meta charset="utf-8"><style>body{background:#101827;color:#e5edf8;font:18px system-ui;padding:28px}pre{font:15px monospace;white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>'+title+'</h1><p>'+html.escape(data['observed_utc']+' | '+data['hostname']+' | '+data['campaign_id'])+'</p><pre>'+html.escape(value)+'</pre></html>').encode();mime='text/html; charset=utf-8'
            else:
                encoded=json.dumps(data).replace('<',r'\u003c')
                body=(PAGE.replace('__DATA__',encoded)).encode();mime='text/html; charset=utf-8'
            self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    server=HTTPServer(('127.0.0.1',cfg['dashboard_port']),Handler);server.timeout=1
    print(json.dumps(dict(status='dashboard_listening',port=cfg['dashboard_port'])),flush=True)
    while datetime.now(timezone.utc)<datetime.fromisoformat(cfg['display_until_utc']):server.handle_request()
    server.server_close()


PAGE='''<!doctype html><html><meta charset="utf-8"><title>ESA Review 26 · Iceberg Evidence</title><style>
body{background:#101827;color:#e5edf8;font:17px system-ui;margin:30px}h1{font-size:30px;margin:0}small{color:#a5b4ce}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:20px 0}.box{background:#1b2940;border:1px solid #344560;border-radius:12px;padding:18px}.v{font-size:30px;font-weight:700;margin:8px 0}.warn{color:#ffc76b}pre{font:12px monospace;white-space:pre-wrap;overflow-wrap:anywhere}svg{width:100%;height:180px}h2{font-size:20px}p{line-height:1.45}</style>
<h1>ESA Review 26 · Forecast-aware Iceberg Maintenance</h1><p id="stamp"></p><small>Live service observations and historical experiment evidence are labelled separately. Missing values remain unknown.</small>
<div class="grid" id="cards"></div><div class="box"><h2>Historical completed-query SQL service times (ms)</h2><p>Last 240 recorded calls shown; arrival workload is not thinned. Failed episode — these are diagnostic observations, not accepted training labels.</p><svg id="chart" viewBox="0 0 1200 180"></svg></div>
<div class="grid"><div class="box"><h2>Actual table layouts</h2><pre id="layout"></pre></div><div class="box"><h2>Recorded queue outcomes</h2><pre id="queue"></pre></div><div class="box"><h2>Audit / model status</h2><pre id="audit"></pre></div></div><div class="box"><h2>LIVE worker3 process snapshot</h2><pre id="process"></pre></div>
<script>let d=__DATA__;const el=id=>document.getElementById(id);function draw(d){el('stamp').textContent=`Observed ${d.observed_utc} | Host ${d.hostname} | Campaign ${d.campaign_id} | ${d.campaign_evidence}`;let c=d.campaign||{},m=d.measured;el('cards').replaceChildren();for(let [k,v] of [['Historical episode status',c.status||'unknown'],['Recorded passed / failed / unattempted',[c.passed_episodes??'?',c.failed_episodes??'?',c.unattempted_episodes??'?'].join(' / ')],['LIVE active Spark jobs',d.live_spark_running_jobs===null?'unavailable':d.live_spark_running_jobs.length]]){let b=document.createElement('div');b.className='box';let t=document.createElement('small');t.textContent=k;let vEl=document.createElement('div');vEl.className='v warn';vEl.textContent=v;b.append(t,vEl);el('cards').append(b)}el('layout').textContent=JSON.stringify({campaign:m.layouts,separate_historical_capability:d.separate_historical_compaction},null,2);el('queue').textContent=JSON.stringify(m.queue_states,null,2);el('audit').textContent=`Terminal task archive: ${m.terminal_archive_captured}\n${c.error||''}\n${d.model_status}\n${d.live_spark_error||''}`;el('process').textContent=d.live_processes;let a=m.completed_query_service_ms.slice(-240),max=Math.max(...a,1);el('chart').replaceChildren();if(a.length){let p=document.createElementNS('http://www.w3.org/2000/svg','polyline');p.setAttribute('points',a.map((v,i)=>`${i*1200/Math.max(a.length-1,1)},${170-v/max*160}`).join(' '));p.setAttribute('fill','none');p.setAttribute('stroke','#54d6b4');p.setAttribute('stroke-width','2');el('chart').append(p)}}draw(d);setInterval(()=>fetch('/api/status').then(r=>r.json()).then(draw).catch(e=>{el('stamp').textContent='LIVE refresh unavailable: '+e}),15000);</script></html>'''


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--protocol',type=Path,required=True);a=p.parse_args();run(a.protocol)
