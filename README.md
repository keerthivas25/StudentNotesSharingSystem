# Student Notes Sharing System

A cloud-based academic web application designed for students to upload, organize, view, and download study materials (PDFs, PPTs, DOCX, etc.) securely, leveraging AWS cloud architecture (Amazon VPC, EC2, RDS MySQL, S3, IAM, and Security Groups).

---

## 1. Problem Statement

> *"Students often store study materials on different devices and platforms, making it difficult to organize and access them. The Student Notes Sharing System provides a centralized cloud-based platform where students can upload, store, and download study materials securely."*

---

## 2. Project Aim

> *"To design and deploy a small cloud-based student notes management application using AWS VPC, EC2, RDS, and S3 with secure communication between the application, database, and cloud storage layers."*

---

## 3. Project Objectives

1. **Centralized Academic Repository:** Provide an intuitive interface for students to share and search lecture notes, lab manuals, and syllabus resources.
2. **Cloud Storage Separation of Concerns:** Store file binaries durably in Amazon S3 while keeping structured metadata (student name, title, course subject, timestamps) in a relational MySQL database.
3. **Multi-Tier Secure Architecture:** Separate the application tier (EC2 in a public subnet) from the database tier (RDS MySQL in private subnets) within an Amazon Virtual Private Cloud (VPC).
4. **Least Privilege Security Posture:** Utilize AWS IAM instance profile roles to grant EC2 temporary scoped permissions to S3 without embedding permanent credentials in the codebase or server.
5. **Local-to-Cloud Compatibility:** Ensure the entire application can be developed, tested, and verified on a local Windows development machine before cloud deployment.

---

## 4. Key Features

- **Upload Notes:** Students can submit lecture materials with metadata (Student Name, Note Title, Subject, Description) supporting `.pdf`, `.ppt`, `.pptx`, `.doc`, `.docx`, `.txt`, and `.csv`.
- **View & Filter Notes:** Clean table display showing ID, Student, Title, Subject, Description, File Name, and Upload Date.
- **Search & Subject Filtering:** Real-time search query and subject dropdown filter.
- **Secure File Download:** Proxies file downloads securely from cloud storage without ever exposing private bucket URLs or AWS credentials to the browser.
- **Health Check Endpoint (`/health`):** Verifies both database connectivity and cloud storage availability.
- **Local Fallback Mode:** Allows complete offline development on a laptop before connecting to live AWS infrastructure.

---

## 5. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend** | Python 3.10+, Flask 3.0 | Web routing, form validation, business logic |
| **WSGI Server** | Gunicorn | Production application server on EC2 |
| **Database** | MySQL / Amazon RDS MySQL | Structured metadata storage (`notes` table) |
| **Object Storage** | Amazon S3 | Durable binary storage for study files |
| **Cloud Compute** | Amazon EC2 (Amazon Linux 2023) | Application hosting |
| **Networking** | Amazon VPC, Subnets, IGW | Isolated network topology |
| **Security** | AWS IAM, Security Groups | Least-privilege roles, firewall rules |
| **Frontend** | HTML5, CSS3, Vanilla JS, Jinja2 | Responsive educational interface (No heavy frameworks) |

---

## 6. AWS Architecture

### High-Level Architecture Diagram (Mermaid)

```mermaid
graph TD
    User([Student / Web Browser]) -->|HTTP Port 80 / 5000| IGW[Internet Gateway]
    
    subgraph VPC ["AWS Virtual Private Cloud (VPC: 10.0.0.0/16)"]
        subgraph PublicSubnet ["Public Subnet (10.0.1.0/24)"]
            IGW --> EC2["Amazon EC2 Instance<br/>(Flask App + Gunicorn)"]
        end
        
        subgraph PrivateSubnets ["Private Subnets (Isolated Tier)"]
            subgraph PrivSub1 ["Private Subnet 1 (10.0.2.0/24)"]
                RDS_Primary["Amazon RDS MySQL<br/>(student_notes DB)"]
            end
            subgraph PrivSub2 ["Private Subnet 2 (10.0.3.0/24)"]
                RDS_Standby["RDS Subnet Group Standby"]
            end
        end
    end
    
    EC2 -->|MySQL Port 3306<br/>(RDS Security Group)| RDS_Primary
    EC2 -.->|IAM Instance Role<br/>(s3:PutObject, s3:GetObject)| S3[("Amazon S3 Bucket<br/>(notes/ prefix)")]
```

