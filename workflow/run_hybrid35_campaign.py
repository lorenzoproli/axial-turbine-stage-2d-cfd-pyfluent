"""Sequential original-position Hybrid runs with a final three-cycle assessment."""
from data_schema import csv, json
from common import *
from cfd import launch, node_processes, ensure_campaign_open
import argparse, traceback

CFG_PATH = CONFIG_DIR / 'hybrid35_campaign_config.json'
CFG = json.loads(CFG_PATH.read_text(encoding='utf-8-sig'))
FAMILY = project_path('03_simulazioni/convergenza_griglia')
RECEIPT = FAMILY / 'campaign_status.json'


def _verify_file(value, expected_hash):
    path = project_path(value)
    if not path.is_file() or sha(path) != expected_hash:
        raise RuntimeError('Missing or changed campaign input: ' + str(path))
    return path


def run_configs():
    """Read only scientific mesh, native case and boundary-setting inputs."""
    supplied = CFG.get('run_inputs')
    if isinstance(supplied, dict):
        supplied = [dict(item, id=identifier) for identifier, item in supplied.items()]
    if not supplied:
        raise ValueError('Campaign configuration must declare its scientific run_inputs.')
    result = []
    for inputs in supplied:
        identifier = inputs['id']
        if identifier not in CFG['run_ids']:
            raise ValueError('Input declaration has an unknown run identifier: ' + identifier)
        periods = CFG.get('period_targets_by_run', {}).get(identifier, CFG['total_periods_each_mesh'])
        base = mesh_base_id(identifier)
        paths = {}
        for path_key, hash_key in [('source_case', 'source_case_sha256'), ('source_mesh', 'source_mesh_sha256'), ('settings_file', 'settings_sha256')]:
            paths[path_key] = _verify_file(inputs[path_key], inputs[hash_key]).relative_to(ROOT).as_posix()
        if inputs['expected_cells'] <= 0:
            raise ValueError('Expected active cell count must be positive.')
        item = dict(inputs, **paths)
        item.update(mesh=base + '_systematic_original_position_Hybrid', timestep_s=CFG['timestep_s'],
            max_iter=CFG['inner_iterations_per_step'], initial_time_s=0.0, target_periods=periods,
            target_steps=periods * CFG['steps_per_period'], warmup_periods=periods - 3, average_periods=3,
            capture_periods=3, capture_fields=['mach-number', 'pressure', 'density', 'temperature'],
            samples_per_period=4, max_run_hours=CFG['max_wall_hours_each_mesh'],
            initialization_method='Hybrid after original rotor position restoration at t=0')
        if base == 'M3' and CFG.get('M3_native_mach_stream_configuration'):
            item.update(native_mach_stream_configuration=CFG['M3_native_mach_stream_configuration'],
                samples_per_period=CFG.get('phase_samples_per_period_for_recurrence', 4))
        if base == 'M2':
            item['native_animation_enabled'] = CFG.get('M2_native_animation_enabled', False)
        result.append(item)
    return result


def validate_configuration():
    if CFG['processor_count'] != 24:
        raise ValueError('This campaign configuration requires 24 MPI processes.')
    if CFG.get('automatic_transient_extensions', False):
        raise ValueError('Automatic transient extension is disabled for this campaign.')
    if abs(CFG['timestep_s'] * CFG['steps_per_period'] - T) >= 1e-15:
        raise ValueError('Timestep and steps per period are inconsistent.')
    _verify_file(CFG['initial_geometry_reference'], CFG['initial_geometry_reference_sha256'])
    return run_configs()


def write_state(state, **extra):
    jwrite(RECEIPT, dict(utc=now(), campaign_id=CFG['campaign_id'], state=state,
        configuration_sha256=sha(CFG_PATH), automatic_extensions=False, **extra))


def prepared_initial_checkpoint(run_config):
    """Verify an immutable supplied Hybrid t=0 pair without running Fluent."""
    directory = project_path(ROOT / 'inputs/initial_conditions' / mesh_base_id(run_config['id']))
    receipt = directory / 'hybrid_initialization_verified.json'
    if not receipt.is_file():
        return None
    evidence = json.loads(receipt.read_text(encoding='utf-8-sig'))
    if (evidence.get('run_id') != run_config['id'] or evidence.get('initial_clock') != {'time_s': 0.0, 'step': 0}
            or evidence.get('restoration_before_hybrid') is not True
            or evidence.get('physical_setup_unchanged') is not True
            or evidence.get('automatic_mesh_adaptation_active') is not False
            or evidence.get('reference_sha256') != CFG['initial_geometry_reference_sha256']):
        raise RuntimeError('The supplied Hybrid checkpoint does not satisfy its t=0 geometry/setup declaration.')
    manifest = evidence.get('manifest_initial_checkpoint', [])
    if len(manifest) != 2:
        raise RuntimeError('The supplied initial checkpoint must include a coherent case/data pair.')
    for item in manifest:
        path = _verify_file(item['file'], item['sha256'])
        if path.stat().st_size != item['byte']:
            raise RuntimeError('Initial checkpoint file size differs: ' + str(path))
    checkpoint = next(project_path(item['file']) for item in manifest if item['file'].endswith('.cas.h5'))
    return checkpoint, evidence


