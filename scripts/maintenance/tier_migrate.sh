#!/bin/bash
# tier_migrate.sh - Migrate matches between storage tiers
# Part of the indie-game-match-history-database project

set -euo pipefail

# Script metadata
VERSION="1.1.0"
SCRIPT_NAME="$(basename "$0")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Help
show_help() {
    cat << EOF
Tier Migration Script v${VERSION}

Migrate matches between hot/warm/cold storage tiers based on retention policy.

Usage: $0 [OPTIONS]

Options:
    --help              Show this help message
    --version           Show version information
    --dry-run           Show what would be done without doing it
    --force             Force migration even if checks fail
    --verbose           Enable verbose output

Environment Variables:
    INDIE_MATCH_DATABASE_PATH    Path to SQLite database
    INDIE_MATCH_LOG_ROOT         Path to log directory

EOF
}

# Parse arguments
DRY_RUN=false
FORCE=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            show_help
            exit 0
            ;;
        --version)
            echo "Tier migration script v${VERSION}"
            exit 0
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Load environment
load_env() {
    # Try to load .env file
    local env_file
    env_file="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/.env"
    if [[ -f "${env_file}" ]]; then
        # shellcheck source=/dev/null
        source "${env_file}"
    fi

    # Set defaults
    DATABASE_PATH="${INDIE_MATCH_DATABASE_PATH:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/data/matches.db}"
    LOG_ROOT="${INDIE_MATCH_LOG_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/logs}"

    # Create log directory if needed
    mkdir -p "${LOG_ROOT}"

    log "Database: ${DATABASE_PATH}"
    log "Log directory: ${LOG_ROOT}"
}

# Check database exists
check_database() {
    if [[ ! -f "${DATABASE_PATH}" ]]; then
        log_error "Database not found: ${DATABASE_PATH}"
        return 1
    fi
    log "Database found"
}

# Get tier counts
get_tier_counts() {
    local hot warm cold

    hot=$(sqlite3 "${DATABASE_PATH}" "SELECT COUNT(*) FROM matches WHERE tier='hot';" 2>/dev/null || echo "0")
    warm=$(sqlite3 "${DATABASE_PATH}" "SELECT COUNT(*) FROM matches WHERE tier='warm';" 2>/dev/null || echo "0")
    cold=$(sqlite3 "${DATABASE_PATH}" "SELECT COUNT(*) FROM matches WHERE tier='cold';" 2>/dev/null || echo "0")

    log "Current tier distribution:"
    log "  Hot:   ${hot}"
    log "  Warm:  ${warm}"
    log "  Cold:  ${cold}"
}

# Migrate hot to warm
migrate_hot_to_warm() {
    local cutoff_date
    cutoff_date=$(date -d "30 days ago" +%Y-%m-%d 2>/dev/null || date -v-30d +%Y-%m-%d)

    log "Migrating matches older than ${cutoff_date} from hot to warm..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        local count
        count=$(sqlite3 "${DATABASE_PATH}" "SELECT COUNT(*) FROM matches WHERE tier='hot' AND played_at < '${cutoff_date}';")
        log "Would migrate ${count} matches from hot to warm"
        return 0
    fi

    local migrated
    migrated=$(sqlite3 "${DATABASE_PATH}" "UPDATE matches SET tier='warm' WHERE tier='hot' AND played_at < '${cutoff_date}"; SELECT changes();")

    log_success "Migrated ${migrated} matches from hot to warm"
}

# Migrate warm to cold
migrate_warm_to_cold() {
    local cutoff_date
    cutoff_date=$(date -d "180 days ago" +%Y-%m-%d 2>/dev/null || date -v-180d +%Y-%m-%d)

    log "Migrating matches older than ${cutoff_date} from warm to cold..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        local count
        count=$(sqlite3 "${DATABASE_PATH}" "SELECT COUNT(*) FROM matches WHERE tier='warm' AND played_at < '${cutoff_date}';")
        log "Would migrate ${count} matches from warm to cold"
        return 0
    fi

    local migrated
    migrated=$(sqlite3 "${DATABASE_PATH}" "UPDATE matches SET tier='cold' WHERE tier='warm' AND played_at < '${cutoff_date}'; SELECT changes();")

    log_success "Migrated ${migrated} matches from warm to cold"
}

# Delete expired cold data
delete_expired_cold() {
    local cutoff_date
    cutoff_date=$(date -d "730 days ago" +%Y-%m-%d 2>/dev/null || date -v-730d +%Y-%m-%d)

    log "Deleting matches older than ${cutoff_date} from cold storage..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        local count
        count=$(sqlite3 "${DATABASE_PATH}" "SELECT COUNT(*) FROM matches WHERE tier='cold' AND played_at < '${cutoff_date}';")
        log "Would delete ${count} expired matches from cold"
        return 0
    fi

    local deleted
    deleted=$(sqlite3 "${DATABASE_PATH}" "DELETE FROM matches WHERE tier='cold' AND played_at < '${cutoff_date}'; SELECT changes();")

    log_success "Deleted ${deleted} expired matches from cold"
}

# Log migration results
log_results() {
    local log_file="${LOG_ROOT}/tier_migrate.log"

    {
        echo "=== Tier Migration Run: $(date -Iseconds) ==="
        echo "Hot→Warm: ${migrated_hot_to_warm:-0}"
        echo "Warm→Cold: ${migrated_warm_to_cold:-0}"
        echo "Cold Deleted: ${deleted_expired:-0}"
        echo ""
    } >> "${log_file}"

    log "Results logged to ${log_file}"
}

# Main migration flow
main() {
    log "Starting tier migration..."

    load_env
    check_database

    log ""
    get_tier_counts
    log ""

    # Migrate hot to warm
    migrate_hot_to_warm
    migrated_hot_to_warm="${?}"

    # Migrate warm to cold
    migrate_warm_to_cold
    migrated_warm_to_cold="${?}"

    # Delete expired cold data
    delete_expired_cold
    deleted_expired="${?}"

    # Show final distribution
    log ""
    log "Final tier distribution:"
    get_tier_counts

    # Log results
    log_results

    log_success "Tier migration complete"
}

# Run main
main "$@"
