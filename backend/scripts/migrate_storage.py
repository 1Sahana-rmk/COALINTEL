"""
COALINTEL — Storage Migration & Reconciliation CLI Tool

Usage:
  # Diagnostic reconciliation across all documents & reports:
  python backend/scripts/migrate_storage.py --reconcile

  # Dry-run migration of documents:
  python backend/scripts/migrate_storage.py --documents --dry-run

  # Dry-run migration of reports:
  python backend/scripts/migrate_storage.py --reports --dry-run

  # Migrate single document by ID:
  python backend/scripts/migrate_storage.py --document-id 42

  # Migrate single report by ID:
  python backend/scripts/migrate_storage.py --report-id 10

  # Live migration of all documents:
  python backend/scripts/migrate_storage.py --documents --live

  # Live migration of all reports:
  python backend/scripts/migrate_storage.py --reports --live
"""

import sys
import os
import argparse
import logging
import json

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import SessionLocal
from app.services.storage_migration_service import (
    migrate_document,
    migrate_report,
    migrate_all_documents,
    migrate_all_reports,
    reconcile_document,
    reconcile_report,
    reconcile_all,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("storage_migration_cli")


def main():
    parser = argparse.ArgumentParser(description="COALINTEL Storage Migration and Reconciliation CLI")
    parser.add_argument("--documents", action="store_true", help="Target all documents for migration")
    parser.add_argument("--reports", action="store_true", help="Target all reports for migration")
    parser.add_argument("--all", action="store_true", help="Target both documents and reports")
    parser.add_argument("--document-id", type=int, default=None, help="Target specific document ID")
    parser.add_argument("--report-id", type=int, default=None, help="Target specific report ID")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Perform dry-run without making changes (default)")
    parser.add_argument("--live", action="store_true", help="Execute LIVE migration (disables dry-run)")
    parser.add_argument("--reconcile", action="store_true", help="Perform diagnostic reconciliation without modifying storage or DB")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of records to process")
    parser.add_argument("--subsidiary", type=str, default=None, help="Filter by subsidiary (e.g. ECL, BCCL, SECL)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    is_dry_run = not args.live

    db = SessionLocal()
    try:
        if args.reconcile:
            logger.info("Starting diagnostic reconciliation...")
            if args.document_id:
                res = reconcile_document(db=db, document_id=args.document_id)
                if args.json:
                    print(json.dumps(res.to_dict(), indent=2))
                else:
                    print(f"\nDocument #{res.resource_id} Reconciliation: {res.status.value} — {res.message}")
            elif args.report_id:
                res = reconcile_report(db=db, report_id=args.report_id)
                if args.json:
                    print(json.dumps(res.to_dict(), indent=2))
                else:
                    print(f"\nReport #{res.resource_id} Reconciliation: {res.status.value} — {res.message}")
            else:
                summary = reconcile_all(db=db, limit=args.limit)
                if args.json:
                    print(json.dumps(summary.to_dict(), indent=2))
                else:
                    print("\n=======================================================")
                    print("RECONCILIATION SUMMARY")
                    print("=======================================================")
                    print(f"Total Inspected:     {summary.total_inspected}")
                    print(f"Healthy Local:       {summary.healthy_local}")
                    print(f"Healthy Supabase:    {summary.healthy_supabase}")
                    print(f"Missing Local:       {summary.missing_local}")
                    print(f"Missing Supabase:    {summary.missing_supabase}")
                    print(f"Integrity Mismatch:  {summary.integrity_mismatch}")
                    print(f"Invalid Reference:   {summary.invalid_reference}")
                    print(f"Errors:              {summary.errors}")
                    print("=======================================================\n")
            return

        # Migration mode
        mode_str = "DRY-RUN" if is_dry_run else "LIVE"
        logger.info(f"Starting Storage Migration in [{mode_str}] mode...")

        if args.document_id:
            res = migrate_document(db=db, document_id=args.document_id, dry_run=is_dry_run)
            if args.json:
                print(json.dumps(res.to_dict(), indent=2))
            else:
                print(f"\nDocument #{res.resource_id}: {res.status.value} — {res.message}")
            return

        if args.report_id:
            res = migrate_report(db=db, report_id=args.report_id, dry_run=is_dry_run)
            if args.json:
                print(json.dumps(res.to_dict(), indent=2))
            else:
                print(f"\nReport #{res.resource_id}: {res.status.value} — {res.message}")
            return

        if args.documents or args.all:
            logger.info("Migrating documents...")
            doc_summary = migrate_all_documents(
                db=db,
                dry_run=is_dry_run,
                limit=args.limit,
                subsidiary=args.subsidiary
            )
            if args.json:
                print(json.dumps(doc_summary.to_dict(), indent=2))
            else:
                print("\n=======================================================")
                print(f"DOCUMENT MIGRATION SUMMARY [{mode_str}]")
                print("=======================================================")
                print(f"Total Inspected:     {doc_summary.total_inspected}")
                print(f"Migrated:            {doc_summary.migrated}")
                print(f"Already Migrated:    {doc_summary.already_migrated}")
                print(f"Dry-Run Eligible:    {doc_summary.dry_run_eligible}")
                print(f"Missing Source:      {doc_summary.missing_source}")
                print(f"Integrity Mismatch:  {doc_summary.integrity_mismatch}")
                print(f"Failed / Errors:     {doc_summary.failed}")
                print("=======================================================\n")

        if args.reports or args.all:
            logger.info("Migrating reports...")
            rep_summary = migrate_all_reports(
                db=db,
                dry_run=is_dry_run,
                limit=args.limit,
                subsidiary=args.subsidiary
            )
            if args.json:
                print(json.dumps(rep_summary.to_dict(), indent=2))
            else:
                print("\n=======================================================")
                print(f"REPORT MIGRATION SUMMARY [{mode_str}]")
                print("=======================================================")
                print(f"Total Inspected:     {rep_summary.total_inspected}")
                print(f"Migrated:            {rep_summary.migrated}")
                print(f"Already Migrated:    {rep_summary.already_migrated}")
                print(f"Dry-Run Eligible:    {rep_summary.dry_run_eligible}")
                print(f"Missing Source:      {rep_summary.missing_source}")
                print(f"Integrity Mismatch:  {rep_summary.integrity_mismatch}")
                print(f"Failed / Errors:     {rep_summary.failed}")
                print("=======================================================\n")

        if not (args.documents or args.reports or args.all or args.document_id or args.report_id):
            print("No operation specified. Use --reconcile, --documents, --reports, --document-id, or --report-id. Run with -h for help.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
