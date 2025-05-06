import cv2
import face_recognition
import numpy as np
import os
import logging
import pickle
from pathlib import Path
from datetime import datetime
from ..utils.config import Config

class FaceRecognizer:
    """Handle face recognition operations"""
    
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger("attendance_system")
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        self.process_current_frame = True
        
        # Load recognition settings
        self.tolerance = self.config.get("recognition", "tolerance")
        self.frame_reduction = self.config.get("recognition", "frame_reduction")
        self.model = self.config.get("recognition", "model")
        
        # Load known faces
        self.load_known_faces()
    
    def load_known_faces(self):
        """Load known faces from the database or encodings file"""
        known_faces_dir = Path(self.config.get("paths", "known_faces_dir"))
        encoding_file = known_faces_dir / "encodings.pkl"
        
        if encoding_file.exists():
            self.logger.info("Loading pre-computed face encodings")
            with open(encoding_file, 'rb') as f:
                data = pickle.load(f)
                self.known_face_encodings = data['encodings']
                self.known_face_names = data['names']
                self.known_face_ids = data['ids']
            self.logger.info(f"Loaded {len(self.known_face_encodings)} face encodings")
            return
            
        # If no encoding file, then process all images in the directory
        self.logger.info("Processing face images to create encodings")
        known_faces_dir.mkdir(parents=True, exist_ok=True)
        
        for student_dir in known_faces_dir.glob("*"):
            if not student_dir.is_dir():
                continue
                
            name = student_dir.name
            student_id = student_dir.name  # Assuming directory name is the student ID
            
            for image_file in student_dir.glob("*.jpg"):
                try:
                    image = face_recognition.load_image_file(image_file)
                    encoding = face_recognition.face_encodings(image)
                    
                    if len(encoding) > 0:
                        self.known_face_encodings.append(encoding[0])
                        self.known_face_names.append(name)
                        self.known_face_ids.append(student_id)
                        self.logger.info(f"Added encoding for {name} ({student_id})")
                    else:
                        self.logger.warning(f"No face found in {image_file}")
                        
                except Exception as e:
                    self.logger.error(f"Error processing {image_file}: {e}")
        
        # Save encodings if any were created
        if self.known_face_encodings:
            data = {
                'encodings': self.known_face_encodings,
                'names': self.known_face_names,
                'ids': self.known_face_ids
            }
            with open(encoding_file, 'wb') as f:
                pickle.dump(data, f)
            self.logger.info(f"Saved {len(self.known_face_encodings)} face encodings")
    
    def add_face(self, image, name, student_id):
        """Add a new face to the known faces"""
        try:
            known_faces_dir = Path(self.config.get("paths", "known_faces_dir"))
            student_dir = known_faces_dir / student_id
            student_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_file = student_dir / f"{timestamp}.jpg"
            cv2.imwrite(str(image_file), image)
            
            # Get face encoding
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            encodings = face_recognition.face_encodings(rgb_image)
            
            if len(encodings) == 0:
                self.logger.warning(f"No face found in the image for {name}")
                return False
            
            # Add to known faces
            self.known_face_encodings.append(encodings[0])
            self.known_face_names.append(name)
            self.known_face_ids.append(student_id)
            
            # Update encodings file
            encoding_file = known_faces_dir / "encodings.pkl"
            data = {
                'encodings': self.known_face_encodings,
                'names': self.known_face_names,
                'ids': self.known_face_ids
            }
            with open(encoding_file, 'wb') as f:
                pickle.dump(data, f)
            
            self.logger.info(f"Added new face for {name} ({student_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding face: {e}")
            return False
    
    def process_frame(self, frame):
        """Process a video frame and recognize faces"""
        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=1/self.frame_reduction, fy=1/self.frame_reduction)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Find faces in frame
        self.face_locations = face_recognition.face_locations(rgb_small_frame, model=self.model)
        
        # Log the number of faces detected
        if len(self.face_locations) > 1:
            self.logger.info(f"Multiple faces detected: {len(self.face_locations)}")
        
        self.face_encodings = face_recognition.face_encodings(rgb_small_frame, self.face_locations)
        
        self.face_names = []
        self.matched_ids = []
        
        # For each detected face, try to identify it
        for face_encoding in self.face_encodings:
            name = "Unknown"
            student_id = None
            
            # Check if face matches any known face
            if len(self.known_face_encodings) > 0:
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=self.tolerance)
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                
                if len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = self.known_face_names[best_match_index]
                        student_id = self.known_face_ids[best_match_index]
            
            self.face_names.append(name)
            self.matched_ids.append(student_id)
        
        return self.face_locations, self.face_names, self.matched_ids
    
    def annotate_frame(self, frame):
        """Add bounding boxes and names to the frame"""
        # Restore to original scale for display
        for (top, right, bottom, left), name in zip(self.face_locations, self.face_names):
            top *= self.frame_reduction
            right *= self.frame_reduction
            bottom *= self.frame_reduction
            left *= self.frame_reduction
            
            # Draw a rectangle around the face with different colors for known vs unknown faces
            color = (0, 255, 0)  # Green for known faces
            if name == "Unknown":
                color = (0, 0, 255)  # Red for unknown faces
                
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            
            # Draw a label with a name below the face
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)
            
        # Add count of faces detected to the frame
        face_count = len(self.face_locations)
        text = f"Faces Detected: {face_count}"
        cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        return frame
