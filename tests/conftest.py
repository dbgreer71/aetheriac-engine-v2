"""
Pytest configuration for AE v2 tests.

This file sets up the test environment before any tests run.
"""

import os

# Set environment variables for testing
os.environ["AE_DISABLE_AUTH"] = "true"
