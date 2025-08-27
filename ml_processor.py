# ml_processor.py

import numpy as np
import pickle
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import StandardScaler
from datetime import datetime

# --- 1. ComplaintDBSCANClustering Class ---
# This class defines the structure of your clustered data for backend.
# The backend will primarily use the 'complaint_groups' attribute from the loaded .pkl file.
class ComplaintDBSCANClustering:
    def __init__(self, eps=0.5, min_samples=3, model_name='sentence-transformers/all-MiniLM-L6-v2'):
        self.eps = eps
        self.min_samples = min_samples
        self.model_name = model_name
        self.complaint_groups = {}
        self.clusters = None

    def get_high_priority_groups(self, min_priority=3):
        high_priority = {
            group_id: data for group_id, data in self.complaint_groups.items()
            if data['priority'] >= min_priority
        }
        return high_priority

# --- 2. RealtimeDBSCANProcessor Class ---
# This class is designed for processing a single new complaint in real-time.
class RealtimeDBSCANProcessor:
    def __init__(self, sentence_model: SentenceTransformer, complaint_groups: dict, eps_distance: float = 0.7):
        self.sentence_model = sentence_model
        self.complaint_groups = complaint_groups
        self.eps_distance = eps_distance
        self.scaler = StandardScaler()

    def process_new_complaint(self, new_complaint_text: str, new_lat: float, new_lon: float) -> dict:
        """
        Processes a new complaint to determine if it merges with an existing group or forms a new one.
        """
        new_embedding = self.sentence_model.encode([new_complaint_text]).reshape(1, -1)
        scaled_new_gps = self.scaler.fit_transform(np.array([[new_lat, new_lon]]))
        combined_new = np.hstack((new_embedding, scaled_new_gps))
        
        min_distance = float('inf')
        best_group_id = None
        
        for group_id, group_data in self.complaint_groups.items():
            representative_complaint_text = group_data['complaints'][0]['complaint']
            representative_embedding = self.sentence_model.encode([representative_complaint_text]).reshape(1, -1)
            scaled_rep_gps = self.scaler.fit_transform(np.array([[group_data['center_latitude'], group_data['center_longitude']]]))
            combined_rep = np.hstack((representative_embedding, scaled_rep_gps))
            
            distance = np.linalg.norm(combined_new - combined_rep)

            if distance < min_distance:
                min_distance = distance
                best_group_id = group_id
        
        # After checking ALL groups, make the final decision
        if min_distance <= self.eps_distance:
            return {
                'action': 'merged',
                'group_id': best_group_id,
                'distance': min_distance,
                'total_complaints': len(self.complaint_groups[best_group_id]['complaints'])
            }
        else:
            return {
                'action': 'new_group',
                'distance': min_distance,
                'total_complaints': 1
            }