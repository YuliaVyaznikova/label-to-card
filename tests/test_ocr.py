import cv2
import numpy as np
import pytest

from card.ocr import ROTATIONS, back, letters, merge


@pytest.mark.parametrize("angle", [90, 180, 270])
def test_box_from_rotated_view_maps_back_to_original(angle):
    image = np.zeros((3, 5), dtype=np.uint8)
    image[0, 1] = 255
    view = cv2.rotate(image, ROTATIONS[angle])
    y, x = map(int, np.argwhere(view == 255)[0])
    corners = [back(x, y, angle, 5, 3), back(x + 1, y + 1, angle, 5, 3)]
    xs = sorted(point[0] for point in corners)
    ys = sorted(point[1] for point in corners)
    assert (xs, ys) == ([1, 2], [0, 1])


def test_letters_ignore_digits_and_unsure_lines():
    items = [{"text": "Масса 500 г", "confidence": 1.0}, {"text": "722277", "confidence": 0.9}, {"text": "Ill", "confidence": 0.3}]
    assert letters(items) == 6


def fragment(text, x0, y0, x1, y1):
    return {"text": text, "confidence": 0.9, "box": [x0, y0, x1, y1], "view": [x0, y0, x1, y1]}


def test_merge_joins_words_of_one_row_and_splits_columns():
    fragments = [
        fragment("нетто", 70, 2, 120, 22), fragment("Масса", 0, 0, 60, 20), fragment("500 г", 130, 1, 170, 21),
        fragment("Белки", 0, 40, 50, 60), fragment("3,2 г", 400, 40, 440, 60),
    ]
    lines = merge(fragments, 0.5, 3)
    assert [line["text"] for line in lines] == ["Масса нетто 500 г", "Белки", "3,2 г"]
    assert lines[0]["box"] == [0, 0, 170, 22]