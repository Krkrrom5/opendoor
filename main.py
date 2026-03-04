#!/usr/bin/env python3
"""
OpenDoor v4
Usage:
  python main.py                        # current directory
  python main.py --root ./myproject     # specific project
  python main.py app.py utils.py        # open files immediately
  python main.py --no-stream            # disable streaming
  python main.py --no-apply             # read-only (don't write files)
  python main.py -v                     # verbose debug
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from opendoor.core.app import run

def main():
    p = argparse.ArgumentParser(prog="opendoor", description="OpenDoor AI coding assistant")
    p.add_argument("files", nargs="*", help="Files to open immediately")
    p.add_argument("--root", default=".", help="Project root (default: current dir)")
    p.add_argument("--model", default=None, help="Model name override")
    p.add_argument("--no-stream", action="store_true", help="Disable streaming")
    p.add_argument("--no-apply", action="store_true", help="Don't auto-write files")
    p.add_argument("-v","--verbose", action="store_true", help="Verbose output")
    args = p.parse_args()
    run(root=args.root, files=args.files or [], model=args.model,
        stream=not args.no_stream, verbose=args.verbose, auto_apply=not args.no_apply)

if __name__ == "__main__":
    main()
