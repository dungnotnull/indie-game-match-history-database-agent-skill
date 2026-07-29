#!/bin/bash
# install.sh - Install dependencies and set up environment
# Part of the indie-game-match-history-database project

set -euo pipefail

# Script metadata
VERSION="1.1.0"
SCRIPT_NAME="$(basename "$0")"
PROJECT_NAME="indie-game-match-history-database"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
log() {
    echo -e "${BLUE}[${SCRIPT_NAME}]${NC} $*"
}

log_error() {
    echo -e "${RED}[${SCRIPT_NAME}] ERROR:${NC} $*" >&2
}

log_success() {
    echo -e "${GREEN}[${SCRIPT_NAME}] SUCCESS:${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[${SCRIPT_NAME}] WARNING:${NC} $*"
}

# Help message
show_help() {
    cat << EOF
${PROJECT_NAME} Installation Script v${VERSION}

Usage: $0 [OPTIONS]

Options:
    --help              Show this help message
    --version           Show version information
    --dry-run           Show what would be done without doing it
    --dev               Install development dependencies
    --skip-python       Skip Python environment setup
    --skip-data         Skip data directory creation
    --python-version    Python version to use (default: 3.8+)

Environment Variables:
    INDIE_MATCH_PROJECT_ROOT    Project root directory
    INDIE_MATCH_DATA_ROOT        Data directory
    INDIE_MATCH_VENV_PATH       Virtual environment path

EOF
}

# Parse arguments
DRY_RUN=false
DEV_MODE=false
SKIP_PYTHON=false
SKIP_DATA=false
PYTHON_VERSION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            show_help
            exit 0
            ;;
        --version)
            echo "${PROJECT_NAME} installation script v${VERSION}"
            exit 0
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --dev)
            DEV_MODE=true
            shift
            ;;
        --skip-python)
            SKIP_PYTHON=true
            shift
            ;;
        --skip-data)
            SKIP_DATA=true
            shift
            ;;
        --python-version)
            PYTHON_VERSION="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Determine paths
PROJECT_ROOT="${INDIE_MATCH_PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
DATA_ROOT="${INDIE_MATCH_DATA_ROOT:-${PROJECT_ROOT}/data"
VENV_PATH="${INDIE_MATCH_VENV_PATH:-${PROJECT_ROOT}/.venv"

log "Project root: ${PROJECT_ROOT}"
log "Data directory: ${DATA_ROOT}"
log "Virtual environment: ${VENV_PATH}"

# Check Python
check_python() {
    if [[ "${SKIP_PYTHON}" == "true" ]]; then
        log "Skipping Python environment setup"
        return 0
    fi

    local python_cmd="python3"
    if [[ -n "${PYTHON_VERSION}" ]]; then
        python_cmd="python${PYTHON_VERSION}"
    fi

    if ! command -v "${python_cmd}" &> /dev/null; then
        log_error "Python not found: ${python_cmd}"
        log "Install Python 3.8+ and try again"
        return 1
    fi

    local python_version
    python_version=$("${python_cmd}" --version | awk '{print $2}')
    log "Found Python: ${python_version} (${python_cmd})"

    # Check version >= 3.8
    local major minor
    major=$(echo "${python_version}" | cut -d. -f1)
    minor=$(echo "${python_version}" | cut -d. -f2)

    if [[ "${major}" -lt 3 ]] || [[ "${major}" -eq 3 && "${minor}" -lt 8 ]]; then
        log_error "Python 3.8+ required, found ${python_version}"
        return 1
    fi

    log_success "Python version OK"
}

# Create virtual environment
create_venv() {
    if [[ "${SKIP_PYTHON}" == "true" ]]; then
        log "Skipping virtual environment creation"
        return 0
    fi

    log "Creating virtual environment..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        log "Would create: ${VENV_PATH}"
        return 0
    fi

    if [[ -d "${VENV_PATH}" ]]; then
        log "Virtual environment already exists: ${VENV_PATH}"
        return 0
    fi

    "${python_cmd}" -m venv "${VENV_PATH}"

    if [[ ! -f "${VENV_PATH}/bin/activate" ]]; then
        log_error "Failed to create virtual environment"
        return 1
    fi

    log_success "Virtual environment created"
}

# Install dependencies
install_dependencies() {
    if [[ "${SKIP_PYTHON}" == "true" ]]; then
        log "Skipping dependency installation"
        return 0
    fi

    log "Installing dependencies..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        log "Would install dependencies from requirements.txt"
        return 0
    fi

    # Activate virtual environment
    # shellcheck source=/dev/null
    source "${VENV_PATH}/bin/activate"

    # Upgrade pip
    log "Upgrading pip..."
    pip install --upgrade pip setuptools wheel

    # Install base requirements
    if [[ -f "${PROJECT_ROOT}/requirements.txt" ]]; then
        log "Installing from requirements.txt..."
        pip install -r "${PROJECT_ROOT}/requirements.txt"
    else
        log_warning "requirements.txt not found, skipping"
    fi

    # Install development dependencies if --dev
    if [[ "${DEV_MODE}" == "true" ]]; then
        log "Installing development dependencies..."
        if [[ -f "${PROJECT_ROOT}/requirements-dev.txt" ]]; then
            pip install -r "${PROJECT_ROOT}/requirements-dev.txt"
        else
            pip install pytest pytest-cov black mypy flake8
        fi
    fi

    log_success "Dependencies installed"
}

