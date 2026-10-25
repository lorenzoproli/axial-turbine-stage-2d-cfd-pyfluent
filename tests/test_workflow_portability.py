"""Offline tests for relocated paths, native monitor IDs and launch protection."""
from pathlib import Path
import importlib.util, json, shutil, subprocess, sys, tempfile, unittest

WORKFLOW = Path(__file__).resolve().parents[1] / 'workflow'


class PortableWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='portable_checkout_', dir=Path(__file__).parent)
        self.checkout = Path(self.temporary.name)
        (self.checkout / 'workflow').mkdir()
        (self.checkout / 'config').mkdir()
        for filename in ['common.py', 'cfd.py', 'monitor_paths.py', 'run_hybrid35_campaign.py']:
            shutil.copy2(WORKFLOW / filename, self.checkout / 'workflow' / filename)
        aliases = {'mapping': {'03_simulazioni/caso': 'runs/example',
                              '03_simulazioni/caso/checkpoint_comune': 'inputs/common_checkpoint',
                              'PROJECT_CLOSURE.json': 'config/campaign_state.json'},
                   'components': {'campi_in_fase': 'phase_samples', 'rotore': 'rotor'},
                   'filenames': {'setup_effettivo.json': 'solver_settings.json'}}
        (self.checkout / 'config/path_aliases.json').write_text(json.dumps(aliases), encoding='utf-8')
        (self.checkout / 'config/campaign_state.json').write_text('{"state":"CLOSED"}', encoding='utf-8')
        (self.checkout / 'config/hybrid35_campaign_config.json').write_text(
            '{"campaign_closed":true,"run_ids":["M3_HYBRID35"]}', encoding='utf-8')

    def tearDown(self):
        self.temporary.cleanup()

    def run_python(self, code, optimised=False):
        command = [sys.executable, '-B'] + (['-O'] if optimised else []) + ['-c', code]
        result = subprocess.run(command, cwd=self.checkout, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + '\n' + result.stderr)
        return result.stdout

    def test_paths_survive_drive_and_root_rename(self):
        self.run_python(r"""
import sys
sys.path.insert(0,'workflow')
from common import ROOT,project_path,output_path
expected=ROOT/'runs/example/phase_samples/step_00100_wall_rotor.csv'
for saved in ['03_simulazioni/caso/campi_in_fase/step_00100_wall_rotore.csv',
              r'D:\previous\different_checkout\03_simulazioni\caso\campi_in_fase\step_00100_wall_rotore.csv']:
    if project_path(saved)!=expected:raise RuntimeError(str(project_path(saved)))
if project_path('03_simulazioni/caso')/'setup_effettivo.json' != ROOT/'runs/example/solver_settings.json':
    raise RuntimeError('Joined filename was not mapped')
if project_path('03_simulazioni/caso')/'checkpoint_comune/checkpoint.cas.h5' != ROOT/'inputs/common_checkpoint/checkpoint.cas.h5':
    raise RuntimeError('Moved input branch was not resolved when joining children')
try:output_path(ROOT/'..'/'outside.txt')
except ValueError:pass
else:raise RuntimeError('Output traversal was not rejected')
""")

    def test_import_is_read_only(self):
        self.run_python("""
from pathlib import Path
import sys
before={str(p) for p in Path('.').rglob('*')}
sys.path.insert(0,'workflow')
import common,cfd
after={str(p) for p in Path('.').rglob('*')}
if before!=after:raise RuntimeError('Import created files or directories')
""")

    def test_closed_guard_precedes_fluent_import_with_and_without_optimisation(self):
        for optimised in [False, True]:
            with self.subTest(optimised=optimised):
                self.run_python("""
import sys
sys.path.insert(0,'workflow')
from common import ROOT
from cfd import launch
try:launch(ROOT/'runs/should_not_exist')
except RuntimeError as error:
    if 'closed' not in str(error):raise
else:raise RuntimeError('Closed campaign accepted a launch')
if any(name.startswith('ansys') for name in sys.modules):raise RuntimeError('PyFluent was imported before closure check')
if (ROOT/'runs').exists():raise RuntimeError('Launch guard created output')
""", optimised)

    def test_controller_stops_before_loading_scientific_dependencies(self):
        for optimised in [False, True]:
            with self.subTest(optimised=optimised):
                self.run_python("""
import sys
sys.path.insert(0,'workflow')
from run_hybrid35_campaign import main
try:main('M3_HYBRID35')
except RuntimeError as error:
    if 'closed' not in str(error):raise
else:raise RuntimeError('Closed controller entered the numerical workflow')
if 'campaign_v2' in sys.modules:raise RuntimeError('Scientific execution modules loaded before closure check')
""", optimised)

    def test_native_monitor_header_survives_english_filename(self):
        directory = self.checkout / 'runs/example'
        directory.mkdir(parents=True)
        path = directory / 'rotor_tangential_force.out'
        path.write_text('"forza_y_rotore-rfile"\n"Time Step"\n("Time Step" "force" "flow-time")\n0 1.5 0\n', encoding='utf-8')
        self.run_python("""
import sys
sys.path.insert(0,'workflow')
from monitor_paths import monitor_path
if monitor_path('runs/example','forza_y_rotore').name!='rotor_tangential_force.out':
    raise RuntimeError('Native report header did not identify renamed monitor')
""")


if __name__ == '__main__':
    unittest.main()
