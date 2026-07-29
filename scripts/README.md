# Scripts Directory

This directory contains automation scripts for the indie-game-match-history-database project.

## Structure

```
scripts/
├── setup/           # Initial setup and installation scripts
├── maintenance/     # Ongoing maintenance and health check scripts
├── ingestion/       # Data ingestion and import scripts
└── README.md        # This file
```

## Setup Scripts (`setup/`)

Scripts for initial project setup and environment configuration:

- `install.sh` / `install.ps1` - Install dependencies and set up environment
- `init_database.sh` - Initialize database with schema migrations
- `generate_env.sh` - Generate `.env` file with defaults
- `validate_setup.sh` - Validate that setup completed successfully

### Usage

```bash
# Linux/macOS
bash scripts/setup/install.sh

# Windows PowerShell
powershell -File scripts/setup/install.ps1

# Initialize database
bash scripts/setup/init_database.sh

# Validate setup
bash scripts/setup/validate_setup.sh
```

## Maintenance Scripts (`maintenance/`)

Scripts for ongoing system maintenance:

- `tier_migrate.sh` - Migrate matches between storage tiers
- `retention_cleanup.sh` - Delete expired matches per retention policy
- `privacy_check.sh` - Identify and process GDPR/COPPA requests
- `knowledge_crawl.sh` - Run knowledge crawl pipeline
- `health_check.sh` - Comprehensive system health check
- `backup_database.sh` - Create database backup
- `schema_migrate.sh` - Run pending schema migrations

### Usage

```bash
# Migrate matches between tiers
bash scripts/maintenance/tier_migrate.sh

# Clean up expired data
bash scripts/maintenance/retention_cleanup.sh

# Process privacy requests
bash scripts/maintenance/privacy_check.sh

# Run knowledge crawl
bash scripts/maintenance/knowledge_crawl.sh

# Health check
bash scripts/maintenance/health_check.sh
```

## Ingestion Scripts (`ingestion/`)

Scripts for importing and processing match data:

- `import_csv.sh` - Import matches from CSV files
- `import_json.sh` - Import matches from JSON files
- `bulk_import.sh` - Bulk import from directory
- `validate_import.sh` - Validate imported data
- `replay_upload.sh` - Upload replay blob files
- `replay_validate.sh` - Validate replay files

### Usage

```bash
# Import from CSV
bash scripts/ingestion/import_csv.sh data/matches.csv

# Bulk import from directory
bash scripts/ingestion/bulk_import.sh data/imports/

# Upload replay files
bash scripts/ingestion/replay_upload.sh data/replays/*.replay
```

## Environment Variables

All scripts respect these environment variables:

```bash
INDIE_MATCH_PROJECT_ROOT=/path/to/project
INDIE_MATCH_DATA_ROOT=/path/to/data
INDIE_MATCH_DATABASE_PATH=/path/to/matches.db
INDIE_MATCH_REPLAY_ROOT=/path/to/replays
INDIE_MATCH_LOG_ROOT=/path/to/logs
```

Or set via `.env` file:

```bash
# Generate .env with defaults
bash scripts/setup/generate_env.sh
```

## Common Tasks

### Initial Setup

```bash
# 1. Install dependencies
bash scripts/setup/install.sh

# 2. Generate .env file
bash scripts/setup/generate_env.sh

# 3. Initialize database
bash scripts/setup/init_database.sh

# 4. Validate setup
bash scripts/setup/validate_setup.sh
```

### Daily Maintenance

```bash
# Run as cron job daily
bash scripts/maintenance/tier_migrate.sh
bash scripts/maintenance/retention_cleanup.sh
bash scripts/maintenance/privacy_check.sh
```

### Weekly Tasks

```bash
# Knowledge crawl (Mondays)
bash scripts/maintenance/knowledge_crawl.sh

# Backup database (Sundays)
bash scripts/maintenance/backup_database.sh
```

### Data Import

```bash
# Single file import
bash scripts/ingestion/import_json.sh data/match_batch_001.json

# Bulk import
bash scripts/ingestion/bulk_import.sh data/imports/

# Upload replays
bash scripts/ingestion/replay_upload.sh data/replays/*.replay
```

## Logging

All scripts log to `$INDIE_MATCH_LOG_ROOT`:

```
logs/
├── setup.log              # Setup script output
├── maintenance.log        # Maintenance script output
├── ingestion.log          # Ingestion script output
├── tier_migrate.log       # Tier migration logs
├── knowledge_crawl.log    # Knowledge crawl logs
└── backup.log             # Backup logs
```

## Error Handling

Scripts follow these error handling conventions:

1. **Exit codes**: 0 = success, 1 = error, 2 = validation failure
2. **Logging**: Errors logged with full stack trace
3. **Rollback**: Destructive operations support rollback
4. **Dry-run**: All scripts support `--dry-run` flag

## Cron Schedule

Recommended cron jobs:

```cron
# Daily maintenance (2 AM)
0 2 * * * /path/to/scripts/maintenance/tier_migrate.sh
0 3 * * * /path/to/scripts/maintenance/retention_cleanup.sh
0 4 * * * /path/to/scripts/maintenance/privacy_check.sh

# Weekly knowledge crawl (Mondays 8 AM)
0 8 * * 1 /path/to/scripts/maintenance/knowledge_crawl.sh

# Weekly backup (Sundays 1 AM)
0 1 * * 0 /path/to/scripts/maintenance/backup_database.sh

# Health check (hourly)
0 * * * * /path/to/scripts/maintenance/health_check.sh
```

## Script Conventions

All scripts follow these conventions:

1. **Shebang**: Explicit bash/python/PowerShell
2. **Set options**: `set -euo pipefail` for bash
3. **Logging**: Structured JSON logging to log file
4. **Dry-run**: Support `--dry-run` flag
5. **Help**: Support `--help` flag
6. **Version**: Support `--version` flag
7. **Error handling**: Trap errors and exit cleanly

## Dependencies

Scripts require:

- **Bash 4.0+** (Linux/macOS) or **PowerShell 5.1+** (Windows)
- **Python 3.8+** (for Python scripts)
- **SQLite 3.35+** (for database scripts)
- **GNU coreutils** (Linux/macOS) or **Windows equivalents**

## Contributing

When adding new scripts:

1. Add to appropriate subdirectory
2. Follow script conventions
3. Add usage example to this README
4. Test on Linux/macOS/Windows if possible
5. Document exit codes and error conditions

## License

These scripts are part of the indie-game-match-history-database project and inherit its license (MIT).
