"""
Unit tests for the CalculationResults class.
Tests data model, properties, and methods.
"""

import pytest

from solarfarmer.models import CalculationResults, ModelChainResponse


class TestCalculationResultsInitialization:
    """Test cases for CalculationResults initialization and field storage."""

    @pytest.fixture
    def results(self):
        """A fully-populated CalculationResults used across init tests."""
        return CalculationResults(
            ModelChainResponse=ModelChainResponse(
                Name="Test Project",
                AnnualEnergyYieldResults=[
                    {
                        "year": 2023,
                        "energyYieldResults": {"netEnergy": 250000, "pac": 150000, "pdc": 160000},
                        "annualEffects": {"soiling": -5000, "temperature": -8000},
                    }
                ],
                SystemAttributes={"dcCapacityW": 10000, "acCapacityW": 10000, "moduleArea": 50},
                TotalModuleArea=50,
            ),
            AnnualData=[
                {
                    "year": 2023,
                    "energyYieldResults": {
                        "netEnergy": 250000,
                        "pac": 150000,
                        "pdc": 160000,
                        "nominalEnergy": 260000,
                    },
                    "annualEffects": {"soiling": -5000, "temperature": -8000, "angular": -3000},
                }
            ],
            MonthlyData=[
                {
                    "monthlyEnergyYieldResults": [
                        {"month": 1, "energyYieldResults": {"netEnergy": 15000, "pac": 10000}},
                        {"month": 2, "energyYieldResults": {"netEnergy": 18000, "pac": 12000}},
                    ]
                }
            ],
            CalculationAttributes={
                "systemAttributes": {"dcCapacityW": 10000, "acCapacityW": 10000, "moduleArea": 50},
                "totalModuleArea": 50,
            },
            Name="Test Project",
        )

    def test_required_fields_are_stored(self, results):
        """All four required constructor fields should be stored on the instance."""
        assert results.ModelChainResponse is not None
        assert results.AnnualData is not None
        assert results.MonthlyData is not None
        assert results.CalculationAttributes is not None

    def test_name_is_stored(self, results):
        """Name should be stored exactly as provided."""
        assert results.Name == "Test Project"

    def test_name_defaults_to_none(self):
        """Name should default to None when not supplied."""
        result = CalculationResults(
            ModelChainResponse=ModelChainResponse(Name=None),
            AnnualData=[],
            MonthlyData=[],
            CalculationAttributes={},
        )
        assert result.Name is None

    @pytest.mark.parametrize(
        "field", ["LossTreeTimeseries", "PVsystTimeseries", "DetailedTimeseries"]
    )
    def test_timeseries_fields_default_to_none(self, results, field):
        """All three optional timeseries fields should default to None."""
        assert getattr(results, field) is None

    def test_annual_data_round_trip(self, results):
        """AnnualData stored in the instance should reflect the input values exactly."""
        assert results.AnnualData[0]["year"] == 2023
        assert results.AnnualData[0]["energyYieldResults"]["netEnergy"] == 250000
        assert results.AnnualData[0]["annualEffects"]["soiling"] == -5000

    def test_calculation_attributes_round_trip(self, results):
        """CalculationAttributes should preserve the nested structure from input."""
        assert results.CalculationAttributes["systemAttributes"]["dcCapacityW"] == 10000
        assert results.CalculationAttributes["totalModuleArea"] == 50


