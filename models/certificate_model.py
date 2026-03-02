from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from database.init_db import get_connection


@dataclass
class Certificate:
    id: int
    student_name: str
    register_number: str
    course: str
    issue_date: str
    cid: str
    blockchain_index: int
    pdf_filename: str
    image_filename: str
    created_at: str
    # Optional stored metadata
    ai_score: float | None = None
    heatmap: str | None = None
    blockchain_tx: str | None = None


def insert_certificate(
    student_name: str,
    register_number: str,
    course: str,
    issue_date: str,
    cid: str,
    blockchain_index: int,
    pdf_filename: str,
    image_filename: str,
) -> int:
    conn = get_connection()
    cur = conn.cursor()
    created_at = datetime.utcnow().isoformat()
    cur.execute(
        """
        INSERT INTO certificates
        (student_name, register_number, course, issue_date,
         cid, blockchain_index, pdf_filename, image_filename, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            student_name,
            register_number,
            course,
            issue_date,
            cid,
            blockchain_index,
            pdf_filename,
            image_filename,
            created_at,
        ),
    )
    conn.commit()
    cert_id = cur.lastrowid
    conn.close()
    return cert_id


def get_certificates_by_register(register_number: str) -> List[Certificate]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM certificates WHERE register_number = ? ORDER BY created_at DESC",
        (register_number,),
    )
    rows = cur.fetchall()
    conn.close()
    return [Certificate(**dict(row)) for row in rows]


def get_all_certificates() -> List[Certificate]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM certificates ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [Certificate(**dict(row)) for row in rows]


def get_certificate_by_cid(cid: str) -> Optional[Certificate]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM certificates WHERE cid = ? LIMIT 1", (cid,))
    row = cur.fetchone()
    conn.close()
    return Certificate(**dict(row)) if row else None


def get_certificate_by_id(cert_id: int) -> Optional[Certificate]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM certificates WHERE id = ? LIMIT 1", (cert_id,))
    row = cur.fetchone()
    conn.close()
    return Certificate(**dict(row)) if row else None


def update_certificate_files(cert_id: int, pdf_filename: str, image_filename: str) -> None:
    """Update the stored filenames for a certificate record after final assets are created."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE certificates SET pdf_filename = ?, image_filename = ? WHERE id = ?",
        (pdf_filename, image_filename, cert_id),
    )
    conn.commit()
    conn.close()


def update_certificate_verification(cert_id: int, ai_score: float | None, heatmap: str | None, blockchain_tx: str | None) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE certificates SET ai_score = ?, heatmap = ?, blockchain_tx = ? WHERE id = ?",
        (ai_score, heatmap, blockchain_tx, cert_id),
    )
    conn.commit()
    conn.close()

