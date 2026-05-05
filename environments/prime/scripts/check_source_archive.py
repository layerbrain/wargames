from __future__ import annotations

import fnmatch
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


ENV_ROOT = Path(__file__).resolve().parents[1]
SKIPPED_DIR_NAMES = {"__pycache__", "build", "dist"}
SKIPPED_DIR_SUFFIXES = (".egg-info",)
ROOT_FILE_PATTERNS = ("README.md", "pyproject.toml", "*.py")
REQUIRED_ARCHIVE_PATHS = (
    "README.md",
    "pyproject.toml",
    "wargames_prime.py",
    "configs/doom/eval-map01.toml",
    "wargames/__init__.py",
    "wargames/environments/prime.py",
    "scenarios/doom/missions/easy/doom.map.map01.easy.json",
    "scenarios/naev/missions/easy/naev.mission.missions-tutorial-tutorial.easy.json",
)


def main() -> int:
    validate_build_sources()
    with tempfile.TemporaryDirectory(prefix="wargames-prime-source-") as temp:
        archive_root = Path(temp) / "wargames"
        copy_prime_source_archive(archive_root)
        validate_archive_contents(archive_root)
        return build_source_wheel(archive_root)


def validate_build_sources() -> None:
    data = tomllib.loads((ENV_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    targets = data["tool"]["hatch"]["build"]["targets"]
    for target_name in ("wheel", "editable"):
        target = targets[target_name]
        sources = list(target.get("only-include", ()))
        sources.extend(target.get("force-include", {}).keys())
        for source in sources:
            path = Path(source)
            if path.is_absolute() or ".." in path.parts:
                raise AssertionError(
                    f"{target_name} build source must stay inside environments/prime: {source}"
                )
            if not (ENV_ROOT / path).exists():
                raise AssertionError(f"{target_name} build source does not exist: {source}")


def copy_prime_source_archive(archive_root: Path) -> None:
    archive_root.mkdir(parents=True)
    for child in sorted(ENV_ROOT.iterdir()):
        if child.is_file() and matches_root_file(child.name):
            copy_file(child, archive_root / child.name)
        elif child.is_dir() and should_include_directory(child.name):
            copy_directory_files(child, archive_root)


def copy_directory_files(source_root: Path, archive_root: Path) -> None:
    for root, dirs, files in os.walk(source_root, followlinks=True):
        dirs[:] = sorted(name for name in dirs if should_include_directory(name))
        root_path = Path(root)
        for filename in sorted(files):
            if should_include_file(filename):
                source = root_path / filename
                destination = archive_root / source.relative_to(ENV_ROOT)
                copy_file(source, destination)


def validate_archive_contents(archive_root: Path) -> None:
    for relative in REQUIRED_ARCHIVE_PATHS:
        if not (archive_root / relative).is_file():
            raise AssertionError(f"Prime source archive is missing {relative}")


def build_source_wheel(archive_root: Path) -> int:
    if not hatchling_available():
        print(
            "Source archive contents passed; install hatchling to run the local wheel build.",
            file=sys.stderr,
        )
        return 0

    wheelhouse = archive_root.parent / "wheelhouse"
    command = [
        sys.executable,
        "-m",
        "pip",
        "wheel",
        str(archive_root),
        "-w",
        str(wheelhouse),
        "--no-deps",
        "--no-build-isolation",
    ]

    result = subprocess.run(command, check=False)
    return result.returncode


def hatchling_available() -> bool:
    try:
        __import__("hatchling")
    except ModuleNotFoundError:
        return False
    return True


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination, follow_symlinks=True)


def matches_root_file(filename: str) -> bool:
    return any(fnmatch.fnmatch(filename, pattern) for pattern in ROOT_FILE_PATTERNS)


def should_include_directory(name: str) -> bool:
    return (
        not name.startswith(".")
        and name not in SKIPPED_DIR_NAMES
        and not name.endswith(SKIPPED_DIR_SUFFIXES)
    )


def should_include_file(name: str) -> bool:
    return not name.startswith(".") and not name.endswith((".pyc", ".pyo"))


if __name__ == "__main__":
    raise SystemExit(main())