class TestCalculationResultsRoundTrip:
    """Test that to_folder() / from_folder() preserves the core result data."""

    @pytest.fixture
    def sample_results(self):
        """A CalculationResults with no ModelChainResponse (the from_folder path)."""
        return CalculationResults(
            ModelChainResponse=None,
            AnnualData=[
                {
                    "year": 2023,
                    "energyYieldResults": {"netEnergy": 250000, "pac": 150000, "pdc": 160000},
                    "annualEffects": {"soiling": -5000, "temperature": -8000},
                }
            ],
            MonthlyData=[
                {
                    "year": 2023,
                    "monthlyEnergyYieldResults": [
                        {"month": 1, "energyYieldResults": {"netEnergy": 15000}},
                        {"month": 2, "energyYieldResults": {"netEnergy": 18000}},
                    ],
                }
            ],
            CalculationAttributes={
                "systemAttributes": {"dcCapacityW": 10000, "location": {"latitude": 46.9}},
                "totalModuleArea": 50,
            },
        )

    def test_annual_and_monthly_data_survive_round_trip(self, sample_results, tmp_path):
        """AnnualData and MonthlyData written by to_folder() should be read back unchanged by from_folder()."""
        sample_results.to_folder(str(tmp_path))
        reloaded = CalculationResults.from_folder(str(tmp_path))

        assert reloaded.AnnualData == sample_results.AnnualData
        assert reloaded.MonthlyData == sample_results.MonthlyData

    def test_calculation_attributes_survive_round_trip(self, sample_results, tmp_path):
        """CalculationAttributes written by to_folder() should be read back unchanged by from_folder()."""
        sample_results.to_folder(str(tmp_path))
        reloaded = CalculationResults.from_folder(str(tmp_path))

        assert reloaded.CalculationAttributes == sample_results.CalculationAttributes

    def test_modelchain_response_is_none_after_round_trip(self, sample_results, tmp_path):
        """from_folder() cannot reconstruct ModelChainResponse — it should always be None."""
        sample_results.to_folder(str(tmp_path))
        reloaded = CalculationResults.from_folder(str(tmp_path))

        assert reloaded.ModelChainResponse is None

    def test_from_folder_raises_on_missing_folder(self, tmp_path):
        """from_folder() should raise FileNotFoundError when the folder does not exist."""
        missing = tmp_path / "does_not_exist"
        with pytest.raises(FileNotFoundError):
            CalculationResults.from_folder(str(missing))

    def test_from_folder_raises_on_missing_results_file(self, tmp_path):
        """from_folder() should raise FileNotFoundError when the annual results JSON is absent."""
        # folder exists but contains no files
        with pytest.raises(FileNotFoundError):
            CalculationResults.from_folder(str(tmp_path))


class TestCalculationResultsDataAccess:
    """Test that CalculationResults stores input data faithfully and by reference."""

    @pytest.fixture
    def annual_data(self):
        """Reusable annual data dict."""
        return [
            {
                "year": 2023,
                "energyYieldResults": {"netEnergy": 250000, "pac": 150000, "pdc": 160000},
            }
        ]

    @pytest.fixture
    def monthly_data(self):
        """Reusable monthly data dict."""
        return [
            {
                "monthlyEnergyYieldResults": [
                    {"month": 1, "netEnergy": 18000},
                    {"month": 2, "netEnergy": 20000},
                ]
            }
        ]

    @pytest.fixture
    def attributes(self):
        """Reusable calculation attributes dict."""
        return {"systemAttributes": {"dcCapacityW": 10000, "acCapacityW": 10000}}

    @pytest.fixture
    def results(self, annual_data, monthly_data, attributes):
        """CalculationResults constructed from the above fixtures."""
        return CalculationResults(
            ModelChainResponse=ModelChainResponse(Name="Test"),
            AnnualData=annual_data,
            MonthlyData=monthly_data,
            CalculationAttributes=attributes,
        )

    @pytest.mark.parametrize(
        "field, fixture_name",
        [
            ("AnnualData", "annual_data"),
            ("MonthlyData", "monthly_data"),
            ("CalculationAttributes", "attributes"),
        ],
    )
    def test_data_stored_by_identity(
        self, results, annual_data, monthly_data, attributes, field, fixture_name
    ):
        """Data fields should be the exact objects passed in, not copies."""
        mapping = {
            "annual_data": annual_data,
            "monthly_data": monthly_data,
            "attributes": attributes,
        }
        assert getattr(results, field) is mapping[fixture_name]

    def test_modelchain_response_name_preserved(self, results):
        """ModelChainResponse should be stored and its Name accessible."""
        assert isinstance(results.ModelChainResponse, ModelChainResponse)
        assert results.ModelChainResponse.Name == "Test"

    def test_annual_data_values_accessible(self, results):
        """Values nested inside AnnualData should remain accessible after construction."""
        assert results.AnnualData[0]["year"] == 2023
        assert results.AnnualData[0]["energyYieldResults"]["netEnergy"] == 250000

    def test_monthly_data_values_accessible(self, results):
        """Values nested in MonthlyData should remain accessible after construction."""
        monthly_items = results.MonthlyData[0]["monthlyEnergyYieldResults"]
        assert len(monthly_items) == 2
        assert monthly_items[0]["month"] == 1


