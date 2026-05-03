"""pytest configuration and package path setup."""
import sys
import os

# Ensure the project root is on sys.path for all tests
sys.path.insert(0, os.path.dirname(__file__))
