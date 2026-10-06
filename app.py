import os
import sys
from pathlib import Path
from flask import (
    Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
)
from werkzeug.exceptions import RequestEntityTooLarge

from config import Config
from services.db import get_db_connection, test_db_connection, init_db
from services.s3_service import (
    upload_file_to_s3,
    download_file_from_s3,
    generate_s3_key,
    test_s3_connection
)

# Initialize Flask Application
app = Flask(__name__)
app.config.from_object(Config)

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS

def format_file_size(size_in_bytes):
    """Format bytes into readable string (KB, MB)."""
    if size_in_bytes is None:
        return "Unknown"
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    else:
        return f"{size_in_bytes / (1024 * 1024):.2f} MB"

def format_datetime(value):
    """Safely format datetime object or string for display."""
    if not value:
        return "—"
    if hasattr(value, 'strftime'):
        return value.strftime('%d %b %Y, %I:%M %p')
    if isinstance(value, str):
        try:
            from datetime import datetime
            clean_str = value.replace('T', ' ')
            # Handle fractional seconds if present
            if '.' in clean_str:
                dt = datetime.strptime(clean_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
            else:
                dt = datetime.strptime(clean_str, '%Y-%m-%d %H:%M:%S')
            return dt.strftime('%d %b %Y, %I:%M %p')
        except Exception:
            return value
    return str(value)

# Register template filters
app.jinja_env.filters['format_size'] = format_file_size
app.jinja_env.filters['format_datetime'] = format_datetime

# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------

@app.route('/')
def home():
    """Home Page: Overview, stats, and quick links."""
    stats = {
        'total_notes': 0,
        'total_subjects': 0,
        'recent_notes': []
    }
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Total notes count
            cursor.execute("SELECT COUNT(*) AS total FROM notes")
            stats['total_notes'] = cursor.fetchone()['total']

            # Total distinct subjects
            cursor.execute("SELECT COUNT(DISTINCT subject) AS total_subj FROM notes")
            stats['total_subjects'] = cursor.fetchone()['total_subj']

            # 3 most recently uploaded notes for preview
            cursor.execute(
                "SELECT id, student_name, title, subject, file_name, uploaded_at "
                "FROM notes ORDER BY uploaded_at DESC LIMIT 3"
            )
            stats['recent_notes'] = cursor.fetchall()
        conn.close()
    except Exception as e:
        app.logger.warning(f"Could not load database stats on home page: {str(e)}")

    return render_template('index.html', stats=stats)


@app.route('/upload', methods=['GET', 'POST'])
def upload_notes():
    """
    GET: Render notes upload form.
    POST: Validate form, upload file to S3, and save metadata to MySQL.
    """
    if request.method == 'GET':
        return render_template('upload.html', allowed_extensions=sorted(list(Config.ALLOWED_EXTENSIONS)))

    # Process POST Request
    student_name = request.form.get('student_name', '').strip()
    title = request.form.get('title', '').strip()
    subject = request.form.get('subject', '').strip()
    description = request.form.get('description', '').strip()

    # Form field validations
    if not student_name:
        flash("Student Name is required.", "danger")
        return redirect(url_for('upload_notes'))

    if not title:
        flash("Note Title is required.", "danger")
        return redirect(url_for('upload_notes'))

    if not subject:
        flash("Subject is required.", "danger")
        return redirect(url_for('upload_notes'))

    # File validation
    if 'file' not in request.files:
        flash("No file part in the request.", "danger")
        return redirect(url_for('upload_notes'))

    file = request.files['file']
    if not file or file.filename == '':
        flash("No file selected. Please choose a file to upload.", "danger")
        return redirect(url_for('upload_notes'))

    if not allowed_file(file.filename):
        allowed_list = ", ".join(sorted(list(Config.ALLOWED_EXTENSIONS))).upper()
        flash(f"Unsupported file type! Allowed formats: {allowed_list}", "danger")
        return redirect(url_for('upload_notes'))

    # Calculate file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    original_filename = file.filename
    s3_key = generate_s3_key(original_filename)

    # 1. Upload to Amazon S3
    try:
        upload_file_to_s3(file, s3_key, content_type=file.content_type)
    except Exception as e:
        app.logger.error(f"S3 upload failed: {str(e)}")
        flash("Failed to upload file to cloud storage. Please check storage configuration.", "danger")
        return redirect(url_for('upload_notes'))

    # 2. Store metadata in MySQL
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO notes (student_name, title, subject, description, s3_key, file_name, file_size)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (student_name, title, subject, description, s3_key, original_filename, file_size))
        conn.close()
    except Exception as e:
        app.logger.error(f"Database insertion failed: {str(e)}")
        flash("File was uploaded to storage, but failed to save metadata in database.", "danger")
        return redirect(url_for('upload_notes'))

    flash(f"Note '{title}' uploaded successfully!", "success")
    return redirect(url_for('view_notes'))


