"""Offline status and explicit entry points for the reproducible CFD workflow."""
from common import *
import argparse, subprocess, sys


def ensure_campaign_open():
    """Reject solver launches before importing PyFluent, including python -O."""
    closure = project_path('PROJECT_CLOSURE.json')
    campaign = CONFIG_DIR / 'hybrid35_campaign_config.json'
    closed = closure.exists()
    if campaign.exists():
        settings = json.loads(campaign.read_text(encoding='utf-8-sig'))
        closed = closed or settings.get('campaign_closed', False)
    if closed:
        raise RuntimeError('The numerical campaign is closed. Solver execution is disabled; offline verification and post-processing remain available.')


def node_processes():
    """Return running two-dimensional double-precision Fluent MPI nodes."""
    if os.name != 'nt':
        raise RuntimeError('The Fluent process check currently supports Windows only.')
    result = subprocess.run(['powershell', '-NoProfile', '-Command',
        "@(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'fl_mpi*.exe' -and $_.ExecutablePath -match '2ddp_node' } | Select-Object ProcessId,ParentProcessId) | ConvertTo-Json -Compress"],
        capture_output=True, text=True, check=True)
    value = json.loads(result.stdout) if result.stdout.strip() else []
    return value if isinstance(value, list) else [value]


def launch(directory, graphics=False):
    ensure_campaign_open()
    if node_processes():
        raise RuntimeError('A Fluent solver is already active. Preserve it and run cases sequentially.')
    import ansys.fluent.core as pyfluent
    settings = json.loads((CONFIG_DIR / 'workflow_config.json').read_text(encoding='utf-8-sig'))['fluent']
    if settings['processor_count'] != 24:
        raise ValueError('The documented campaign requires 24 MPI processes.')
    directory = output_path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    session = pyfluent.launch_fluent(product_version=settings['version'], dimension=settings['dimension'], precision=settings['precision'],
        processor_count=24, ui_mode='hidden_gui' if graphics else 'no_gui', graphics_driver='opengl2' if graphics else None,
        cwd=str(directory), start_timeout=180, cleanup_on_exit=True, start_transcript=False)
    nodes = node_processes()
    if len(nodes) != 24:
        session.exit()
        raise RuntimeError(f'Expected 24 MPI nodes; detected {len(nodes)}.')
    jwrite(directory / 'mpi_resources.json', dict(utc=now(), processor_count=24, nodes=nodes,
           graphics_driver='opengl2' if graphics else 'null'))
    return session


def status():
    """Summarise saved results; recorded MPI counts are not live CPU activity."""
    values = []
    states = {'eseguita_analizzata': 'COMPLETE_AND_ANALYSED',
        'eseguita_periodicita_monitor_verificata': 'COMPLETE_OPERATIONAL_PERIODICITY_CHECKS_PASSED',
        'eseguita_periodicita_non_confermata': 'COMPLETE_PERIODICITY_UNCONFIRMED',
        'fallita': 'TECHNICAL_FAILURE', 'arrestata_con_checkpoint': 'STOPPED_WITH_CHECKPOINT',
        'interrotta_checkpoint_disponibile': 'INTERRUPTED_WITH_CHECKPOINT',
        'in_corso_24_processi': 'RECORDED_RUNNING_STATE',
        'calcolo_completato_statistiche_da_verificare': 'COMPLETE_ASSESSMENT_PENDING'}
    for run_id in ['ITER30', 'ITER60', 'T100', 'T200', 'T400', 'M1_HYBRID35', 'M2_HYBRID35', 'M3_HYBRID35']:
        path = case_directory(run_id) / 'progress.json'
        if not path.exists():
            continue
        item = json.loads(path.read_text(encoding='utf-8-sig'))
        values.append(dict(run_id=item.get('id', run_id), recorded_status=states.get(item.get('stato'), item.get('stato')),
            completed_steps=item.get('passi_completati'), target_steps=item.get('passi_pianificati'),
            physical_time_s=item.get('tempo_corrente_s'), configured_mpi_processes=24,
            last_recorded_active_mpi_processes=item.get('processi_attuali'),
            record_updated_utc=item.get('updated_utc'), source=path.relative_to(ROOT).as_posix()))
    return dict(mode='OFFLINE_SAVED_RECORDS', live_process_measurement=False, runs=values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'run', 'resume', 'analyse', 'report', 'quality-figures'])
    parser.add_argument('--id', help='Run identifier recorded in the campaign configuration')
    args = parser.parse_args()
    if args.action == 'status':
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return
    if args.action in ['run', 'resume']:
        ensure_campaign_open()
        if not args.id:
            parser.error('--id is required for execution and restart')
        from campaign_v2 import prepare, advance, resume, CONFIG
        session = launch(ROOT / 'runs' / 'launcher' / datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
        try:
            if args.action == 'resume':
                target, metadata = resume(session, args.id)
            else:
                run_config = next(item for item in CONFIG['campaign']['runs'] if item['id'] == args.id)
                target, metadata = prepare(session, run_config)
            result = advance(session, target, metadata)
        finally:
            session.exit()
        if result['passi_completati'] == result['passi_pianificati']:
            from monitor_analysis import analyse
            analyse(target)
        return
    if args.action == 'analyse':
        if not args.id:
            parser.error('--id is required for analysis')
        from monitor_analysis import analyse
        print(json.dumps(analyse(case_directory(args.id))['esiti'], indent=2))
        return
    script = 'compile_report.py' if args.action == 'report' else 'plot_mesh_quality.py'
    subprocess.run([sys.executable, str(Path(__file__).with_name(script))], check=True)


if __name__ == '__main__':
    main()
