import logging
import os

import pytest

from solarfarmer.logging import configure_logging, get_logger


@pytest.fixture(autouse=True)
def _reset_solarfarmer_logger():
    """Restore the solarfarmer logger to its pristine state after each test."""
    sf_logger = logging.getLogger("solarfarmer")
    original_level = sf_logger.level
    original_handlers = list(sf_logger.handlers)
    yield
    sf_logger.setLevel(original_level)
    sf_logger.handlers = original_handlers


class TestConfigureLogging:
    def test_returns_logger_instance(self):
        result = configure_logging()
        assert isinstance(result, logging.Logger)

    def test_default_level_is_info(self):
        logger = configure_logging()
        assert logger.level == logging.INFO

    def test_verbose_sets_debug_level(self):
        logger = configure_logging(verbose=True)
        assert logger.level == logging.DEBUG

    def test_explicit_level_respected(self):
        logger = configure_logging(level="WARNING")
        assert logger.level == logging.WARNING

    def test_stream_handler_added(self):
        logger = configure_logging()
        stream_handlers = [
            h
            for h in logger.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.NullHandler)
        ]
        assert len(stream_handlers) >= 1

    def test_calling_twice_does_not_stack_handlers(self):
        configure_logging(level="INFO")
        configure_logging(level="INFO")
        sf_logger = logging.getLogger("solarfarmer")
        real_handlers = [h for h in sf_logger.handlers if not isinstance(h, logging.NullHandler)]
        assert len(real_handlers) == 1

    def test_custom_handler_is_added(self):
        custom_handler = logging.FileHandler(os.devnull)
        try:
            logger = configure_logging(handler=custom_handler)
            assert custom_handler in logger.handlers
        finally:
            custom_handler.close()


class TestGetLogger:
    def test_returns_child_of_solarfarmer(self):
        child = get_logger("mymodule")
        assert child.name == "solarfarmer.mymodule"

    def test_nested_name(self):
        child = get_logger("a.b.c")
        assert child.name == "solarfarmer.a.b.c"

    def test_returns_logger_instance(self):
        assert isinstance(get_logger("x"), logging.Logger)

    def test_same_name_returns_same_logger(self):
        assert get_logger("same") is get_logger("same")
