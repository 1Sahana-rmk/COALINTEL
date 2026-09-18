"""
COALINTEL Official Government Mine Master Operational Seeding Runner
Phase 11C Seeder Hardening: Dedicated One-Shot Execution Entry Point

Safety Guarantees:
1. Explicit CLI invocation only (no execution on import).
2. Authoritative Government of India dataset only (Zero demo/synthetic records).
3. 100% Isolated from RAG pipeline (Zero writes to Documents, ExtractedMetrics, or ChromaDB).
4. Strictly Idempotent: safe to run multiple times without duplicating entities.
5. Emits canonical IngestionRun (GOV-RUN-CANONICAL-MASTER-2024-25).
6. Returns exit code 0 on success and exit code 1 on failure with full diagnostics.
"""

import os
import sys
import json
import logging

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import SessionLocal
from data.government_mine_data_seed import run_government_data_ingestion

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SEEDER-CLI-RUNNER")


def main():
    print("=" * 80)
    print("COALINTEL CANONICAL GOVERNMENT MINE DATA INGESTION")
    print("Run ID: GOV-RUN-CANONICAL-MASTER-2024-25")
    print("=" * 80)

    db = SessionLocal()
    try:
        result = run_government_data_ingestion(db=db)
        print("\n" + "=" * 80)
        print("SEEDING EXECUTION SUMMARY:")
        print("=" * 80)
        print(json.dumps(result, indent=2))
        print("=" * 80)
        print("STATUS: SUCCESS")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Seeding operation failed: {e}", exc_info=True)
        print(f"\nFATAL: Government mine master seeding failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
