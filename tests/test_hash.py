"""Tests for _hash.py — stable_id."""

import pytest
from chinese_scraper_utils import stable_id


class TestStableId:
    def test_deterministic(self):
        """Same inputs produce same output."""
        a = stable_id("a", "b", "c")
        b = stable_id("a", "b", "c")
        assert a == b

    def test_different_inputs_differ(self):
        a = stable_id("a", "b", "c")
        b = stable_id("x", "y", "z")
        assert a != b

    def test_output_length(self):
        assert len(stable_id("test")) == 16

    def test_single_input(self):
        result = stable_id("hello")
        assert isinstance(result, str)
        assert len(result) == 16

    def test_multiple_inputs_joined(self):
        """Multiple parts produce a different hash than concatenated single part."""
        separate = stable_id("a", "b")
        combined = stable_id("ab")
        assert separate != combined  # Because separator is "|"

    def test_hex_format(self):
        result = stable_id("test")
        assert all(c in "0123456789abcdef" for c in result)
