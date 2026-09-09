#!/usr/bin/env python3
"""Entry point: `python tool.py query --scope default "SELECT ..."`."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pcp_spike.tool import main
raise SystemExit(main())
