"""
Integration tests for CrossRepoValidator and InputValidator (TEST-03)
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from integration.cross_repo_validator import CrossRepoValidator
from utils.validation import InputValidator, ValidationError


class TestCrossRepoValidator:

    def test_validate_stream2_k3_ranking_pass(self, tmp_path):
        report = tmp_path / "report.json"
        report.write_text(json.dumps({"selected_k3": "cooper_s7"}))
        assert CrossRepoValidator.validate_stream2_k3_ranking(report) is True

    def test_validate_stream2_k3_ranking_fail(self, tmp_path):
        report = tmp_path / "report.json"
        report.write_text(json.dumps({"selected_k3": "cooper_s18"}))
        assert CrossRepoValidator.validate_stream2_k3_ranking(report) is False

    def test_validate_stream3_gpu_pass(self, tmp_path):
        log = tmp_path / "gpu.log"
        log.write_text("pass rate: 100%")
        assert CrossRepoValidator.validate_stream3_gpu_results(log) is True

    def test_validate_stream3_gpu_fail(self, tmp_path):
        log = tmp_path / "gpu.log"
        log.write_text("pass rate: 80%")
        assert CrossRepoValidator.validate_stream3_gpu_results(log) is False

    def test_validate_stream2_missing_file(self, tmp_path):
        assert CrossRepoValidator.validate_stream2_k3_ranking(tmp_path / "missing.json") is False

    def test_validate_stream3_missing_file(self, tmp_path):
        assert CrossRepoValidator.validate_stream3_gpu_results(tmp_path / "missing.log") is False


class TestInputValidator:

    def test_validate_positive_integer_ok(self):
        assert InputValidator.validate_positive_integer(42, "pop") == 42

    def test_validate_positive_integer_zero_raises(self):
        with pytest.raises(ValidationError):
            InputValidator.validate_positive_integer(0, "pop")

    def test_validate_positive_integer_negative_raises(self):
        with pytest.raises(ValidationError):
            InputValidator.validate_positive_integer(-1, "pop")

    def test_validate_probability_ok(self):
        assert InputValidator.validate_probability(0.5, "rate") == 0.5

    def test_validate_probability_zero_ok(self):
        assert InputValidator.validate_probability(0.0, "rate") == 0.0

    def test_validate_probability_one_ok(self):
        assert InputValidator.validate_probability(1.0, "rate") == 1.0

    def test_validate_probability_out_of_range(self):
        with pytest.raises(ValidationError):
            InputValidator.validate_probability(1.5, "rate")

    def test_validate_list_length_ok(self):
        assert InputValidator.validate_list_length([1, 2, 3], 2) == [1, 2, 3]

    def test_validate_list_length_too_short(self):
        with pytest.raises(ValidationError):
            InputValidator.validate_list_length([1], 2, name="coeffs")

    def test_validate_list_length_too_long(self):
        with pytest.raises(ValidationError):
            InputValidator.validate_list_length([1, 2, 3, 4], 1, max_length=3, name="coeffs")

    def test_validate_file_path_existing(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("ok")
        result = InputValidator.validate_file_path(f, exists=True, is_file=True)
        assert result == f

    def test_validate_file_path_missing_raises(self, tmp_path):
        with pytest.raises(ValidationError):
            InputValidator.validate_file_path(tmp_path / "missing.txt", exists=True)
