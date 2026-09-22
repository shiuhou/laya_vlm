"""Regenerate summary.csv and failures.csv without loading simulator or models."""
import argparse
import json

from .records import summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory")
    args = parser.parse_args()
    print(json.dumps(summarize(args.run_directory), sort_keys=True))


if __name__ == "__main__":
    main()