### High-Level Architecture Diagram (ASCII)

```text
                        INTERNET
                           |
                    INTERNET GATEWAY
                           |
                      AWS VPC (10.0.0.0/16)
                           |
                     PUBLIC SUBNET (10.0.1.0/24)
                           |
                          EC2 (Amazon Linux 2023)
                     Flask Application + Gunicorn
                           |
                 ----------------------------------
                 |                                |
         PRIVATE SUBNET 1 (10.0.2.0/24)   PRIVATE SUBNET 2 (10.0.3.0/24)
                 |                                |
            Amazon RDS MySQL                 RDS Subnet Group
          (Port 3306 restricted)
                           
    EC2 Instance Profile (IAM Role: NotesAppEC2Role)
         |
         +----------------------------------------> Amazon Simple Storage Service (S3)
                                                    s3://student-notes-<unique>/notes/
```

---

## 7. Project Structure

```text
StudentNotesSharingSystem/
│
├── app.py                     # Main Flask web application & route handlers
├── config.py                  # Configuration loader (.env, AWS, DB parameters)
├── requirements.txt           # Python dependencies
├── schema.sql                 # MySQL database and table schema definition
├── README.md                  # Complete project documentation and guide
├── .env.example               # Template environment configuration file
├── .gitignore                 # Files excluded from version control
│
├── services/                  # Business logic services
│   ├── __init__.py
│   ├── db.py                  # PyMySQL database connection & helper utilities
│   └── s3_service.py          # AWS boto3 S3 upload/download module + local fallback
│
├── templates/                 # Jinja2 HTML templates
│   ├── base.html              # Base layout with navbar, footer, flash alerts
│   ├── index.html             # Home page with stats and quick links
│   ├── upload.html            # Upload form with file drag-and-drop
│   └── notes.html             # View notes table with search & subject filter
│
├── static/                    # Static assets
│   ├── css/
│   │   └── style.css          # Educational blue/white theme styling
│   └── js/
│       └── app.js             # Client-side validation, search filter & animations
│
└── sample_data/               # Demonstration data & seeding tool
    ├── sample_notes.csv       # Academic sample records
    └── seed_data.py           # Automated one-click seeding script
```

---

## 8. Database Design

### Database Name
`student_notes`

### Table Name
`notes`

### Table Schema (`schema.sql`)
```sql
CREATE DATABASE IF NOT EXISTS student_notes
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE student_notes;

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

CREATE INDEX idx_subject ON notes (subject);
CREATE INDEX idx_uploaded_at ON notes (uploaded_at DESC);
```

---

## 9. Local Setup & Execution (Windows PowerShell)

Follow these exact steps to run and test the application on your Windows laptop first:

### Step 1: Open PowerShell and Navigate to the Project
```powershell
cd c:\Users\91944\Desktop\AG_projects\StudentNotesSharingSystem
```

### Step 2: Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If PowerShell shows an execution policy error, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Edit `.env` with your local MySQL credentials:
```ini
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=college-mini-project-secret-key-2026

DB_HOST=localhost
DB_PORT=3306
DB_NAME=student_notes
DB_USER=root
DB_PASSWORD=YourLocalMySQLPassword

AWS_REGION=ap-south-1
AWS_S3_BUCKET=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

USE_LOCAL_STORAGE=true
```
> **Note on Local Storage Mode:** When `USE_LOCAL_STORAGE=true` (or when AWS keys are placeholders), uploaded study files are safely stored locally in `local_storage/notes/`. This allows you to test 100% of the workflow offline without needing active AWS billing.

### Step 5: Initialize MySQL Database
Open MySQL command line or execute `schema.sql`:
```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -e "source schema.sql"
```
Or simply run the automated seeding script which initializes the schema and inserts sample records:
```powershell
python sample_data/seed_data.py
```