# Create data directories
create_data_dirs() {
    if [[ "${SKIP_DATA}" == "true" ]]; then
        log "Skipping data directory creation"
        return 0
    fi

    log "Creating data directories..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        log "Would create directories in ${DATA_ROOT}"
        return 0
    fi

    mkdir -p "${DATA_ROOT}/matches"
    mkdir -p "${DATA_ROOT}/replays"
    mkdir -p "${DATA_ROOT}/exports"

    log_success "Data directories created"
}

# Generate .env file
generate_env() {
    log "Generating .env file..."

    local env_file="${PROJECT_ROOT}/.env"

    if [[ "${DRY_RUN}" == "true" ]]; then
        log "Would generate: ${env_file}"
        return 0
    fi

    if [[ -f "${env_file}" ]]; then
        log_warning ".env file already exists, skipping"
        return 0
    fi

    cat > "${env_file}" << EOF
# indie-game-match-history-database environment configuration
# Generated: $(date -Iseconds)

# Project paths
INDIE_MATCH_PROJECT_ROOT=${PROJECT_ROOT}
INDIE_MATCH_DATA_ROOT=${DATA_ROOT}
INDIE_MATCH_DATABASE_PATH=${DATA_ROOT}/matches.db
INDIE_MATCH_REPLAY_ROOT=${DATA_ROOT}/replays
INDIE_MATCH_LOG_ROOT=${PROJECT_ROOT}/logs
INDIE_MATCH_KNOWLEDGE_PATH=${PROJECT_ROOT}/SECOND-KNOWLEDGE-BRAIN.md

# LLM configuration
INDIE_MATCH_LLM_PROVIDER=anthropic
INDIE_MATCH_LLM_MODEL=claude-sonnet-4-6
INDIE_MATCH_LLM_TEMPERATURE=0.7
INDIE_MATCH_LLM_MAX_TOKENS=8192

# Logging
INDIE_MATCH_LOG_LEVEL=INFO
INDIE_MATCH_LOG_FORMAT=json
INDIE_MATCH_LOG_CONSOLE=true

# Features
INDIE_MATCH_ENABLE_TIERED_STORAGE=true
INDIE_MATCH_ENABLE_REPLAY_COMPRESSION=true
INDIE_MATCH_ENABLE_GDPR_PIPELINE=true
INDIE_MATCH_ENABLE_COPPA_COMPLIANCE=true

# Knowledge crawl
INDIE_MATCH_ENABLE_CRAWL=true
INDIE_MATCH_CRAWL_INTERVAL_HOURS=24

# Environment
INDIE_MATCH_ENVIRONMENT=development
EOF

    log_success ".env file generated"
}

# Verify installation
verify_installation() {
    log "Verifying installation..."

    local checks_failed=0

    # Check virtual environment
    if [[ "${SKIP_PYTHON}" == "false" ]]; then
        if [[ ! -d "${VENV_PATH}" ]]; then
            log_error "Virtual environment not found"
            ((checks_failed++))
        elif [[ ! -f "${VENV_PATH}/bin/python" ]]; then
            log_error "Python not found in virtual environment"
            ((checks_failed++))
        else
            log "✓ Virtual environment OK"
        fi
    fi

    # Check data directories
    if [[ "${SKIP_DATA}" == "false" ]]; then
        if [[ ! -d "${DATA_ROOT}" ]]; then
            log_error "Data directory not found"
            ((checks_failed++))
        else
            log "✓ Data directory OK"
        fi
    fi

    # Check .env file
    if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
        log_error ".env file not found"
        ((checks_failed++))
    else
        log "✓ .env file OK"
    fi

    if [[ ${checks_failed} -gt 0 ]]; then
        log_error "Verification failed with ${checks_failed} error(s)"
        return 1
    fi

    log_success "Installation verified"
}

# Main installation flow
main() {
    log "Starting installation for ${PROJECT_NAME} v${VERSION}"
    log ""

    check_python
    create_venv
    install_dependencies
    create_data_dirs
    generate_env
    verify_installation

    log ""
    log_success "Installation complete!"
    log ""
    log "Next steps:"
    log "  1. Review .env file and adjust settings"
    log "  2. Initialize database: bash scripts/setup/init_database.sh"
    log "  3. Run tests: pytest"
    log "  4. Start the engine: python -m indie_match_history.cli"
}

# Run main
main "$@"
