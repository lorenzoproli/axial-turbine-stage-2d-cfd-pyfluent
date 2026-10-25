"""Measure native PNG colour-bar borders without modifying the image."""
import numpy as np
from PIL import Image

def colour_bar_rectangle(path):
    with Image.open(path) as image:
        width, height = image.size
        data = np.asarray(image.convert('RGB'))
    roi = data[:int(height * 0.875), :int(width * 0.15)]
    black = np.all(roi < 95, axis=2)
    runs = []
    for x in range(black.shape[1]):
        padded = np.r_[False, black[:, x], False].astype(np.int8)
        starts = np.flatnonzero(np.diff(padded) == 1)
        ends = np.flatnonzero(np.diff(padded) == -1)
        for start, end in zip(starts, ends):
            if end - start > height * 0.25:
                runs.append((x, int(start), int(end - 1), int(end - start)))
    assert runs, 'No long vertical colour-bar border detected'
    largest = max((r[3] for r in runs))
    edges = [r for r in runs if r[3] >= largest - 2]
    left = min((r[0] for r in edges))
    right = max((r[0] for r in edges))
    top = max((r[1] for r in edges))
    bottom = min((r[2] for r in edges))
    assert right - left > 10, 'Colour-bar left/right borders could not be distinguished'
    return [left, top, right, bottom]
