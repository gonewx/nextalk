#!/usr/bin/env bash
#
# verify-desktop-integration.sh - Nextalk Desktop Integration Verification
# Version: 1.0.0
#
# Verifies desktop entry, icon installation, and desktop integration
# for freedesktop.org compliance.
#
set -euo pipefail

# ==============================================================================
# Configuration
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Expected paths (installed locations)
DESKTOP_FILE="/usr/share/applications/nextalk.desktop"
ICON_256="/usr/share/icons/hicolor/256x256/apps/nextalk.png"
ICON_128="/usr/share/icons/hicolor/128x128/apps/nextalk.png"
ICON_48="/usr/share/icons/hicolor/48x48/apps/nextalk.png"
APP_BINARY="/opt/nextalk/nextalk"
SYMLINK_PATH="/usr/bin/nextalk"

# Source file path (for pre-installation validation)
SOURCE_DESKTOP="$PROJECT_ROOT/packaging/deb/nextalk.desktop"
SOURCE_ICON="$PROJECT_ROOT/voice_capsule/assets/icons/icon.png"

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
error()   { echo -e "${RED}[✗]${NC} $*"; }
header()  { echo -e "${CYAN}▶${NC} $*"; }

# Counters
PASSED=0
FAILED=0
WARNINGS=0

pass()    { PASSED=$((PASSED + 1)); success "$*"; }
fail()    { FAILED=$((FAILED + 1)); error "$*"; }
warning() { WARNINGS=$((WARNINGS + 1)); warn "$*"; }

# ==============================================================================
# Help Message
# ==============================================================================
show_help() {
    cat << EOF
Nextalk Desktop Integration Verification Script

Usage: $(basename "$0") [OPTIONS]

Options:
  --source      Validate source files only (pre-installation check)
  --installed   Validate installed files only (post-installation check)
  --all         Run all validations (default)
  --help        Show this help message

Examples:
  $(basename "$0")           # Run all validations
  $(basename "$0") --source  # Check source files before building
  $(basename "$0") --installed # Verify installation is correct

Exit Codes:
  0 - All checks passed
  1 - One or more checks failed
  2 - Warnings only (no failures)

EOF
}

# ==============================================================================
# Validation Functions
# ==============================================================================

# Check if a command exists
check_command() {
    local cmd="$1"
    if ! command -v "$cmd" &>/dev/null; then
        return 1
    fi
    return 0
}

# Validate desktop file using desktop-file-validate
validate_desktop_file() {
    local file="$1"
    local label="$2"

    header "Validating desktop file: $label"

    if [[ ! -f "$file" ]]; then
        fail "Desktop file not found: $file"
        echo ""
        return 0  # Continue to other validations
    fi

    pass "Desktop file exists: $file"

    # Check required fields
    local required_fields=("Type" "Name" "Exec" "Icon")
    for field in "${required_fields[@]}"; do
        if grep -q "^${field}=" "$file"; then
            pass "Required field present: $field"
        else
            fail "Missing required field: $field"
        fi
    done

    # Check Categories (recommended)
    if grep -q "^Categories=" "$file"; then
        local categories
        categories=$(grep "^Categories=" "$file" | cut -d= -f2)
        if [[ "$categories" == *"Utility"* ]] || [[ "$categories" == *"Accessibility"* ]]; then
            pass "Categories valid: $categories"
        else
            warning "Categories should include Utility or Accessibility: $categories"
        fi
    else
        warning "Missing recommended field: Categories"
    fi

    # Check StartupWMClass
    if grep -q "^StartupWMClass=" "$file"; then
        local wmclass
        wmclass=$(grep "^StartupWMClass=" "$file" | cut -d= -f2)
        pass "StartupWMClass defined: $wmclass"
    else
        warning "Missing StartupWMClass (recommended for window matching)"
    fi

    # Check Chinese localization
    if grep -q "^Name\[zh_CN\]=" "$file"; then
        pass "Chinese localization present: Name[zh_CN]"
    else
        warning "Missing Chinese localization: Name[zh_CN]"
    fi

    # Run desktop-file-validate if available
    if check_command "desktop-file-validate"; then
        info "Running desktop-file-validate..."
        local validate_output
        if validate_output=$(desktop-file-validate "$file" 2>&1); then
            pass "desktop-file-validate: PASSED"
        else
            if [[ -n "$validate_output" ]]; then
                fail "desktop-file-validate errors:"
                echo "$validate_output" | sed 's/^/    /'
            fi
        fi
    else
        warning "desktop-file-validate not installed (apt install desktop-file-utils)"
    fi

    echo ""
}

