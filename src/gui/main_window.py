import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
import os
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageTk
import threading
import time
import sys

from ..utils.config import Config
from ..utils.camera_utils import get_available_cameras
from ..utils.local_storage import LocalStorage
from ..face_recognition.recognizer import FaceRecognizer
from ..database.db_manager import DatabaseManager

class MainWindow:
    """Main application window for the attendance system"""
    
    def __init__(self, root):
        self.root = root
        self.config = Config()
        self.logger = logging.getLogger("attendance_system")
        
        # Initialize components
        self.db = DatabaseManager()  # Keep for compatibility with existing code
        self.local_storage = LocalStorage()  # Add local storage
        self.recognizer = FaceRecognizer()
        
        # Camera settings
        self.camera_source = self.config.get("camera", "source")
        self.frame_width = self.config.get("camera", "frame_width")
        self.frame_height = self.config.get("camera", "frame_height")
        
        # Available cameras
        self.available_cameras = []
        if self.config.get("camera", "detect_cameras", default=True):
            self.available_cameras = get_available_cameras()
        
        # Video capture variables
        self.cap = None
        self.is_capturing = False
        self.capture_thread = None
        
        # Track recognized people to avoid duplicate attendance marks
        self.recently_recognized = set()
        self.recognition_cooldown = 5  # seconds
        self.last_recognition_time = {}
        
        # Setup UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface"""
        app_name = self.config.get("app", "name")
        window_size = self.config.get("gui", "window_size")
        
        self.root.title(app_name)
        self.root.geometry(window_size)
        self.root.resizable(True, True)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True)
        
        # Create tabs
        self.tab_main = ttk.Frame(self.notebook)
        self.tab_register = ttk.Frame(self.notebook)
        self.tab_reports = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_main, text='Attendance')
        self.notebook.add(self.tab_register, text='Register Student')
        self.notebook.add(self.tab_reports, text='Reports')
        
        # Set up each tab
        self.setup_main_tab()
        self.setup_register_tab()
        self.setup_reports_tab()
        
        # Set up window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def setup_main_tab(self):
        """Set up the main attendance tracking tab"""
        # Create frames
        frame_controls = ttk.Frame(self.tab_main)
        frame_controls.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        frame_camera_selection = ttk.Frame(self.tab_main)
        frame_camera_selection.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))
        
        frame_video = ttk.Frame(self.tab_main)
        frame_video.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        frame_info = ttk.Frame(self.tab_main)
        frame_info.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        # Add a frame for multi-face detection info
        frame_multi_face = ttk.Frame(self.tab_main)
        frame_multi_face.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        
        # Face counting display
        self.face_count_var = tk.StringVar(value="Faces detected: 0")
        face_count_label = ttk.Label(frame_multi_face, textvariable=self.face_count_var, font=("Helvetica", 12, "bold"))
        face_count_label.pack(side=tk.LEFT)
        
        # Recent detections display (for multiple faces)
        self.recent_detections_var = tk.StringVar(value="Recent detections: None")
        recent_detections_label = ttk.Label(frame_info, textvariable=self.recent_detections_var)
        recent_detections_label.pack(side=tk.RIGHT)
        
        # Camera selection
        ttk.Label(frame_camera_selection, text="Select Camera:").pack(side=tk.LEFT, padx=5)
        
        # Create a StringVar for camera selection
        self.selected_camera = tk.StringVar(value=str(self.camera_source))
        
        # Create camera dropdown options
        camera_options = []
        if self.available_cameras:
            camera_options = [(f"{cam_name} (ID: {cam_id})", str(cam_id)) for cam_id, cam_name in self.available_cameras]
        else:
            # Default option if no cameras detected
            camera_options = [("Default Camera (ID: 0)", "0")]
            
        # Create the combobox
        self.camera_combo = ttk.Combobox(frame_camera_selection, textvariable=self.selected_camera, state="readonly", width=30)
        self.camera_combo['values'] = [option[0] for option in camera_options]
        
        # Set the initial selection to match camera_source
        for i, (_, cam_id) in enumerate(camera_options):
            if int(cam_id) == self.camera_source:
                self.camera_combo.current(i)
                break
        else:
            # If camera_source not in options, select first camera
            if camera_options:
                self.camera_combo.current(0)
                
        self.camera_combo.pack(side=tk.LEFT, padx=5)
        
        # Button to refresh camera list
        ttk.Button(frame_camera_selection, text="Refresh List", 
                   command=self.refresh_camera_list).pack(side=tk.LEFT, padx=5)
        
        # Control buttons
        self.btn_start = ttk.Button(frame_controls, text="Start Camera", command=self.start_camera)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = ttk.Button(frame_controls, text="Stop Camera", command=self.stop_camera, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        
        # Video display
        self.video_label = ttk.Label(frame_video)
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # Info display
        self.status_var = tk.StringVar(value="Camera: Off")
        status_label = ttk.Label(frame_info, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT)
        
        self.last_detection_var = tk.StringVar(value="Last detection: None")
        last_detection_label = ttk.Label(frame_info, textvariable=self.last_detection_var)
        last_detection_label.pack(side=tk.RIGHT)
    
    def refresh_camera_list(self):
        """Refresh the list of available cameras"""
        self.logger.info("Refreshing camera list")
        
        # Stop current camera if running
        was_capturing = self.is_capturing
        if was_capturing:
            self.stop_camera()
        
        # Re-detect cameras
        self.available_cameras = get_available_cameras()
        
        # Update dropdown options
        camera_options = []
        if self.available_cameras:
            camera_options = [(f"{cam_name} (ID: {cam_id})", str(cam_id)) for cam_id, cam_name in self.available_cameras]
        else:
            camera_options = [("Default Camera (ID: 0)", "0")]
            
        # Update combobox values
        self.camera_combo['values'] = [option[0] for option in camera_options]
        
        # Select first option in the list
        if camera_options:
            self.camera_combo.current(0)
            # Update the camera source
            for option in camera_options:
                if option[0] == self.camera_combo.get():
                    self.camera_source = int(option[1])
                    break
        
        # Restart camera if it was on
        if was_capturing:
            self.start_camera()
        
        messagebox.showinfo("Camera List", f"Found {len(self.available_cameras)} camera(s)")
    
    def start_camera(self):
        """Start the camera capture"""
        if self.is_capturing:
            return
        
        # Get the selected camera index
        selected_option = self.camera_combo.get()
        for option_text, option_id in [(f"{cam_name} (ID: {cam_id})", str(cam_id)) 
                                      for cam_id, cam_name in self.available_cameras]:
            if option_text == selected_option:
                self.camera_source = int(option_id)
                break
            
        self.logger.info(f"Starting camera with index: {self.camera_source}")
            
        try:
            self.cap = cv2.VideoCapture(self.camera_source)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
            
            if not self.cap.isOpened():
                messagebox.showerror("Error", f"Could not open camera with index {self.camera_source}")
                return
                
            self.is_capturing = True
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            self.status_var.set(f"Camera {self.camera_source}: On")
            
            # Start the capture thread
            self.capture_thread = threading.Thread(target=self.update_frame)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            
            self.logger.info(f"Camera {self.camera_source} started")
            
        except Exception as e:
            self.logger.error(f"Error starting camera {self.camera_source}: {e}")
            messagebox.showerror("Error", f"Could not start camera {self.camera_source}: {e}")
    
    def update_frame(self):
        """Update the video frame in a separate thread"""
        while self.is_capturing:
            ret, frame = self.cap.read()
            
            if not ret:
                self.logger.warning("Failed to grab frame")
                time.sleep(0.1)
                continue
                
            # Process the frame for face recognition
            face_locations, face_names, student_ids = self.recognizer.process_frame(frame)
            
            # Update face count display
            self.root.after(1, lambda count=len(face_locations): 
                           self.face_count_var.set(f"Faces detected: {count}"))
            
            # Track recognized people for display
            recognized_names = []
            current_time = time.time()
            
            # Process each detected face
            for name, student_id in zip(face_names, student_ids):
                if name != "Unknown" and student_id is not None:
                    # Add to recognized names list for display
                    recognized_names.append(name)
                    
                    # Check if this person was recently recognized (avoid duplicate marks)
                    if student_id not in self.last_recognition_time or \
                       (current_time - self.last_recognition_time[student_id]) > self.recognition_cooldown:
                        
                        self.logger.info(f"Recognized: {name} ({student_id})")
                        self.last_detection_var.set(f"Last detection: {name} ({student_id})")
                        
                        # Mark attendance in database AND local storage
                        self.db.mark_attendance(student_id)  # Original DB storage
                        self.local_storage.mark_attendance(student_id, name)  # Local storage
                        
                        # Update recognition time
                        self.last_recognition_time[student_id] = current_time
            
            # Update the recent detections display
            if recognized_names:
                if len(recognized_names) > 3:
                    # If more than 3 names, show first 2 and count
                    display_text = f"{recognized_names[0]}, {recognized_names[1]} +{len(recognized_names)-2} more"
                else:
                    display_text = ", ".join(recognized_names)
                self.root.after(1, lambda t=display_text: 
                               self.recent_detections_var.set(f"Recent detections: {t}"))
            
            # Annotate frame with bounding boxes and names
            annotated_frame = self.recognizer.annotate_frame(frame)
            
            # Convert to a format displayable by Tkinter
            cv2image = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            
            # Update UI in the main thread
            self.root.after(1, lambda: self.update_video_display(imgtk))
    
    def update_video_display(self, imgtk):
        """Update the video display in the main thread"""
        if self.is_capturing:
            self.video_label.configure(image=imgtk)
            self.video_label.image = imgtk
            
            current_tab = self.notebook.index(self.notebook.select())
            if current_tab == 1:  # Register tab
                self.register_video_label.configure(image=imgtk)
                self.register_video_label.image = imgtk
    
    def stop_camera(self):
        """Stop the camera capture"""
        self.is_capturing = False
        
        if self.capture_thread:
            self.capture_thread.join(1.0)  # Wait for thread to finish
        
        if self.cap:
            self.cap.release()
        
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status_var.set("Camera: Off")
        
        # Clear the video display
        self.video_label.configure(image='')
        self.register_video_label.configure(image='')
        
        self.logger.info("Camera stopped")
    
    def capture_photo(self):
        """Capture a photo for student registration"""
        if not self.is_capturing:
            messagebox.showwarning("Warning", "Camera is not active. Start camera first.")
            return
            
        student_id = self.entry_student_id.get().strip()
        name = self.entry_name.get().strip()
        
        if not student_id or not name:
            messagebox.showwarning("Warning", "Student ID and Name are required.")
            return
            
        # Capture current frame
        ret, frame = self.cap.read()
        if not ret:
            messagebox.showerror("Error", "Could not capture image")
            return
            
        self.captured_image = frame.copy()
        self.register_status_var.set("Image captured! Click 'Register Student' to complete.")
        
        self.logger.info(f"Photo captured for {name} ({student_id})")
    
    def register_student(self):
        """Register a new student"""
        student_id = self.entry_student_id.get().strip()
        name = self.entry_name.get().strip()
        
        if not student_id or not name:
            messagebox.showwarning("Warning", "Student ID and Name are required.")
            return
            
        if not hasattr(self, 'captured_image'):
            messagebox.showwarning("Warning", "Please capture a photo first.")
            return
            
        # Add the student to the database AND local storage
        db_success = self.db.register_student(name, student_id)
        local_success = self.local_storage.register_student(name, student_id)
        
        if db_success or local_success:  # Allow success from either storage method
            # Add the face to the recognizer
            if self.recognizer.add_face(self.captured_image, name, student_id):
                messagebox.showinfo("Success", f"Student {name} registered successfully!")
                self.entry_student_id.delete(0, tk.END)
                self.entry_name.delete(0, tk.END)
                del self.captured_image
                self.register_status_var.set("Registration complete")
                self.logger.info(f"Student registered: {name} ({student_id})")
            else:
                messagebox.showerror("Error", "Failed to process face. Please try again.")
        else:
            messagebox.showerror("Error", f"Student ID {student_id} already exists or storage error occurred.")
    
    def generate_report(self):
        """Generate an attendance report"""
        try:
            date = self.date_var.get().strip()
            
            # Validate date format
            try:
                if date:
                    datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Error", "Invalid date format. Please use YYYY-MM-DD")
                return
                
            # Clear existing data
            for item in self.report_tree.get_children():
                self.report_tree.delete(item)
                
            # First try to get records from database
            records = self.db.get_attendance_report(date)
            
            # If no records in database, try from local storage
            if not records:
                self.logger.info("No records in database, trying local storage")
                records = self.local_storage.get_attendance_report(date)
                
            if not records:
                self.logger.info("No attendance records found")
                messagebox.showinfo("Information", "No attendance records found for the specified date.")
                return
                
            # Display records in the treeview
            for record in records:
                self.report_tree.insert("", tk.END, values=(
                    record["name"],
                    record["student_id"],
                    record["date"],
                    record["time"],
                    record["status"]
                ))
                
            self.logger.info(f"Generated report for {date if date else 'all dates'}")
                
        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            messagebox.showerror("Error", f"Could not generate report: {e}")
    
    def export_report(self):
        """Export the attendance report to a CSV file"""
        try:
            # Get the date from the filter
            date = self.date_var.get().strip()
            
            # First try to get records from database
            records = self.db.get_attendance_report(date)
            
            # If no records in database, try from local storage
            if not records:
                records = self.local_storage.get_attendance_report(date)
            
            if not records:
                messagebox.showwarning("Warning", "No records to export")
                return
                
            # Ask for save location
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Save Attendance Report"
            )
            
            if not filename:
                return
                
            # Save to CSV
            df = pd.DataFrame(records)
            df.to_csv(filename, index=False)
            
            messagebox.showinfo("Success", f"Report exported to {filename}")
            self.logger.info(f"Report exported to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error exporting report: {e}")
            messagebox.showerror("Error", f"Could not export report: {e}")
    
    def on_close(self):
        """Handle window close event"""
        self.stop_camera()
        self.logger.info("Application closed")
        self.root.destroy()
    
    def setup_register_tab(self):
        """Set up the student registration tab"""
        # Create frames
        frame_form = ttk.Frame(self.tab_register)
        frame_form.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        frame_photo = ttk.Frame(self.tab_register)
        frame_photo.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Form fields
        ttk.Label(frame_form, text="Student ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.entry_student_id = ttk.Entry(frame_form, width=30)
        self.entry_student_id.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(frame_form, text="Name:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.entry_name = ttk.Entry(frame_form, width=30)
        self.entry_name.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Photo capture
        self.register_video_label = ttk.Label(frame_photo)
        self.register_video_label.pack(fill=tk.BOTH, expand=True)
        
        frame_reg_controls = ttk.Frame(self.tab_register)
        frame_reg_controls.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        self.btn_capture_photo = ttk.Button(frame_reg_controls, text="Capture Photo", command=self.capture_photo)
        self.btn_capture_photo.pack(side=tk.LEFT, padx=5)
        
        self.btn_register = ttk.Button(frame_reg_controls, text="Register Student", command=self.register_student)
        self.btn_register.pack(side=tk.RIGHT, padx=5)
        
        # Register camera status
        self.register_status_var = tk.StringVar(value="Ready")
        register_status_label = ttk.Label(frame_reg_controls, textvariable=self.register_status_var)
        register_status_label.pack(side=tk.LEFT, padx=20)
        
        # Add note about camera
        camera_note = ttk.Label(self.tab_register, 
                               text="Note: Camera selection is controlled in the Attendance tab")
        camera_note.pack(side=tk.BOTTOM, padx=10, pady=(0, 10))
    
    def setup_reports_tab(self):
        """Set up the attendance reports tab"""
        # Create frames
        frame_filters = ttk.Frame(self.tab_reports)
        frame_filters.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        frame_report = ttk.Frame(self.tab_reports)
        frame_report.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Date filter
        ttk.Label(frame_filters, text="Date:").pack(side=tk.LEFT, padx=5)
        
        today = datetime.now().strftime("%Y-%m-%d")
        self.date_var = tk.StringVar(value=today)
        self.date_entry = ttk.Entry(frame_filters, textvariable=self.date_var, width=15)
        self.date_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame_filters, text="View Report", command=self.generate_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_filters, text="Export to CSV", command=self.export_report).pack(side=tk.RIGHT, padx=5)
        
        # Report display as table
        self.report_tree = ttk.Treeview(frame_report, columns=("Name", "ID", "Date", "Time", "Status"), show="headings")
        
        # Define headings
        self.report_tree.heading("Name", text="Name")
        self.report_tree.heading("ID", text="Student ID")
        self.report_tree.heading("Date", text="Date")
        self.report_tree.heading("Time", text="Time")
        self.report_tree.heading("Status", text="Status")
        
        # Define columns
        self.report_tree.column("Name", width=150)
        self.report_tree.column("ID", width=100)
        self.report_tree.column("Date", width=100)
        self.report_tree.column("Time", width=100)
        self.report_tree.column("Status", width=100)
        
        # Add a scrollbar
        scrollbar = ttk.Scrollbar(frame_report, orient=tk.VERTICAL, command=self.report_tree.yview)
        self.report_tree.configure(yscroll=scrollbar.set)
        
        # Pack the treeview and scrollbar
        self.report_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
