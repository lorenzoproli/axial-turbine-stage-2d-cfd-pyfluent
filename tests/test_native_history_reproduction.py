"""Reproduce saved scientific summaries from the optional local native dataset."""
from pathlib import Path
import json, sys, unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workflow'))
from common import T, case_directory, project_path, sha, english_name
from monitor_analysis import NAMES, read_monitor, merge_series, segment
from monitor_paths import monitor_path


class NativeHistoryReproduction(unittest.TestCase):
    def test_original_position_hybrid_checkpoint_inputs(self):
        if not (ROOT / 'inputs/initial_conditions/M1/hybrid_initial.cas.h5').is_file():
            self.skipTest('The optional native CFD dataset is not installed.')
        from run_hybrid35_campaign import validate_configuration, prepared_initial_checkpoint
        for configuration in validate_configuration():
            checkpoint, evidence = prepared_initial_checkpoint(configuration)
            self.assertTrue(checkpoint.is_file())
            self.assertEqual(evidence['initial_clock'], {'time_s': 0.0, 'step': 0})
            self.assertTrue(evidence['restoration_before_hybrid'])
            self.assertFalse(evidence['AMR_active'])

    def test_final_phase_sample_paths_and_hashes(self):
        if not (ROOT / 'runs/systematic_mesh/M1/progress.json').is_file():
            self.skipTest('The optional native CFD dataset is not installed.')
        for run_id in ['M1_HYBRID35', 'M2_HYBRID35', 'M3_HYBRID35']:
            metadata = json.loads((case_directory(run_id) / 'progress.json').read_text(encoding='utf-8-sig'))
            start, end = metadata['finestra_media_s']
            samples = [sample for sample in metadata['captures'] if start-1e-12 <= sample['solution_time_s'] <= end+1e-12]
            self.assertEqual(len(samples), 13)
            self.assertTrue(np.allclose(np.diff([sample['solution_time_s'] for sample in samples]), T/4, rtol=0, atol=1e-12))
            for sample in samples:
                for item in sample['manifest']:
                    path = project_path(item['file'])
                    self.assertEqual(path.stat().st_size, item['byte'])
                    self.assertEqual(sha(path), item['sha256'])
                for wall in ['wall_statore', 'wall_rotore']:
                    expected = english_name(sample['tag'] + '_' + wall + '.csv')
                    self.assertEqual(sum(project_path(item['file']).name == expected for item in sample['manifest']), 1)

    def test_three_mesh_statistics_and_phase_sampling(self):
        if not (ROOT / 'runs/systematic_mesh/M1/progress.json').is_file():
            self.skipTest('The optional native CFD dataset is not installed.')
        for run_id in ['M1_HYBRID35', 'M2_HYBRID35', 'M3_HYBRID35']:
            with self.subTest(run_id=run_id):
                metadata = json.loads((case_directory(run_id) / 'progress.json').read_text(encoding='utf-8-sig'))
                saved = json.loads(project_path(f'05_postprocessing/campagna/{run_id}/analisi.json').read_text(encoding='utf-8-sig'))
                start, end = saved['finestra_s']
                self.assertAlmostEqual((end - start) / T, 3, places=9)
                self.assertAlmostEqual(metadata['dt_s'], T / 400, places=16)
                self.assertEqual(metadata['iterazioni_per_passo'], 30)
                for name in NAMES:
                    pieces = []
                    for part in metadata['monitor_segments']:
                        values = read_monitor(monitor_path(part['directory'], name))
                        if part.get('from_s') is not None:
                            values = values[values[:, 2] >= part['from_s'] - 1e-13]
                        if part.get('to_s') is not None:
                            values = values[values[:, 2] <= part['to_s'] + 1e-13]
                        pieces.append(values)
                    native = merge_series(pieces)
                    self.assertTrue(np.all(np.diff(native[:, 0]) == 1))
                    self.assertEqual(native[-1, 0], metadata['passi_completati'])
                    self.assertTrue(np.allclose(native[:, 2], native[:, 0] * metadata['dt_s'], rtol=0, atol=1e-12))
                    times, values = segment(native[:, 2], native[:, 1], start, end)
                    mean = float(np.trapezoid(values, times) / (end - start))
                    amplitude = float(np.mean([np.ptp(segment(native[:, 2], native[:, 1], start + index*T, start + (index+1)*T)[1]) for index in range(3)]))
                    expected = next(row for row in saved['statistiche'] if row['monitor'] == name)
                    self.assertTrue(np.isclose(mean, expected['media'], rtol=1e-10, atol=1e-10))
                    self.assertTrue(np.isclose(amplitude, expected['ampiezza_picco_picco_media_cicli'], rtol=1e-10, atol=1e-10))

    def test_final_native_pairs_remain_unchanged(self):
        if not (ROOT / 'runs/systematic_mesh/M1/progress.json').is_file():
            self.skipTest('The optional native CFD dataset is not installed.')
        for run_id in ['M1_HYBRID35', 'M2_HYBRID35', 'M3_HYBRID35']:
            metadata = json.loads((case_directory(run_id) / 'progress.json').read_text(encoding='utf-8-sig'))
            self.assertEqual(len(metadata['manifest_finale']), 2)
            for item in metadata['manifest_finale']:
                path = project_path(item['file'])
                self.assertEqual(path.stat().st_size, item['byte'])
                self.assertEqual(sha(path), item['sha256'])


if __name__ == '__main__':
    unittest.main()
