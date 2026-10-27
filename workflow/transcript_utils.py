"""Release only transcript handles owned by the current PyFluent session."""
from data_schema import csv, json
from common import WORK, ROOT
from pathlib import Path
import gc
from ansys.fluent.core.streaming_services.transcript_streaming import AppendToFile

def close_transcript(s):
    s.transcript.stop()
    for obj in gc.get_objects():
        try:
            if isinstance(obj, AppendToFile) and (not obj.f.closed) and (project_path(obj.f.name).resolve().is_relative_to(WORK.resolve()) or project_path(obj.f.name).resolve().is_relative_to(project_path(ROOT / '03_simulazioni/convergenza_griglia').resolve())):
                obj.f.flush()
                obj.f.close()
        except (ReferenceError, AttributeError):
            continue
    gc.collect()
