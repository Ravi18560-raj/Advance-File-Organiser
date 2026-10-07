"""Allows running the tool with: python3 -m smart_file_manager"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
