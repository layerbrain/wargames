from __future__ import annotations

import shutil
import subprocess


def bring_openra_to_front() -> bool:
    wmctrl = shutil.which("wmctrl")
    if wmctrl is None:
        return False
    return subprocess.run([wmctrl, "-a", "OpenRA"], check=False).returncode == 0
