/**
 * Student Notes Sharing System - Client-side interactivity
 */

document.addEventListener('DOMContentLoaded', () => {
    // -------------------------------------------------------------
    // Mobile Navigation Toggle
    // -------------------------------------------------------------
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');

    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            navMenu.classList.toggle('open');
        });
    }

    // -------------------------------------------------------------
    // Auto-dismiss Alerts after 5 seconds
    // -------------------------------------------------------------
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 400);
        }, 5000);
    });

    // -------------------------------------------------------------
    // File Upload Drag & Drop and Preview
    // -------------------------------------------------------------
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file');
    const fileLabel = document.getElementById('file-label');
    const fileDetails = document.getElementById('file-details');

    if (dropZone && fileInput) {
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('dragover');
            });
        });

        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            if (dt.files && dt.files.length > 0) {
                fileInput.files = dt.files;
                updateFileDisplay(dt.files[0]);
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files && fileInput.files.length > 0) {
                updateFileDisplay(fileInput.files[0]);
            }
        });
    }

    function updateFileDisplay(file) {
        if (!file) return;

        const sizeInMb = (file.size / (1024 * 1024)).toFixed(2);
        const maxSizeMb = 25;

        if (file.size > maxSizeMb * 1024 * 1024) {
            alert(`File size (${sizeInMb} MB) exceeds maximum allowed size of ${maxSizeMb} MB.`);
            fileInput.value = '';
            fileLabel.innerHTML = 'Drag & drop your study file here or <span class="browse-link">browse</span>';
            fileDetails.textContent = '';
            return;
        }

        fileLabel.innerHTML = `Selected: <strong>${file.name}</strong>`;
        fileDetails.textContent = `File Size: ${sizeInMb} MB (${file.type || 'Document'})`;
    }

    // -------------------------------------------------------------
    // Client-side quick filter on notes table
    // -------------------------------------------------------------
    const searchInput = document.getElementById('search-input');
    const notesTable = document.getElementById('notes-table');

    if (searchInput && notesTable) {
        searchInput.addEventListener('input', () => {
            const query = searchInput.value.toLowerCase().trim();
            const rows = notesTable.querySelectorAll('tbody tr');

            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(query)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
});
