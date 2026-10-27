"""Offline acceptance tests for independent work copies and safe data installs."""
from pathlib import Path
import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workflow"))


def load(name):
    spec = importlib.util.spec_from_file_location("reuse_" + name, ROOT / "workflow" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReuseDeliveryTests(unittest.TestCase):
    def test_legacy_records_use_english_without_changing_native_ids_or_values(self):
        from data_schema import json as records, csv as tables
        import io
        raw = '{"passi_completati":14000,"tempo_corrente_s":0.010415432475,"stato":"eseguita_periodicita_non_confermata","monitor":"forza_y_rotore"}'
        data = records.loads(raw)
        self.assertEqual(data["completed_steps"], 14000)
        self.assertEqual(data["current_time_s"], 0.010415432475)
        self.assertEqual(data["status"], "COMPLETED_PERIODICITY_UNCONFIRMED")
        self.assertEqual(data["monitor"], "forza_y_rotore")
        self.assertEqual(records.loads(records.dumps(data)), data)
        table = tables.DictReader(io.StringIO("tempo_s,media\n0.01,-1305.516\n"))
        self.assertEqual(table.fieldnames, ["physical_time_s", "mean"])
        self.assertEqual(next(table), {"physical_time_s":"0.01", "mean":"-1305.516"})
        with self.assertRaises(ValueError):
            records.loads('{"passi_completati":1,"completed_steps":2}')

    def test_prepare_isolated_copy_and_preserve_historical_guard(self):
        module = load("create_study")
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            shutil.copytree(ROOT / "workflow", base / "workflow", ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(ROOT / "config", base / "config")
            cfg = json.loads((base / "config/hybrid35_campaign_config.json").read_text(encoding="utf-8"))
            run = next(row for row in cfg["run_inputs"] if row["id"] == "M3_HYBRID35")
            files = {cfg["initial_geometry_reference"]: b"reference",
                     run["source_case"]: b"prepared case", run["source_mesh"]: b"mesh",
                     run["settings_file"]: b"settings",
                     "inputs/initial_conditions/M3/hybrid_initial.cas.h5": b"initial case",
                     "inputs/initial_conditions/M3/hybrid_initial.dat.h5": b"initial data"}
            pairs = [dict(file=p, byte=len(v), sha256=hashlib.sha256(v).hexdigest())
                     for p, v in files.items() if "/hybrid_initial." in p]
            evidence = dict(initial_clock=dict(time_s=0.0, step=0), restoration_before_hybrid=True,
                            physical_setup_unchanged=True, automatic_mesh_adaptation_active=False, manifest_initial_checkpoint=pairs)
            files["inputs/initial_conditions/M3/hybrid_initialization_verified.json"] = json.dumps(evidence).encode()
            records = []
            for relative, value in files.items():
                path = base / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(value)
                records.append(dict(path=relative, bytes=len(value), sha256=hashlib.sha256(value).hexdigest()))
            run["source_case_sha256"] = hashlib.sha256(files[run["source_case"]]).hexdigest()
            run["source_mesh_sha256"] = hashlib.sha256(files[run["source_mesh"]]).hexdigest()
            run["settings_sha256"] = hashlib.sha256(files[run["settings_file"]]).hexdigest()
            cfg["initial_geometry_reference_sha256"] = hashlib.sha256(files[cfg["initial_geometry_reference"]]).hexdigest()
            (base / "config/hybrid35_campaign_config.json").write_text(json.dumps(cfg), encoding="utf-8")
            (base / "config/native_data_index.json").write_text(json.dumps(dict(files=records)), encoding="utf-8")
            module.ROOT = base
            protected = (base / "config/campaign_state.json").read_bytes()
            dry = module.prepare("M3", "comparison", 4)
            self.assertFalse((base / dry["destination"]).exists())
            with self.assertRaises(ValueError):
                module.prepare("M3", "../escape", 4)
            with self.assertRaises(ValueError):
                module.prepare("M3", "short", 3)
            result = module.prepare("M3", "comparison", 4, write=True)
            study = base / result["destination"]
            self.assertEqual(protected, (base / "config/campaign_state.json").read_bytes())
            copied = json.loads((study / "config/hybrid35_campaign_config.json").read_text())
            self.assertFalse(copied["campaign_closed"])
            self.assertFalse(copied["run_inputs"][0]["native_animation_enabled"])
            self.assertNotIn("M3_native_mach_stream_configuration", copied)
            self.assertEqual(copied["period_targets_by_run"], {"M3_HYBRID35": 4})
            for relative, value in files.items():
                self.assertEqual((base / relative).read_bytes(), value)
            check = subprocess.run([sys.executable, "-B", "workflow/run_hybrid35_campaign.py", "--check-inputs"],
                                   cwd=study, capture_output=True, text=True, timeout=30)
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            guard = subprocess.run([sys.executable, "-B", "-c",
                "import sys;sys.path.insert(0,'workflow');from cfd import ensure_campaign_open;ensure_campaign_open();"
                "assert not any(k.startswith('ansys') for k in sys.modules)"],
                cwd=study, capture_output=True, text=True, timeout=30)
            self.assertEqual(guard.returncode, 0, guard.stdout + guard.stderr)
            with self.assertRaises(FileExistsError):
                module.prepare("M3", "comparison", 4, write=True)
            (base / run["source_mesh"]).write_bytes(b"changed")
            with self.assertRaises(ValueError):
                module.prepare("M3", "tampered", 4)

    def test_native_install_rejects_extra_members_and_preserves_different_files(self):
        module = load("native_data")
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp) / "checkout"
            (base / "config").mkdir(parents=True)
            payload = b"native data fixture"
            row = dict(path="inputs/mesh.dat", bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
            (base / "config/native_data_index.json").write_text(json.dumps(dict(files=[row])))
            module.ROOT = base
            for bad in [True, False]:
                archive_path = Path(temp) / ("bad.zip" if bad else "good.zip")
                with zipfile.ZipFile(archive_path, "x") as archive:
                    archive.writestr(row["path"], payload)
                    archive.writestr("NATIVE_ARCHIVE_MANIFEST.json", json.dumps(dict(kind="inputs", files=[row])))
                    archive.writestr("NATIVE_DATA_LICENSE.md", "licence fixture")
                    if bad:
                        archive.writestr("../outside.dat", b"unexpected")
                record = dict(bytes=archive_path.stat().st_size, sha256=hashlib.sha256(archive_path.read_bytes()).hexdigest())
                (base / "config/release_assets.json").write_text(json.dumps(dict(assets=dict(inputs=record))))
                if bad:
                    with self.assertRaises(ValueError):
                        module.install(archive_path, "inputs")
                    self.assertFalse((base / "inputs").exists())
                else:
                    check = module.install(archive_path, "inputs", check_only=True)
                    self.assertFalse((base / "inputs").exists())
                    self.assertEqual(check["files"], 1)
                    self.assertEqual(module.install(archive_path, "inputs")["newly_installed"], 1)
                    self.assertEqual(module.install(archive_path, "inputs")["existing_identical"], 1)
                    (base / row["path"]).write_bytes(b"preserved")
                    with self.assertRaises(FileExistsError):
                        module.install(archive_path, "inputs")
                    self.assertEqual((base / row["path"]).read_bytes(), b"preserved")


if __name__ == "__main__":
    unittest.main()
