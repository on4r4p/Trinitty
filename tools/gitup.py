#!/usr/bin/env python3
import importlib.util
from pathlib import Path


ROOT_GITUP = Path(__file__).resolve().parents[1] / "gitup.py"


def load_root_gitup():
    spec = importlib.util.spec_from_file_location("trinitty_root_gitup", ROOT_GITUP)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    return load_root_gitup().main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