### Step 6: Start the Flask Application
```powershell
python app.py
```

### Step 7: Open in Web Browser
Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## 10. Verification of Flask Routes

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Home page with repository stats and feature cards |
| `GET` | `/upload` | Renders study material upload form |
| `POST` | `/upload` | Validates file, uploads to S3/storage, inserts metadata into MySQL |
| `GET` | `/notes` | Displays all notes with live search and subject dropdown filter |
| `GET` | `/download/<id>` | Safely fetches file from S3 and initiates browser download |
| `GET` | `/health` | Returns health status JSON of app, MySQL, and storage layers |

---

## 11. AWS Cloud Infrastructure Architecture & Deployment

Once the local application has been verified, deploy to AWS according to the following step-by-step procedure:

---

### Phase A: Amazon VPC Setup

1. **Create VPC:**
   - Name: `StudentNotes-VPC`
   - IPv4 CIDR Block: `10.0.0.0/16`
   - Tenancy: `Default`
2. **Create Subnets:**
   - **Public Subnet (EC2):**
     - CIDR: `10.0.1.0/24`
     - AZ: `ap-south-1a`
     - Setting: Enable *"Auto-assign public IPv4 address"*.
   - **Private Subnet 1 (RDS Primary):**
     - CIDR: `10.0.2.0/24`
     - AZ: `ap-south-1a`
   - **Private Subnet 2 (RDS Multi-AZ / Subnet Group):**
     - CIDR: `10.0.3.0/24`
     - AZ: `ap-south-1b`
3. **Internet Gateway (IGW):**
   - Create IGW named `StudentNotes-IGW`.
   - Attach it to `StudentNotes-VPC`.
4. **Route Tables:**
   - **Public Route Table:**
     - Associate with `10.0.1.0/24`.
     - Add route: Destination `0.0.0.0/0` -> Target `StudentNotes-IGW`.
   - **Private Route Table:**
     - Associate with `10.0.2.0/24` and `10.0.3.0/24`.
     - No direct route to `0.0.0.0/0` via IGW (guarantees isolation).

---

### Phase B: Security Groups Configuration

Create two security groups with strict isolation:

#### 1. EC2 Web Security Group (`EC2-Web-SG`)
- **VPC:** `StudentNotes-VPC`
- **Inbound Rules:**
  - Type: `SSH` | Port: `22` | Source: `My IP` (for administrative terminal access)
  - Type: `HTTP` | Port: `80` | Source: `0.0.0.0/0` (public web traffic)
  - Type: `Custom TCP` | Port: `5000` | Source: `0.0.0.0/0` (Gunicorn/Flask testing port)
- **Outbound Rules:**
  - All traffic to `0.0.0.0/0`.

#### 2. RDS Database Security Group (`RDS-MySQL-SG`)
- **VPC:** `StudentNotes-VPC`
- **Inbound Rules:**
  - Type: `MYSQL/Aurora` | Port: `3306` | Source: `EC2-Web-SG` (Specify Security Group ID, e.g., `sg-0123456789abcdef`)
  - ⚠️ **CRITICAL SECURITY REQUIREMENT:** Port 3306 must **NEVER** allow `0.0.0.0/0`. Only the EC2 instance can reach the database.
- **Outbound Rules:**
  - All traffic allowed.

---

### Phase C: Amazon S3 Bucket Creation

1. Navigate to the **Amazon S3 Console** and click **Create Bucket**.
2. **Bucket Name:** `student-notes-repository-<your-rollnumber>` (must be globally unique).
3. **Region:** `ap-south-1` (Asia Pacific - Mumbai) or matching your VPC region.
4. **Public Access:** Keep **"Block all public access"** checked (Enabled).
5. **Encryption:** Server-Side Encryption with Amazon S3 managed keys (SSE-S3).
6. Files will be organized under the folder prefix: `notes/`.

---

### Phase D: IAM Role for EC2 (Least Privilege)

To prevent storing long-lived AWS Access Keys on the EC2 server, configure an IAM Role:

