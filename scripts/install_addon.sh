#!/usr/bin/env bash
#
# install_addon.sh - Nextalk Fcitx5 Plugin Installation Script
# Version: 0.1.0
#
# This script compiles and installs the Nextalk Fcitx5 plugin.
#
set -euo pipefail

# ==============================================================================
# Version and Script Info
# ==============================================================================
VERSION="0.1.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ADDON_DIR="$PROJECT_ROOT/addons/fcitx5"
BUILD_DIR="$ADDON_DIR/build"

# ==============================================================================
# Terminal Color Detection (Task 2.1, 2.2)
# ==============================================================================
if [[ -t 1 ]] && [[ "${TERM:-}" != "dumb" ]] && command -v tput &>/dev/null && [[ $(tput colors 2>/dev/null || echo 0) -ge 8 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# ==============================================================================
# Output Functions (Task 5.1)
# ==============================================================================
info()    { echo -e "${BLUE}[ℹ]${NC} $*"; }
success() { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[✗]${NC} $*" >&2; }

# ==============================================================================
# Help Message (Task 4.2)
# ==============================================================================
show_help() {
    cat << EOF
Nextalk Fcitx5 Plugin Installation Script v${VERSION}

Usage: $(basename "$0") [OPTIONS]

Options:
  --user      Install to user directory (~/.local/) [default]
  --system    Install to system directory (requires sudo)
  --clean     Clean build directory and exit
  --verify    Verify plugin installation (restart Fcitx5 and check)
  --help      Show this help message
  --version   Show version number

Examples:
  $(basename "$0")           # Build and install to user directory
  $(basename "$0") --user    # Same as above
  sudo $(basename "$0") --system  # Install to system directory
  $(basename "$0") --clean   # Clean build directory only
  $(basename "$0") --verify  # Verify plugin is loaded correctly

EOF
}

# ==============================================================================
# Dependency Check Functions (Task 2.3, 2.4, 2.5)
# ==============================================================================
check_command() {
    local cmd="$1"
    local pkg="${2:-$1}"
    
    if command -v "$cmd" &>/dev/null; then
        success "$cmd found"
        return 0
    else
        error "$cmd not found. Install with: sudo apt install $pkg"
        return 1
    fi
}

check_fcitx5_dev() {
    # Use Fcitx5Core package name (not fcitx5)
    if ! pkg-config --modversion Fcitx5Core &>/dev/null; then
        error "fcitx5-dev not found. Install with: sudo apt install libfcitx5core-dev"
        return 1
    fi

    # Verify headers exist using pkg-config includedir (M3 fix - tighter validation)
    local includedir
    includedir="$(pkg-config --variable=includedir Fcitx5Core 2>/dev/null || echo '/usr/include')"
    if [[ ! -d "${includedir}/Fcitx5" ]] && [[ ! -d "${includedir}/Fcitx5Core" ]]; then
        error "Fcitx5 headers not found at ${includedir}/Fcitx5"
        error "Install with: sudo apt install libfcitx5core-dev"
        return 1
    fi

    success "fcitx5-dev ($(pkg-config --modversion Fcitx5Core))"
    return 0
}

check_dependencies() {
    info "Checking dependencies..."
    local failed=false
    
    check_command "cmake" "cmake" || failed=true
    check_command "make" "make" || failed=true
    check_command "pkg-config" "pkg-config" || failed=true
    check_command "fcitx5" "fcitx5" || failed=true
    check_fcitx5_dev || failed=true
    
    if [[ "$failed" == "true" ]]; then
        echo ""
        error "Missing dependencies. Please install them and try again."
        echo -e "  ${YELLOW}Quick fix:${NC} sudo apt install cmake make pkg-config fcitx5 libfcitx5core-dev"
        exit 1
    fi
    
    success "All dependencies satisfied"
}

# ==============================================================================
# Build Functions (Task 3)
# ==============================================================================
clean_build() {
    info "Cleaning build directory..."
    rm -rf "$BUILD_DIR"
    success "Build directory cleaned"
}

build_plugin() {
    info "Building Nextalk Fcitx5 plugin..."

    # Check source directory exists
    if [[ ! -d "$ADDON_DIR" ]]; then
        error "Plugin source not found at: $ADDON_DIR"
        exit 1
    fi

    if [[ ! -f "$ADDON_DIR/CMakeLists.txt" ]]; then
        error "CMakeLists.txt not found in: $ADDON_DIR"
        exit 1
    fi

    # Clean and create build directory (Task 3.3)
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"

    # Run cmake and make in subshell to preserve working directory (M2 fix)
    (
        cd "$BUILD_DIR" || exit 1

        # Run cmake (Task 3.4)
        info "Running cmake..."
        if ! cmake .. -DCMAKE_CXX_FLAGS="-Wall -Wextra" 2>&1; then
            error "CMake configuration failed"
            if [[ -f "CMakeFiles/CMakeError.log" ]]; then
                warn "Check error log: $BUILD_DIR/CMakeFiles/CMakeError.log"
            fi
            exit 1
        fi
        success "CMake configuration complete"

        # Run make (Task 3.5)
        info "Compiling..."
        local nproc_count
        nproc_count=$(nproc 2>/dev/null || echo 1)
        if ! make -j"$nproc_count" 2>&1; then
            error "Compilation failed"
            if [[ -f "CMakeFiles/CMakeError.log" ]]; then
                warn "Check error log: $BUILD_DIR/CMakeFiles/CMakeError.log"
            fi
            exit 1
        fi
        success "Compilation complete"
    ) || exit 1

    # Verify build artifacts (Task 3.6) - outside subshell
    if [[ ! -f "$BUILD_DIR/nextalk.so" ]]; then
        error "Build artifact not found: nextalk.so"
        exit 1
    fi

    if ! file "$BUILD_DIR/nextalk.so" | grep -q "shared object"; then
        error "nextalk.so is not a valid ELF shared object"
        exit 1
    fi

    if [[ ! -f "$BUILD_DIR/nextalk.conf" ]]; then
        error "Build artifact not found: nextalk.conf"
        exit 1
    fi

    success "Build artifacts verified: nextalk.so, nextalk.conf"
}

# ==============================================================================
# Install Functions (Task 4)
# ==============================================================================
get_install_paths() {
    local mode="$1"

    if [[ "$mode" == "--system" ]]; then
        # System-level paths using pkg-config (AC4 compliance)
        local libdir pkgdatadir
        # Get library directory with architecture-aware fallback
        libdir="$(pkg-config --variable=libdir Fcitx5Core 2>/dev/null)" || {
            # Fallback: detect architecture dynamically
            local arch
            arch="$(dpkg-architecture -qDEB_HOST_MULTIARCH 2>/dev/null || uname -m)"
            libdir="/usr/lib/${arch}"
        }
        # Get data directory from pkg-config (per Dev Notes requirement)
        pkgdatadir="$(pkg-config --variable=pkgdatadir fcitx5 2>/dev/null || echo '/usr/share/fcitx5')"
        PLUGIN_DIR="${libdir}/fcitx5"
        CONFIG_DIR="${pkgdatadir}/addon"
    else
        # User-level paths
        PLUGIN_DIR="$HOME/.local/lib/fcitx5"
        CONFIG_DIR="$HOME/.local/share/fcitx5/addon"
    fi
}

install_plugin() {
    local mode="$1"
    
    get_install_paths "$mode"
    
    info "Installing plugin..."
    info "  Plugin directory: $PLUGIN_DIR"
    info "  Config directory: $CONFIG_DIR"
    
    # Create directories (Task 4.7)
    mkdir -p "$PLUGIN_DIR"
    mkdir -p "$CONFIG_DIR"
    
    # Copy files (Task 4.8)
    cp "$BUILD_DIR/nextalk.so" "$PLUGIN_DIR/"
    cp "$BUILD_DIR/nextalk.conf" "$CONFIG_DIR/"
    
    # Verify installation
    if [[ -f "$PLUGIN_DIR/nextalk.so" ]] && [[ -f "$CONFIG_DIR/nextalk.conf" ]]; then
        success "Plugin installed successfully"
    else
        error "Installation verification failed"
        exit 1
    fi
}

# ==============================================================================
# Summary and Restart Prompt (Task 5.2, 5.3, 5.4)
# ==============================================================================
show_summary() {
    local mode="$1"

    get_install_paths "$mode"

    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo -e "${GREEN}Installation Complete!${NC}"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "Installed files:"
    echo "  Plugin: $PLUGIN_DIR/nextalk.so"
    echo "  Config: $CONFIG_DIR/nextalk.conf"
    echo ""
    echo "Next steps:"
    echo -e "  1. Restart Fcitx5:  ${YELLOW}fcitx5 -r${NC}"
    echo -e "  2. Verify plugin:   ${YELLOW}$0 --verify${NC}"
    echo ""
}

# ==============================================================================
# Verification Function (Task 6.2 - Automated Verification)
# ==============================================================================
verify_plugin() {
    info "Verifying Nextalk plugin installation..."
    local failed=false

    # Step 1: Restart Fcitx5
    info "Restarting Fcitx5..."
    if command -v fcitx5 &>/dev/null; then
        fcitx5 -r -d 2>/dev/null &
        sleep 2  # Wait for Fcitx5 to restart
        success "Fcitx5 restarted"
    else
        error "fcitx5 command not found"
        return 1
    fi

    # Step 2: Check if plugin is loaded via fcitx5-diagnose
    info "Checking plugin status..."
    if command -v fcitx5-diagnose &>/dev/null; then
        local diagnose_output
        diagnose_output="$(fcitx5-diagnose 2>&1)"
        if echo "$diagnose_output" | grep -qi "nextalk"; then
            success "Plugin 'nextalk' found in fcitx5-diagnose output"
        else
            warn "Plugin 'nextalk' not found in fcitx5-diagnose output"
            failed=true
        fi
    else
        warn "fcitx5-diagnose not found, skipping diagnose check"
    fi

    # Step 3: Check for Socket file
    info "Checking Socket file..."
    local socket_path="${XDG_RUNTIME_DIR:-/tmp}/nextalk-fcitx5.sock"
    if [[ -S "$socket_path" ]]; then
        success "Socket file exists: $socket_path"
        ls -la "$socket_path" 2>/dev/null | sed 's/^/  /'
    else
        warn "Socket file not found: $socket_path"
        warn "This is expected if no application has focus"
    fi

    echo ""
    if [[ "$failed" == "true" ]]; then
        echo -e "${YELLOW}Verification completed with warnings${NC}"
        echo "Plugin may not be fully loaded. Check:"
        echo "  - Fcitx5 logs: journalctl --user -u fcitx5 -n 20"
        echo "  - Plugin files exist in install directory"
        return 1
    else
        echo -e "${GREEN}Verification passed!${NC}"
        return 0
    fi
}

# ==============================================================================
# Main
# ==============================================================================
main() {
    local install_mode="--user"
    
    # Parse arguments (Task 4.1)
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --user)
                install_mode="--user"
                shift
                ;;
            --system)
                install_mode="--system"
                shift
                ;;
            --clean)
                clean_build
                exit 0
                ;;
            --verify)
                verify_plugin
                exit $?
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            --version|-v)
                echo "Nextalk Fcitx5 Plugin Installer v${VERSION}"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                echo "Use --help for usage information."
                exit 1
                ;;
        esac
    done
    
    # Check root for system install (Task 4.5)
    if [[ "$install_mode" == "--system" ]] && [[ $EUID -ne 0 ]]; then
        error "System install requires root privileges."
        echo -e "  Run: ${YELLOW}sudo $0 --system${NC}"
        exit 1
    fi
    
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  Nextalk Fcitx5 Plugin Installer v${VERSION}"
    echo "  Install mode: ${install_mode/--/}"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    # Execute build and install
    check_dependencies
    echo ""
    build_plugin
    echo ""
    install_plugin "$install_mode"
    show_summary "$install_mode"
}

main "$@"
