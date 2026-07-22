#!/usr/bin/env python3
"""Convenience wrapper so coworkers can just run: python report.py"""

import sys

from geoguessr_scraper.report_cli import main

if __name__ == "__main__":
    sys.exit(main())
