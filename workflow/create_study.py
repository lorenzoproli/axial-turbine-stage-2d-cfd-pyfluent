"""Prepare an independent, single-mesh work copy; no solver starts by default."""
from data_schema import csv, json
from pathlib import Path
import argparse
import hashlib
import re
import shutil
import subprocess
import sys

# Native files are opened with writer sharing denied during input copies.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import safe_read

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def plan(mesh, name, periods):
    if mesh not in ("M1", "M2", "M3"):
        raise ValueError("Mesh must be M1, M2 or M3.")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", name):
        raise ValueError("Study name must start with a letter and contain only letters, digits, _ or -.")
    if type(periods) is not int or not 4 <= periods <= 100:
        raise ValueError("Choose 4 to 100 complete periods; the final three are analysed.")
    target = ROOT / "runs/new_studies" / name
    if target.exists():
        raise FileExistsError("Study already exists; use its documented restart command: " + str(target))
    configuration = json.loads((ROOT / "config/hybrid35_campaign_config.json").read_text(encoding="utf-8"))
    run_id = mesh + "_HYBRID35"
    run = next(row for row in configuration["run_inputs"] if row["id"] == run_id)
    receipt_path = "inputs/initial_conditions/" + mesh + "/hybrid_initialization_verified.json"
    paths = {configuration["initial_geometry_reference"], run["source_case"], run["source_mesh"],
             run["settings_file"], receipt_path}
    evidence_path = ROOT / receipt_path
    if not evidence_path.is_file():
        raise FileNotFoundError("Install the native-inputs release asset first: " + receipt_path)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if (evidence.get("initial_clock") != {"time_s": 0.0, "step": 0}
            or evidence.get("restoration_before_hybrid") is not True
            or evidence.get("physical_setup_unchanged") is not True
            or evidence.get("automatic_mesh_adaptation_active") is not False):
        raise ValueError("Hybrid initial-state declaration failed.")
    paths.update(row["file"] for row in evidence["manifest_initial_checkpoint"])
    index = {row["path"]: row for row in json.loads((ROOT / "config/native_data_index.json").read_text(encoding="utf-8"))["files"]}
    records = []
    for relative in sorted(paths):
        row = index[relative]
        source = ROOT / relative
        if not source.is_file() or source.stat().st_size != row["bytes"] or sha(source) != row["sha256"]:
            raise ValueError("Missing or changed native input: " + relative)
        records.append(row)
    return target, configuration, run, records


