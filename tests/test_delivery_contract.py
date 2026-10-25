"""Offline regression checks for publication packaging and restored histories."""
from pathlib import Path
import contextlib, csv, hashlib, importlib.util, io, json, math, shutil, subprocess, sys, tempfile, unittest, zipfile

ROOT = Path(__file__).resolve().parents[1]


class DeliveryContractTests(unittest.TestCase):
    def test_source_archive_excludes_private_and_native_material(self):
        spec = importlib.util.spec_from_file_location('delivery_packager', ROOT/'workflow/package_project.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); checkout = base/'project'; checkout.mkdir()
            content = {'README.md':'public', 'LICENSE':'software terms', 'LICENSE-CONTENT':'content terms', 'docs/method.md':'method', 'config/model.json':'{}',
                '.env':'private placeholder', '.workspace/session.json':'private placeholder',
                '.git/config':'private placeholder', '.venv/pyvenv.cfg':'runtime placeholder',
                'config/local_config.json':'private placeholder', 'docs/.private':'private placeholder',
                'scratch.txt':'not a deliverable', 'inputs/reference.cas.h5':'native placeholder'}
            for name,text in content.items():
                p=checkout/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
            module.ROOT=checkout
            for native in [False,True]:
                with self.subTest(native=native):
                    target=base/('with_native.zip' if native else 'source.zip')
                    with contextlib.redirect_stdout(io.StringIO()):module.package(target,native)
                    with zipfile.ZipFile(target) as archive:
                        expected={'README.md','LICENSE','LICENSE-CONTENT','docs/method.md','config/model.json','ARCHIVE_SHA256.json'}
                        if native:expected.add('inputs/reference.cas.h5')
                        self.assertEqual(set(archive.namelist()),expected)
                        for item in json.loads(archive.read('ARCHIVE_SHA256.json')):
                            self.assertEqual(hashlib.sha256(archive.read(item['path'])).hexdigest(),item['sha256'])

    def test_legacy_iteration_restart_is_analysed_by_documented_cli(self):
        with tempfile.TemporaryDirectory() as temporary:
            checkout=Path(temporary)
            shutil.copytree(ROOT/'workflow',checkout/'workflow',ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(ROOT/'config',checkout/'config')
            initial=checkout/'runs/adapted_mesh/ITER30'; resumed=initial/'resume_24_processes'
            resumed.mkdir(parents=True)
            period=2.97583785e-4;dt=3e-6;t0=0.010653
            metadata=dict(id='ITER30',passi_completati=596,passi_pianificati=596,dt_s=dt,
                iterazioni_per_passo=30,finestra_media_s=[t0+3*period,t0+6*period],
                output_correnti='runs/adapted_mesh/ITER30/ripresa_24_processi',
                segmenti_risorse=[dict(processi=8,passi=240),dict(processi=24,passi_iniziali=240,tempo_iniziale_s=t0+240*dt)])
            (initial/'progress.json').write_text(json.dumps(metadata),encoding='utf-8')
            names=['forza_y_rotore','mdot_inlet','mdot_outlet','pt_outlet']; originals={}
            for name in names:
                for directory,steps in [(initial,range(241)),(resumed,range(240,597))]:
                    lines=['"'+name+'-rfile"','"Time Step"','("Time Step" "value" "flow-time")']
                    for step in steps:
                        time=t0+step*dt;wave=math.sin(2*math.pi*(time-t0)/period)
                        value={'forza_y_rotore':-100+wave,'mdot_inlet':5+.01*wave,'mdot_outlet':-5-.01*wave,'pt_outlet':100000+100*wave}[name]
                        lines.append(f'{step} {value:.17g} {time:.17g}')
                    path=directory/(name+'.out');path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
                    originals[path]=hashlib.sha256(path.read_bytes()).hexdigest()
            result=subprocess.run([sys.executable,'-B','workflow/cfd.py','analyse','--id','ITER30'],cwd=checkout,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            analysis=json.loads((checkout/'runs/analysis/adapted_mesh/ITER30/analysis.json').read_text(encoding='utf-8'))
            self.assertEqual(len(analysis['statistiche']),4)
            self.assertEqual(analysis['cicli'],3)
            self.assertEqual(len(analysis['sorgenti']),8)
            self.assertTrue(analysis['periodicita_monitor_entro_criteri_proposti'])
            plotted=subprocess.run([sys.executable,'-B','workflow/plot_histories.py','ITER30'],cwd=checkout,capture_output=True,text=True,timeout=60)
            self.assertEqual(plotted.returncode,0,plotted.stdout+plotted.stderr)
            provenance_files=list((checkout/'results/figures').rglob('history_plot_provenance.json'))
            self.assertEqual(len(provenance_files),1)
            provenance=json.loads(provenance_files[0].read_text(encoding='utf-8'))
            self.assertEqual(len(provenance['sources']),8)
            for path,digest in originals.items():self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),digest)

    def test_source_only_status_reports_published_results_without_a_solver(self):
        with tempfile.TemporaryDirectory() as temporary:
            checkout=Path(temporary)
            shutil.copytree(ROOT/'workflow',checkout/'workflow',ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(ROOT/'config',checkout/'config')
            (checkout/'results').mkdir();shutil.copy2(ROOT/'results/run_summary.csv',checkout/'results/run_summary.csv')
            result=subprocess.run([sys.executable,'-B','workflow/cfd.py','status'],cwd=checkout,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            data=json.loads(result.stdout)
            self.assertEqual(data['mode'],'OFFLINE_PUBLISHED_RESULTS')
            self.assertFalse(data['live_process_measurement'])
            self.assertEqual(len(data['runs']),8)
            iteration=next(item for item in data['runs'] if item['run_id']=='ITER30')
            self.assertEqual(iteration['recorded_mpi_process_counts'],[8,24])
            self.assertIsNone(iteration['last_recorded_active_mpi_processes'])


if __name__=='__main__':unittest.main()