def _make_annual_year(calendar_year: int, net_energy: float, soiling: float) -> dict:
    """Build a minimal but complete annual data entry."""
    return {
        "year": calendar_year,
        "energyYieldResults": {
            "recordCount": 8760,
            "percentComplete": 100.0,
            "averageTemperature": 12.5,
            "ghi": 1250.0,
            "gi": 1450.0,
            "giWithHorizon": 1440.0,
            "gainOnTiltedPlane": 0.16,
            "globalEffectiveIrradiance": 1380.0,
            "modulePower": 9800.0,
            "modulePowerAtSTC": 10000.0,
            "nominalEnergy": 260000.0,
            "pdc": 255000.0,
            "pac": 245000.0,
            "performanceRatio": 0.82,
            "performanceRatioBifacial": 0.0,
            "netEnergy": net_energy,
            "energyYield": 1200.0,
        },
        "annualEffects": {
            "soiling": soiling,
            "temperature": -8000.0,
            "angular": -3000.0,
        },
    }


def _make_monthly_year(calendar_year: int) -> dict:
    """Build a minimal monthly data entry with 12 months of results and effects."""
    monthly_results = [
        {
            "month": m,
            "energyYieldResults": {
                "netEnergy": 20000.0 + m * 500,
                "pac": 18000.0,
                "pdc": 19000.0,
                "ghi": 100.0,
                "gi": 110.0,
                "giWithHorizon": 109.0,
                "gainOnTiltedPlane": 0.10,
                "globalEffectiveIrradiance": 105.0,
                "averageTemperature": 12.0,
                "energyYield": 100.0,
                "performanceRatio": 0.80,
                "performanceRatioBifacial": 0.0,
            },
            "monthlyEffects": {"soiling": -400.0, "temperature": -600.0},
        }
        for m in range(1, 13)
    ]
    return {
        "year": calendar_year,
        "monthlyEnergyYieldResults": monthly_results,
    }


def _two_year_results(name: str = "TestProject") -> "CalculationResults":
    """Return a CalculationResults with two years of annual and monthly data."""
    annual_data = [
        _make_annual_year(2022, net_energy=240000.0, soiling=-5000.0),
        _make_annual_year(2023, net_energy=245000.0, soiling=-4500.0),
    ]
    monthly_data = [_make_monthly_year(2022), _make_monthly_year(2023)]
    return CalculationResults(
        ModelChainResponse=ModelChainResponse(Name=name),
        AnnualData=annual_data,
        MonthlyData=monthly_data,
        CalculationAttributes={"systemAttributes": {"dcCapacityW": 10000}},
        Name=name,
    )


class TestCalculationResultsRepr:
    """Test cases for CalculationResults.__repr__."""

    @pytest.fixture
    def results(self):
        """Two-year results with a named project for repr tests."""
        return _two_year_results("Solar Farm A")

    def test_repr_contains_year_count(self, results):
        """repr should show the number of years derived from AnnualData."""
        assert "years=2" in repr(results)


class TestGetInfo:
    """Test cases for CalculationResults.get_info."""

    @pytest.fixture
    def results(self):
        """Standard two-year results for get_info tests."""
        return _two_year_results("Solarpark X")

    def test_get_info_returns_dict(self, results):
        """get_info should return a dictionary."""
        assert isinstance(results.get_info(), dict)

    def test_get_info_all_expected_keys_present(self, results):
        """get_info should contain every documented key."""
        expected_keys = {
            "name",
            "has_annual_data",
            "has_monthly_data",
            "has_calculation_attributes",
            "has_loss_tree_timeseries",
            "has_pvsyst_timeseries",
            "has_detailed_timeseries",
        }
        assert expected_keys == set(results.get_info().keys())

    def test_get_info_name(self, results):
        """get_info should reflect the Name attribute."""
        assert results.get_info()["name"] == "Solarpark X"

    def test_get_info_name_none(self):
        """get_info name should be None when Name is not set."""
        results = CalculationResults(
            ModelChainResponse=ModelChainResponse(Name=None),
            AnnualData=[_make_annual_year(2023, 240000.0, -5000.0)],
            MonthlyData=[_make_monthly_year(2023)],
            CalculationAttributes={},
        )
        assert results.get_info()["name"] is None

    @pytest.mark.parametrize(
        "key", ["has_annual_data", "has_monthly_data", "has_calculation_attributes"]
    )
    def test_get_info_data_flags_true_when_present(self, results, key):
        """has_* flags should be True when the corresponding data is supplied."""
        assert results.get_info()[key] is True

    @pytest.mark.parametrize(
        "key", ["has_loss_tree_timeseries", "has_pvsyst_timeseries", "has_detailed_timeseries"]
    )
    def test_get_info_timeseries_flags_false_when_absent(self, results, key):
        """Timeseries flags should be False when not supplied (default)."""
        assert results.get_info()[key] is False


