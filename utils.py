import json
import os

#This file handles general utilities (data loading, etc.)

def load_past_scans(file_path="past_scans.json"):
    """Load past scans from a JSON file."""
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return []
