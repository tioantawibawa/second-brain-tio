"""Historical systemd entry point delegated to the shared v2 runner."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from second_brain.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["bot", *sys.argv[1:]]))