class TestGetPerformance:
    """Test cases for CalculationResults.get_performance."""

    @pytest.fixture
    def results(self):
        """Standard two-year results for get_performance tests."""
        return _two_year_results()

    def test_get_performance_returns_dict(self, results):
        """get_performance should return a dictionary."""
        assert isinstance(results.get_performance(), dict)

    def test_get_performance_expected_keys(self, results):
        """get_performance should contain every documented key."""
        expected_keys = {
            "project_year",
            "calendar_year",
            "average_temperature",
            "horizontal_irradiation",
            "irradiation_on_tilted_plane",
            "effective_irradiation",
            "energy_yield",
            "net_energy",
            "performance_ratio",
            "performance_ratio_bifacial",
        }
        assert expected_keys == set(results.get_performance(project_year=1).keys())

    @pytest.mark.parametrize(
        "project_year, exp_calendar_year, exp_net_energy",
        [
            (1, 2022, 240000.0),
            (2, 2023, 245000.0),
        ],
    )
    def test_get_performance_year_values(
        self, results, project_year, exp_calendar_year, exp_net_energy
    ):
        """get_performance should return correct data for the requested project year."""
        perf = results.get_performance(project_year=project_year)
        assert perf["project_year"] == project_year
        assert perf["calendar_year"] == exp_calendar_year
        assert perf["net_energy"] == exp_net_energy

    def test_get_performance_out_of_range_returns_empty(self, results):
        """An out-of-range project_year should return an empty dict."""
        assert results.get_performance(project_year=99) == {}
        assert results.get_performance(project_year=0) == {}
        assert results.get_performance(project_year=-1) == {}

    def test_get_performance_no_data_returns_empty(self):
        """get_performance should return an empty dict when AnnualData is empty."""
        results = CalculationResults(
            ModelChainResponse=ModelChainResponse(Name="Empty"),
            AnnualData=[],
            MonthlyData=[],
            CalculationAttributes={},
        )
        assert results.get_performance() == {}


