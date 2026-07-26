"""Unit tests for detection TTA's D4 (dihedral) symmetry transforms.

Pure tensor-manipulation logic, no model needed -- verified against synthetic
data before ever running on Kaggle, per this project's standing methodology.
"""

import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from predict_unet_transformer import _TTA_VARIANTS, _d4_forward, _d4_inverse

_ALL_8 = [(False, 0), (True, 0), (False, 1), (True, 1), (False, 2), (True, 2), (False, 3), (True, 3)]


def test_forward_inverse_round_trip_reconstructs_original():
    x = torch.randn(1, 1, 6, 6)
    for flip, k in _ALL_8:
        transformed = _d4_forward(x, flip, k)
        assert transformed.shape == x.shape
        reconstructed = _d4_inverse(transformed, flip, k)
        assert torch.equal(reconstructed, x), f"round-trip failed for flip={flip}, k={k}"


def test_all_8_variants_are_distinct():
    # An asymmetric image: if any two of the 8 D4 elements produced the same
    # output, the "variants" list wouldn't actually be averaging 8 independent
    # views -- guards against an algebra mistake collapsing the group.
    x = torch.arange(36, dtype=torch.float32).reshape(1, 1, 6, 6)
    outputs = [_d4_forward(x, flip, k) for flip, k in _ALL_8]
    for i in range(len(outputs)):
        for j in range(i + 1, len(outputs)):
            assert not torch.equal(outputs[i], outputs[j]), f"{_ALL_8[i]} and {_ALL_8[j]} collided"


def test_tta_variant_counts():
    assert _TTA_VARIANTS["off"] == []
    assert len(_TTA_VARIANTS["flips"]) == 3  # + identity = 4-way (Klein four-group)
    assert len(_TTA_VARIANTS["d4"]) == 7  # + identity = full 8-way dihedral group


def test_flips_is_a_subset_of_d4():
    # "flips" (current default) must be exactly the subset of "d4" that
    # excludes the 90/270-degree rotations -- d4 is a strict superset, not a
    # different parameterization, so it's a genuine extension of the default.
    assert set(_TTA_VARIANTS["flips"]).issubset(set(_TTA_VARIANTS["d4"]))


def test_identity_not_listed_as_a_variant():
    # (False, 0) is the identity, handled implicitly by the untransformed
    # base pass -- it must never appear in the "extra variants" lists, or it
    # would be double-counted in the average.
    for mode in ("off", "flips", "d4"):
        assert (False, 0) not in _TTA_VARIANTS[mode]
