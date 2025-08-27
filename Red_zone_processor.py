import pandas as pd
import numpy as np
import json
import warnings

warnings.filterwarnings('ignore')

class RedZoneDetector:
    def __init__(self, grid_size_meters=500):
        self.grid_size_meters = grid_size_meters
        self.grid_data = {}

    def _get_grid_id(self, lat, lon):
        """
        Calculates a unique ID for a grid square based on its coordinates.
        This function is the heart of the grid-based system.
        """
        lat_per_meter = 1 / 111111
        lon_per_meter = 1 / (111111 * np.cos(np.radians(lat)))
        
        grid_lat = int(lat / (self.grid_size_meters * lat_per_meter))
        grid_lon = int(lon / (self.grid_size_meters * lon_per_meter))
        
        return f"{grid_lat}_{grid_lon}"

    def assign_complaints_to_grids(self, complaints: pd.DataFrame):
        """
        Assigns each complaint to its corresponding grid square and counts them.
        This is a batch process that should be run periodically to update the map.
        """
        self.grid_data = {}
        for _, row in complaints.iterrows():
            grid_id = self._get_grid_id(row['latitude'], row['longitude'])
            if grid_id not in self.grid_data:
                self.grid_data[grid_id] = {'count': 0, 'complaints': []}
            self.grid_data[grid_id]['count'] += 1
            self.grid_data[grid_id]['complaints'].append(row.to_dict())

    def get_map_data(self):
        """
        Prepares the data for frontend visualization in a JSON format.
        This is the final output that the backend will serve to the frontend.
        """
        map_data = {'zones': []}
        for grid_id, data in self.grid_data.items():
            count = data['count']
            
            # Assign a risk level and color based on the number of complaints
            if count >= 50: risk, color = "RED", "#FF0000"
            elif count >= 25: risk, color = "ORANGE", "#FFA500"
            elif count >= 10: risk, color = "YELLOW", "#FFFF00"
            else: risk, color = "GREEN", "#00FF00"
            
            # Calculate the center point of the complaints for the map
            if count > 0:
                lats = [c['latitude'] for c in data['complaints']]
                lons = [c['longitude'] for c in data['complaints']]
                center_lat, center_lon = np.mean(lats), np.mean(lons)
                map_data['zones'].append({
                    'grid_id': grid_id, 
                    'complaint_count': count, 
                    'risk_level': risk,
                    'color': color, 
                    'center_lat': center_lat, 
                    'center_lon': center_lon
                })
        return map_data