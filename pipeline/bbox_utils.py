"""
bbox_utils.py
Shared bounding-box helpers for the crop pipeline.
Pure functions only (no I/O / side effects) so they are unit-testable.
"""
import math

DEFAULT_PADDING = 15


def pad_box(box, page_width, page_height, padding=DEFAULT_PADDING):
    """Expand a [x1, y1, x2, y2] box by `padding` px on every side, clamped to
    the page bounds [0, page_width] x [0, page_height].

    Pixels are discrete, so the result is returned as **integers** suitable for
    ``PIL.Image.crop``: the top-left corner is floored and the bottom-right
    corner is ceiled, i.e. padding always rounds *outward* to whole pixels.

    Returns a new list; the input `box` is never mutated.
    """
    x1, y1, x2, y2 = box
    return [
        math.floor(max(0, x1 - padding)),
        math.floor(max(0, y1 - padding)),
        math.ceil(min(page_width, x2 + padding)),
        math.ceil(min(page_height, y2 + padding)),
    ]
