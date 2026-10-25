"""Check portable publication assets and optional local native data offline."""
from pathlib import Path
import argparse,hashlib,json
from package_project import source_files

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'manifest_sha256.json'
BASELINE={'historical_baseline.cas.h5':'c9f78c24b1a5263f655136f0c1a632ba4276c2eec23a6e1b02622d7276378f7b',
          'historical_baseline.dat.h5':'1038a1e420ebfa1a47a87d002627b207c05b8016d12ff650990773d737710be1'}

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def verify_native():
    from common import project_path,case_directory
    import h5py
    checked=0
    index=json.loads((ROOT/'config/native_data_index.json').read_text(encoding='utf-8'))
    for row in index['files']:
        path=ROOT/row['path']
        if not path.resolve().is_relative_to(ROOT) or not path.is_file():raise ValueError('Missing native file: '+row['path'])
        if path.stat().st_size!=row['bytes'] or sha(path)!=row['sha256']:raise ValueError('Native data checksum mismatch: '+row['path'])
    for name,digest in BASELINE.items():
        path=ROOT/'inputs/baseline'/name
        if not path.is_file() or sha(path)!=digest:raise ValueError('Historical reference mismatch: '+name)
        checked+=1
    for rid in ['ITER30','ITER60','T100','T200','T400','M1_HYBRID35','M2_HYBRID35','M3_HYBRID35']:
        meta=json.loads((case_directory(rid)/'progress.json').read_text(encoding='utf-8'))
        current=project_path(meta.get('output_correnti',case_directory(rid)))
        records=meta.get('manifest_finale') or [dict(file=str(current/('final.'+ext+'.h5'))) for ext in ['cas','dat']]
        for row in records:
            path=project_path(row['file'])
            if not path.is_file() or row.get('sha256') and sha(path)!=row['sha256']:raise ValueError('Native checkpoint mismatch: '+str(path))
            with h5py.File(path,'r'):pass
            checked+=1
    return checked,len(index['files'])

def main(write=False,native=False):
    report=ROOT/'docs/report';record=json.loads((report/'manifest.json').read_text(encoding='utf-8'))
    if sha(report/'axial_turbine_stage_2d_report.pdf')!=record['PDF']['sha256']:raise ValueError('Report PDF checksum mismatch')
    if sha(report/'main.tex')!=record['source']['sha256']:raise ValueError('Report source differs from reviewed manuscript')
    if record.get('visual_review')!='PASSED':raise ValueError('Report visual review is incomplete')
    results=ROOT/'results'
    data=json.loads((results/'data_manifest.json').read_text(encoding='utf-8'))
    for row in data['outputs']:
        path=(results/row['file']).resolve()
        if not path.is_relative_to(results) or not path.is_file() or sha(path)!=row['sha256']:
            raise ValueError('Scientific table checksum mismatch: '+row['file'])
    video=json.loads((results/'videos/video_manifest.json').read_text(encoding='utf-8'))
    if sha(results/'videos'/video['file'])!=video['sha256']:raise ValueError('Selected movie checksum mismatch')
    if sha(results/'videos'/video['source_frame_index'])!=video['source_frame_index_sha256']:raise ValueError('Movie source index mismatch')
    if write:
        rows=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in source_files() if p!=MANIFEST]
        MANIFEST.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
    rows=json.loads(MANIFEST.read_text(encoding='utf-8'))
    actual={p.relative_to(ROOT).as_posix() for p in source_files() if p!=MANIFEST}
    declared={row['path'] for row in rows}
    if actual!=declared:raise ValueError('Publication inventory differs: '+str(sorted(actual^declared)))
    for row in rows:
        path=ROOT/row['path']
        if not path.resolve().is_relative_to(ROOT) or not path.is_file():raise ValueError(row['path'])
        if path.stat().st_size!=row['bytes'] or sha(path)!=row['sha256']:raise ValueError('Asset checksum mismatch: '+row['path'])
    count,native_count=verify_native() if native else (0,0)
    print(json.dumps(dict(status='PASSED',publication_assets=len(rows),native_case_data_files=count,native_files_verified=native_count,solver_started=False),indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-manifest',action='store_true');parser.add_argument('--native',action='store_true')
    args=parser.parse_args();main(args.write_manifest,args.native)