def await_preflight_visual_review(directory, timeout_s=600):
    """Require a technical visual QA record bound to the actual preflight proof."""
    directory = project_path(directory)
    receipt = directory / 'visual_review.json'
    proof_hash = sha(directory / 'proof.json')
    deadline = time.monotonic() + timeout_s
    print('GRAPHICS_VISUAL_REVIEW_REQUIRED', directory, flush=True)
    while time.monotonic() < deadline:
        if receipt.exists():
            record = json.loads(receipt.read_text(encoding='utf-8-sig'))
            if record.get('state') != 'VISUALLY_VERIFIED' or record.get('proof_sha256') != proof_hash:
                raise RuntimeError('Visual QA record does not match the current graphics preflight.')
            if len(record.get('reviewed_frames', [])) != 3:
                raise RuntimeError('Three decoded preflight frames must be reviewed.')
            for item in record['reviewed_frames']:
                path = project_path(directory / item['file'])
                if path.stat().st_size != item['byte'] or sha(path) != item['sha256']:
                    raise RuntimeError('Preflight frame changed after visual review.')
            return
        if (WORK / 'STOP_AFTER_BATCH.txt').exists():
            raise RuntimeError('Controlled stop requested during graphics preflight.')
        time.sleep(2)
    raise RuntimeError('Graphics visual QA was not completed; the production field has not advanced.')


def main(selected_id):
    ensure_campaign_open()
    from campaign_v2 import prepare, advance, resume
    from initial_position_hybrid import initialise
    from assess_hybrid35 import assess
    from transcript_utils import close_transcript
    configs = validate_configuration()
    run_config = next(item for item in configs if item['id'] == selected_id)
    if node_processes():
        raise RuntimeError('Another Fluent solver is active; cases must run sequentially.')
    if (WORK / 'STOP_AFTER_BATCH.txt').exists():
        raise RuntimeError('The controlled-stop flag is present.')
    target = case_directory(selected_id)
    session = None
    try:
        if (target / 'progress.json').exists():
            metadata = json.loads((target / 'progress.json').read_text(encoding='utf-8-sig'))
            if metadata['completed_steps'] == metadata['planned_steps']:
                print('EXISTING_COMPLETED_RESULT_PRESERVED', selected_id, flush=True)
                return
            if metadata['planned_steps'] != run_config['target_steps']:
                raise RuntimeError('Restart target differs from the saved run; configure a separate extension explicitly.')
            session = launch(ROOT / 'runs/launcher' / (selected_id + '_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f')),
                             graphics=run_config.get('native_animation_enabled', True))
            target, metadata = resume(session, selected_id)
        else:
            session = launch(ROOT / 'runs/launcher' / (selected_id + '_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f')), graphics=run_config.get('native_animation_enabled', True))
            prepared = prepared_initial_checkpoint(run_config)
            checkpoint, evidence = prepared if prepared is not None else initialise(session, run_config, CFG)
            if run_config.get('native_mach_stream_configuration'):
                from verify_mach_stream import preflight
                preflight_directory = project_path(ROOT / 'runs/graphics_preflight' /
                    (selected_id + '_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f')))
                proof = preflight(session, checkpoint, selected_id, preflight_directory, evidence['manifest_initial_checkpoint'])
                if proof['state'] != 'MACH_STREAM_T0_MOVING_RESTART_AND_PLAYBACK_VERIFIED':
                    raise RuntimeError('Native Mach stream preflight failed.')
                await_preflight_visual_review(preflight_directory)
            target, metadata = prepare(session, dict(run_config, checkpoint=checkpoint.relative_to(ROOT).as_posix()))
            metadata.update(initialization_evidence=(checkpoint.parent / 'hybrid_initialization_verified.json').relative_to(ROOT).as_posix(),
                total_periods=run_config['target_periods'], automatic_transient_extensions=False,
                original_position_restored_before_Hybrid=True, hybrid35_configuration_sha256=sha(CFG_PATH))
            jwrite(target / 'progress.json', metadata)
        write_state('RUNNING', run_id=selected_id, target_steps=run_config['target_steps'])
        result = advance(session, target, metadata)
        close_transcript(session)
        session.exit()
        session = None
        if result['completed_steps'] != run_config['target_steps']:
            write_state('STOPPED_WITH_CHECKPOINT', run_id=selected_id, reason=result.get('stop_reason'))
            return
        for _ in range(30):
            if not node_processes():
                break
            time.sleep(1)
        if node_processes():
            raise RuntimeError('Solver processes must exit before the final assessment.')
        assessment = assess(selected_id, CFG)
        write_state('COMPLETED_AND_ASSESSED', run_id=selected_id, assessment=assessment['state'],
            further_runs_started=False)
    except Exception as error:
        write_state('TECHNICAL_REVIEW_REQUIRED', run_id=selected_id, error=repr(error), traceback=traceback.format_exc())
        raise
    finally:
        if session is not None:
            close_transcript(session)
            session.exit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', choices=CFG['run_ids'], help='Execute exactly one mesh, then assess and stop')
    parser.add_argument('--check-inputs', action='store_true', help='Verify technical inputs and exit without launching Fluent')
    arguments = parser.parse_args()
    if arguments.check_inputs:
        print(json.dumps(dict(status='INPUTS_VERIFIED', solver_started=False, runs=validate_configuration()), indent=2))
    elif arguments.only:
        main(arguments.only)
    else:
        parser.error('Specify --check-inputs for offline verification or --only for a single-mesh run.')
