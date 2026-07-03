"""
bbox_utils.py
Shared bounding-box helpers for the crop pipeline.
Pure functions only (no I/O / side effects) so they are unit-testable.
"""

DEFAULT_PADDING = 15


def pad_box(box, page_width, page_height, padding=DEFAULT_PADDING):
    """Expand a [x1, y1, x2, y2] box by `padding` px on every side, clamped to
    the page bounds [0, page_width] x [0, page_height].

    Returns a new list; the input `box` is never mutated.
    """
    x1, y1, x2, y2 = box
    return [
        max(0, x1 - padding),
        max(0, y1 - padding),
        min(page_width, x2 + padding),
        min(page_height, y2 + padding),
    ]
