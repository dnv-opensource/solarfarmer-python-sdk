"""Tests for weather module: TSV validation and DataFrame conversion utilities."""

import textwrap
from pathlib import Path

import pytest

from solarfarmer.weather import (
    PVLIB_COLUMN_MAP,
    SOLCAST_COLUMN_MAP,
    SRC_COLUMN_MAP,
    check_sequential_year_timestamps,
    from_dataframe,
    from_pvlib,
    from_solcast,
    from_src,
    shift_period_end_to_beginning,
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


class TestFromSolcast:
    """Tests for from_solcast() convenience wrapper."""

    @pytest.fixture
    def solcast_df(self):
        pd = pytest.importorskip("pandas")
        idx = pd.date_range("1990-01-01 00:30", periods=3, freq="30min", tz="UTC")
        return pd.DataFrame(
            {
                "ghi": [0, 500, 800],
                "dhi": [0, 200, 300],
                "air_temp": [5.0, 15.0, 25.0],
                "wind_speed_10m": [2.0, 3.0, 4.0],
                "surface_pressure": [1013.25, 1013.25, 1013.25],
                "precipitable_water": [1.0, 2.0, 3.0],
            },
            index=idx,
        )

    def test_columns_renamed(self, tmp_path, solcast_df):
        out = from_solcast(solcast_df, tmp_path / "out.tsv")
        header = out.read_text().splitlines()[0]
        # Only columns present in the fixture are mapped
        for solcast_col, sf_col in SOLCAST_COLUMN_MAP.items():
            if solcast_col in solcast_df.columns:
                assert sf_col in header

    def test_pressure_not_converted(self, tmp_path, solcast_df):
        """surface_pressure is hPa = mbar; no conversion should be applied."""
        out = from_solcast(solcast_df, tmp_path / "out.tsv")
        lines = out.read_text().splitlines()
        header = lines[0].split("\t")
        pressure_idx = header.index("Pressure")
        first_data = lines[1].split("\t")
        assert float(first_data[pressure_idx]) == pytest.approx(1013.25)

    def test_precipitable_water_converted(self, tmp_path, solcast_df):
        """precipitable_water is kg/m² (= mm), must be divided by 10 to get cm."""
        out = from_solcast(solcast_df, tmp_path / "out.tsv")
        lines = out.read_text().splitlines()
        header = lines[0].split("\t")
        water_idx = header.index("Water")
        first_data = lines[1].split("\t")
        assert float(first_data[water_idx]) == pytest.approx(0.1)  # 1.0 / 10

    def test_timestamp_shifted_to_period_beginning(self, tmp_path, solcast_df):
        """Solcast period_end timestamps must be shifted back by the time resolution."""
        out = from_solcast(solcast_df, tmp_path / "out.tsv")
        first_data = out.read_text().splitlines()[1]
        # Original index starts at 00:30; shifted by -30 min → 00:00
        assert "T00:00" in first_data

    def test_unknown_columns_dropped(self, tmp_path):
        """Columns not in SOLCAST_COLUMN_MAP (e.g. gti) are dropped."""
        pd = pytest.importorskip("pandas")
        idx = pd.date_range("1990-01-01 01:00", periods=2, freq="h", tz="UTC")
        df = pd.DataFrame(
            {"ghi": [0, 500], "air_temp": [5.0, 15.0], "gti": [100.0, 200.0]},
            index=idx,
        )
        out = from_solcast(df, tmp_path / "out.tsv")
        header = out.read_text().splitlines()[0]
        assert "gti" not in header

    def test_no_datetimeindex_raises(self, tmp_path):
        pd = pytest.importorskip("pandas")
        df = pd.DataFrame({"ghi": [0, 100], "air_temp": [5.0, 15.0]})
        with pytest.raises(ValueError, match="DatetimeIndex"):
            from_solcast(df, tmp_path / "out.tsv")

    def test_output_passes_validation(self, tmp_path, solcast_df):
        """TSV written by from_solcast should pass check_sequential_year_timestamps."""
        out = from_solcast(solcast_df, tmp_path / "out.tsv")
        check_sequential_year_timestamps(out)  # should not raise

    @pytest.mark.parametrize(
        "soiling_col", ["hsu_loss_fraction", "kimber_loss_fraction", "soiling"]
    )
    def test_soiling_columns_mapped(self, tmp_path, soiling_col):
        """hsu_loss_fraction, kimber_loss_fraction, and soiling all map to Soiling."""
        pd = pytest.importorskip("pandas")
        idx = pd.date_range("1990-01-01 00:30", periods=3, freq="30min", tz="UTC")
        df = pd.DataFrame(
            {"ghi": [0, 500, 800], "air_temp": [5.0, 15.0, 25.0], soiling_col: [0.01, 0.02, 0.03]},
            index=idx,
        )
        out = from_solcast(df, tmp_path / "out.tsv")
        header = out.read_text().splitlines()[0].split("\t")
        assert "Soiling" in header
        soiling_idx = header.index("Soiling")
        first_data = out.read_text().splitlines()[1].split("\t")
        assert float(first_data[soiling_idx]) == pytest.approx(0.01)


class TestFromSrc:
    """Tests for from_src() convenience wrapper (DNV Solar Resource Compass)."""

    @pytest.fixture
    def src_records(self):
        """Hourly period_end records matching the SRC weather_hourly format."""
        return [
            {
                "Timestamp": "1990-01-01 01:00:00+00:00",
                "GHI": 0,
                "DHI": 0,
                "Tamb": -9.5,
                "Wspd": 3.3,
            },
            {
                "Timestamp": "1990-01-01 02:00:00+00:00",
                "GHI": 0,
                "DHI": 0,
                "Tamb": -9.9,
                "Wspd": 3.0,
            },
            {
                "Timestamp": "1990-01-01 03:00:00+00:00",
                "GHI": 50,
                "DHI": 20,
                "Tamb": -9.4,
                "Wspd": 2.5,
            },
        ]

    def test_columns_renamed(self, tmp_path, src_records):
        """SRC columns must be mapped to SolarFarmer TSV column names."""
        pytest.importorskip("pandas")
        out = from_src(src_records, tmp_path / "out.tsv")
        header = out.read_text().splitlines()[0]
        for sf_col in SRC_COLUMN_MAP.values():
            assert sf_col in header

    def test_timestamp_shifted_to_period_beginning(self, tmp_path, src_records):
        """SRC period_end timestamps must be shifted back by the time resolution (1 h)."""
        pytest.importorskip("pandas")
        out = from_src(src_records, tmp_path / "out.tsv")
        first_data = out.read_text().splitlines()[1]
        # Original first record is 01:00; shifted by -1 h → 00:00
        assert "T00:00" in first_data

    def test_year_remap(self, tmp_path, src_records):
        """year parameter remaps all timestamps to the given calendar year."""
        pytest.importorskip("pandas")
        out = from_src(src_records, tmp_path / "out.tsv", year=1990)
        first_data = out.read_text().splitlines()[1]
        assert first_data.startswith("1990-")

    def test_empty_list_raises(self, tmp_path):
        """Empty weather_hourly list must raise ValueError."""
        pytest.importorskip("pandas")
        with pytest.raises(ValueError, match="empty"):
            from_src([], tmp_path / "out.tsv")

    def test_missing_timestamp_key_raises(self, tmp_path):
        """Records without a Timestamp key must raise ValueError."""
        pytest.importorskip("pandas")
        records = [{"GHI": 0, "DHI": 0, "Tamb": 5.0, "Wspd": 2.0}]
        with pytest.raises(ValueError, match="Timestamp"):
            from_src(records, tmp_path / "out.tsv")

    def test_output_passes_validation(self, tmp_path, src_records):
        """TSV written by from_src should pass check_sequential_year_timestamps."""
        pytest.importorskip("pandas")
        out = from_src(src_records, tmp_path / "out.tsv", year=1990)
        check_sequential_year_timestamps(out)  # should not raise


class TestShiftPeriodEndToBeginning:
    """Tests for shift_period_end_to_beginning()."""

    def test_shifts_timestamps_by_time_resolution(self):
        """Timestamps should be shifted back by the inferred time resolution."""
        pd = pytest.importorskip("pandas")
        # Create 30-minute resolution data starting at 00:30
        idx = pd.date_range("1990-01-01 00:30", periods=3, freq="30min", tz="UTC")
        df = pd.DataFrame({"ghi": [0, 100, 200]}, index=idx)

        result = shift_period_end_to_beginning(df)

        # Result should be shifted back by 30 minutes
        expected_idx = pd.date_range("1990-01-01 00:00", periods=3, freq="30min", tz="UTC")
        pd.testing.assert_index_equal(result.index, expected_idx)
        # Data values should be unchanged (indices differ, so compare values only)
        assert list(result["ghi"].values) == list(df["ghi"].values)

    def test_no_datetimeindex_raises(self):
        """Should raise ValueError when DataFrame has no DatetimeIndex."""
        pd = pytest.importorskip("pandas")
        df = pd.DataFrame({"ghi": [0, 100, 200]})

        with pytest.raises(ValueError, match="DatetimeIndex"):
            shift_period_end_to_beginning(df)
