"""Compatibility import for the two-agent packet builder."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from second_brain.execution import prepare
