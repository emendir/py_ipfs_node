#!/bin/bash
## Setup script for macOS - Installs prerequisites for building libkubo

set -euo pipefail # Exit if any command fails

echo "=== macOS Build Prerequisites Setup ==="
echo ""

# Required Go version
REQUIRED_GO_VERSION="1.19"
GO_DOWNLOAD_URL="https://go.dev/dl/go${REQUIRED_GO_VERSION}.darwin-amd64.tar.gz"
GO_DOWNLOAD_URL_ARM64="https://go.dev/dl/go${REQUIRED_GO_VERSION}.darwin-arm64.tar.gz"

# Detect architecture
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"
echo ""

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for Apple Silicon
    if [ "$ARCH" = "arm64" ]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo "✓ Homebrew is already installed"
fi

echo ""

# Check if Xcode Command Line Tools are installed
if ! xcode-select -p &> /dev/null; then
    echo "Installing Xcode Command Line Tools..."
    xcode-select --install
    echo "Please complete the Xcode Command Line Tools installation and re-run this script."
    exit 1
else
    echo "✓ Xcode Command Line Tools are installed"
fi

echo ""

# Check Go version
if command -v go &> /dev/null; then
    INSTALLED_GO_VERSION=$(go version | awk '{print $3}' | sed 's/go//')
    echo "Found Go version: $INSTALLED_GO_VERSION"
    
    if [ "$INSTALLED_GO_VERSION" = "$REQUIRED_GO_VERSION" ]; then
        echo "✓ Go $REQUIRED_GO_VERSION is already installed"
    else
        echo "Warning: Go $INSTALLED_GO_VERSION is installed, but $REQUIRED_GO_VERSION is required"
        read -p "Do you want to install Go $REQUIRED_GO_VERSION? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            INSTALL_GO=true
        else
            echo "Skipping Go installation. Build may fail."
            INSTALL_GO=false
        fi
    fi
else
    echo "Go is not installed"
    INSTALL_GO=true
fi

if [ "${INSTALL_GO:-false}" = true ]; then
    echo ""
    echo "Installing Go $REQUIRED_GO_VERSION..."
    
    # Determine download URL based on architecture
    if [ "$ARCH" = "arm64" ]; then
        DOWNLOAD_URL="$GO_DOWNLOAD_URL_ARM64"
    else
        DOWNLOAD_URL="$GO_DOWNLOAD_URL"
    fi
    
    # Download Go
    echo "Downloading from $DOWNLOAD_URL..."
    tmp_dir=$(mktemp -d)
    cd $tmp_dir

    curl -LO "$DOWNLOAD_URL"
    tarfile=$(ls *.gz)
    
    # Extract and install
    echo "Installing Go to /usr/local/go..."
    sudo rm -rf /usr/local/go
    sudo tar -C /usr/local -xzf "$tarfile"
    
    # Add to PATH if not already there
    if ! grep -q '/usr/local/go/bin' ~/.zprofile 2>/dev/null; then
        echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.zprofile
        echo 'export PATH=$PATH:$HOME/go/bin' >> ~/.zprofile
    fi
    
    export PATH=$PATH:/usr/local/go/bin
    export PATH=$PATH:$HOME/go/bin
    
    # Clean up
    rm -f "go${REQUIRED_GO_VERSION}.darwin-*.tar.gz"
    
    echo "✓ Go $REQUIRED_GO_VERSION installed successfully"
    echo ""
    echo "IMPORTANT: Run 'source ~/.zprofile' or restart your terminal to update PATH"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Installed components:"
echo "  - Homebrew: $(brew --version | head -n1)"
echo "  - Xcode Command Line Tools: $(xcode-select -p)"
echo "  - Go: $(go version 2>/dev/null || echo 'Run source ~/.zprofile')"
echo ""
echo "You can now run ./compile/macos.sh to build libkubo"
