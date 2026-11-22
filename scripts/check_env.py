"""Cetak versi environment dan status GPU."""

from __future__ import annotations

import platform
import sys
from importlib.metadata import PackageNotFoundError, version


def main() -> int:
    print("python", sys.version.split()[0])
    print("platform", platform.platform())

    for name in ("torch", "transformers", "peft", "trl", "bitsandbytes"):
        try:
            print(name, version(name))
        except PackageNotFoundError:
            print(name, "belum terpasang")

    try:
        import torch
    except ImportError:
        return 0

    print("cuda", torch.cuda.is_available())
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        print("gpu", torch.cuda.get_device_name(0))
        print("vram_mb", round(props.total_memory / 1024 / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