class TestGetAnnualResultsTable:
    """Test cases for CalculationResults.get_annual_results_table."""

    @pytest.fixture
    def results(self):
        """Standard two-year results for annual table tests."""
        return _two_year_results()

    def test_returns_dict_with_both_keys_by_default(self, results):
        """Default call should return both 'energy_results' and 'effects' keys."""
        data = results.get_annual_results_table()
        assert "energy_results" in data
        assert "effects" in data

    @pytest.mark.parametrize("key", ["energy_results", "effects"])
    def test_row_count_per_key(self, results, key):
        """Both output keys should have one row per year."""
        data = results.get_annual_results_table()
        assert len(data[key]) == 2

    @pytest.mark.parametrize(
        "kwargs, present_key, absent_key",
        [
            ({"include_effects": False}, "energy_results", "effects"),
            ({"include_energy_results": False}, "effects", "energy_results"),
        ],
    )
    def test_single_include_flag(self, results, kwargs, present_key, absent_key):
        """Setting one flag to False should omit only that key from the output."""
        data = results.get_annual_results_table(**kwargs)
        assert present_key in data
        assert absent_key not in data

    def test_both_false_returns_empty(self, results):
        """Setting both flags to False should return an empty dict."""
        data = results.get_annual_results_table(include_energy_results=False, include_effects=False)
        assert data == {}

    def test_no_annual_data_returns_empty(self):
        """get_annual_results_table should return {} when AnnualData is empty."""
        results = CalculationResults(
            ModelChainResponse=ModelChainResponse(Name="Empty"),
            AnnualData=[],
            MonthlyData=[],
            CalculationAttributes={},
        )
        assert results.get_annual_results_table() == {}

    def test_energy_results_field_values(self, results):
        """Energy results rows should carry correct calendar year and net_energy."""
        row1, row2 = results.get_annual_results_table()["energy_results"]
        assert row1["calendar_year"] == 2022
        assert row1["net_energy"] == 240000.0
        assert row2["calendar_year"] == 2023
        assert row2["net_energy"] == 245000.0

    def test_effects_field_values(self, results):
        """Effects rows should carry correct soiling values."""
        row1, row2 = results.get_annual_results_table()["effects"]
        assert row1["soiling"] == -5000.0
        assert row2["soiling"] == -4500.0

    @pytest.mark.parametrize(
        "project_years, exp_calendar_year",
        [
            ([2], 2023),  # 1-based project year index
            ([2022], 2022),  # calendar year
        ],
    )
    def test_filter_single_year(self, results, project_years, exp_calendar_year):
        """Filtering by a single year (index or calendar) should return one row."""
        data = results.get_annual_results_table(project_years=project_years)
        assert len(data["energy_results"]) == 1
        assert data["energy_results"][0]["calendar_year"] == exp_calendar_year

    @pytest.mark.parametrize(
        "project_years",
        [
            [1999],  # calendar year not in dataset
            [50],  # project year index out of range
        ],
    )
    def test_invalid_year_filter_falls_back_to_all(self, results, project_years):
        """An unresolvable year filter should fall back to the full dataset."""
        data = results.get_annual_results_table(project_years=project_years)
        assert len(data["energy_results"]) == 2

    def test_energy_result_rows_have_project_year_field(self, results):
        """Each energy result row should include a sequential project_year field."""
        data = results.get_annual_results_table()
        for i, row in enumerate(data["energy_results"], start=1):
            assert row["project_year"] == i


class TestGetMonthlyResultsTable:
    """Test cases for CalculationResults.get_monthly_results_table."""

    @pytest.fixture
    def results(self):
        """Standard two-year results for monthly table tests."""
        return _two_year_results()

    def test_returns_dict_with_both_keys_by_default(self, results):
        """Default call should return both 'energy_results' and 'effects' keys."""
        data = results.get_monthly_results_table()
        assert "energy_results" in data
        assert "effects" in data

    @pytest.mark.parametrize("key", ["energy_results", "effects"])
    def test_row_count_two_years(self, results, key):
        """Both output keys should contain 12 rows per year (24 total)."""
        data = results.get_monthly_results_table()
        assert len(data[key]) == 24

    @pytest.mark.parametrize(
        "kwargs, present_key, absent_key",
        [
            ({"include_effects": False}, "energy_results", "effects"),
            ({"include_energy_results": False}, "effects", "energy_results"),
        ],
    )
    def test_single_include_flag(self, results, kwargs, present_key, absent_key):
        """Setting one flag to False should omit only that key from the output."""
        data = results.get_monthly_results_table(**kwargs)
        assert present_key in data
        assert absent_key not in data

    def test_both_false_returns_empty(self, results):
        """Setting both flags to False should return an empty dict."""
        data = results.get_monthly_results_table(
            include_energy_results=False, include_effects=False
        )
        assert data == {}

    def test_no_monthly_data_returns_empty(self):
        """get_monthly_results_table should return {} when MonthlyData is empty."""
        results = CalculationResults(
            ModelChainResponse=ModelChainResponse(Name="Empty"),
            AnnualData=[],
            MonthlyData=[],
            CalculationAttributes={},
        )
        assert results.get_monthly_results_table() == {}

    @pytest.mark.parametrize(
        "project_years, exp_calendar_year",
        [
            ([1], 2022),  # 1-based project year index
            ([2023], 2023),  # calendar year
        ],
    )
    def test_filter_single_year(self, results, project_years, exp_calendar_year):
        """Filtering to a single year should return 12 rows for that year only."""
        data = results.get_monthly_results_table(project_years=project_years)
        assert len(data["energy_results"]) == 12
        assert all(row["calendar_year"] == exp_calendar_year for row in data["energy_results"])

    def test_month_names_present(self, results):
        """Each row should carry a non-empty month_name, Jan through Dec."""
        data = results.get_monthly_results_table(project_years=[1])
        month_names = [row["month_name"] for row in data["energy_results"]]
        assert all(name != "" for name in month_names)
        assert month_names[0] == "Jan"
        assert month_names[11] == "Dec"

    def test_energy_rows_have_project_year_field(self, results):
        """Both project years should be represented in the project_year field."""
        data = results.get_monthly_results_table()
        project_years_seen = {row["project_year"] for row in data["energy_results"]}
        assert project_years_seen == {1, 2}


