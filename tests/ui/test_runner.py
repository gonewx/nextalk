#!/usr/bin/env python
"""
Simple test runner for UI tests.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import unittest

# Import test modules
from tests.ui import test_menu, test_tray

def main():
    """Run UI tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test modules
    suite.addTests(loader.loadTestsFromModule(test_menu))
    suite.addTests(loader.loadTestsFromModule(test_tray))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(main())