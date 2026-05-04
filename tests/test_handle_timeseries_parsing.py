import warnings

import pandas as pd

from solarfarmer.models.energy_calculation_results import (
    _handle_losstree_results,
    _handle_pvsyst_results,
    _handle_timeseries_results,
)
from solarfarmer.models.model_chain_response import ModelChainResponse

# --- Synthetic data matching SF-Core output formats ---

# PVsyst CSV: 10 header rows skipped (indices 0-9), column row, units row
# (index 11 skipped), blank row (index 12 skipped), then data.
# Separator: semicolon. Date format: dd/MM/yy HH:mm
PVSYST_CSV = (
    "SF-Core 0.4.443\n"
    "\n"
    "\n"
    "\n"
    "\n"
    "\n"
    "Simulation date;;30/04/26 14h00\n"
    "\n"
    "\n"
    "\n"
    "date;GlobHor;T_Amb;WindVel\n"
    "-;kWh/m2;deg. C;m/s\n"
    "\n"
    "01/06/24 06:00;0.15;18.3;2.1\n"
    "15/06/24 12:00;0.85;25.1;3.0\n"
    "01/01/24 00:00;0.0;-2.5;5.4\n"
    "31/12/24 23:00;0.0;5.2;4.1\n"
)

# Loss tree TSV: 2 header rows (descriptive + blank), then column headers,
# then data. Separator: tab. Date format: yyyy-MM-ddTHH:mm:sszzz (ISO 8601)
LOSSTREE_TSV = (
    "Loss tree results for each time-step. Each value is an energy in kWh"
    " for a certain step in the calculation\n"
    "\n"
    "Start of period\tGHI\tGlobalEffective\tNetEnergy\n"
    "2024-06-01T06:00:00+00:00\t0.150\t0.120\t0.100\n"
    "2024-06-01T07:00:00+00:00\t0.450\t0.400\t0.380\n"
    "2024-06-01T08:00:00+00:00\t0.720\t0.680\t0.650\n"
)

# Detailed TSV: single header row then data rows. Separator: tab.
# First columns are StartOfPeriod and PeriodInMinutes.
DETAILED_TSV = (
    "StartOfPeriod\tPeriodInMinutes\tGHI\tDHI\tTAmb\n"
    "2024-06-01T06:00:00+00:00\t60\t150\t80\t18.3\n"
    "2024-06-01T07:00:00+00:00\t60\t450\t200\t19.1\n"
    "2024-06-01T08:00:00+00:00\t60\t720\t300\t20.5\n"
)


class TestHandlePvsystResults:
    """Tests for _handle_pvsyst_results with PVsyst-format CSV data."""

    def test_parses_pvsyst_csv_to_dataframe(self, tmp_path):
        """Parsing a valid PVsyst CSV returns a DataFrame with expected shape and columns."""
        response = ModelChainResponse(PvSystFormatResultsFile=PVSYST_CSV)
        df = _handle_pvsyst_results(response, tmp_path, save_outputs=False)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 4
        assert list(df.columns) == ["GlobHor", "T_Amb", "WindVel"]

    def test_dates_parsed_day_first(self, tmp_path):
        """Date column uses dd/MM/yy format; 01/06 must be June 1st, not Jan 6th."""
        response = ModelChainResponse(PvSystFormatResultsFile=PVSYST_CSV)
        df = _handle_pvsyst_results(response, tmp_path, save_outputs=False)

        # 01/06/24 must parse as June 1st, not January 6th
        assert pd.Timestamp("2024-06-01 06:00:00") in df.index
        # 31/12/24 would blow up with month=31 if parsed month-first
        assert pd.Timestamp("2024-12-31 23:00:00") in df.index

    def test_sort_preserves_data_alignment(self, tmp_path):
        """Sorting the index must keep data rows aligned with their timestamps."""
        response = ModelChainResponse(PvSystFormatResultsFile=PVSYST_CSV)
        df = _handle_pvsyst_results(response, tmp_path, save_outputs=False)

        # Input row "01/01/24 00:00" has GlobHor=0.0 and T_Amb=-2.5
        jan_row = df.loc[pd.Timestamp("2024-01-01 00:00:00")]
        assert jan_row["GlobHor"] == 0.0
        assert jan_row["T_Amb"] == -2.5

    def test_index_is_timezone_naive(self, tmp_path):
        """Index must be tz-naive: the SF API returns site-local time."""
        response = ModelChainResponse(PvSystFormatResultsFile=PVSYST_CSV)
        df = _handle_pvsyst_results(response, tmp_path, save_outputs=False)

        assert df.index.tz is None

    def test_no_warning_emitted(self, tmp_path):
        """Parsing must not emit UserWarning about dateutil fallback (SM-326)."""
        response = ModelChainResponse(PvSystFormatResultsFile=PVSYST_CSV)
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            _handle_pvsyst_results(response, tmp_path, save_outputs=False)

    def test_saves_file_when_requested(self, tmp_path):
        """With save_outputs=True, the raw CSV is written to disk."""
        response = ModelChainResponse(PvSystFormatResultsFile=PVSYST_CSV)
        _handle_pvsyst_results(response, tmp_path, save_outputs=True)

        saved = list(tmp_path.glob("*"))
        assert len(saved) == 1
        assert saved[0].name == "PVsystResults.csv"


class TestHandleLosstreeResults:
    """Tests for _handle_losstree_results with loss-tree TSV data."""

    def test_parses_losstree_tsv_to_dataframe(self, tmp_path):
        """Parsing a valid loss-tree TSV returns a DataFrame with expected shape."""
        response = ModelChainResponse(LossTreeResults=LOSSTREE_TSV)
        df = _handle_losstree_results(response, tmp_path, save_outputs=False)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["GHI", "GlobalEffective", "NetEnergy"]
        assert df.index.name == "Start of period"

    def test_iso_dates_parsed_correctly(self, tmp_path):
        """ISO 8601 timestamps are parsed to correct datetime values."""
        response = ModelChainResponse(LossTreeResults=LOSSTREE_TSV)
        df = _handle_losstree_results(response, tmp_path, save_outputs=False)

        assert df.index[0] == pd.Timestamp("2024-06-01 06:00:00", tz="UTC")

    def test_sort_preserves_data_alignment(self, tmp_path):
        """Sorting the index must keep data rows aligned with their timestamps."""
        response = ModelChainResponse(LossTreeResults=LOSSTREE_TSV)
        df = _handle_losstree_results(response, tmp_path, save_outputs=False)

        # First row in sorted output should have GHI=0.150
        assert df.iloc[0]["GHI"] == 0.150
        assert df.index[0] == pd.Timestamp("2024-06-01 06:00:00", tz="UTC")


class TestHandleTimeseriesResults:
    """Tests for _handle_timeseries_results (detailed format) with TSV data."""

    def test_parses_detailed_tsv_to_dataframe(self, tmp_path):
        """Parsing a valid detailed TSV returns a DataFrame with expected columns."""
        response = ModelChainResponse(ResultsFile=DETAILED_TSV)
        df = _handle_timeseries_results(response, tmp_path, save_outputs=False)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["StartOfPeriod", "PeriodInMinutes", "GHI", "DHI", "TAmb"]
