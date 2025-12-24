#!/usr/bin/env bash
#
# build-pkg.sh - Nextalk Package Builder (DEB & RPM)
# Version: 0.2.0
#
# Unified script for building DEB and RPM packages
#
set -euo pipefail

# ==============================================================================
# Version and Script Info
# ==============================================================================
VERSION="0.2.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Directories
VOICE_CAPSULE_DIR="$PROJECT_ROOT/voice_capsule"
ADDON_DIR="$PROJECT_ROOT/addons/fcitx5"
LIBS_DIR="$PROJECT_ROOT/libs"
PACKAGING_DIR="$PROJECT_ROOT/packaging"
BUILD_DIR="$PROJECT_ROOT/build/pkg-staging"
OUTPUT_DIR="$PROJECT_ROOT/dist"

# Package info
PACKAGE_VERSION=""
PACKAGE_ARCH=""

# ==============================================================================
# Terminal Color Detection
# ==============================================================================
if [[ -t 1 ]] && [[ "${TERM:-}" != "dumb" ]] && command -v tput &>/dev/null && [[ $(tput colors 2>/dev/null || echo 0) -ge 8 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    CYAN=''
    NC=''
fi

# ==============================================================================
# Output Functions
# ==============================================================================
info()    { echo -e "${BLUE}[ℹ]${NC} $*"; }
success() { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[✗]${NC} $*" >&2; }
header()  { echo -e "${CYAN}▶${NC} $*"; }

# ==============================================================================
# Help Message
# ==============================================================================
show_help() {
    cat << EOF
Nextalk Package Builder v${VERSION}

Usage: $(basename "$0") [OPTIONS] [FORMAT]

Format:
  --deb         Build DEB package (Debian/Ubuntu)
  --rpm         Build RPM package (Fedora/CentOS/RHEL)
  --all         Build all package formats

Options:
  --clean       Clean staging directory and exit
  --rebuild     Force rebuild (ignore existing build artifacts)
  --help        Show this help message
  --version     Show version number

Examples:
  $(basename "$0") --deb           # Build DEB package only
  $(basename "$0") --rpm           # Build RPM package only
  $(basename "$0") --all           # Build both DEB and RPM
  $(basename "$0") --all --rebuild # Force rebuild everything

Output:
  dist/nextalk_<version>_amd64.deb
  dist/nextalk-<version>-1.<arch>.rpm

EOF
}

# ==============================================================================
# Dependency Check Functions
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

check_common_dependencies() {
    info "Checking common build dependencies..."
    local failed=false

    check_command "flutter" "flutter" || failed=true
    check_command "cmake" "cmake" || failed=true
    check_command "convert" "imagemagick" || failed=true

    if [[ "$failed" == "true" ]]; then
        echo ""
        error "Missing common dependencies."
        exit 1
    fi

    success "Common dependencies satisfied"
}

check_deb_dependencies() {
    info "Checking DEB build dependencies..."
    local failed=false

    check_command "dpkg-deb" "dpkg" || failed=true
    check_command "dpkg-architecture" "dpkg-dev" || failed=true

    if [[ "$failed" == "true" ]]; then
        echo ""
        error "Missing DEB dependencies. Install: sudo apt install dpkg dpkg-dev"
        return 1
    fi

    success "DEB dependencies satisfied"
    return 0
}

check_rpm_dependencies() {
    info "Checking RPM build dependencies..."
    local failed=false

    if ! command -v rpmbuild &>/dev/null; then
        error "rpmbuild not found."
        if command -v apt &>/dev/null; then
            echo -e "  ${YELLOW}Install with:${NC} sudo apt install rpm"
        elif command -v dnf &>/dev/null; then
            echo -e "  ${YELLOW}Install with:${NC} sudo dnf install rpm-build"
        elif command -v yum &>/dev/null; then
            echo -e "  ${YELLOW}Install with:${NC} sudo yum install rpm-build"
        fi
        failed=true
    else
        success "rpmbuild found"
    fi

    if [[ "$failed" == "true" ]]; then
        return 1
    fi

    success "RPM dependencies satisfied"
    return 0
}

# ==============================================================================
# Version Extraction
# ==============================================================================
extract_version() {
    local pubspec="$VOICE_CAPSULE_DIR/pubspec.yaml"

    if [[ ! -f "$pubspec" ]]; then
        error "pubspec.yaml not found: $pubspec"
        exit 1
    fi

    local raw_version
    raw_version=$(grep "^version:" "$pubspec" | head -1 | awk '{print $2}')

    if [[ -z "$raw_version" ]]; then
        error "Cannot extract version from pubspec.yaml"
        exit 1
    fi

    # Convert + to - for package version (0.1.0+1 -> 0.1.0-1)
    PACKAGE_VERSION="${raw_version//+/-}"
    success "Package version: $PACKAGE_VERSION"
}

# ==============================================================================
# Build Functions
# ==============================================================================
build_flutter() {
    info "Building Flutter application (release mode)..."

    (
        cd "$VOICE_CAPSULE_DIR" || exit 1

        if ! flutter build linux --release 2>&1; then
            error "Flutter build failed"
            exit 1
        fi
    ) || exit 1

    local bundle_dir="$VOICE_CAPSULE_DIR/build/linux/x64/release/bundle"

    if [[ ! -f "$bundle_dir/voice_capsule" ]]; then
        error "Flutter build artifact not found: $bundle_dir/voice_capsule"
        exit 1
    fi

    success "Flutter build complete"
}

build_fcitx5_plugin() {
    info "Building Fcitx5 plugin..."

    local addon_build_dir="$ADDON_DIR/build"

    rm -rf "$addon_build_dir"
    mkdir -p "$addon_build_dir"

    (
        cd "$addon_build_dir" || exit 1

        if ! cmake .. 2>&1; then
            error "CMake configuration failed"
            exit 1
        fi

        local nproc_count
        nproc_count=$(nproc 2>/dev/null || echo 1)

        if ! make -j"$nproc_count" 2>&1; then
            error "Plugin compilation failed"
            exit 1
        fi
    ) || exit 1

    if [[ ! -f "$addon_build_dir/nextalk.so" ]]; then
        error "Plugin artifact not found: nextalk.so"
        exit 1
    fi

    success "Fcitx5 plugin build complete"
}

# ==============================================================================
# Common Package Assembly (shared between DEB and RPM)
# ==============================================================================
assemble_common() {
    local staging_dir="$1"
    local lib_arch="$2"

    info "Assembling package structure..."

    local bundle_dir="$VOICE_CAPSULE_DIR/build/linux/x64/release/bundle"
    local addon_build_dir="$ADDON_DIR/build"

    # Create directory structure
    mkdir -p "$staging_dir/opt/nextalk/lib"
    mkdir -p "$staging_dir/opt/nextalk/data"
    mkdir -p "$staging_dir/usr/lib/${lib_arch}/fcitx5"
    mkdir -p "$staging_dir/usr/share/fcitx5/addon"
    mkdir -p "$staging_dir/usr/share/applications"
    mkdir -p "$staging_dir/usr/share/icons/hicolor/256x256/apps"

    # Copy Flutter bundle
    info "  Copying Flutter bundle..."
    cp "$bundle_dir/voice_capsule" "$staging_dir/opt/nextalk/nextalk"
    chmod 755 "$staging_dir/opt/nextalk/nextalk"

    # Copy Flutter runtime libraries
    cp -r "$bundle_dir/lib/"* "$staging_dir/opt/nextalk/lib/"

    # Copy Flutter data directory
    cp -r "$bundle_dir/data/"* "$staging_dir/opt/nextalk/data/"

    # Copy project dependency libraries
    info "  Copying dependency libraries..."
    if [[ -f "$LIBS_DIR/libsherpa-onnx-c-api.so" ]]; then
        cp "$LIBS_DIR/libsherpa-onnx-c-api.so" "$staging_dir/opt/nextalk/lib/"
    else
        warn "libsherpa-onnx-c-api.so not found in libs/"
    fi

    if [[ -f "$LIBS_DIR/libonnxruntime.so" ]]; then
        cp "$LIBS_DIR/libonnxruntime.so" "$staging_dir/opt/nextalk/lib/"
    else
        warn "libonnxruntime.so not found in libs/"
    fi

    # Copy Fcitx5 plugin
    info "  Copying Fcitx5 plugin..."
    cp "$addon_build_dir/nextalk.so" "$staging_dir/usr/lib/${lib_arch}/fcitx5/"
    cp "$addon_build_dir/nextalk.conf" "$staging_dir/usr/share/fcitx5/addon/"

    # Copy desktop entry (ensure world-readable)
    info "  Installing desktop entry..."
    cp "$PACKAGING_DIR/deb/nextalk.desktop" "$staging_dir/usr/share/applications/"
    chmod 644 "$staging_dir/usr/share/applications/nextalk.desktop"

    # Process icon (multi-size for better desktop integration)
    info "  Processing icons..."
    local icon_src="$VOICE_CAPSULE_DIR/assets/icons/icon.png"
    if [[ -f "$icon_src" ]]; then
        # Create directory structure for multiple icon sizes
        mkdir -p "$staging_dir/usr/share/icons/hicolor/48x48/apps"
        mkdir -p "$staging_dir/usr/share/icons/hicolor/128x128/apps"
        mkdir -p "$staging_dir/usr/share/icons/hicolor/256x256/apps"

        # Generate icons at standard freedesktop.org sizes
        convert "$icon_src" -resize 48x48 "$staging_dir/usr/share/icons/hicolor/48x48/apps/nextalk.png"
        convert "$icon_src" -resize 128x128 "$staging_dir/usr/share/icons/hicolor/128x128/apps/nextalk.png"
        convert "$icon_src" -resize 256x256 "$staging_dir/usr/share/icons/hicolor/256x256/apps/nextalk.png"
        success "Icons processed (48x48, 128x128, 256x256)"
    else
        warn "Icon not found: $icon_src"
    fi

    success "Package structure assembled"
}

# ==============================================================================
# DEB Package Building
# ==============================================================================
build_deb() {
    header "Building DEB package..."

    local deb_staging="$BUILD_DIR/deb"
    rm -rf "$deb_staging"
    mkdir -p "$deb_staging"

    # Get architecture
    local arch
    arch=$(dpkg-architecture -qDEB_HOST_MULTIARCH 2>/dev/null || echo "x86_64-linux-gnu")

    # Assemble common files
    assemble_common "$deb_staging" "$arch"

    # Add DEBIAN control files
    mkdir -p "$deb_staging/DEBIAN"

    # Copy maintainer scripts
    cp "$PACKAGING_DIR/deb/postinst" "$deb_staging/DEBIAN/"
    cp "$PACKAGING_DIR/deb/prerm" "$deb_staging/DEBIAN/"
    chmod 755 "$deb_staging/DEBIAN/postinst"
    chmod 755 "$deb_staging/DEBIAN/prerm"

    # Calculate installed size
    local installed_size
    installed_size=$(du -sk "$deb_staging" | cut -f1)

    # Generate control file
    sed -e "s/{{VERSION}}/$PACKAGE_VERSION/g" \
        -e "s/{{INSTALLED_SIZE}}/$installed_size/g" \
        "$PACKAGING_DIR/deb/control.template" > "$deb_staging/DEBIAN/control"

    success "Control file generated (Installed-Size: ${installed_size}KB)"

    # Build DEB package
    mkdir -p "$OUTPUT_DIR"

    local deb_name="nextalk_${PACKAGE_VERSION}_amd64.deb"
    local deb_path="$OUTPUT_DIR/$deb_name"

    info "Building DEB package..."
    if ! dpkg-deb --build --root-owner-group "$deb_staging" "$deb_path" 2>&1; then
        error "dpkg-deb failed"
        return 1
    fi

    success "DEB package created: $deb_path"
    echo "  Size: $(du -h "$deb_path" | cut -f1)"
}

# ==============================================================================
# RPM Package Building
# ==============================================================================
build_rpm() {
    header "Building RPM package..."

    local rpm_staging="$BUILD_DIR/rpm"
    local rpm_buildroot="$BUILD_DIR/rpm-buildroot"

    rm -rf "$rpm_staging" "$rpm_buildroot"
    mkdir -p "$rpm_staging"
    mkdir -p "$rpm_buildroot"

    # Detect architecture for RPM
    local rpm_arch
    case "$(uname -m)" in
        x86_64)  rpm_arch="x86_64" ;;
        aarch64) rpm_arch="aarch64" ;;
        *)       rpm_arch="$(uname -m)" ;;
    esac

    # Library path for RPM (Fedora/RHEL style)
    local lib_arch
    if [[ "$rpm_arch" == "x86_64" ]]; then
        lib_arch="x86_64-linux-gnu"  # Use same path for compatibility
    else
        lib_arch="${rpm_arch}-linux-gnu"
    fi

    # Assemble common files into staging directory
    assemble_common "$rpm_staging" "$lib_arch"

    # Generate spec file from template
    local spec_file="$BUILD_DIR/nextalk.spec"

    # Split version: 0.1.0-1 -> Version=0.1.0, Release=1
    local rpm_version="${PACKAGE_VERSION%%-*}"   # 0.1.0
    local rpm_release="${PACKAGE_VERSION##*-}"   # 1

    sed -e "s/{{VERSION}}/${rpm_version}/g" \
        -e "s/{{RELEASE}}/${rpm_release}/g" \
        -e "s|%{_libdir}|/usr/lib/${lib_arch}|g" \
        "$PACKAGING_DIR/rpm/nextalk.spec.template" > "$spec_file"

    success "Spec file generated"

    # Setup RPM build directories
    local rpmbuild_dir="$BUILD_DIR/rpmbuild"
    mkdir -p "$rpmbuild_dir"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

    # Copy staging to BUILD directory
    mkdir -p "$rpmbuild_dir/BUILD/staging"
    cp -a "$rpm_staging"/* "$rpmbuild_dir/BUILD/staging/"

    # Copy spec file
    cp "$spec_file" "$rpmbuild_dir/SPECS/"

    # Build RPM
    info "Building RPM package..."
    mkdir -p "$OUTPUT_DIR"

    if ! rpmbuild --define "_topdir $rpmbuild_dir" \
                  --define "buildroot $rpmbuild_dir/BUILDROOT" \
                  --buildroot "$rpmbuild_dir/BUILDROOT" \
                  -bb "$rpmbuild_dir/SPECS/nextalk.spec" 2>&1; then
        error "rpmbuild failed"
        return 1
    fi

    # Find and move the built RPM
    local built_rpm
    built_rpm=$(find "$rpmbuild_dir/RPMS" -name "*.rpm" -type f | head -1)

    if [[ -n "$built_rpm" ]]; then
        local rpm_name
        rpm_name=$(basename "$built_rpm")

        # Remove old RPM files from output directory
        rm -f "$OUTPUT_DIR"/nextalk-*.rpm 2>/dev/null || true

        cp "$built_rpm" "$OUTPUT_DIR/"
        success "RPM package created: $OUTPUT_DIR/$rpm_name"
        echo "  Size: $(du -h "$OUTPUT_DIR/$rpm_name" | cut -f1)"
    else
        error "RPM package not found after build"
        return 1
    fi
}

# ==============================================================================
# Clean Function
# ==============================================================================
clean_build() {
    info "Cleaning staging directory..."
    rm -rf "$BUILD_DIR"
    success "Staging directory cleaned"
}

# ==============================================================================
# Summary Function
# ==============================================================================
show_summary() {
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo -e "${GREEN}Build Complete!${NC}"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "Output directory: $OUTPUT_DIR"
    echo ""

    if [[ -f "$OUTPUT_DIR/nextalk_${PACKAGE_VERSION}_amd64.deb" ]]; then
        echo -e "DEB: ${CYAN}nextalk_${PACKAGE_VERSION}_amd64.deb${NC}"
        echo "  Install: sudo dpkg -i dist/nextalk_${PACKAGE_VERSION}_amd64.deb"
    fi

    local rpm_file
    rpm_file=$(find "$OUTPUT_DIR" -name "nextalk-*.rpm" -type f 2>/dev/null | head -1)
    if [[ -n "$rpm_file" ]]; then
        echo -e "RPM: ${CYAN}$(basename "$rpm_file")${NC}"
        echo "  Install: sudo rpm -i $rpm_file"
    fi

    echo ""
}

# ==============================================================================
# Main
# ==============================================================================
main() {
    local do_rebuild=false
    local build_deb_flag=false
    local build_rpm_flag=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --deb)
                build_deb_flag=true
                shift
                ;;
            --rpm)
                build_rpm_flag=true
                shift
                ;;
            --all)
                build_deb_flag=true
                build_rpm_flag=true
                shift
                ;;
            --clean)
                clean_build
                exit 0
                ;;
            --rebuild)
                do_rebuild=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            --version|-v)
                echo "Nextalk Package Builder v${VERSION}"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                echo "Use --help for usage information."
                exit 1
                ;;
        esac
    done

    # Default to --deb if no format specified
    if [[ "$build_deb_flag" == "false" ]] && [[ "$build_rpm_flag" == "false" ]]; then
        build_deb_flag=true
    fi

    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  Nextalk Package Builder v${VERSION}"
    echo "═══════════════════════════════════════════════════════════"
    echo ""

    # Check common dependencies
    check_common_dependencies
    echo ""

    # Check format-specific dependencies
    if [[ "$build_deb_flag" == "true" ]]; then
        if ! check_deb_dependencies; then
            build_deb_flag=false
            warn "Skipping DEB build due to missing dependencies"
        fi
        echo ""
    fi

    if [[ "$build_rpm_flag" == "true" ]]; then
        if ! check_rpm_dependencies; then
            build_rpm_flag=false
            warn "Skipping RPM build due to missing dependencies"
        fi
        echo ""
    fi

    # Exit if no builds are possible
    if [[ "$build_deb_flag" == "false" ]] && [[ "$build_rpm_flag" == "false" ]]; then
        error "No packages can be built. Please install required dependencies."
        exit 1
    fi

    # Extract version
    extract_version
    echo ""

    # Build components
    local flutter_bundle="$VOICE_CAPSULE_DIR/build/linux/x64/release/bundle/voice_capsule"
    local plugin_so="$ADDON_DIR/build/nextalk.so"

    if [[ "$do_rebuild" == "true" ]] || [[ ! -f "$flutter_bundle" ]]; then
        build_flutter
    else
        success "Flutter build exists, skipping (use --rebuild to force)"
    fi
    echo ""

    if [[ "$do_rebuild" == "true" ]] || [[ ! -f "$plugin_so" ]]; then
        build_fcitx5_plugin
    else
        success "Plugin build exists, skipping (use --rebuild to force)"
    fi
    echo ""

    # Build packages
    if [[ "$build_deb_flag" == "true" ]]; then
        build_deb
        echo ""
    fi

    if [[ "$build_rpm_flag" == "true" ]]; then
        build_rpm
        echo ""
    fi

    show_summary
}

main "$@"
