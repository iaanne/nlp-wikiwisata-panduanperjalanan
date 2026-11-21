import argparse
from pathlib import Path

from .config import load_config
from .pipeline import build, fetch, index, run_experiments


def main() -> None:
    parser = argparse.ArgumentParser(description="WikiWisata corpus/retrieval pipeline")
    parser.add_argument(
        "command", choices=("fetch", "build", "index", "experiments")
    )
    parser.add_argument("--config", default="config.json")
    args = parser.parse_args()
    root = Path.cwd()
    config = load_config(root / args.config)
    if args.command == "fetch":
        print(f"Snapshots written: {fetch(config, root)}")
    elif args.command == "build":
        print(f"Usage counts: {build(config, root)}")
    elif args.command == "index":
        print(f"Index hashes: {index(config, root)}")
    else:
        print(f"Retrieval runs written: {run_experiments(config, root)}")


if __name__ == "__main__":
    main()
