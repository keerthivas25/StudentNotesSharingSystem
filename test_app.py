"""
Comprehensive Test Suite for Student Notes Sharing System.
Verifies routes, validations, database queries, and storage operations.
"""
import io
import unittest
from app import app
from services.db import get_db_connection

class StudentNotesTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_01_health_endpoint(self):
        """Test /health returns 200 and JSON with status info."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('status', data)
        self.assertIn('database', data)
        self.assertIn('storage', data)
        print("  [PASS] Test 1: Health check endpoint is healthy")

    def test_02_home_page(self):
        """Test / renders successfully and contains title."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Student Notes Sharing System', response.data)
        self.assertIn(b'Upload, manage and download study materials', response.data)
        print("  [PASS] Test 2: Home page renders correctly")

    def test_03_upload_get_page(self):
        """Test GET /upload renders upload form with fields."""
        response = self.client.get('/upload')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Student Name', response.data)
        self.assertIn(b'Note Title', response.data)
        self.assertIn(b'Subject', response.data)
        self.assertIn(b'Upload Notes', response.data)
        print("  [PASS] Test 3: Upload page renders with all form fields")

    def test_04_upload_invalid_file(self):
        """Test POST /upload rejects unsupported file extension."""
        data = {
            'student_name': 'Test Student',
            'title': 'Dangerous Executable',
            'subject': 'Cyber Security',
            'description': 'Malicious file attempt',
            'file': (io.BytesIO(b'malicious script'), 'payload.exe')
        }
        response = self.client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Unsupported file type', response.data)
        print("  [PASS] Test 4: Upload rejects unsupported file types (.exe)")

    def test_05_upload_valid_pdf_and_view(self):
        """Test POST /upload accepts valid PDF, stores metadata and file."""
        sample_pdf_bytes = b"%PDF-1.4 ... Sample College Mini-Project PDF Content ..."
        data = {
            'student_name': 'Keerthivas Test',
            'title': 'Cloud Computing Unit 1 Notes',
            'subject': 'Cloud Computing',
            'description': 'AWS Architecture and VPC overview notes',
            'file': (io.BytesIO(sample_pdf_bytes), 'Cloud_Computing_Unit1.pdf')
        }
        response = self.client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cloud Computing Unit 1 Notes', response.data)
        self.assertIn(b'uploaded successfully', response.data)

        # Verify entry in database
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM notes WHERE title = %s", ('Cloud Computing Unit 1 Notes',))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row['student_name'], 'Keerthivas Test')
            self.assertEqual(row['subject'], 'Cloud Computing')
            self.assertEqual(row['file_name'], 'Cloud_Computing_Unit1.pdf')
            note_id = row['id']
        conn.close()
        print("  [PASS] Test 5: Valid PDF upload stored metadata in database and redirected to /notes")

        # Test download of this newly uploaded note
        download_resp = self.client.get(f'/download/{note_id}')
        self.assertEqual(download_resp.status_code, 200)
        self.assertEqual(download_resp.data, sample_pdf_bytes)
        print("  [PASS] Test 6: Note download successfully streamed original file bytes")

    def test_07_notes_search_and_filter(self):
        """Test /notes with subject filtering and search query."""
        # Filter by subject
        response = self.client.get('/notes?subject=Cloud+Computing')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cloud Computing', response.data)

        # Search query
        search_resp = self.client.get('/notes?search=Keerthivas')
        self.assertEqual(search_resp.status_code, 200)
        self.assertIn(b'Keerthivas', search_resp.data)
        print("  [PASS] Test 7: Notes view supports subject filtering and text search")

    def test_08_download_nonexistent_note(self):
        """Test /download/99999 redirects gracefully with error."""
        response = self.client.get('/download/99999', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Note not found', response.data)
        print("  [PASS] Test 8: Non-existent note download handled gracefully")

if __name__ == '__main__':
    unittest.main()
