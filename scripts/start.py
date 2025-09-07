#!/usr/bin/env python
"""
NexTalk startup script.

This script provides a convenient way to start NexTalk from anywhere.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path so we can import nextalk
sys.path.insert(0, str(Path(__file__).parent.parent))

from nextalk.main import main

if __name__ == "__main__":
    sys.exit(main())