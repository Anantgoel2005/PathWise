import numpy as np
import pytest

from modules.perspective import PerspectiveTransformer


def test_identity_homography_preserves_points():
    square = np.float32([[0, 0], [100, 0], [100, 100], [0, 100]])
    transformer = PerspectiveTransformer(square, square, (100, 100))

    assert transformer.transform_point(25, 40) == pytest.approx((25.0, 40.0))


def test_empty_point_collection_is_supported():
    square = np.float32([[0, 0], [100, 0], [100, 100], [0, 100]])
    transformer = PerspectiveTransformer(square, square, (100, 100))
    points = np.empty((0, 1, 2), dtype=np.float32)

    assert transformer.transform_points(points).shape == (0, 1, 2)