class TestResolveYearIndices:
    """Test cases for CalculationResults._resolve_year_indices (all four branches)."""

    @pytest.fixture
    def results(self):
        """Two-year CalculationResults used as host for _resolve_year_indices."""
        return _two_year_results()

    @pytest.fixture
    def data(self):
        """Minimal data list matching the two years used in the fixture."""
        return [{"year": 2022}, {"year": 2023}]

    def test_none_returns_all_indices(self, results, data):
        """None project_years should return indices for every year in data."""
        assert results._resolve_year_indices(data, None) == [0, 1]

    @pytest.mark.parametrize(
        "project_years, expected",
        [
            ([1, 2], [0, 1]),
            ([2], [1]),
        ],
    )
    def test_project_year_to_index(self, results, data, project_years, expected):
        """1-based project year integers should map to 0-based indices."""
        assert results._resolve_year_indices(data, project_years) == expected

    @pytest.mark.parametrize(
        "project_years, expected",
        [
            ([2022, 2023], [0, 1]),
            ([2023], [1]),
        ],
    )
    def test_calendar_year_to_index(self, results, data, project_years, expected):
        """Calendar years should resolve to their correct 0-based indices."""
        assert results._resolve_year_indices(data, project_years) == expected

    @pytest.mark.parametrize(
        "project_years",
        [
            [1999],  # calendar year absent from data
            [99],  # project year index beyond dataset length
        ],
    )
    def test_invalid_input_falls_back_to_all(self, results, data, project_years):
        """Unresolvable years should fall back to all indices with a warning."""
        assert results._resolve_year_indices(data, project_years) == [0, 1]

    def test_partial_calendar_years_only_valid_returned(self, results, data):
        """Mixed valid/invalid calendar years should return only the valid index."""
        assert results._resolve_year_indices(data, [2022, 1999]) == [0]


class TestAccessors:
    """Test cases for the simple accessor methods."""

    @pytest.fixture
    def results(self):
        """Standard two-year results for accessor tests."""
        return _two_year_results()

    def test_calculation_attributes_returns_dict(self, results):
        """calculation_attributes() should return the CalculationAttributes dict."""
        attrs = results.calculation_attributes()
        assert attrs is results.CalculationAttributes
        assert isinstance(attrs, dict)

    @pytest.mark.parametrize(
        "method", ["loss_tree_timeseries", "pvsyst_timeseries", "detailed_timeseries"]
    )
    def test_timeseries_accessors_return_none_by_default(self, results, method):
        """Timeseries accessors should return None when no timeseries data is set."""
        assert getattr(results, method)() is None


class TestPrintMethods:
    """Test cases for methods that write to stdout."""

    @pytest.fixture
    def results(self):
        """Standard two-year results for print method tests."""
        return _two_year_results("PrintTest")

    def test_info_prints_name(self, results, capsys):
        """info() should print the project name."""
        results.info()
        assert "PrintTest" in capsys.readouterr().out

    def test_info_prints_all_flags(self, results, capsys):
        """info() should mention all data availability flags."""
        results.info()
        out = capsys.readouterr().out
        assert "Annual data" in out
        assert "Monthly data" in out
        assert "Loss tree timeseries" in out

    def test_performance_prints_output(self, results, capsys):
        """performance() should produce non-empty output for a valid year."""
        results.performance(project_year=1)
        assert capsys.readouterr().out.strip() != ""

    def test_performance_contains_net_energy_label(self, results, capsys):
        """performance() output should include the 'Net energy' label."""
        results.performance(project_year=1)
        assert "Net energy" in capsys.readouterr().out

    def test_print_annual_results_produces_output(self, results, capsys):
        """print_annual_results() should produce non-empty stdout."""
        results.print_annual_results()
        assert capsys.readouterr().out.strip() != ""

    def test_print_annual_results_energy_only(self, results, capsys):
        """print_annual_results(show_effects=False) should not raise."""
        results.print_annual_results(show_effects=False)
        assert capsys.readouterr().out.strip() != ""

    def test_print_annual_results_effects_only(self, results, capsys):
        """print_annual_results(show_energy_results=False) should not raise."""
        results.print_annual_results(show_energy_results=False)
        assert capsys.readouterr().out.strip() != ""

    def test_print_monthly_results_produces_output(self, results, capsys):
        """print_monthly_results() should produce non-empty stdout."""
        results.print_monthly_results()
        assert capsys.readouterr().out.strip() != ""

    def test_print_monthly_results_single_year(self, results, capsys):
        """print_monthly_results(project_years=[1]) should not raise."""
        results.print_monthly_results(project_years=[1])
        assert capsys.readouterr().out.strip() != ""


