#!/usr/bin/env python3
"""Run construction with verification/correction loops and optional Docker checks."""

if __package__:
    from .pipeline_runner import main
else:
    from pipeline_runner import main


if __name__ == "__main__":
    raise SystemExit(main(verified=True))