1. In the **IAM Console**, go to **Roles** -> **Create Role**.
2. **Trusted Entity Type:** AWS Service -> EC2.
3. Click **Next**, then click **Create Policy** -> JSON editor:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowStudentNotesS3Operations",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::student-notes-repository-<your-rollnumber>",
                "arn:aws:s3:::student-notes-repository-<your-rollnumber>/*"
            ]
        }
    ]
}
```
4. Name the policy: `StudentNotesS3AccessPolicy`.
5. Attach the policy and name the role: `EC2-StudentNotes-Role`.
6. Attach this role to your EC2 instance: **EC2 Console -> Actions -> Security -> Modify IAM Role -> Select `EC2-StudentNotes-Role`**.

---

### Phase E: Amazon RDS MySQL Setup

1. **DB Subnet Group:**
   - Go to **RDS Console -> Subnet groups -> Create DB Subnet Group**.
   - VPC: `StudentNotes-VPC`.
   - Add Subnets: Select `10.0.2.0/24` (AZ a) and `10.0.3.0/24` (AZ b).
2. **Create Database:**
   - Engine: **MySQL** (Version 8.0).
   - Template: **Free Tier**.
   - DB instance identifier: `student-notes-db`.
   - Master username: `admin`.
   - Master password: `SecurePassword2026!`.
   - DB Instance class: `db.t3.micro` or `db.t4g.micro`.
   - Connectivity:
     - VPC: `StudentNotes-VPC`.
     - Subnet group: Subnet group created above.
     - **Publicly Accessible:** `No`.
     - Existing VPC Security Groups: Select `RDS-MySQL-SG` (remove default).
   - Additional Configuration:
     - Initial database name: `student_notes`.
3. Note down the **RDS Endpoint** (e.g., `student-notes-db.c123456789.ap-south-1.rds.amazonaws.com`).

---

### Phase F: Amazon EC2 Launch & Application Deployment

1. **Launch EC2 Instance:**
   - AMI: **Amazon Linux 2023 AMI**.
   - Instance type: `t2.micro` or `t3.micro` (Free Tier eligible).
   - Key pair: Select or create `student-notes-key.pem`.
   - Network settings:
     - VPC: `StudentNotes-VPC`.
     - Subnet: Public Subnet (`10.0.1.0/24`).
     - Auto-assign public IP: `Enable`.
     - Security Group: Select `EC2-Web-SG`.
   - Advanced Details:
     - IAM instance profile: `EC2-StudentNotes-Role`.
2. **SSH into the EC2 Instance:**
```bash
ssh -i student-notes-key.pem ec2-user@<EC2-PUBLIC-IP>
```
3. **Install Dependencies on EC2:**
```bash
sudo dnf update -y
sudo dnf install -y python3.11 python3.11-pip git mariadb105
```
4. **Clone or Copy Application:**
```bash
git clone <your-repository-url> StudentNotesSharingSystem
cd StudentNotesSharingSystem
```
5. **Setup Python Virtual Environment:**
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
6. **Configure Production `.env` File:**
```bash
cat << 'EOF' > .env
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=college-production-secret-key-super-secure

DB_HOST=<YOUR-RDS-ENDPOINT>
DB_PORT=3306
DB_NAME=student_notes
DB_USER=admin
DB_PASSWORD=SecurePassword2026!

AWS_REGION=ap-south-1
AWS_S3_BUCKET=student-notes-repository-<your-rollnumber>

# Leave empty so boto3 automatically uses the EC2 IAM Role!
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