# Validate icon file
validate_icon() {
    local file="$1"
    local expected_size="$2"
    local label="$3"

    if [[ ! -f "$file" ]]; then
        fail "Icon not found: $file"
        return 0  # Continue to other validations
    fi

    pass "Icon exists: $file"

    # Check format with file command
    local file_type
    file_type=$(file "$file" 2>/dev/null)
    if [[ "$file_type" == *"PNG"* ]]; then
        pass "Icon format: PNG"
    else
        fail "Icon should be PNG format: $file_type"
    fi

    # Check dimensions with identify (ImageMagick)
    if check_command "identify"; then
        local dimensions
        dimensions=$(identify -format "%wx%h" "$file" 2>/dev/null || echo "unknown")
        if [[ "$dimensions" == "$expected_size" ]]; then
            pass "Icon dimensions: $dimensions"
        else
            fail "Icon dimensions mismatch: expected $expected_size, got $dimensions"
        fi
    else
        warning "ImageMagick not installed, cannot verify icon dimensions"
    fi
}

# Validate installed icons
validate_installed_icons() {
    header "Validating installed icons"

    # Check 256x256 (required)
    if [[ -f "$ICON_256" ]]; then
        validate_icon "$ICON_256" "256x256" "Primary icon"
    else
        fail "Primary icon (256x256) not found: $ICON_256"
    fi

    # Check 128x128 (optional but recommended)
    if [[ -f "$ICON_128" ]]; then
        validate_icon "$ICON_128" "128x128" "Medium icon"
    else
        info "Optional 128x128 icon not installed"
    fi

    # Check 48x48 (optional but recommended)
    if [[ -f "$ICON_48" ]]; then
        validate_icon "$ICON_48" "48x48" "Small icon"
    else
        info "Optional 48x48 icon not installed"
    fi

    echo ""
}

# Validate source icon
validate_source_icon() {
    header "Validating source icon"

    if [[ ! -f "$SOURCE_ICON" ]]; then
        fail "Source icon not found: $SOURCE_ICON"
        echo ""
        return 0  # Continue to other validations
    fi

    pass "Source icon exists: $SOURCE_ICON"

    if check_command "identify"; then
        local dimensions
        dimensions=$(identify -format "%wx%h" "$SOURCE_ICON" 2>/dev/null || echo "unknown")
        local width height
        width=$(echo "$dimensions" | cut -dx -f1)
        height=$(echo "$dimensions" | cut -dx -f2)

        if [[ "$width" -ge 256 ]] && [[ "$height" -ge 256 ]]; then
            pass "Source icon size adequate: ${dimensions} (>= 256x256)"
        else
            fail "Source icon too small: $dimensions (need >= 256x256)"
        fi
    fi

    echo ""
}

