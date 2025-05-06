# Face Recognition Based Attendance System

A modern, real-time attendance tracking system that uses computer vision and facial recognition technology to automatically mark student attendance.

## Features

- Real-time face detection and recognition
- **Multi-face detection** - can identify multiple students simultaneously in a single frame
- Automated attendance tracking with timestamp recording
- Student registration with photo capture
- Local storage backup for offline operation
- Attendance reporting and analytics
- Export attendance reports to CSV
- Camera selection for multi-camera setups
- User-friendly GUI interface

## Requirements

- Python 3.8+
- OpenCV
- face_recognition library
- Other dependencies listed in requirements.txt

## Installation

1. Clone this repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
   
   Note: The face_recognition library requires dlib, which may need additional setup:
   - On Windows: You may need to install Visual C++ build tools
   - On Linux: You may need to install development libraries for building dlib

## Usage

1. Run the application:
   ```
   python main.py
   ```

2. Register students:
   - Go to the "Register Student" tab
   - Enter student details
   - Click "Start Camera" if not already started
   - Click "Capture Photo" to take a photo
   - Click "Register Student" to complete registration

3. Track attendance:
   - Go to the "Attendance" tab
   - Select your preferred camera from the dropdown
   - Click "Start Camera"
   - The system will automatically recognize registered students and mark attendance
   - Multiple students can be detected and marked simultaneously

4. Generate reports:
   - Go to the "Reports" tab
   - Enter a date or leave blank for all dates
   - Click "View Report" to see attendance records
   - Click "Export to CSV" to save the report

## Multi-Face Detection

This system features advanced multi-face detection capabilities:

- Can detect and recognize multiple students in a single frame
- Displays face count in real-time
- Uses color-coding to distinguish between known faces (green) and unknown faces (red)
- Processes attendance for all recognized students simultaneously
- Maintains individual cooldown timers to prevent duplicate attendance records

## Configuration

The system can be configured by editing the `config.yaml` file:

```yaml
recognition:
  tolerance: 0.6  # Lower for stricter matching, higher for more lenient matching
  frame_reduction: 4  # Higher values improve performance but may reduce accuracy
  model: "hog"  # "hog" is faster, "cnn" is more accurate but requires GPU
  multi_face:
    enabled: true
    max_faces: 10  # Maximum number of faces to detect in a single frame
```

## Troubleshooting

- **Camera not detected**: Try refreshing the camera list or specifying a different camera index
- **Face not recognized**: Try adjusting lighting conditions or decreasing the recognition tolerance
- **Multiple false detections**: Increase the recognition tolerance for stricter matching
- **Performance issues**: Try increasing the frame_reduction value in config.yaml

## Project Structure

The project is organized as follows:

```
face-recognition-based-attendance-system/
│
├── main.py                 # Main application script
├── config.yaml             # Configuration file
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
│
├── data/                   # Directory for storing student data and photos
│   ├── students/           # Subdirectory for student photos
│   └── attendance/         # Subdirectory for attendance records
│
├── models/                 # Directory for storing machine learning models
│
├── utils/                  # Utility scripts and helper functions
│   ├── face_recognition.py # Face recognition related functions
│   └── camera.py           # Camera handling functions
│
└── gui/                    # GUI related scripts and resources
    ├── main_window.py      # Main window script
    └── register_window.py  # Student registration window script
```

## Contribution Guidelines

We welcome contributions to improve this project! Here are some guidelines:

1. Fork the repository
2. Create a new branch (`git checkout -b feature-branch`)
3. Make your changes
4. Commit your changes (`git commit -m 'Add some feature'`)
5. Push to the branch (`git push origin feature-branch`)
6. Create a new Pull Request

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

## Acknowledgements

- [OpenCV](https://opencv.org/)
- [face_recognition](https://github.com/ageitgey/face_recognition)
- [dlib](http://dlib.net/)