USE_LOCAL_STORAGE=false
EOF
```
7. **Initialize RDS Schema from EC2:**
```bash
mysql -h <YOUR-RDS-ENDPOINT> -u admin -p student_notes < schema.sql
```
8. **Run with Gunicorn (Production WSGI Server):**
```bash
gunicorn --bind 0.0.0.0:5000 --workers 3 app:app
```
*(Optionally setup Nginx as reverse proxy on port 80 to port 5000, or run Gunicorn directly).*

---

## 12. Complete Testing & Verification Checklist

| Test Item | Verification Procedure | Expected Outcome |
|---|---|---|
| **1. Home Page** | Navigate to `http://<IP>:5000/` | HTTP 200, shows hero section, navigation, and repository overview |
| **2. Health Check** | Navigate to `http://<IP>:5000/health` | Returns status 200 with `"database": {"connected": true}` and `"storage": {"connected": true}` |
| **3. Form Validation** | Submit `/upload` with empty title or subject | Form rejected, shows friendly alert message |
| **4. File Type Check** | Attempt to upload `.exe` or `.bat` file | Rejected with error: *"Unsupported file type"* |
| **5. Valid Upload** | Upload sample PDF `ML_Unit1.pdf` | Success message, redirected to `/notes` |
| **6. S3 Verification** | Check S3 console in AWS or check bucket | File exists under `notes/<timestamp>_ML_Unit1.pdf` |
| **7. RDS Verification** | Run `SELECT * FROM notes;` on RDS | Record contains student name, s3_key, file_size, and title |
| **8. View Notes Display** | Navigate to `/notes` | Uploaded note is listed in table with subject badge |
| **9. Search Filter** | Type "ML" in search bar | Real-time filter isolates only matching notes |
| **10. Subject Dropdown** | Select "Machine Learning" in dropdown | Page updates showing only notes for that subject |
| **11. File Download** | Click "Download" on note #1 | File streams correctly to user device with matching file name |
| **12. EC2 → RDS Security** | Attempt to connect to RDS from laptop directly | Connection timed out (Verifies port 3306 is not open to public) |
| **13. IAM Role Security** | Run `aws s3 ls` on EC2 without `.aws/credentials` | Bucket contents list successfully via IAM instance profile |
| **14. S3 Bucket Privacy** | Attempt to open direct S3 URL in browser | Access Denied 403 (Verifies bucket is not public) |

---

## 13. Application Workflow Explained

```text
[Student Browser]
       │
       ▼  1. Fills form (Student Name, Subject, Title, PDF)
[Flask on EC2]
       │
       ├──► 2. Validates inputs & file extension
       ├──► 3. Generates safe unique key: notes/20261007_021500_ML_Unit1.pdf
       │
       ├──► 4. Streams file binary to Amazon S3 via boto3 (using IAM Role)
       │       [Amazon S3 Bucket] ◄── Stored durably
       │
       └──► 5. Inserts metadata row into MySQL
               [Amazon RDS MySQL] ◄── Stored in private subnet
       │
       ▼  6. Redirects student to View Notes page
[Student Browser]
       │
       ▼  7. Clicks "Download"
[Flask on EC2]
       │
       ├──► 8. Queries note record by ID from MySQL
       ├──► 9. Streams file bytes from S3 into memory buffer
       │
       ▼ 10. Sends attachment stream to browser via HTTP
[Student File Saved to Laptop]
```

---

## 14. Faculty Viva & Examination Q&A

**Q1: Why did you separate files (S3) from metadata (MySQL)?**
> *Answer:* Storing large binary files (PDFs, PPTs) inside relational databases bloats database storage, degrades backup speeds, and severely impacts query indexing performance. Amazon S3 is an object storage service designed specifically for virtually unlimited, highly durable (99.999999999%), cost-effective file storage. MySQL is optimized for fast relational lookups, searching, and filtering on metadata.

**Q2: Why is Amazon RDS placed in private subnets?**
> *Answer:* A database should never have direct exposure to the public internet to prevent brute-force attacks and unauthorized data exfiltration. By placing RDS in private subnets without an Internet Gateway route and configuring its Security Group to accept traffic exclusively on port 3306 from the EC2 Security Group, only the application tier can communicate with the database.

**Q3: How does the EC2 instance communicate with S3 without AWS access keys?**
> *Answer:* We use an AWS IAM Instance Profile Role attached to the EC2 instance. The AWS SDK (`boto3`) automatically retrieves rotating temporary credentials from the EC2 instance metadata service (IMDSv2), adhering to the security best practice of least privilege and eliminating hardcoded keys.

**Q4: How does this project demonstrate Big Data Analytics and Cloud concepts?**
> *Answer:* It illustrates core cloud architectural tenets: Decoupled storage vs. compute, scalable object storage for unstructured data (educational media), transactional SQL for structured metadata, and multi-tier network segregation using VPC subnets and security firewalls.
