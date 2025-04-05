# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test Commands
```bash
# Install in development mode
pip install -e .

# Rebuild Go library manually if needed
cd libkubo && ./compile_linux.sh  # Linux
cd libkubo && ./compile_android.sh  # Android

# Run all tests
python -m unittest discover tests

# Run a specific test file/case/method
python -m unittest tests/test_utils.py
python -m unittest tests.test_utils.TestCIDUtils
python -m unittest tests.test_utils.TestCIDUtils.test_valid_cid_v0
```

## Style Guidelines
- **Python naming**: Classes `PascalCase`, functions/variables `snake_case`, constants `UPPER_SNAKE_CASE`
- **Go naming**: Exported functions `PascalCase`, local variables `camelCase`
- **Imports**: Standard lib → third-party → local, alphabetically ordered in groups
- **Types**: Use type annotations for all function parameters and return values
- **Docstrings**: Google-style format with Args/Returns sections
- **Error handling**: Specific exceptions with descriptive messages, check Go errors immediately
- **Resource management**: Use context managers (`with`) and explicit cleanup in `close()` methods