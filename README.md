# Scholar CBT Platform

Scholar CBT Platform is a modern web-based Computer-Based Test (CBT) system designed to simplify the creation, administration, and evaluation of online examinations. It provides an intuitive experience for students, instructors, and administrators while ensuring secure and efficient assessment management.

## Features

- Student registration and authentication
- Administrator dashboard
- Create and manage examinations
- Multiple-choice question support
- Configurable exam duration and scheduling
- Automatic submission when time expires
- Instant scoring and result generation
- Performance analytics
- Question and category management
- Secure login and session management
- Responsive user interface
- Database-driven architecture

## Technology Stack

- **Backend:** Flask (Python)
- **Frontend:** HTML, CSS, JavaScript
- **Database:** MySQL
- **ORM:** SQLAlchemy
- **Authentication:** Flask-Login
- **Database Migration:** Flask-Migrate
- **Forms:** Flask-WTF

## Installation

```bash
git clone https://github.com/caliphab/cbt.git
cd scholar-cbt-platform

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

python run.py