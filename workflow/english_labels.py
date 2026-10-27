"""English presentation labels; native Fluent identifiers remain traceable."""
from data_schema import csv, json
from pathlib import Path
from data_schema import json
TRANSLATIONS = json.raw_loads((Path(__file__).resolve().parents[1] / 'config/display_labels.json').read_text(encoding='utf-8'))['labels']

def translate(value):
    value = str(value)
    for old, new in sorted(TRANSLATIONS.items(), key=lambda item: len(item[0]), reverse=True):
        value = value.replace(old, new)
    return value

def install():
    from matplotlib.figure import Figure
    from matplotlib.text import Text
    if getattr(Figure.savefig, 'english_labels_installed', False):
        return
    original = Figure.savefig

    def savefig(figure, *args, **kwargs):
        for artist in figure.findobj(match=Text):
            artist.set_text(translate(artist.get_text()))
        return original(figure, *args, **kwargs)
    savefig.english_labels_installed = True
    Figure.savefig = savefig
