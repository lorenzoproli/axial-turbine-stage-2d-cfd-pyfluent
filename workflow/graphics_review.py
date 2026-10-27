"""Record an operator's visual acceptance of the three native scene previews."""
from pathlib import Path
import argparse
from common import ROOT, output_path, sha, jwrite, json


def approve(directory):
    directory = output_path(directory)
    proof = directory / "proof.json"
    record = json.loads(proof.read_text(encoding="utf-8"))
    if record.get("state") != "MACH_STREAM_T0_MOVING_RESTART_AND_PLAYBACK_VERIFIED":
        raise ValueError("The native scene preview did not finish successfully.")
    frames = sorted(directory.glob("decoded_*.png"))
    if len(frames) != 3:
        raise ValueError("Three decoded preview frames are required.")
    target = directory / "visual_review.json"
    if target.exists():
        raise FileExistsError("The visual scene record already exists.")
    result = dict(state="VISUALLY_VERIFIED", proof_sha256=sha(proof),
                  reviewed_frames=[dict(file=p.name, byte=p.stat().st_size, sha256=sha(p)) for p in frames])
    jwrite(target, result)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True)
    parser.add_argument("--approve", action="store_true", required=True,
                        help="Record acceptance after inspecting all three preview PNGs")
    args = parser.parse_args()
    print(approve(args.directory))