class TestConvenienceProperties:
    """Test cases for convenience properties on CalculationResults."""

    @pytest.fixture
    def results(self):
        return _two_year_results()

    def test_net_energy_MWh(self, results):
        """net_energy_MWh should return year-1 net energy."""
        assert results.net_energy_MWh == results.get_performance()["net_energy"]

    def test_performance_ratio(self, results):
        """performance_ratio should return year-1 PR."""
        assert results.performance_ratio == results.get_performance()["performance_ratio"]

    def test_performance_ratio_bifacial(self, results):
        """performance_ratio_bifacial should return year-1 bifacial PR."""
        assert (
            results.performance_ratio_bifacial
            == results.get_performance()["performance_ratio_bifacial"]
        )

    def test_energy_yield_kWh_per_kWp(self, results):
        """energy_yield_kWh_per_kWp should return year-1 specific yield."""
        assert results.energy_yield_kWh_per_kWp == results.get_performance()["energy_yield"]

    def test_empty_results_return_nan(self):
        """Convenience properties should return NaN when no data is available."""
        import math

        results = CalculationResults(
            ModelChainResponse=ModelChainResponse(Name=None),
            AnnualData=[],
            MonthlyData=[],
            CalculationAttributes={},
        )
        assert math.isnan(results.net_energy_MWh)
        assert math.isnan(results.performance_ratio)
        assert math.isnan(results.performance_ratio_bifacial)
        assert math.isnan(results.energy_yield_kWh_per_kWp)


class TestPerformancePrinting:
    """Test conditional bifacial PR row in performance()."""

    def _make_results(self, pr: float, pr_bifacial: float) -> CalculationResults:
        """Build a minimal CalculationResults with the given PR values."""
        annual_data = [
            {
                "year": 2023,
                "energyYieldResults": {
                    "averageTemperature": 12.0,
                    "ghi": 1200.0,
                    "gi": 1400.0,
                    "globalEffectiveIrradiance": 1350.0,
                    "energyYield": 1100.0,
                    "netEnergy": 200000.0,
                    "performanceRatio": pr,
                    "performanceRatioBifacial": pr_bifacial,
                },
                "annualEffects": {},
            }
        ]
        return CalculationResults(
            ModelChainResponse=ModelChainResponse(Name="test"),
            AnnualData=annual_data,
            MonthlyData=[],
            CalculationAttributes=None,
        )

    def test_bifacial_row_shown_when_pr_differs(self, capsys):
        """Bifacial PR row must appear when it differs from standard PR."""
        results = self._make_results(pr=0.82, pr_bifacial=0.85)
        results.performance()
        captured = capsys.readouterr().out
        assert "Performance Ratio (bifacial)" in captured
        assert "0.8500" in captured

    def test_bifacial_row_suppressed_for_monofacial(self, capsys):
        """Bifacial PR row must not appear when both PR values are equal (monofacial)."""
        results = self._make_results(pr=0.82, pr_bifacial=0.82)
        results.performance()
        captured = capsys.readouterr().out
        assert "Performance Ratio (bifacial)" not in captured

    def test_bifacial_row_suppressed_for_near_equal_values(self, capsys):
        """Floating-point near-equal values must not produce a spurious bifacial row."""
        results = self._make_results(pr=0.82, pr_bifacial=0.82 + 1e-12)
        results.performance()
        captured = capsys.readouterr().out
        assert "Performance Ratio (bifacial)" not in captured