def prepare(mesh, name, periods=35, write=False, capture_mach=False):
    if capture_mach and mesh != "M3":
        raise ValueError("The native Mach capture preset is provided for M3.")
    target, cfg, run, records = plan(mesh, name, periods)
    result = dict(state="OFFLINE_INPUTS_VERIFIED", solver_started=False, mesh=mesh, name=name,
                  periods=periods, mpi_processes=24, timestep_s=cfg["timestep_s"], capture_mach=capture_mach,
                  destination=target.relative_to(ROOT).as_posix(), inputs=records)
    if not write:
        return result
    target.mkdir(parents=True, exist_ok=False)
    for item in records:
        destination = target / item["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        with safe_read(ROOT / item["path"]) as source, destination.open("xb") as output:
            shutil.copyfileobj(source, output)
        if sha(destination) != item["sha256"]:
            raise ValueError("Working input copy checksum differs: " + item["path"])
    shutil.copytree(ROOT / "workflow", target / "workflow", ignore=shutil.ignore_patterns("__pycache__"))
    (target / "config").mkdir()
    for filename in ["workflow_config.json", "path_aliases.json", "legacy_schema.json", "display_labels.json", "native_animation_config.json", "mach_stream_config.json"]:
        shutil.copy2(ROOT / "config" / filename, target / "config" / filename)
    cfg.update(campaign_id="INDEPENDENT_" + name, campaign_closed=False, run_ids=[run["id"]],
               run_inputs=[run], period_targets_by_run={run["id"]: periods},
               total_periods_each_mesh=periods, total_steps_each_mesh=periods * cfg["steps_per_period"],
               total_time_each_mesh_s=periods * cfg["steps_per_period"] * cfg["timestep_s"],
               native_animation_meshes=[], M2_native_animation_enabled=False)
    if not capture_mach:
        cfg.pop("M3_native_mach_stream_configuration", None)
        run.pop("native_mach_stream_configuration", None)
    run["native_animation_enabled"] = bool(capture_mach)
    (target / "config/hybrid35_campaign_config.json").write_text(json.dumps(cfg, indent=2)+"\n", encoding="utf-8")
    state = dict(state="OPEN_INDEPENDENT_STUDY", campaign_closed=False, solver_launches_enabled=True,
                 historical_campaign_reopened=False, automatic_extensions=False)
    (target / "config/campaign_state.json").write_text(json.dumps(state, indent=2)+"\n", encoding="utf-8")
    result.update(state="PREPARED_NOT_EXECUTED", initialisation="Reload the verified original-position Hybrid t=0 case/data; no reinitialisation",
                  source_configuration_sha256=sha(ROOT / "config/hybrid35_campaign_config.json"))
    (target / "study.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    (target / "README.md").write_text(
        "# Independent CFD study\n\nRun from this directory with the original environment's Python. "
        "24 MPI processes and Fluent 2024 R2 are required. Image capture is opt-in. "
        "The final three complete periods supply the statistics.\n\n"
        "    python workflow/run_hybrid35_campaign.py --check-inputs\n\n"
        "    python workflow/run_hybrid35_campaign.py --only " + run["id"] + "\n\n"
        "The same --only command resumes an interrupted run from a verified checkpoint; "
        "a completed run is preserved. Create a new study for a different duration. "
        "Do not edit checkpoint times or merge independent monitor histories.\n", encoding="utf-8")
    return result


def prepare_baseline(name, write=False):
    """Prepare one common-checkpoint workspace for iteration/timestep tests."""
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", name):
        raise ValueError("Use a study name containing letters, digits, _ or -.")
    target = ROOT / "runs/new_studies" / name
    if target.exists():
        raise FileExistsError("Study already exists: " + str(target))
    configuration = json.loads((ROOT / "config/workflow_config.json").read_text(encoding="utf-8"))
    checkpoint = configuration["campaign"]["checkpoint"]
    paths = [checkpoint, checkpoint.replace(".cas.h5", ".dat.h5")]
    index = {row["path"]: row for row in json.loads((ROOT / "config/native_data_index.json").read_text(encoding="utf-8"))["files"]}
    records = []
    for relative in paths:
        row = index[relative]
        source = ROOT / relative
        if not source.is_file() or source.stat().st_size != row["bytes"] or sha(source) != row["sha256"]:
            raise ValueError("Missing or changed common checkpoint: " + relative)
        records.append(row)
    result = dict(state="OFFLINE_INPUTS_VERIFIED", solver_started=False, name=name,
                  dataset="baseline_comparisons", mpi_processes=24, initial_time_s=0.010653,
                  run_ids=[row["id"] for row in configuration["campaign"]["runs"]],
                  destination=target.relative_to(ROOT).as_posix(), inputs=records)
    if not write:
        return result
    target.mkdir(parents=True, exist_ok=False)
    for row in records:
        destination = target / row["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        with safe_read(ROOT / row["path"]) as source, destination.open("xb") as output:
            shutil.copyfileobj(source, output)
        if sha(destination) != row["sha256"]:
            raise ValueError("Common checkpoint copy differs: " + row["path"])
    shutil.copytree(ROOT / "workflow", target / "workflow", ignore=shutil.ignore_patterns("__pycache__"))
    (target / "config").mkdir()
    for filename in ["workflow_config.json", "path_aliases.json", "legacy_schema.json", "display_labels.json"]:
        shutil.copy2(ROOT / "config" / filename, target / "config" / filename)
    (target / "config/campaign_state.json").write_text(json.dumps(dict(
        state="OPEN_INDEPENDENT_BASELINE_STUDY", campaign_closed=False,
        solver_launches_enabled=True, automatic_extensions=False), indent=2)+"\n", encoding="utf-8")
    (target / "config/hybrid35_campaign_config.json").write_text(json.dumps(dict(
        campaign_id="BASELINE_" + name, campaign_closed=False, run_ids=[]), indent=2)+"\n", encoding="utf-8")
    result["state"] = "PREPARED_NOT_EXECUTED"
    (target / "study.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    (target / "README.md").write_text(
        "# Baseline comparison workspace\n\nEvery run reloads the same common checkpoint. "
        "Physical time, moving-mesh position and native time histories are preserved. "
        "Execute one run at a time with python workflow/cfd.py run --id ITER30 "
        "(then ITER60, T100, T200 or T400). Use resume instead of run after a controlled stop. "
        "The first three periods after changing settings are excluded from the final statistics. "
        "Report preparation is separate from the numerical workflow.\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--mesh", choices=["M1", "M2", "M3"])
    selection.add_argument("--baseline-comparisons", action="store_true")
    parser.add_argument("--name", required=True)
    parser.add_argument("--capture-mach", action="store_true", help="Enable the M3 native Mach preset and its visual scene check")
    parser.add_argument("--periods", type=int)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare", action="store_true", help="Create an isolated work copy without starting Fluent")
    mode.add_argument("--execute", action="store_true", help="Create the work copy and explicitly start one Fluent run")
    args = parser.parse_args()
    if args.baseline_comparisons:
        if args.execute or args.periods is not None or args.capture_mach:
            parser.error("Baseline preparation uses the recorded comparison windows; start each run explicitly with cfd.py.")
        result = prepare_baseline(args.name, args.prepare)
    else:
        result = prepare(args.mesh, args.name, args.periods if args.periods is not None else 35, args.prepare or args.execute, args.capture_mach)
    print(json.dumps(result, indent=2), flush=True)
    if args.execute:
        target = ROOT / result["destination"]
        subprocess.run([sys.executable, "-B", str(target / "workflow/run_hybrid35_campaign.py"),
                        "--only", args.mesh + "_HYBRID35"], cwd=target, check=True)


if __name__ == "__main__":
    main()
