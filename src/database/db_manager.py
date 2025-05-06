import sqlite3
import os
import logging
from datetime import datetime
from pathlib import Path
from ..utils.config import Config

class DatabaseManager:
    """Manager for database operations"""
    
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger("attendance_system")
        self.db_path = Path(self.config.get("paths", "database"))
        
        # Ensure the parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.initialize_database()
    
    def initialize_database(self):
        """Create database tables if they don't exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create students table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    student_id TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # Create attendance records table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    status TEXT NOT NULL,
                    FOREIGN KEY (student_id) REFERENCES students(student_id),
                    UNIQUE(student_id, date)
                )
                ''')
                
                conn.commit()
                self.logger.info("Database initialized successfully")
        except sqlite3.Error as e:
            self.logger.error(f"Database initialization error: {e}")
    
    def register_student(self, name, student_id):
        """Register a new student"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO students (name, student_id) VALUES (?, ?)",
                    (name, student_id)
                )
                conn.commit()
                self.logger.info(f"Student registered: {name} ({student_id})")
                return True
        except sqlite3.IntegrityError:
            self.logger.warning(f"Student ID {student_id} already exists")
            return False
        except sqlite3.Error as e:
            self.logger.error(f"Error registering student: {e}")
            return False
    
    def mark_attendance(self, student_id):
        """Mark attendance for a student"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if student exists
                cursor.execute("SELECT name FROM students WHERE student_id = ?", (student_id,))
                student = cursor.fetchone()
                
                if not student:
                    self.logger.warning(f"Student ID {student_id} not found in database")
                    return False
                
                # Get current date and time
                current_date = datetime.now().strftime("%Y-%m-%d")
                current_time = datetime.now().strftime("%H:%M:%S")
                
                # Check if attendance already marked for today
                cursor.execute(
                    "SELECT id FROM attendance WHERE student_id = ? AND date = ?", 
                    (student_id, current_date)
                )
                
                if cursor.fetchone():
                    self.logger.info(f"Attendance already marked for student {student_id} today")
                    return True
                
                # Mark attendance
                cursor.execute(
                    "INSERT INTO attendance (student_id, date, time, status) VALUES (?, ?, ?, ?)",
                    (student_id, current_date, current_time, "present")
                )
                conn.commit()
                self.logger.info(f"Attendance marked for student {student_id} at {current_time}")
                return True
                
        except sqlite3.Error as e:
            self.logger.error(f"Error marking attendance: {e}")
            return False
    
    def get_attendance_report(self, date=None):
        """Get attendance report for a specific date or all dates"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if date:
                    cursor.execute("""
                        SELECT s.name, s.student_id, a.date, a.time, a.status
                        FROM attendance a
                        JOIN students s ON a.student_id = s.student_id
                        WHERE a.date = ?
                        ORDER BY a.time
                    """, (date,))
                else:
                    cursor.execute("""
                        SELECT s.name, s.student_id, a.date, a.time, a.status
                        FROM attendance a
                        JOIN students s ON a.student_id = s.student_id
                        ORDER BY a.date, a.time
                    """)
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            self.logger.error(f"Error getting attendance report: {e}")
            return []
