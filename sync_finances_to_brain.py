#!/usr/bin/env python3
"""Compatibility entry point for the retired local-vault finance sync."""

import argparse


def run_sync(initialize: bool = False) -> bool:
    """Skip the retired destination without writing files or publishing balances."""
    print(
        "Skipped: local Second Brain finance sync is retired. "
        "No files or Notion records were changed. "
        "Use Supabase for current financial values and analysis/reports for local reports."
    )
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initialize", action="store_true", help="Accepted for compatibility; no effect")
    args = parser.parse_args()
    run_sync(initialize=args.initialize)


if __name__ == "__main__":
    main()
