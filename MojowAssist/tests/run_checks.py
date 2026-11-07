"""Run WoW Lua 5.1 fixtures with deterministic C character classes."""
import locale
import unittest
from pathlib import Path
locale.setlocale(locale.LC_CTYPE, 'C')
root = Path(__file__).resolve().parent
result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover(str(root)))
raise SystemExit(not result.wasSuccessful())
