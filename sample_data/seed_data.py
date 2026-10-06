"""
Script to seed sample notes into MySQL database and S3 / storage.
Reads from sample_data/sample_notes.csv and populates the application.
"""
import csv
import io
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from services.db import get_db_connection, init_db
from services.s3_service import upload_file_to_s3, generate_s3_key

def seed():
    csv_path = Path(__file__).resolve().parent / 'sample_notes.csv'
    if not csv_path.exists():
        print(f"Error: {csv_path} not found.")
        return

    print(">>> Initializing database schema if needed...")
    ok, msg = init_db()
    if not ok:
        print(f"Database initialization note: {msg}")

    print(">>> Connecting to MySQL database...")
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Please ensure MySQL is running and your .env credentials are correct.")
        return

    print(f">>> Reading sample records from {csv_path.name}...")
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            student_name = row['student_name'].strip()
            title = row['title'].strip()
            subject = row['subject'].strip()
            description = row['description'].strip()

            # Create sample document content
            file_name = f"{subject.lower().replace(' ', '_')}_notes.txt"
            content = (
                f"====================================================\n"
                f"Course Subject : {subject}\n"
                f"Topic / Title  : {title}\n"
                f"Uploaded By    : {student_name}\n"
                f"====================================================\n\n"
                f"Description:\n{description}\n\n"
                f"STUDY NOTES CONTENT SUMMARY:\n"
                f"1. Core concepts and definitions\n"
                f"2. Theoretical framework and architecture\n"
                f"3. Practical examples and lab assignments\n"
                f"4. Key questions for semester examinations\n"
            ).encode('utf-8')

            file_stream = io.BytesIO(content)
            file_size = len(content)
            s3_key = generate_s3_key(file_name)

            # Upload to S3 or local storage
            try:
                upload_file_to_s3(file_stream, s3_key, content_type='text/plain')
            except Exception as e:
                print(f"Failed to upload sample file for '{title}': {e}")
                continue

            # Insert metadata into MySQL
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO notes (student_name, title, subject, description, s3_key, file_name, file_size)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (student_name, title, subject, description, s3_key, file_name, file_size))
            count += 1
            print(f"  [OK] Seeded: {title} ({student_name})")

    conn.close()
    print(f"\nSuccessfully seeded {count} sample notes into MySQL and storage!")

if __name__ == '__main__':
    seed()
