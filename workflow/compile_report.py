"""Compile the self-contained LaTeX report and optionally render its pages."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,tempfile
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'docs/report'

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def tool(explicit,name):
    value=explicit or shutil.which(name)
    if not value or not Path(value).is_file():
        raise FileNotFoundError(f'{name} is unavailable. Add it to PATH or supply its explicit command-line option.')
    return str(value)

def compile_report(compiler=None,pdftoppm=None,render=False):
    executable=tool(compiler,'pdflatex')
    build_root=ROOT/'.build/report';build_root.mkdir(parents=True,exist_ok=True)
    directory=Path(tempfile.mkdtemp(prefix='build_',dir=build_root))
    for index in range(3):
        command=[executable,'-interaction=nonstopmode','-halt-on-error','-file-line-error',
                 '-jobname=axial_turbine_stage_2d_report',f'-output-directory={directory}','main.tex']
        result=subprocess.run(command,cwd=PROJECT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240)
        (directory/f'pass_{index+1}.txt').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
        if result.returncode:raise RuntimeError(f'LaTeX compilation failed. Diagnostics: {directory}')
    log=(directory/'axial_turbine_stage_2d_report.log').read_text(encoding='utf-8',errors='replace')
    warnings=[line for line in log.splitlines() if any(word in line for word in ['Overfull','undefined','Float too large','multiply defined'])]
    if warnings:raise RuntimeError('Report layout/reference warnings: '+'; '.join(warnings))
    source=directory/'axial_turbine_stage_2d_report.pdf';reader=PdfReader(source)
    if reader.metadata.author!='Lorenzo Proli':raise ValueError('Unexpected report author metadata')
    target=PROJECT/source.name;shutil.copy2(source,target)
    record=dict(language='English',author=reader.metadata.author,pages=len(reader.pages),
                PDF=dict(path=target.relative_to(ROOT).as_posix(),bytes=target.stat().st_size,sha256=sha(target)),
                source=dict(path='docs/report/main.tex',sha256=sha(PROJECT/'main.tex')),
                compiler_warnings=warnings,visual_review='PENDING')
    if render:
        renderer=tool(pdftoppm,'pdftoppm');qa=ROOT/'.build/report_review'/sha(target)[:12];qa.mkdir(parents=True,exist_ok=True)
        subprocess.run([renderer,'-r','110','-png',str(target),str(qa/'page')],check=True,timeout=240)
        if len(list(qa.glob('page-*.png')))!=len(reader.pages):raise RuntimeError('Incomplete PDF rendering')
        record['rendered_pages']=len(reader.pages)
        print('Rendered pages: '+str(qa),flush=True)
    (PROJECT/'manifest.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record,indent=2),flush=True)
    return record

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler');parser.add_argument('--pdftoppm');parser.add_argument('--render',action='store_true')
    args=parser.parse_args();compile_report(args.compiler,args.pdftoppm,args.render)
