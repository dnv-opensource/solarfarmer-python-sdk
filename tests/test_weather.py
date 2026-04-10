"""Tests for weather module: TSV validation and DataFrame conversion utilities."""

import textwrap
from pathlib import Path

import pytest

from solarfarmer.weather import (
    PVLIB_COLUMN_MAP,
    check_sequential_year_timestamps,
    from_dataframe,
    from_pvlib,
)


class TestCheckSequentialYearTimestamps:
    """Tests for check_sequential_year_timestamps()."""

    def test_single_year_passes(self, tmp_path):
        tsv = tmp_path / "good.tsv"
        tsv.write_text(
            textwrap.dedent("""\
            DateTime\tGHI\tTAmb
            1990-01-01T00:00+00:00\t0\t5.0
            1990-06-15T12:00+00:00\t800\t25.0
            1990-12-31T23:00+00:00\t0\t3.0
        """)
        )
        check_sequential_year_timestamps(tsv)  # should not raise

    def test_sequential_multi_year_passes(self, tmp_path):
        tsv = tmp_path / "multi_year.tsv"
        tsv.write_text(
            textwrap.dedent("""\
            DateTime\tGHI\tTAmb
            2020-06-15T12:00+00:00\t800\t25.0
            2021-06-15T12:00+00:00\t810\t26.0
            2022-06-15T12:00+00:00\t820\t27.0
        """)
        )
        check_sequential_year_timestamps(tsv)  # should not raise

    def test_shuffled_tmy_years_raises(self, tmp_path):
        tsv = tmp_path / "bad.tsv"
        tsv.write_text(
            textwrap.dedent("""\
            DateTime\tGHI\tTAmb
            2010-01-01T00:00+00:00\t0\t5.0
            2003-06-15T12:00+00:00\t800\t25.0
            2016-12-31T23:00+00:00\t0\t3.0
        """)
        )
        with pytest.raises(ValueError, match="non-sequential years"):
            check_sequential_year_timestamps(tsv)

    def test_header_only_passes(self, tmp_path):
        tsv = tmp_path / "header_only.tsv"
        tsv.write_text("DateTime\tGHI\tTAmb\n")
        check_sequential_year_timestamps(tsv)  # no data lines, no error

    def test_string_path_accepted(self, tmp_path):
        tsv = tmp_path / "str_path.tsv"
        tsv.write_text(
            textwrap.dedent("""\
            DateTime\tGHI\tTAmb
            1990-01-01T00:00+00:00\t0\t5.0
        """)
        )
        check_sequential_year_timestamps(str(tsv))  # str path should work


class TestFromDataframe:
    """Tests for from_dataframe()."""

    @pytest.fixture
    def sample_df(self):
        pd = pytest.importorskip("pandas")
        idx = pd.date_range("2020-01-01", periods=3, freq="h", tz="UTC")
        return pd.DataFrame(
            {"ghi": [0, 100, 200], "temp_air": [5.0, 6.0, 7.0]},
            index=idx,
        )

    def test_basic_write(self, tmp_path, sample_df):
        out = from_dataframe(sample_df, tmp_path / "out.tsv")
        assert out.exists()
        lines = out.read_text().splitlines()
        assert lines[0].startswith("DateTime")
        assert len(lines) == 4  # header + 3 data rows

    def test_column_rename(self, tmp_path, sample_df):
        out = from_dataframe(
            sample_df,
            tmp_path / "out.tsv",
            column_map={"ghi": "GHI", "temp_air": "TAmb"},
        )
        header = out.read_text().splitlines()[0]
        assert "GHI" in header
        assert "TAmb" in header

    def test_year_remap(self, tmp_path, sample_df):
        out = from_dataframe(sample_df, tmp_path / "out.tsv", year=1990)
        first_data = out.read_text().splitlines()[1]
        assert first_data.startswith("1990-")

    def test_pressure_conversion(self, tmp_path):
        pd = pytest.importorskip("pandas")
        idx = pd.date_range("2020-01-01", periods=2, freq="h", tz="UTC")
        df = pd.DataFrame({"Pressure": [101325.0, 100000.0]}, index=idx)
        out = from_dataframe(df, tmp_path / "out.tsv", pressure_pa_to_mbar=True)
        lines = out.read_text().splitlines()
        # 101325 / 100 = 1013.25
        assert "1013.25" in lines[1]

    def test_no_datetimeindex_raises(self, tmp_path):
        pd = pytest.importorskip("pandas")
        df = pd.DataFrame({"ghi": [0, 100]})
        with pytest.raises(ValueError, match="DatetimeIndex"):
            from_dataframe(df, tmp_path / "out.tsv")

    def test_timestamp_format_has_utc_offset(self, tmp_path, sample_df):
        out = from_dataframe(sample_df, tmp_path / "out.tsv")
        first_data = out.read_text().splitlines()[1]
        # Should contain +00:00 UTC offset
        assert "+00:00" in first_data

    def test_timestamp_format_non_utc_offset(self, tmp_path):
        """Non-UTC timezone (e.g. +05:30) must produce correct ±HH:MM offset."""
        pd = pytest.importorskip("pandas")
        import datetime as dt

        tz = dt.timezone(dt.timedelta(hours=5, minutes=30))
        idx = pd.date_range("2020-01-01", periods=2, freq="h", tz=tz)
        df = pd.DataFrame({"GHI": [0, 100]}, index=idx)
        out = from_dataframe(df, tmp_path / "out.tsv")
        lines = out.read_text().splitlines()
        assert "+05:30" in lines[1]
        assert "+05:30" in lines[2]

    def test_returns_path(self, tmp_path, sample_df):
        result = from_dataframe(sample_df, tmp_path / "weather.tsv")
        assert isinstance(result, Path)


class TestFromPvlib:
    """Tests for from_pvlib() convenience wrapper."""

    @pytest.fixture
    def pvlib_df(self):
        pd = pytest.importorskip("pandas")
        idx = pd.date_range("2020-01-01", periods=3, freq="h", tz="UTC")
        return pd.DataFrame(
            {
                "ghi": [0, 500, 800],
                "dhi": [0, 200, 300],
                "temp_air": [5.0, 15.0, 25.0],
                "wind_speed": [2.0, 3.0, 4.0],
                "pressure": [101325.0, 101325.0, 101325.0],
            },
            index=idx,
        )

    def test_columns_renamed(self, tmp_path, pvlib_df):
        out = from_pvlib(pvlib_df, tmp_path / "out.tsv")
        header = out.read_text().splitlines()[0]
        for sf_col in PVLIB_COLUMN_MAP.values():
            assert sf_col in header

    def test_pressure_converted(self, tmp_path, pvlib_df):
        out = from_pvlib(pvlib_df, tmp_path / "out.tsv")
        lines = out.read_text().splitlines()
        # 101325 / 100 = 1013.25
        assert "1013.25" in lines[1]

    def test_year_remapped_to_1990(self, tmp_path, pvlib_df):
        out = from_pvlib(pvlib_df, tmp_path / "out.tsv")
        first_data = out.read_text().splitlines()[1]
        assert first_data.startswith("1990-")

    def test_custom_year(self, tmp_path, pvlib_df):
        out = from_pvlib(pvlib_df, tmp_path / "out.tsv", year=2000)
        first_data = out.read_text().splitlines()[1]
        assert first_data.startswith("2000-")

    def test_output_passes_validation(self, tmp_path, pvlib_df):
        """TSV written by from_pvlib should pass check_sequential_year_timestamps."""
        out = from_pvlib(pvlib_df, tmp_path / "out.tsv")
        check_sequential_year_timestamps(out)  # should not raise
