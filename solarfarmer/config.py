import os

__all__ = [
    "BASE_API_URL",
    "SF_PORTAL_URL",
    "ABOUT_ENDPOINT_URL",
    "SERVICE_ENDPOINT_URL",
    "MODELCHAIN_ENDPOINT_URL",
    "MODELCHAIN_ASYNC_ENDPOINT_URL",
    "TERMINATE_ASYNC_ENDPOINT_URL",
    "API_TOKEN",
    "ANNUAL_MONTHLY_RESULTS_FILENAME",
    "CALCULATION_ATTRIBUTES_FILENAME",
    "LOSS_TREE_TIMESERIES_FILENAME",
    "LOSS_TREE_TIMESERIES_DATAFRAME_FILENAME",
    "PVSYST_TIMESERIES_FILENAME",
    "PVSYST_TIMESERIES_DATAFRAME_FILENAME",
    "DETAILED_TIMESERIES_FILENAME",
    "GENERAL_TIMEOUT",
    "MODELCHAIN_TIMEOUT",
    "MODELCHAIN_ASYNC_TIMEOUT_CONNECTION",
    "MODELCHAIN_ASYNC_TIMEOUT_UPLOAD",
    "MODELCHAIN_ASYNC_POLL_TIME",
    "PANDAS_INSTALL_MSG",
    # RCL
    "RCL_BASE_URL",
    "RCL_CATALOG_URL",
    "RCL_MODULES_URL",
    "RCL_INVERTERS_URL",
    "RCL_TIMEOUT",
    "RCL_RATE_LIMIT_WARNING_THRESHOLD",
]

BASE_API_URL = os.getenv(
    "SF_API_URL", "https://solarfarmer.dnv.com/latest/api"
)  # Used for API calls using 'latest' version only
SF_PORTAL_URL = "https://solarfarmer.dnv.com"  # Used for API calls using version numbers
ABOUT_ENDPOINT_URL = "About"
SERVICE_ENDPOINT_URL = "Service"
MODELCHAIN_ENDPOINT_URL = "ModelChain"
MODELCHAIN_ASYNC_ENDPOINT_URL = "ModelChainAsync"
TERMINATE_ASYNC_ENDPOINT_URL = "TerminateModelChainAsync"
API_TOKEN = os.getenv("SF_API_KEY")

ANNUAL_MONTHLY_RESULTS_FILENAME = "Annual and Monthly Results.json"
CALCULATION_ATTRIBUTES_FILENAME = "CalculationAttributes.json"
LOSS_TREE_TIMESERIES_FILENAME = "LossTreeResults.tsv"
LOSS_TREE_TIMESERIES_DATAFRAME_FILENAME = "LossTreeResults_frame.tsv"
PVSYST_TIMESERIES_FILENAME = "PVsystResults.csv"
PVSYST_TIMESERIES_DATAFRAME_FILENAME = "PVsystResults_frame.csv"
DETAILED_TIMESERIES_FILENAME = "DetailedTimeseries.tsv"

# Default times (in seconds)
GENERAL_TIMEOUT = 15  # Used in About, Service endpoints
MODELCHAIN_TIMEOUT = 600  # 10 mins
MODELCHAIN_ASYNC_TIMEOUT_CONNECTION = 7200  # 2 hours
MODELCHAIN_ASYNC_TIMEOUT_UPLOAD = 60
MODELCHAIN_ASYNC_POLL_TIME = 4  # Polling frequency for the status of ModelChainAsync calculations

PANDAS_INSTALL_MSG = (
    "pandas is required for this function. Install it with: pip install 'dnv-solarfarmer[weather]'"
)

# RCL (Renewable Component Library) configuration
RCL_BASE_URL = "https://solarfarmer.dnv.com/rcl"
RCL_CATALOG_URL = f"{RCL_BASE_URL}/catalog"
RCL_MODULES_URL = f"{RCL_CATALOG_URL}/modules"
RCL_INVERTERS_URL = f"{RCL_CATALOG_URL}/inverters"
RCL_TIMEOUT = 30  # seconds
RCL_RATE_LIMIT_WARNING_THRESHOLD = 0.20  # Warn when < 20% remaining
