"""Reproduce the ANSYS Meshing family by direct export in a new output directory."""
from common import *
import argparse, subprocess

def generate(output, execute=False):
    if execute:
        from cfd import ensure_campaign_open
        ensure_campaign_open()
    inputs = project_path('02_setup/pyfluent/meshing_inputs')
    plan = json.loads((inputs / 'parameters_family.json').read_text())
    controls = json.loads((inputs / 'controls_meshing.json').read_text())
    archive = project_path(ROOT / plan['source_archive_relative'])
    geometry = project_path(ROOT / plan['geometry_relative'])
    assert archive.is_file() and geometry.is_file()
    output = output.resolve()
    assert output.is_relative_to(ROOT.resolve()) and (not output.exists())
    output.mkdir(parents=True)
    blocks = []
    configs = []
    for entry in plan['family']:
        assert sha(geometry) == entry['geometry_source_sha256']
        cfg = dict(entry)
        directory = output / cfg['id']
        directory.mkdir()
        cfg.update(export_mesh=str(directory / (cfg['id'] + '_systematic.msh')), receipt=str(directory / 'mesh_export.json'), error_file=str(directory / 'mesh_generation_error.txt'))
        project = directory / (cfg['id'] + '.wbpj')
        inner = (inputs / 'meshing_act_template.py.in').read_text().replace('__CONFIG_LITERAL__', repr(json.dumps(cfg))).replace('__CONTROLS_LITERAL__', repr(json.dumps(controls)))
        blocks.append('Reset()\nUnarchive(ArchivePath=' + repr(str(archive)) + ',ProjectPath=' + repr(str(project)) + ',Overwrite=False)\n' + 'system=GetAllSystems()[0]\nmesh=system.GetContainer(ComponentName="Mesh")\nmesh.SendCommand(Language="Python",Command=' + repr(inner) + ')\nSave(Overwrite=True)\n')
        configs.append(cfg)
    journal = output / 'generate_direct_meshes.wbjn'
    text(journal, '# encoding: utf-8\nSetScriptVersion(Version="24.2.133")\n' + '\n'.join(blocks))
    jwrite(output / 'reproduction_plan.json', dict(utc=now(), state='JOURNAL_PREPARED_NOT_EXECUTED', archive=str(archive), archive_sha256=sha(archive), configs=configs))
    if execute:
        from cfd import node_processes
        from cfd import ensure_campaign_open
        ensure_campaign_open()
        if node_processes():
            raise RuntimeError('Do not regenerate meshes while a Fluent solver is active.')
        executable = project_path('C:/Program Files/ANSYS Inc/v242/Framework/bin/Win64/RunWB2.exe')
        assert executable.exists()
        with (output / 'workbench_stdout.log').open('x', encoding='utf-8') as log:
            result = subprocess.run([str(executable), '-B', '-R', str(journal)], cwd=output, stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.returncode == 0, 'Workbench returned an error; inspect its log'
        receipts = []
        for cfg in configs:
            p = project_path(cfg['export_mesh'])
            receipt = json.loads(project_path(cfg['receipt']).read_text())
            assert p.is_file() and p.stat().st_size > 0 and (receipt['status'] == 'MESH_GENERATED_DIRECT_EXPORT')
            receipts.append(dict(id=cfg['id'], file=str(p), byte=p.stat().st_size, sha256=sha(p), meshing_elements=receipt['elements']))
        jwrite(output / 'direct_export_manifest.json', dict(utc=now(), state='MESH_EXPORTED_FLUENT_COUNT_AND_SETUP_NOT_YET_VERIFIED', meshes=receipts))
    return journal
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    print(generate(project_path(ROOT / a.output), a.execute))
