"""
test_bbox_padding.py
Standalone tests for pad_box() bounding-box padding logic.
Run: python pipeline/test_bbox_padding.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bbox_utils import pad_box, DEFAULT_PADDING


class MockPage:
    """Minimal stand-in for a rendered page image with a fixed size."""

    def __init__(self, width, height):
        self.width = width
        self.height = height


PAD = DEFAULT_PADDING  # 15


def _assert(name, cond):
    if not cond:
        raise AssertionError(f"FAILED: {name}")
    print(f"PASS: {name}")


def _assert_all_int(name, padded):
    _assert(f"{name}: all coords are int",
            all(isinstance(c, int) for c in padded))


def test_standard_middle():
    page = MockPage(1366, 1899)
    box = [400, 300, 600, 500]
    padded = pad_box(box, page.width, page.height)
    print(f"  standard: box={box} -> padded={padded}")
    _assert("standard middle box pads 15px on all sides",
            padded == [385, 285, 615, 515])
    _assert_all_int("standard", padded)


def test_top_left_edge():
    page = MockPage(1366, 1899)
    box = [5, 5, 200, 200]
    padded = pad_box(box, page.width, page.height)
    print(f"  top-left: box={box} -> padded={padded}")
    _assert("top-left edge clamps x1/y1 to 0 (no negatives)",
            padded[0] == 0 and padded[1] == 0)
    _assert("top-left edge still pads x2/y2 normally",
            padded[2] == 215 and padded[3] == 215)
    _assert_all_int("top-left", padded)


def test_bottom_right_edge():
    page = MockPage(1366, 1899)
    box = [1166, 1699, 1366, 1899]  # x2/y2 already at page max
    padded = pad_box(box, page.width, page.height)
    print(f"  bottom-right: box={box} -> padded={padded}")
    _assert("bottom-right edge clamps x2 to page_width",
            padded[2] == page.width)
    _assert("bottom-right edge clamps y2 to page_height",
            padded[3] == page.height)
    _assert("bottom-right edge still pads x1/y1 normally",
            padded[0] == 1151 and padded[1] == 1684)
    _assert_all_int("bottom-right", padded)


def test_immutability():
    page = MockPage(1366, 1899)
    box = [400, 300, 600, 500]
    box_snapshot = list(box)
    box_id = id(box)
    padded = pad_box(box, page.width, page.height)
    print(f"  immutability: box_after={box} padded={padded}")
    _assert("original box value unchanged after padding",
            box == box_snapshot)
    _assert("original box identity unchanged (not replaced/mutated)",
            id(box) == box_id)
    _assert("padded is a distinct object from box",
            padded is not box)


def test_fractional_coords():
    page = MockPage(1366, 1899)
    box = [10.5, 4.2, 1365.9, 1898.5]
    padded = pad_box(box, page.width, page.height)
    print(f"  fractional: box={box} -> padded={padded}")
    _assert("fractional near-edge coords clamp to integer page bounds",
            padded == [0, 0, 1366, 1899])
    _assert_all_int("fractional-edge", padded)

    # A fractional box safely inside the page: top-left floors, bottom-right ceils.
    box2 = [100.5, 100.25, 200.75, 200.5]
    padded2 = pad_box(box2, page.width, page.height)
    print(f"  fractional-inner: box={box2} -> padded={padded2}")
    _assert("fractional inner box floors x1/y1 and ceils x2/y2 to ints",
            padded2 == [85, 85, 216, 216])
    _assert_all_int("fractional-inner", padded2)


def test_pil_crop_smoke():
    """End-to-end: padded (integer) box must produce a valid PIL crop at the
    production render resolution 1366x1899."""
    from PIL import Image
    img = Image.new("RGB", (1366, 1899), "white")
    for box in ([400, 300, 600, 500], [5, 5, 200, 200],
                [1166, 1699, 1366, 1899], [100.5, 100.25, 200.75, 200.5]):
        padded = pad_box(box, img.width, img.height)
        cropped = img.crop(tuple(padded))
        print(f"  smoke: box={box} -> padded={padded} crop_size={cropped.size}")
        _assert_all_int("smoke-padded", padded)
        _assert("smoke crop has positive size",
                cropped.size[0] > 0 and cropped.size[1] > 0)


def main():
    tests = [
        test_standard_middle,
        test_top_left_edge,
        test_bottom_right_edge,
        test_immutability,
        test_fractional_coords,
        test_pil_crop_smoke,
    ]
    print(f"Running {len(tests)} bbox padding tests (PADDING={PAD})...\n")
    for t in tests:
        print(f"[{t.__name__}]")
        t()
        print()
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
