# TEACH-System-Management
A localized classroom management system for educators focused on data privacy and offline utility.

TEACH is an integrated productivity hub designed specifically for Grade 6–8 educators to streamline daily classroom operations. By utilizing a local-first architecture, the system prioritizes student data privacy and ensures absolute functionality in environments with intermittent internet connectivity, providing teachers with a high-speed "Command Center" for instructional management.

Technical Stack
Language: Python 3.x
Web Framework: Flask
Database: SQLite (ACID-compliant local persistence)
Data Manipulation: Pandas (DataFrame serialization and sorting)
Testing: PyTest (White-box unit testing)
Architecture: Layered Monolithic (MVC Pattern)

Key Features
Gamified Behavior System: Real-time reward and deduction logic (+3, +5, -3, -5) with visual CSS3 animations (Hammer/Confetti).
Interactive Seat Plan: Drag-and-drop student avatars allowing teachers to physically arrange the class layout.
CSV Reporting Module: Automated data serialization for longitudinal student performance analysis and parent-teacher communication.
Lesson Library: Local management of PDF and PowerPoint resources with integrated archiving capabilities.
Class-Wide Silence Tool: Global classroom state management with grayscale visual feedback filters.

Installation and Setup
To run the TEACH system locally on your device, follow these steps:

Install Dependencies:
pip install flask flask_sqlalchemy pandas pytest

Initialize the Database:
The system is configured to auto-generate the SQLite schema on the first run.

Run the Application:
python app.py

Running Unit Tests:
pytest
