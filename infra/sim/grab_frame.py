#!/usr/bin/env python3
"""Capture one frame from the worker's gimbal camera topic -> PNG.

Runs INSIDE the sim container (needs gz-transport + gz-msgs bindings).
Usage: grab_frame.py <out.png> [timeout_s]
"""

import struct
import sys
import threading

from gz.msgs10.image_pb2 import Image
from gz.transport13 import Node
from PIL import Image as PILImage

TOPIC = (
    "/world/iris_runway/model/iris_with_gimbal/model/gimbal"
    "/link/pitch_link/sensor/camera/image"
)

# gz::msgs::PixelFormatType values we decode
RGB_INT8 = 3
BGR_INT8 = 4


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/frame.png"
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
    got = threading.Event()
    frame: dict = {}

    def cb(msg) -> None:
        frame["w"] = msg.width
        frame["h"] = msg.height
        frame["fmt"] = msg.pixel_format_type
        frame["data"] = bytes(msg.data)
        got.set()

    node = Node()
    if not node.subscribe(Image, TOPIC, cb):
        print("SUBSCRIBE FAILED", flush=True)
        return 1
    if not got.wait(timeout=timeout):
        print("NO FRAME", flush=True)
        return 2
    w, h, fmt, data = frame["w"], frame["h"], frame["fmt"], frame["data"]
    if fmt == RGB_INT8:
        img = PILImage.frombytes("RGB", (w, h), data)
    elif fmt == BGR_INT8:
        img = PILImage.frombytes("RGB", (w, h), data)
        r, g, b = img.split()
        img = PILImage.merge("RGB", (b, g, r))
    else:
        print(f"UNSUPPORTED FORMAT {fmt}", flush=True)
        return 3
    img.save(out)
    print(f"OK {out} {w}x{h}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
