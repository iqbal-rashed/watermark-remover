"""Build script: builds frontend then packages with PyInstaller."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def run(cmd: list, cwd=None):
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd or ROOT)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)


def main():
    # 1. Build frontend
    frontend = ROOT / "frontend"
    print("=== Building frontend ===")
    run(["npm", "install"], cwd=frontend)
    run(["npm", "run", "build"], cwd=frontend)

    # 2. Package with PyInstaller
    print("\n=== Packaging with PyInstaller ===")
    run([
        sys.executable, "-m", "PyInstaller",
        str(ROOT / "build" / "watermark_remover.spec"),
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build" / "work"),
        "--clean",
    ])

    # 3. Report
    dist = ROOT / "dist"
    exes = list(dist.glob("watermark-remover*"))
    if exes:
        for exe in exes:
            size_mb = exe.stat().st_size / 1048576
            print(f"\n✓ Output: {exe}  ({size_mb:.1f} MB)")
    else:
        print("\n✓ Build complete. Check dist/")


if __name__ == "__main__":
    main()
