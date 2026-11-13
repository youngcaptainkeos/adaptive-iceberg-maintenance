from pathlib import Path
import json,hashlib,re,datetime,traceback
root=Path('/media/shashank/Data1/PDocuments/Capstone/implementation')
out=root/'results/research_documentation_integrity_20261113_01'
out.mkdir(exist_ok=False)
report={'status':'running','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'documentation and final-source binding; no scientific experiment'}
try:
    m=json.loads((root/'docs/research_program_2026-11-13/ARTIFACT_MANIFEST.json').read_text())
    for p,v in m['files'].items():
        assert hashlib.sha256((root/p).read_bytes()).hexdigest()==v['sha256'],p
    checked=0
    for p in (root/'docs/research_program_2026-11-13').glob('*.md'):
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',p.read_text()):
            if '://' in target or target.startswith('#'):continue
            assert (p.parent/target.split('#')[0]).exists(),(p.name,target)
            checked+=1
    program=json.loads((root/'three_model_maintenance/protocols/research_program_20261113.json').read_text())
    cat=(root/'docs/research_program_2026-11-13/02_experiment_catalogue.md').read_text()
    assert re.findall(r'^## (E\d+) —',cat,re.M)==[e['id'] for e in program['experiments']]
    for e in program['experiments']:
        for field in ('question','intervention','held_fixed','evidence','continue_if','stop_if'):
            assert e[field] in cat,(e['id'],field)
    src=json.loads((root/'results/research_saved_regression_20261113_02/registration.json').read_text())['code_sha256']
    for p,h in src.items():assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h,p
    append=json.loads((root/'results/research_saved_regression_20261113_02/methodology_append_receipt.json').read_text())
    for p,v in append.items():
        raw=(root/p).read_bytes()
        assert hashlib.sha256(raw[:v['original_bytes']]).hexdigest()==v['original_sha256'],p
        assert hashlib.sha256(raw).hexdigest()==v['final_sha256'],p
    report.update(status='passed_package_links_registry_and_source_binding',files=len(m['files']),local_links=checked,experiment_cards=len(program['experiments']),historical_methodology_prefix_preserved=True)
except Exception as e:
    report.update(status='failed_preserved',error=str(e),traceback=traceback.format_exc())
    raise
finally:
    report['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
