import os
import yaml
from pathlib import Path

class Config:
    """Configuration manager for the application"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """Load configuration from yaml file"""
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config.yaml"
        
        with open(config_path, 'r') as config_file:
            self.config = yaml.safe_load(config_file)
            
        # Ensure directories exist
        for path_key in ['known_faces_dir', 'attendance_records', 'logs']:
            path = project_root / self.config['paths'][path_key]
            path.mkdir(parents=True, exist_ok=True)
    
    def get(self, section, key=None, default=None):
        """Get configuration value with optional default
        
        Args:
            section: The configuration section
            key: The specific key within the section (optional)
            default: Default value to return if the key doesn't exist
            
        Returns:
            The configuration value or default if not found
        """
        if key is not None:
            section_dict = self.config.get(section, {})
            return section_dict.get(key, default)
        return self.config.get(section, {})
