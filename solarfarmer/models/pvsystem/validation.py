# Some common validation messages
ERRORS = {
    "required": "{} is required",
    "min_length": "{} must be at least {} characters.",
    "invalid_value": "{} has an invalid value.",
    "out_of_range": "{} is {}. It must be between {} and {}.",
}


class ValidationMessage:
    """
    Represents a validation message for a specific field, including the message and its severity level.
    Attributes    ----------
    field : str
        The name of the field that the validation message pertains to.
    message : str
        The validation message describing the issue with the field.
    severity : str
        The severity level of the validation message (e.g., "error", "warning", "info"). Default is "error".
    """

    def __init__(self, field, message, severity="error"):
        self.field = field
        self.message = message
        self.severity = severity

    def __repr__(self):
        """Return a string representation of the ValidationMessage instance."""
        return f"{self.severity.upper()}: {self.field}: {self.message}"
