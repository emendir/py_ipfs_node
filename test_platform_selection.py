#!/usr/bin/env python3
"""
Test script to verify platform-specific library selection logic.
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

def test_library_selection():
    """Test that the correct library is selected based on platform detection."""

    test_cases = [
        {
            "name": "Android ARM64",
            "env_vars": {"ANDROID_ROOT": "/system", "ANDROID_DATA": "/data"},
            "expected_lib": "libkubo_android_arm64.so",
            "expected_header": "libkubo_android_arm64.h"
        },
        {
            "name": "Linux ARM64",
            "env_vars": {},
            "expected_lib": "libkubo_linux_arm64.so",
            "expected_header": "libkubo_linux_arm64.h"
        }
    ]

    for test_case in test_cases:
        print(f"\n=== Testing {test_case['name']} ===")

        # Create test environment
        env = os.environ.copy()

        # Clear Android environment variables first
        for key in ["ANDROID_ROOT", "ANDROID_DATA"]:
            if key in env:
                del env[key]

        # Set test-specific environment variables
        env.update(test_case["env_vars"])

        # Mock the platform to be ARM64/Linux for this test
        test_code = f"""
import sys
import os
import platform

# Mock platform functions for ARM64/Linux
original_system = platform.system
original_machine = platform.machine

platform.system = lambda: "Linux"
platform.machine = lambda: "aarch64"

try:
    # Import the loader module
    sys.path.insert(0, 'src')
    from libkubo import libkubo_loader

    print(f"Selected library: {{libkubo_loader.lib_name}}")
    print(f"Selected header: {{libkubo_loader.header_name}}")
    print(f"Android detected: {{libkubo_loader.is_android()}}")

    # Verify correct selection
    expected_lib = "{test_case['expected_lib']}"
    expected_header = "{test_case['expected_header']}"

    if libkubo_loader.lib_name == expected_lib:
        print(f"✓ Library selection correct: {{expected_lib}}")
    else:
        print(f"✗ Library selection wrong: expected {{expected_lib}}, got {{libkubo_loader.lib_name}}")
        sys.exit(1)

    if libkubo_loader.header_name == expected_header:
        print(f"✓ Header selection correct: {{expected_header}}")
    else:
        print(f"✗ Header selection wrong: expected {{expected_header}}, got {{libkubo_loader.header_name}}")
        sys.exit(1)

    print(f"✓ {test_case['name']} test passed")

finally:
    # Restore original functions
    platform.system = original_system
    platform.machine = original_machine
"""

        try:
            result = subprocess.run([sys.executable, "-c", test_code],
                                  env=env, capture_output=True, text=True, timeout=10)

            print("STDOUT:", result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

            if result.returncode == 0:
                print(f"✓ {test_case['name']} selection test PASSED")
            else:
                print(f"✗ {test_case['name']} selection test FAILED")
                return False

        except Exception as e:
            print(f"✗ {test_case['name']} test ERROR: {e}")
            return False

    return True

def test_wheel_contains_both_libraries():
    """Test that the linux_aarch64 wheel contains both libraries."""

    print(f"\n=== Testing wheel contents ===")

    wheel_path = Path("dist/ipfs_node-0.1.12rc1-py3-none-linux_aarch64.whl")
    if not wheel_path.exists():
        print(f"✗ Wheel not found: {wheel_path}")
        return False

    try:
        result = subprocess.run([
            sys.executable, "-m", "zipfile", "-l", str(wheel_path)
        ], capture_output=True, text=True)

        contents = result.stdout

        required_files = [
            "libkubo/libkubo_linux_arm64.so",
            "libkubo/libkubo_linux_arm64.h",
            "libkubo/libkubo_android_arm64.so",
            "libkubo/libkubo_android_arm64.h"
        ]

        all_present = True
        for file in required_files:
            if file in contents:
                print(f"✓ Found: {file}")
            else:
                print(f"✗ Missing: {file}")
                all_present = False

        if all_present:
            print("✓ All required libraries present in wheel")
            return True
        else:
            print("✗ Some libraries missing from wheel")
            return False

    except Exception as e:
        print(f"✗ Error checking wheel contents: {e}")
        return False

def main():
    """Main test function."""
    print("Testing platform-specific library selection...")

    success1 = test_library_selection()
    success2 = test_wheel_contains_both_libraries()

    print(f"\n=== Test Summary ===")
    if success1 and success2:
        print("✓ All tests passed!")
        print("✓ Android systems will use libkubo_android_arm64.so")
        print("✓ Linux ARM64 systems will use libkubo_linux_arm64.so")
        print("✓ Both libraries are included in linux_aarch64 wheel")
    else:
        print("✗ Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()