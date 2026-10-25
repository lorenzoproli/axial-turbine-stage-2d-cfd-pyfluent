"""Verify immutable baseline inputs; a new native audit requires a clean project."""
from common import *
import argparse
EXPECTED = {'stadio_assiale_2D_CFD_final.cas.h5': 'c9f78c24b1a5263f655136f0c1a632ba4276c2eec23a6e1b02622d7276378f7b', 'stadio_assiale_2D_CFD_final.dat.h5': '1038a1e420ebfa1a47a87d002627b207c05b8016d12ff650990773d737710be1'}

def verify():
    rows = []
    for name, expected in EXPECTED.items():
        p = original_path(name)
        actual = sha(p)
        if actual != expected:
            raise RuntimeError('Historical baseline checksum changed: ' + name)
        rows.append(dict(file=str(p), byte=p.stat().st_size, sha256=actual, esito='VERIFICATO'))
    return rows

def new_audit():
    from cfd import ensure_campaign_open
    ensure_campaign_open()
    assert not (AUDIT / 'audit_baseline.json').exists() and (not (WORK / 'checkpoint_comune').exists()), 'Audit esistente: non ripeterlo o sovrascriverlo. Usare una copia indipendente con soli input e codice.'
    verify()
    prepare_input()
    from cfd import launch
    from transcript_utils import close_transcript
    from quality_export import export_quality
    s = launch(WORK / 'launcher' / ('audit_' + datetime.now().strftime('%Y%m%d_%H%M%S')))
    try:
        s.transcript.start(file_name=str(AUDIT / 'audit_fluent.trn'), write_to_stdout=False)
        s.settings.file.read_case_data(file_name=str(INPUT / original_path('stadio_assiale_2D_CFD_final.cas.h5').name))
        state = s.settings.get_state()
        jwrite(AUDIT / 'setup_completo_originale.json', state)
        s.settings.mesh.check()
        s.settings.mesh.quality()
        script = Path(__file__).with_name('audit_verify.py')
        namespace = {'s': s, 'state': state, '__file__': str(script), '__name__': 'audit_owned_session'}
        exec(compile(script.read_text(encoding='utf-8'), str(script), 'exec'), namespace)
        quality = export_quality(s, 'baseline_adattata', 289671)
        print('BASELINE_AUDIT_24_COMPLETED', quality['celle_attive'], flush=True)
    finally:
        close_transcript(s)
        s.exit()

def new_smoke():
    from cfd import ensure_campaign_open
    ensure_campaign_open()
    assert (WORK / 'checkpoint_comune/checkpoint.cas.h5').exists()
    assert not (WORK / 'prova_breve/smoke_final.cas.h5').exists(), 'Prova breve gia eseguita: usare una riproduzione indipendente'
    from cfd import launch
    from transcript_utils import close_transcript
    s = launch(WORK / 'launcher' / ('smoke_' + datetime.now().strftime('%Y%m%d_%H%M%S')))
    try:
        d = WORK / 'prova_breve'
        d.mkdir(exist_ok=True)
        s.transcript.start(file_name=str(d / 'fluent.trn'), write_to_stdout=False)
        script = Path(__file__).with_name('smoke_test.py')
        exec(compile(script.read_text(encoding='utf-8'), str(script), 'exec'), {'s': s, '__file__': str(script), '__name__': 'smoke_owned_session'})
    finally:
        close_transcript(s)
        s.exit()
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group()
    g.add_argument('--audit-new', action='store_true')
    g.add_argument('--smoke-new', action='store_true')
    args = p.parse_args()
    if args.audit_new:
        new_audit()
    elif args.smoke_new:
        new_smoke()
    else:
        print(json.dumps(verify(), ensure_ascii=False, indent=2))
