"""Build a size/SHA256-verified source archive without network operations."""
from pathlib import Path
import argparse,hashlib,json,zipfile

ROOT=Path(__file__).resolve().parents[1]
PUBLIC_DIRECTORIES={'config','docs','geometry','results','tests','tools','workflow'}
PUBLIC_ROOT_FILES={'README.md','NOTICE.md','CITATION.cff','requirements.txt',
                   'requirements-lock.txt','.gitignore','.gitattributes','manifest_sha256.json'}

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def source_files(include_native=False):
    """Yield only the technical publication tree and explicitly requested native data."""
    directories=PUBLIC_DIRECTORIES | ({'inputs','runs'} if include_native else set())
    for path in sorted(ROOT.rglob('*')):
        rel=path.relative_to(ROOT)
        if not path.is_file():
            continue
        allowed=(len(rel.parts)==1 and path.name in PUBLIC_ROOT_FILES) or rel.parts[0] in directories
        private=any(part.startswith('.') or part=='__pycache__' for part in rel.parts)
        if len(rel.parts)==1 and path.name in PUBLIC_ROOT_FILES:
            private=False
        if (allowed and not private and path.name not in ['path_map.json','local_config.json']
                and path.suffix not in ['.pyc','.pyo','.tmp','.lock']):
            yield path


def package(destination,include_native=False):
    destination=Path(destination).resolve()
    if destination.is_relative_to(ROOT) or destination.exists() or not destination.parent.is_dir():
        raise ValueError('Choose a new archive path outside the project in an existing directory')
    records=[]
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as archive:
        for path in source_files(include_native):
            rel=path.relative_to(ROOT).as_posix();digest=sha(path)
            archive.write(path,rel,compress_type=zipfile.ZIP_STORED if path.suffix in ['.png','.mp4','.h5','.npz','.pdf','.wbpz'] else zipfile.ZIP_DEFLATED)
            records.append(dict(path=rel,bytes=path.stat().st_size,sha256=digest))
        archive.writestr('ARCHIVE_SHA256.json',json.dumps(records,indent=2))
    with zipfile.ZipFile(destination) as archive:
        for row in records:
            if archive.getinfo(row['path']).file_size!=row['bytes']:raise ValueError(row['path'])
            with archive.open(row['path']) as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()!=row['sha256']:raise ValueError(row['path'])
    record=dict(archive=destination.name,bytes=destination.stat().st_size,sha256=sha(destination),files=len(records),native_data_included=include_native,verification='PASSED')
    destination.with_suffix('.manifest.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--destination',required=True);parser.add_argument('--include-native',action='store_true')
    args=parser.parse_args();package(args.destination,args.include_native)
