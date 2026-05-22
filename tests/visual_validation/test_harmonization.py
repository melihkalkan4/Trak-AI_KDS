"""Harmonization mapping invariants for all three modalities."""

from visual_validation import config


def test_yolov8_mapping_covers_all_raw_classes():
    raw = set(config.YOLOV8_CLASS_NAMES)
    mapped = set(config.YOLOV8_TO_HARMONIZED)
    missing = raw - mapped
    assert not missing, f"YOLOv8 mapping missing: {missing}"


def test_yolov8_targets_are_canonical():
    for raw, harm in config.YOLOV8_TO_HARMONIZED.items():
        assert harm in config.HARMONIZED_LABELS, f"{raw} -> {harm} (bad target)"


def test_satellite_does_not_emit_disease():
    assert "disease" not in config.SATELLITE_CLASS_NAMES
    for raw, harm in config.SATELLITE_TO_HARMONIZED.items():
        assert harm != "disease", "satellite should never map to disease"


def test_feature_zscore_thresholds_monotonic():
    f = config.feature_zscore_to_class
    assert f(0.0) == "healthy"
    assert f(-0.5) == "healthy"
    assert f(-1.5) == "mild_stress"
    assert f(-3.0) == "severe_stress"
    assert f(float("nan")) == "healthy"        # NaN guard


def test_harmonized_labels_unique_and_canonical():
    assert len(set(config.HARMONIZED_LABELS)) == len(config.HARMONIZED_LABELS)
    assert set(config.HARMONIZED_INDEX.keys()) == set(config.HARMONIZED_LABELS)
