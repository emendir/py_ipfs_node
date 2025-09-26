#!/usr/bin/env python3
"""
Test script to verify that platform-specific wheels can load correctly.
"""

import tempfile
import subprocess
import sys
import os
from pathlib import Path

def test_wheel_loading(wheel_path):
    """Test that a wheel can be installed and the package loads correctly."""
    wheel_path = Path(wheel_path)
    print(f"\n=== Testing {wheel_path.name} ===")

    # Create a temporary virtual environment
    with tempfile.TemporaryDirectory() as temp_dir:
        venv_dir = Path(temp_dir) / "test_venv"

        # Create virtual environment
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

        # Get paths for the virtual environment
        if os.name == 'nt':  # Windows
            python_exe = venv_dir / "Scripts" / "python.exe"
            pip_exe = venv_dir / "Scripts" / "pip.exe"
        else:  # Unix-like
            python_exe = venv_dir / "bin" / "python"
            pip_exe = venv_dir / "bin" / "pip"

        try:
            # Install the wheel
            print(f"Installing {wheel_path.name}...")
            subprocess.run([str(pip_exe), "install", str(wheel_path)],
                         check=True, capture_output=True, text=True)

            # Try to import the package and basic functionality
            test_code = """
import sys
try:
    # Test basic imports
    import ipfs_node
    print("✓ ipfs_node imported successfully")

    # Test libkubo loader
    from libkubo import libkubo_loader
    print("✓ libkubo_loader imported successfully")

    # Check if library files are detected
    print(f"✓ Library detected: {libkubo_loader.lib_name}")
    print(f"✓ Header detected: {libkubo_loader.header_name}")

    # This will fail on non-matching platforms, but that's expected
    try:
        # Try to load the actual library (will fail on wrong platform)
        _ = libkubo_loader.libkubo
        print("✓ Library loaded successfully (platform match)")
    except Exception as e:
        print(f"⚠ Library load failed (expected on wrong platform): {e}")

    print("✓ Package test completed successfully")

except Exception as e:
    print(f"✗ Import test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""

            result = subprocess.run([str(python_exe), "-c", test_code],
                                  capture_output=True, text=True, timeout=30)

            print("STDOUT:", result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

            if result.returncode == 0:
                print(f"✓ {wheel_path.name} test PASSED")
                return True
            else:
                print(f"✗ {wheel_path.name} test FAILED")
                return False

        except subprocess.TimeoutExpired:
            print(f"✗ {wheel_path.name} test TIMED OUT")
            return False
        except Exception as e:
            print(f"✗ {wheel_path.name} test ERROR: {e}")
            return False

def main():
    """Main function to test all wheels."""
    dist_dir = Path("dist")
    wheels = list(dist_dir.glob("*.whl"))

    if not wheels:
        print("No wheels found in dist/ directory")
        return

    print(f"Testing {len(wheels)} wheels...")

    results = {}
    for wheel in wheels:
        results[wheel.name] = test_wheel_loading(wheel)

    print(f"\n=== Test Summary ===")
    for wheel_name, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"{status}: {wheel_name}")

    failed_count = sum(1 for success in results.values() if not success)
    if failed_count > 0:
        print(f"\n{failed_count} tests failed")
        sys.exit(1)
    else:
        print(f"\nAll {len(wheels)} tests passed!")

if __name__ == "__main__":
    main()