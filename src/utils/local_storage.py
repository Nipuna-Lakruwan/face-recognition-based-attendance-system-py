import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from .config import Config

class LocalStorage:
    """Utility class to handle temporary local storage operations"""
    
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger("attendance_system")
        self.project_root = Path(__file__).parent.parent.parent
        
        # Create a local storage directory
        self.storage_dir = self.project_root / "data" / "local_storage"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.attendance_file = self.storage_dir / "attendance_records.json"
        
        # Initialize storage files if they don't exist
        self._init_storage_files()
        
    def _init_storage_files(self):
        """Initialize storage files if they don't exist"""
        # Attendance records file
        if not self.attendance_file.exists():
            self._save_data(self.attendance_file, [])
            
    def _load_data(self, file_path: Path) -> Any:
        """Load data from a JSON file"""
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading data from {file_path}: {e}")
            return None
            
    def _save_data(self, file_path: Path, data: Any) -> bool:
        """Save data to a JSON file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except Exception as e:
            self.logger.error(f"Error saving data to {file_path}: {e}")
            return False
            
    def mark_attendance(self, student_id: str, name: str) -> bool:
        """Mark attendance for a student"""
        # Load current attendance records
        records = self._load_data(self.attendance_file) or []
        
        # Get current date and time
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Check if already marked for today
        for record in records:
            if record.get("student_id") == student_id and record.get("date") == current_date:
                self.logger.info(f"Attendance already marked for student {name} ({student_id}) today")
                return True
                
        # Add new attendance record
        new_record = {
            "student_id": student_id,
            "name": name,
            "date": current_date,
            "time": current_time,
            "status": "present"
        }
        
        records.append(new_record)
        
        # Save updated records
        success = self._save_data(self.attendance_file, records)
        if success:
            self.logger.info(f"Attendance marked for student {name} ({student_id}) at {current_time}")
        return success
        
    def get_attendance_report(self, date=None) -> List[Dict]:
        """Get attendance report for a specific date or all dates"""
        records = self._load_data(self.attendance_file) or []
        
        if date:
            # Filter records for the specified date
            return [record for record in records if record.get("date") == date]
        
        return records
        
    def register_student(self, name: str, student_id: str) -> bool:
        """Register a new student"""
        # In a real implementation, you would save this to a students file
        # For this demo, we'll just log it as the face recognition system will handle the face data
        self.logger.info(f"Student registered: {name} ({student_id})")
        return True