@app.route('/notes')
def view_notes():
    """
    View all uploaded notes in a clean table/card layout.
    Supports filtering by subject and search query.
    """
    search_query = request.args.get('search', '').strip()
    selected_subject = request.args.get('subject', '').strip()

    notes = []
    subjects = []

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Fetch all distinct subjects for the filter dropdown
            cursor.execute("SELECT DISTINCT subject FROM notes WHERE subject IS NOT NULL AND subject != '' ORDER BY subject ASC")
            subjects = [row['subject'] for row in cursor.fetchall()]

            # Build query with optional filters
            sql = "SELECT * FROM notes WHERE 1=1"
            params = []

            if selected_subject:
                sql += " AND subject = %s"
                params.append(selected_subject)

            if search_query:
                sql += " AND (title LIKE %s OR student_name LIKE %s OR description LIKE %s OR file_name LIKE %s)"
                search_like = f"%{search_query}%"
                params.extend([search_like, search_like, search_like, search_like])

            sql += " ORDER BY uploaded_at DESC"
            cursor.execute(sql, params)
            notes = cursor.fetchall()
        conn.close()
    except Exception as e:
        app.logger.error(f"Failed to fetch notes: {str(e)}")
        flash("Unable to connect to the database. Please verify MySQL service and credentials.", "danger")

    return render_template(
        'notes.html',
        notes=notes,
        subjects=subjects,
        selected_subject=selected_subject,
        search_query=search_query
    )


@app.route('/download/<int:id>')
def download_note(id):
    """
    Retrieve note metadata from MySQL, fetch file stream from S3,
    and send the file to the user's browser.
    AWS credentials are never exposed to the frontend.
    """
    # 1. Fetch note metadata from database
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM notes WHERE id = %s", (id,))
            note = cursor.fetchone()
        conn.close()
    except Exception as e:
        app.logger.error(f"Database query failed for note {id}: {str(e)}")
        flash("Database error while retrieving note metadata.", "danger")
        return redirect(url_for('view_notes'))

    if not note:
        flash("Note not found.", "danger")
        return redirect(url_for('view_notes'))

    # 2. Retrieve file stream from S3
    try:
        file_stream, content_type = download_file_from_s3(note['s3_key'])
        return send_file(
            file_stream,
            as_attachment=True,
            download_name=note['file_name'],
            mimetype=content_type
        )
    except FileNotFoundError:
        flash("The requested file was not found in storage.", "danger")
        return redirect(url_for('view_notes'))
    except Exception as e:
        app.logger.error(f"Error downloading file {note['s3_key']}: {str(e)}")
        flash("Failed to download file from cloud storage.", "danger")
        return redirect(url_for('view_notes'))


@app.route('/health')
def health():
    """
    Health check endpoint.
    Returns status of the application, MySQL connection, and storage layer.
    """
    db_ok, db_msg = test_db_connection()
    s3_ok, s3_msg, storage_type = test_s3_connection()

    status_code = 200 if (db_ok and s3_ok) else 503

    return jsonify({
        "status": "healthy" if (db_ok and s3_ok) else "degraded",
        "database": {
            "connected": db_ok,
            "message": db_msg
        },
        "storage": {
            "type": storage_type,
            "connected": s3_ok,
            "message": s3_msg
        }
    }), status_code


# ---------------------------------------------------------
# ERROR HANDLERS
# ---------------------------------------------------------

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    max_mb = Config.MAX_CONTENT_LENGTH / (1024 * 1024)
    flash(f"File too large! Maximum allowed upload size is {max_mb:.0f} MB.", "danger")
    return redirect(url_for('upload_notes'))

@app.errorhandler(404)
def handle_not_found(e):
    return render_template('base.html', not_found=True), 404

@app.errorhandler(500)
def handle_server_error(e):
    flash("An unexpected server error occurred. Please try again.", "danger")
    return redirect(url_for('home'))


if __name__ == '__main__':
    # When starting locally, optionally initialize database if requested
    print("=" * 60)
    print(" Starting Student Notes Sharing System ")
    print(f" Environment : {os.getenv('FLASK_ENV', 'development')}")
    print(f" Storage Mode: {'Local Fallback' if Config.USE_LOCAL_STORAGE else 'Amazon S3'}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