# Validate application binary and symlink
validate_app_installation() {
    header "Validating application installation"

    # Check binary
    if [[ -f "$APP_BINARY" ]]; then
        pass "Application binary exists: $APP_BINARY"
        if [[ -x "$APP_BINARY" ]]; then
            pass "Application binary is executable"
        else
            fail "Application binary is not executable"
        fi
    else
        fail "Application binary not found: $APP_BINARY"
    fi

    # Check symlink
    if [[ -L "$SYMLINK_PATH" ]]; then
        local target
        target=$(readlink "$SYMLINK_PATH")
        if [[ "$target" == "$APP_BINARY" ]] || [[ "$target" == "/opt/nextalk/nextalk" ]]; then
            pass "Symlink correct: $SYMLINK_PATH -> $target"
        else
            warning "Symlink target unexpected: $SYMLINK_PATH -> $target"
        fi
    elif [[ -f "$SYMLINK_PATH" ]]; then
        warning "Expected symlink but found regular file: $SYMLINK_PATH"
    else
        fail "Application symlink not found: $SYMLINK_PATH"
    fi

    echo ""
}

# Check icon cache status
check_icon_cache() {
    header "Checking icon cache"

    local icon_cache="/usr/share/icons/hicolor/icon-theme.cache"
    if [[ -f "$icon_cache" ]]; then
        local cache_time icon_time
        cache_time=$(stat -c %Y "$icon_cache" 2>/dev/null || echo 0)

        if [[ -f "$ICON_256" ]]; then
            icon_time=$(stat -c %Y "$ICON_256" 2>/dev/null || echo 0)
            if [[ "$cache_time" -ge "$icon_time" ]]; then
                pass "Icon cache is up-to-date"
            else
                warning "Icon cache may be outdated (run: sudo gtk-update-icon-cache /usr/share/icons/hicolor)"
            fi
        fi
    else
        info "Icon cache not found (may be managed by desktop environment)"
    fi

    echo ""
}

# Check desktop database status
check_desktop_database() {
    header "Checking desktop database"

    local mimeinfo="/usr/share/applications/mimeinfo.cache"
    if [[ -f "$mimeinfo" ]]; then
        if grep -q "nextalk" "$mimeinfo" 2>/dev/null; then
            pass "Application registered in mimeinfo.cache"
        else
            info "Application not in mimeinfo.cache (may not have MIME associations)"
        fi
    else
        info "mimeinfo.cache not found"
    fi

    echo ""
}

# ==============================================================================
# Main Validation Functions
# ==============================================================================

validate_source() {
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  Source Files Validation (Pre-Installation)"
    echo "═══════════════════════════════════════════════════════════"
    echo ""

    validate_desktop_file "$SOURCE_DESKTOP" "Source desktop file"
    validate_source_icon
}

validate_installed() {
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  Installed Files Validation (Post-Installation)"
    echo "═══════════════════════════════════════════════════════════"
    echo ""

    validate_desktop_file "$DESKTOP_FILE" "Installed desktop file"
    validate_installed_icons
    validate_app_installation
    check_icon_cache
    check_desktop_database
}

# ==============================================================================
# Summary
# ==============================================================================

show_summary() {
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  Validation Summary"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo -e "  ${GREEN}Passed:${NC}   $PASSED"
    echo -e "  ${YELLOW}Warnings:${NC} $WARNINGS"
    echo -e "  ${RED}Failed:${NC}   $FAILED"
    echo ""

    if [[ $FAILED -gt 0 ]]; then
        echo -e "${RED}⚠ Validation FAILED - $FAILED issue(s) need attention${NC}"
        return 1
    elif [[ $WARNINGS -gt 0 ]]; then
        echo -e "${YELLOW}⚡ Validation passed with $WARNINGS warning(s)${NC}"
        return 2
    else
        echo -e "${GREEN}✓ All validations PASSED${NC}"
        return 0
    fi
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    local mode="all"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --source)
                mode="source"
                shift
                ;;
            --installed)
                mode="installed"
                shift
                ;;
            --all)
                mode="all"
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                echo "Use --help for usage information."
                exit 1
                ;;
        esac
    done

    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  Nextalk Desktop Integration Verification"
    echo "═══════════════════════════════════════════════════════════"

    case "$mode" in
        source)
            validate_source
            ;;
        installed)
            validate_installed
            ;;
        all)
            validate_source
            validate_installed
            ;;
    esac

    show_summary
    local exit_code=$?
    exit $exit_code
}

main "$@"

