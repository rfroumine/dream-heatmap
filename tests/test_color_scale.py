"""Tests for ColorScale."""

import numpy as np
import pytest

from dream_heatmap.core.color_scale import ColorScale


class TestColorScaleInit:
    def test_default(self):
        cs = ColorScale()
        assert cs.cmap_name == "viridis"
        assert cs.vmin == 0.0
        assert cs.vmax == 1.0

    def test_custom_cmap(self):
        cs = ColorScale("plasma", vmin=-1.0, vmax=1.0)
        assert cs.cmap_name == "plasma"

    def test_invalid_cmap_raises(self):
        with pytest.raises(ValueError, match="Unknown colormap"):
            ColorScale("not_a_real_cmap")


class TestColorScaleLUT:
    def test_lut_shape(self):
        cs = ColorScale()
        assert cs.lut.shape == (256, 4)

    def test_lut_dtype(self):
        cs = ColorScale()
        assert cs.lut.dtype == np.uint8

    def test_lut_values_in_range(self):
        cs = ColorScale()
        assert cs.lut.min() >= 0
        assert cs.lut.max() <= 255

    def test_different_cmaps_differ(self):
        cs1 = ColorScale("viridis")
        cs2 = ColorScale("plasma")
        # The LUTs should be different
        assert not np.array_equal(cs1.lut, cs2.lut)


class TestColorScaleToBytes:
    def test_bytes_length(self):
        cs = ColorScale()
        b = cs.to_bytes()
        assert len(b) == 256 * 4  # 1024 bytes

    def test_bytes_roundtrip(self):
        cs = ColorScale()
        b = cs.to_bytes()
        restored = np.frombuffer(b, dtype=np.uint8).reshape(256, 4)
        np.testing.assert_array_equal(restored, cs.lut)


class TestColorScaleValueToIndex:
    def test_min_maps_to_0(self):
        cs = ColorScale("viridis", vmin=0, vmax=100)
        assert cs.value_to_index(0) == 0

    def test_max_maps_to_255(self):
        cs = ColorScale("viridis", vmin=0, vmax=100)
        assert cs.value_to_index(100) == 255

    def test_midpoint(self):
        cs = ColorScale("viridis", vmin=0, vmax=100)
        idx = cs.value_to_index(50)
        assert 125 <= idx <= 129  # approximately 127

    def test_below_min_clamps(self):
        cs = ColorScale("viridis", vmin=0, vmax=100)
        assert cs.value_to_index(-50) == 0

    def test_above_max_clamps(self):
        cs = ColorScale("viridis", vmin=0, vmax=100)
        assert cs.value_to_index(200) == 255

    def test_equal_vmin_vmax(self):
        cs = ColorScale("viridis", vmin=5, vmax=5)
        assert cs.value_to_index(5) == 127


class TestColorScaleNanColor:
    def test_default_nan_color(self):
        cs = ColorScale()
        assert cs.nan_color == (200, 200, 200, 255)

    def test_custom_nan_color(self):
        cs = ColorScale(nan_color=(0, 0, 0, 0))
        assert cs.nan_color == (0, 0, 0, 0)
