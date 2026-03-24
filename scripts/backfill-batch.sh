#!/bin/bash
# Backfill Batch Pipeline
# Runs bronze -> silver -> gold for a date range

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    echo "Usage: $0 <start_date> <end_date> [options]"
    echo ""
    echo "Arguments:"
    echo "  start_date    Start date (YYYY-MM-DD)"
    echo "  end_date      End date (YYYY-MM-DD)"
    echo ""
    echo "Options:"
    echo "  --skip-bronze     Skip bronze extraction"
    echo "  --skip-silver     Skip silver transformation"
    echo "  --skip-gold       Skip gold aggregation"
    echo "  --dry-run         Show what would be done"
    echo "  --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 2024-01-01 2024-01-31"
    echo "  $0 2024-01-01 2024-01-31 --skip-bronze"
    exit 1
}

SKIP_BRONZE=false
SKIP_SILVER=false
SKIP_GOLD=false
DRY_RUN=false

# Parse date arguments first
POSITIONAL_ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-bronze) SKIP_BRONZE=true; shift ;;
        --skip-silver) SKIP_SILVER=true; shift ;;
        --skip-gold) SKIP_GOLD=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --help) usage ;;
        -*) echo "Unknown option: $1"; usage ;;
        *) POSITIONAL_ARGS+=("$1"); shift ;;
    esac
done

set -- "${POSITIONAL_ARGS[@]}"

START_DATE="${1:-}"
END_DATE="${2:-}"

if [[ -z "$START_DATE" ]] || [[ -z "$END_DATE" ]]; then
    usage
fi

echo "=========================================="
echo "Clickstream Batch Backfill"
echo "=========================================="
echo "Start Date: $START_DATE"
echo "End Date:   $END_DATE"
echo "------------------------------------------"
echo "Bronze:  $([ "$SKIP_BRONZE" = true ] && echo "SKIP" || echo "RUN")"
echo "Silver:  $([ "$SKIP_SILVER" = true ] && echo "SKIP" || echo "RUN")"
echo "Gold:    $([ "$SKIP_GOLD" = true ] && echo "SKIP" || echo "RUN")"
echo "Dry Run: $([ "$DRY_RUN" = true ] && echo "YES" || echo "NO")"
echo "=========================================="

if [[ "$DRY_RUN" = true ]]; then
    echo ""
    echo "[DRY RUN] Would execute:"
    [[ "$SKIP_BRONZE" = false ]] && echo "  spark-submit bronze_clicks.py --start-date $START_DATE --end-date $END_DATE"
    [[ "$SKIP_SILVER" = false ]] && echo "  spark-submit silver_clicks.py --start-date $START_DATE --end-date $END_DATE"
    [[ "$SKIP_GOLD" = false ]] && echo "  For each date: spark-submit gold_metrics.py --date <date>"
    echo ""
    echo "Dry run complete."
    exit 0
fi

FAILED=0

echo ""
echo "Starting backfill..."

if [[ "$SKIP_BRONZE" = false ]]; then
    echo ""
    echo ">>> Step 1: Bronze Extraction"
    echo ">>> spark-submit bronze_clicks.py --start-date $START_DATE --end-date $END_DATE"
    docker compose exec spark-master spark-submit \
        --packages org.postgresql:postgresql:42.6.0 \
        /opt/spark/jobs/bronze_clicks.py \
        --start-date "$START_DATE" \
        --end-date "$END_DATE" \
        || { echo "Bronze extraction failed"; FAILED=1; }
else
    echo ""
    echo ">>> Step 1: Bronze Extraction - SKIPPED"
fi

if [[ "$SKIP_SILVER" = false ]] && [[ $FAILED -eq 0 ]]; then
    echo ""
    echo ">>> Step 2: Silver Transformation"
    echo ">>> spark-submit silver_clicks.py --start-date $START_DATE --end-date $END_DATE"
    docker compose exec spark-master spark-submit \
        /opt/spark/jobs/silver_clicks.py \
        --start-date "$START_DATE" \
        --end-date "$END_DATE" \
        || { echo "Silver transformation failed"; FAILED=1; }
else
    echo ""
    echo ">>> Step 2: Silver Transformation - SKIPPED"
fi

if [[ "$SKIP_GOLD" = false ]] && [[ $FAILED -eq 0 ]]; then
    echo ""
    echo ">>> Step 3: Gold Aggregation"
    
    CURRENT_DATE="$START_DATE"
    while [[ "$CURRENT_DATE" < "$END_DATE" ]]; do
        echo ">>> Processing: $CURRENT_DATE"
        docker compose exec spark-master spark-submit \
            /opt/spark/jobs/gold_metrics.py \
            --date "$CURRENT_DATE" \
            || { echo "Gold aggregation failed for $CURRENT_DATE"; FAILED=1; }
        
        # Increment date by 1 day (macOS compatible)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            CURRENT_DATE=$(date -j -f "%Y-%m-%d" -v+1d "$CURRENT_DATE" +"%Y-%m-%d")
        else
            CURRENT_DATE=$(date -d "$CURRENT_DATE + 1 day" +"%Y-%m-%d")
        fi
    done
    echo ">>> Gold Aggregation Complete"
else
    echo ""
    echo ">>> Step 3: Gold Aggregation - SKIPPED"
fi

echo ""
echo "=========================================="
if [[ $FAILED -eq 0 ]]; then
    echo "Backfill Complete!"
else
    echo "Backfill Completed with Errors"
fi
echo "=========================================="

exit $FAILED
