import os
import logging
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base
from config import settings
from app.models import User, Document, ExtractedMetric, DocumentChunk, DataConflict, Report, AuditLog
from app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("COALINTEL-SEED")


def ensure_sample_documents_exist():
    """Generates physical sample document files on disk if not present in storage/uploads."""
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)

    # 1. ECL_Annual_Report_2023-24.pdf
    ecl_path = os.path.join(upload_dir, "ECL_Annual_Report_2023-24.pdf")
    if not os.path.exists(ecl_path):
        try:
            import fitz
            doc = fitz.open()
            for p in range(1, 14):
                page = doc.new_page()
                page.insert_text((50, 50), f"Eastern Coalfields Limited (ECL) Annual Report FY 2023-24 - Section {p}\nOverview and operational highlights.")
            
            p14 = doc.new_page()  # Page 14
            p14.insert_text(
                (50, 50),
                "Eastern Coalfields Limited (ECL) Annual Report FY 2023-24.\n"
                "Total coal production for ECL as a whole reached 42.50 Million Tonnes (MT) in FY 2023-24, representing a 4.2% YoY increase compared to 40.80 MT in FY 2022-23.\n"
                "Rajmahal OpenCast Mine recorded total coal production of 42.50 Lakh Tonnes (4.25 MT) for FY 2023-24, compared to 40.80 Lakh Tonnes in FY 2022-23."
            )
            
            for p in range(15, 22):
                page = doc.new_page()
                page.insert_text((50, 50), f"Eastern Coalfields Limited (ECL) Annual Report FY 2023-24 - Section {p}")

            p22 = doc.new_page()  # Page 22
            p22.insert_text(
                (50, 50),
                "Overburden removal at Rajmahal OC stood at 120.40 M.Cu.M against an annual plan of 120.00 M.Cu.M in FY 2023-24."
            )
            
            for p in range(23, 85):
                page = doc.new_page()
                page.insert_text((50, 50), f"Eastern Coalfields Limited (ECL) Annual Report FY 2023-24 - Appendix Page {p}")

            doc.save(ecl_path)
            doc.close()
            logger.info(f"Generated sample PDF document at '{ecl_path}'.")
        except Exception as e:
            logger.warning(f"Could not generate ECL sample PDF on disk: {e}")

    # 2. BCCL_Production_Audit_Q4.pdf
    bccl_path = os.path.join(upload_dir, "BCCL_Production_Audit_Q4.pdf")
    if not os.path.exists(bccl_path):
        try:
            import fitz
            doc = fitz.open()
            for p in range(1, 8):
                page = doc.new_page()
                page.insert_text((50, 50), f"Bharat Coking Coal Limited (BCCL) Production Audit Q4 FY 2023-24 - Page {p}")

            p8 = doc.new_page()  # Page 8
            p8.insert_text(
                (50, 50),
                "Bharat Coking Coal Limited (BCCL) Audit Report FY 2023-24.\n"
                "Audit disclosure reports Rajmahal OC production at 41.80 Lakh Tonnes (4.18 MT) for FY 2023-24."
            )
            
            for p in range(9, 43):
                page = doc.new_page()
                page.insert_text((50, 50), f"BCCL Audit Page {p}")

            doc.save(bccl_path)
            doc.close()
            logger.info(f"Generated sample PDF document at '{bccl_path}'.")
        except Exception as e:
            logger.warning(f"Could not generate BCCL sample PDF on disk: {e}")

    # 3. SECL_Gevra_Monthly_Despatch.csv
    secl_path = os.path.join(upload_dir, "SECL_Gevra_Monthly_Despatch.csv")
    if not os.path.exists(secl_path):
        try:
            with open(secl_path, "w", encoding="utf-8") as f:
                f.write("Mine,Subsidiary,Metric,NumericValue,Unit,FiscalYear\n")
                f.write("Gevra OpenCast,SECL,Overburden Removal,310.50,M.Cu.M,2023-24\n")
                f.write("Monthly OBR cumulative for Gevra OC reached 310.50 M.Cu.M.\n")
            logger.info(f"Generated sample CSV document at '{secl_path}'.")
        except Exception as e:
            logger.warning(f"Could not generate SECL sample CSV on disk: {e}")

    # 4. MCL_Samaleswari_Performance.xlsx
    mcl_path = os.path.join(upload_dir, "MCL_Samaleswari_Performance.xlsx")
    if not os.path.exists(mcl_path):
        try:
            import pandas as pd
            df = pd.DataFrame([{
                "Mine": "Samaleswari OpenCast",
                "Subsidiary": "MCL",
                "Metric": "Coal Production",
                "NumericValue": 193.30,
                "Unit": "MT",
                "FiscalYear": "2023-24",
                "Notes": "Samaleswari OC achieved 193.30 MT annual output."
            }])
            df.to_excel(mcl_path, index=False)
            logger.info(f"Generated sample XLSX document at '{mcl_path}'.")
        except Exception as e:
            logger.warning(f"Could not generate MCL sample XLSX on disk: {e}")


