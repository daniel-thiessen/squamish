#!/usr/bin/env python3
"""
Analyze GPX file to understand the route data structure and calculate distances.
"""

import xml.etree.ElementTree as ET
import math

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    Returns distance in meters
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in meters
    r = 6371000
    
    return c * r

def analyze_gpx(gpx_file):
    """Analyze the GPX file and calculate cumulative distances."""
    tree = ET.parse(gpx_file)
    root = tree.getroot()
    
    # Handle namespace
    namespace = {'': 'http://www.topografix.com/GPX/1/1'}
    
    # Find all track points
    trkpts = root.findall('.//trkpt', namespace)
    
    if not trkpts:
        print("No track points found in GPX file")
        return
    
    print(f"Found {len(trkpts)} track points")
    
    # Calculate cumulative distances
    cumulative_distance = 0
    distances = [0]  # Start with 0 distance
    
    prev_lat = float(trkpts[0].get('lat'))
    prev_lon = float(trkpts[0].get('lon'))
    
    for i, trkpt in enumerate(trkpts[1:], 1):
        lat = float(trkpt.get('lat'))
        lon = float(trkpt.get('lon'))
        
        # Calculate distance from previous point
        segment_distance = haversine_distance(prev_lat, prev_lon, lat, lon)
        cumulative_distance += segment_distance
        distances.append(cumulative_distance)
        
        # Update previous coordinates
        prev_lat = lat
        prev_lon = lon
        
        # Print some sample points
        if i <= 5 or i % 1000 == 0:
            ele = trkpt.find('ele', namespace)
            elevation = float(ele.text) if ele is not None else 0
            print(f"Point {i}: lat={lat:.6f}, lon={lon:.6f}, ele={elevation:.1f}m, cum_dist={cumulative_distance/1000:.3f}km")
    
    total_distance_km = cumulative_distance / 1000
    print(f"\nTotal route distance: {total_distance_km:.2f} km")
    
    return distances, trkpts

if __name__ == "__main__":
    gpx_file = "CMTR - Squamish 50 - 50-mile route (2025).gpx"
    analyze_gpx(gpx_file)