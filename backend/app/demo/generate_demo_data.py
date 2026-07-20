import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import math

def generate_circular_patrol(center_lat, center_lon, radius_km, altitude, duration_minutes, start_time, points=500):
    """Generate a circular patrol pattern."""
    t = np.linspace(0, 2*np.pi, points)
    timestamps = [start_time + timedelta(minutes=duration_minutes*i/points) for i in range(points)]
    
    # Convert radius from km to degrees (approximate)
    radius_lat = radius_km / 111.32  # 1 degree = 111.32 km
    radius_lon = radius_km / (111.32 * np.cos(np.radians(center_lat)))
    
    latitude = center_lat + radius_lat * np.sin(t)
    longitude = center_lon + radius_lon * np.cos(t)
    
    # Add some altitude variation
    altitude_variation = np.sin(t * 2) * 20  # ±20m variation
    altitudes = altitude + altitude_variation

    # Calculate heading (direction of movement)
    heading = (np.degrees(np.arctan2(np.diff(longitude, append=longitude[0]), 
                                   np.diff(latitude, append=latitude[0]))) + 360) % 360
    
    return pd.DataFrame({
        'timestamp': timestamps,
        'latitude': latitude,
        'longitude': longitude,
        'altitude': altitudes,
        'heading': heading
    })

def generate_grid_search(start_lat, start_lon, width_km, height_km, altitude, duration_minutes, start_time, rows=5):
    """Generate a grid search pattern."""
    points_per_row = 50
    total_points = rows * points_per_row
    timestamps = [start_time + timedelta(minutes=duration_minutes*i/total_points) for i in range(total_points)]
    
    # Convert dimensions to degrees
    width_lat = width_km / 111.32
    height_lon = height_km / (111.32 * np.cos(np.radians(start_lat)))
    
    latitudes = []
    longitudes = []
    headings = []
    
    for i in range(rows):
        row_lat = start_lat + (i * width_lat / rows)
        if i % 2 == 0:
            # Left to right
            lons = np.linspace(start_lon, start_lon + height_lon, points_per_row)
            headings.extend([90] * points_per_row)
        else:
            # Right to left
            lons = np.linspace(start_lon + height_lon, start_lon, points_per_row)
            headings.extend([270] * points_per_row)
        
        latitudes.extend([row_lat] * points_per_row)
        longitudes.extend(lons)
    
    # Add some altitude variation
    altitude_variation = np.sin(np.linspace(0, 4*np.pi, total_points)) * 15
    altitudes = altitude + altitude_variation
    
    return pd.DataFrame({
        'timestamp': timestamps,
        'latitude': latitudes,
        'longitude': longitudes,
        'altitude': altitudes,
        'heading': headings
    })

def generate_point_to_point(start_lat, start_lon, end_lat, end_lon, altitude, duration_minutes, start_time, points=200):
    """Generate a point-to-point flight with realistic acceleration and deceleration."""
    timestamps = [start_time + timedelta(minutes=duration_minutes*i/points) for i in range(points)]
    
    # Use sigmoid function for smooth acceleration and deceleration
    t = np.linspace(-6, 6, points)
    progress = 1 / (1 + np.exp(-t))
    
    latitude = start_lat + (end_lat - start_lat) * progress
    longitude = start_lon + (end_lon - start_lon) * progress
    
    # Add some altitude variation
    altitude_variation = np.sin(np.linspace(0, 4*np.pi, points)) * 10
    altitudes = altitude + altitude_variation
    
    # Calculate heading
    heading = math.degrees(math.atan2(end_lon - start_lon, end_lat - start_lat))
    if heading < 0:
        heading += 360
    headings = [heading] * points
    
    return pd.DataFrame({
        'timestamp': timestamps,
        'latitude': latitude,
        'longitude': longitude,
        'altitude': altitudes,
        'heading': headings
    })

def main():
    # Set the base time for the simulation
    start_time = datetime(2024, 1, 1, 12, 0)  # Start at noon
    
    # Define base location (example: Central Park, NYC)
    base_lat, base_lon = 40.7829, -73.9654
    
    # Generate data for multiple drones
    drones_data = []
    
    # Drone 1: Circular patrol
    df1 = generate_circular_patrol(
        center_lat=base_lat,
        center_lon=base_lon,
        radius_km=1,
        altitude=150,
        duration_minutes=30,
        start_time=start_time
    )
    df1['aircraft_id'] = 'PATROL01'
    drones_data.append(df1)
    
    # Drone 2: Grid search pattern
    df2 = generate_grid_search(
        start_lat=base_lat - 0.02,
        start_lon=base_lon - 0.02,
        width_km=2,
        height_km=2,
        altitude=120,
        duration_minutes=45,
        start_time=start_time + timedelta(minutes=5)
    )
    df2['aircraft_id'] = 'SEARCH01'
    drones_data.append(df2)
    
    # Drone 3: Point-to-point delivery
    df3 = generate_point_to_point(
        start_lat=base_lat + 0.01,
        start_lon=base_lon - 0.01,
        end_lat=base_lat - 0.01,
        end_lon=base_lon + 0.01,
        altitude=100,
        duration_minutes=15,
        start_time=start_time + timedelta(minutes=10)
    )
    df3['aircraft_id'] = 'DELIV01'
    drones_data.append(df3)
    
    # Drone 4: Another circular patrol (different radius and altitude)
    df4 = generate_circular_patrol(
        center_lat=base_lat + 0.005,
        center_lon=base_lon + 0.005,
        radius_km=0.8,
        altitude=180,
        duration_minutes=25,
        start_time=start_time + timedelta(minutes=15)
    )
    df4['aircraft_id'] = 'PATROL02'
    drones_data.append(df4)
    
    # Drone 5: Emergency response (fast point-to-point)
    df5 = generate_point_to_point(
        start_lat=base_lat - 0.015,
        start_lon=base_lon - 0.015,
        end_lat=base_lat + 0.015,
        end_lon=base_lon + 0.015,
        altitude=200,
        duration_minutes=10,
        start_time=start_time + timedelta(minutes=20)
    )
    df5['aircraft_id'] = 'EMERG01'
    drones_data.append(df5)
    
    # Combine all drone data
    combined_df = pd.concat(drones_data, ignore_index=True)
    combined_df = combined_df.sort_values('timestamp')
    
    # Save to CSV
    combined_df.to_csv('demo_drone_data.csv', index=False)
    print(f"Generated demo data with {len(combined_df)} total records")
    print(f"Time range: {combined_df['timestamp'].min()} to {combined_df['timestamp'].max()}")
    print(f"Number of drones: {len(combined_df['aircraft_id'].unique())}")
    print(f"Drone IDs: {', '.join(combined_df['aircraft_id'].unique())}")

if __name__ == '__main__':
    main() 