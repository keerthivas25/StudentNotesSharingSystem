-- =======================================================
-- Student Notes Sharing System - Database Schema
-- Database: MySQL / Amazon RDS MySQL
-- =======================================================

-- Create Database if not exists
CREATE DATABASE IF NOT EXISTS student_notes
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE student_notes;

-- Create notes Table
CREATE TABLE IF NOT EXISTS notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_name VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    description TEXT,
    s3_key VARCHAR(500) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size BIGINT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexing for fast search and subject filtering
CREATE INDEX idx_subject ON notes (subject);
CREATE INDEX idx_uploaded_at ON notes (uploaded_at DESC);
