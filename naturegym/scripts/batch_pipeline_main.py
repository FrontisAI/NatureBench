#!/usr/bin/env python3
"""Run construction stages 1–4, optionally followed by Docker verification."""

if __package__:
    from .pipeline_runner import main
else:
    from pipeline_runner import main


if __name__ == "__main__":
    raise SystemExit(main(verified=False))
