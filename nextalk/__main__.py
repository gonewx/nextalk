"""
NexTalk command line interface.

Allows running NexTalk as a module: python -m nextalk
"""

import sys
from .main import main

if __name__ == "__main__":
    sys.exit(main())