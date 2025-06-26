import pytest
import logging
import tempfile
import os
from pathlib import Path
from utils.logger import setup_logger, get_logger


class TestLoggingSystem:
    """Test the logging system functionality."""
    
    def test_setup_logger_creates_logger(self, tmp_path):
        """Test that setup_logger creates a logger with correct name."""
        logger = setup_logger("test_logger", log_dir=tmp_path)
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO
    
    def test_setup_logger_creates_log_directory(self, tmp_path):
        """Test that setup_logger creates the log directory."""
        log_dir = tmp_path / "logs"
        setup_logger("test_logger", log_dir=log_dir)
        assert log_dir.exists()
    
    def test_setup_logger_creates_log_files(self, tmp_path):
        """Test that setup_logger creates log files."""
        log_dir = tmp_path / "logs"
        
        # Use unique logger name to avoid conflicts
        logger_name = f"test_logger_files_{id(tmp_path)}"
        logger = setup_logger(logger_name, log_dir=log_dir)
        
        # Trigger log creation by logging something
        logger.info("Test message")
        logger.error("Test error")
        
        # Force all handlers to flush to ensure file creation
        for handler in logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
        
        # Check that log files exist
        assert (log_dir / f"{logger_name}.log").exists()
        assert (log_dir / f"{logger_name}_errors.log").exists()
    
    def test_logger_writes_to_files(self, tmp_path):
        """Test that logger writes messages to files."""
        log_dir = tmp_path / "logs"
        
        # Use unique logger name to avoid conflicts
        logger_name = f"test_logger_writes_{id(tmp_path)}"
        logger = setup_logger(logger_name, log_dir=log_dir)
        
        # Log different levels
        logger.info("Info message")
        logger.error("Error message")
        logger.warning("Warning message")
        
        # Flush handlers to ensure messages are written
        for handler in logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
        
        # Check main log file
        main_log = log_dir / f"{logger_name}.log"
        with open(main_log, 'r') as f:
            content = f.read()
            assert "Info message" in content
            assert "Error message" in content
            assert "Warning message" in content
        
        # Check error log file
        error_log = log_dir / f"{logger_name}_errors.log"
        with open(error_log, 'r') as f:
            content = f.read()
            assert "Error message" in content
            assert "Info message" not in content  # Info should not be in error log
    
    def test_get_logger_returns_existing_logger(self, tmp_path):
        """Test that get_logger returns existing logger."""
        # Create logger first
        logger1 = setup_logger("test_logger", log_dir=tmp_path)
        
        # Get the same logger
        logger2 = get_logger("test_logger")
        
        assert logger1 is logger2
    
    def test_get_logger_creates_new_logger_if_not_exists(self):
        """Test that get_logger creates a new logger if it doesn't exist."""
        # Use a unique name to avoid conflicts
        logger_name = "unique_test_logger_123"
        
        # Clear any existing logger with this name
        if logger_name in logging.Logger.manager.loggerDict:
            del logging.Logger.manager.loggerDict[logger_name]
        
        logger = get_logger(logger_name)
        assert logger.name == logger_name
        assert len(logger.handlers) > 0  # Should have handlers from setup_logger
    
    def test_log_levels_configuration(self, tmp_path):
        """Test different log levels configuration."""
        # Test DEBUG level
        debug_logger = setup_logger("debug_logger", log_level="DEBUG", log_dir=tmp_path)
        assert debug_logger.level == logging.DEBUG
        
        # Test ERROR level  
        error_logger = setup_logger("error_logger", log_level="ERROR", log_dir=tmp_path)
        assert error_logger.level == logging.ERROR
    
    def test_logger_prevents_duplicate_handlers(self, tmp_path):
        """Test that calling setup_logger multiple times doesn't add duplicate handlers."""
        logger1 = setup_logger("test_logger", log_dir=tmp_path)
        initial_handler_count = len(logger1.handlers)
        
        # Call setup_logger again with same name
        logger2 = setup_logger("test_logger", log_dir=tmp_path)
        
        assert logger1 is logger2
        assert len(logger2.handlers) == initial_handler_count
    
    def test_log_format_includes_required_fields(self, tmp_path):
        """Test that log format includes timestamp, level, filename, line number, and message."""
        log_dir = tmp_path / "logs"
        
        # Use unique logger name to avoid conflicts
        logger_name = f"test_logger_format_{id(tmp_path)}"
        logger = setup_logger(logger_name, log_dir=log_dir)
        
        logger.info("Test message for format check")
        
        # Flush handlers
        for handler in logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
        
        # Read log content
        main_log = log_dir / f"{logger_name}.log"
        with open(main_log, 'r') as f:
            content = f.read()
            
        # Check format components
        assert "INFO" in content  # Log level
        assert "test_logging.py" in content  # Filename
        assert "Test message for format check" in content  # Message
        # Check for timestamp pattern (YYYY-MM-DD HH:MM:SS)
        import re
        timestamp_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
        assert re.search(timestamp_pattern, content) is not None