def seed_default_users(db: Session) -> dict:
    """
    Idempotently seeds default institutional user accounts if not present.
    Returns mapping of username -> user_id.
    """
    default_users = [
        {
            "username": "admin",
            "password": "Admin@123",
            "full_name": "System Administrator",
            "email": "admin@coalintel.cil.in",
            "role": "Admin",
            "subsidiary": "CIL HQ"
        },
        {
            "username": "analyst",
            "password": "Analyst@123",
            "full_name": "CMPDI Mining Analyst",
            "email": "analyst@cmpdi.co.in",
            "role": "Analyst",
            "subsidiary": "CMPDI"
        },
        {
            "username": "reviewer",
            "password": "Reviewer@123",
            "full_name": "ECL Report Reviewer",
            "email": "reviewer@easterncoal.in",
            "role": "Reviewer",
            "subsidiary": "ECL"
        },
        {
            "username": "auditor",
            "password": "Auditor@123",
            "full_name": "Ministry Technical Auditor",
            "email": "auditor@coal.gov.in",
            "role": "Viewer",
            "subsidiary": "Ministry of Coal"
        }
    ]

    user_map = {}
    for user_data in default_users:
        existing_user = db.query(User).filter(User.username == user_data["username"]).first()
        if not existing_user:
            new_user = User(
                username=user_data["username"],
                hashed_password=get_password_hash(user_data["password"]),
                full_name=user_data["full_name"],
                email=user_data["email"],
                role=user_data["role"],
                subsidiary=user_data["subsidiary"]
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            user_map[user_data["username"]] = new_user.id
            logger.info(f"Seeded default user: {user_data['username']} (Role: {user_data['role']})")
        else:
            user_map[user_data["username"]] = existing_user.id

    return user_map


def init_db(db: Session) -> None:
    """
    Creates all 7 PostgreSQL database tables if they do not exist and seeds initial default users,
    documents, extracted metrics, conflicts, and audit logs.
    """
    logger.info("Creating database tables if not present...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")

    # Ensure physical sample files exist in storage/uploads
    ensure_sample_documents_exist()
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)

    # 1. Seed Default Users
    user_map = seed_default_users(db)

    # 2. Seed Default Mining Documents
    default_docs = [
        {
            "filename": "ECL_Annual_Report_2023-24.pdf",
            "file_path": os.path.join(upload_dir, "ECL_Annual_Report_2023-24.pdf"),
            "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "file_type": "PDF",
            "file_size_bytes": 14889728,
            "subsidiary": "ECL",
            "fiscal_year": "2023-24",
            "status": "PARSED",
            "total_pages": 84
        },
        {
            "filename": "BCCL_Production_Audit_Q4.pdf",
            "file_path": os.path.join(upload_dir, "BCCL_Production_Audit_Q4.pdf"),
            "file_hash": "8f4e5d6c7b8a90123456789abcdef0123456789abcdef0123456789abcdef012",
            "file_type": "PDF",
            "file_size_bytes": 9122611,
            "subsidiary": "BCCL",
            "fiscal_year": "2023-24",
            "status": "PARSED",
            "total_pages": 42
        },
        {
            "filename": "SECL_Gevra_Monthly_Despatch.csv",
            "file_path": os.path.join(upload_dir, "SECL_Gevra_Monthly_Despatch.csv"),
            "file_hash": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
            "file_type": "CSV",
            "file_size_bytes": 524288,
            "subsidiary": "SECL",
            "fiscal_year": "2023-24",
            "status": "PARSED",
            "total_pages": 4
        },
        {
            "filename": "MCL_Samaleswari_Performance.xlsx",
            "file_path": os.path.join(upload_dir, "MCL_Samaleswari_Performance.xlsx"),
            "file_hash": "123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0",
            "file_type": "XLSX",
            "file_size_bytes": 2202009,
            "subsidiary": "MCL",
            "fiscal_year": "2023-24",
            "status": "PARSED",
            "total_pages": 12
        }
    ]

    doc_ids = []
    for d in default_docs:
        existing_doc = db.query(Document).filter(Document.file_hash == d["file_hash"]).first()
        if not existing_doc:
            doc_rec = Document(
                filename=d["filename"],
                file_path=d["file_path"],
                file_hash=d["file_hash"],
                file_type=d["file_type"],
                file_size_bytes=d["file_size_bytes"],
                subsidiary=d["subsidiary"],
                fiscal_year=d["fiscal_year"],
                status=d["status"],
                total_pages=d["total_pages"],
                uploaded_by=user_map.get("admin")
            )
            db.add(doc_rec)
            db.commit()
            db.refresh(doc_rec)
            doc_ids.append(doc_rec.id)
        else:
            existing_doc.file_path = d["file_path"]
            db.commit()
            doc_ids.append(existing_doc.id)

    # 3. Trigger Real Ingestion/Chunking Pipeline for Document Chunks
    try:
        from app.services.processing_pipeline import execute_document_processing_pipeline
        for did in doc_ids:
            execute_document_processing_pipeline(db, did)
    except Exception as pipe_err:
        logger.warning(f"Note executing document processing pipeline during seed: {pipe_err}")

    # 4. Seed Extracted Mining Metrics (Curated test fixtures with deterministic confidence scores)
    if doc_ids:
        default_metrics = [
            {
                "document_id": doc_ids[0],
                "page_number": 14,
                "mine_name": "Rajmahal OpenCast",
                "subsidiary": "ECL",
                "metric_name": "Coal Production",
                "numeric_value": 42.50,
                "unit": "Lakh Tonnes",
                "raw_unit": "Lakh Tonnes",
                "standard_value": 4.25,
                "standard_unit": "MT",
                "fiscal_year": "2023-24",
                "confidence_score": 0.985,
                "validation_status": "CONFLICT_DETECTED",
                "raw_snippet": "Total coal production at Rajmahal OC recorded 42.50 Lakh Tonnes (4.25 MT) for FY 2023-24."
            },
            {
                "document_id": doc_ids[0],
                "page_number": 14,
                "mine_name": "ECL Total",
                "subsidiary": "ECL",
                "metric_name": "Coal Production",
                "numeric_value": 42.50,
                "unit": "MT",
                "raw_unit": "MT",
                "standard_value": 42.50,
                "standard_unit": "MT",
                "fiscal_year": "2023-24",
                "confidence_score": 0.995,
                "validation_status": "VALIDATED",
                "raw_snippet": "Eastern Coalfields Limited (ECL) total coal production reached 42.50 Million Tonnes (MT) in FY 2023-24."
            },
            {
                "document_id": doc_ids[0],
                "page_number": 22,
                "mine_name": "Rajmahal OpenCast",
                "subsidiary": "ECL",
                "metric_name": "Overburden Removal",
                "numeric_value": 120.40,
                "unit": "M.Cu.M",
                "raw_unit": "M.Cu.M",
                "standard_value": 120.40,
                "standard_unit": "M.Cu.M",
                "fiscal_year": "2023-24",
                "confidence_score": 0.990,
                "validation_status": "VALIDATED",
                "raw_snippet": "Overburden removal at Rajmahal OC stood at 120.40 M.Cu.M."
            },
            {
                "document_id": doc_ids[1] if len(doc_ids) > 1 else doc_ids[0],
                "page_number": 8,
                "mine_name": "Rajmahal OpenCast",
                "subsidiary": "ECL",
                "metric_name": "Coal Production",
                "numeric_value": 41.80,
                "unit": "Lakh Tonnes",
                "raw_unit": "Lakh Tonnes",
                "standard_value": 4.18,
                "standard_unit": "MT",
                "fiscal_year": "2023-24",
                "confidence_score": 0.970,
                "validation_status": "CONFLICT_DETECTED",
                "raw_snippet": "Audit disclosure reports Rajmahal OC production at 41.80 Lakh Tonnes (4.18 MT)."
            },
            {
                "document_id": doc_ids[2] if len(doc_ids) > 2 else doc_ids[0],
                "page_number": 3,
                "mine_name": "Gevra OpenCast",
                "subsidiary": "SECL",
                "metric_name": "Overburden Removal",
                "numeric_value": 310.50,
                "unit": "M.Cu.M",
                "raw_unit": "M.Cu.M",
                "standard_value": 310.50,
                "standard_unit": "M.Cu.M",
                "fiscal_year": "2023-24",
                "confidence_score": 0.992,
                "validation_status": "WARNING_ARITHMETIC",
                "raw_snippet": "Monthly OBR cumulative for Gevra OC reached 310.50 M.Cu.M."
            },
            {
                "document_id": doc_ids[3] if len(doc_ids) > 3 else doc_ids[0],
                "page_number": 5,
                "mine_name": "Samaleswari OpenCast",
                "subsidiary": "MCL",
                "metric_name": "Coal Production",
                "numeric_value": 193.30,
                "unit": "MT",
                "raw_unit": "MT",
                "standard_value": 193.30,
                "standard_unit": "MT",
                "fiscal_year": "2023-24",
                "confidence_score": 0.995,
                "validation_status": "VALIDATED",
                "raw_snippet": "Samaleswari OC achieved 193.30 MT annual output."
            }
        ]

        for m in default_metrics:
            existing_m = db.query(ExtractedMetric).filter(
                ExtractedMetric.mine_name == m["mine_name"],
                ExtractedMetric.metric_name == m["metric_name"],
                ExtractedMetric.document_id == m["document_id"]
            ).first()
            if not existing_m:
                db.add(ExtractedMetric(**m))
            else:
                existing_m.numeric_value = m["numeric_value"]
                existing_m.unit = m["unit"]
                existing_m.raw_unit = m["raw_unit"]
                existing_m.standard_value = m["standard_value"]
                existing_m.standard_unit = m["standard_unit"]
                existing_m.confidence_score = m["confidence_score"]
                existing_m.validation_status = m["validation_status"]
                existing_m.raw_snippet = m["raw_snippet"]

    db.commit()

    logger.info("Database seeding completed successfully.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()


