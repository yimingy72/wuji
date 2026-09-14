"""Refresh an existing vNext configuration with published image digests only."""

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
for package in ("packages/wuji-core/src", "packages/task-runtime/src", "packages/maf-worker/src"):
    sys.path.insert(0, str(ROOT / package))
CONFIGURE_DIR = ROOT / "ops/vnext/kubernetes"
sys.path.insert(0, str(CONFIGURE_DIR))

from configure import refresh_images  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    args = parser.parse_args()
    images = json.loads(args.images.read_bytes())
    if isinstance(images, dict) and set(images) == {"images", "source_revision"}:
        images = images["images"]
    result = refresh_images(ROOT, args.state, images)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
