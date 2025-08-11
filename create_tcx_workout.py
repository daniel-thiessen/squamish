#!/usr/bin/env python3
"""
Convert Squamish 50-mile pacing CSV to TCX workout file using GPX-based distances.
This version uses the actual GPS track to calculate more accurate distances for pacing zones.
TCX files can be imported into Garmin Connect and then synced to devices.
"""

import csv
import sys
import os
import math
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from xml.dom import minidom

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

def parse_gpx_route(gpx_file):
    """Parse GPX file and return track points with cumulative distances."""
    tree = ET.parse(gpx_file)
    root = tree.getroot()
    
    # Handle namespace
    namespace = {'': 'http://www.topografix.com/GPX/1/1'}
    
    # Find all track points
    trkpts = root.findall('.//trkpt', namespace)
    
    if not trkpts:
        raise ValueError("No track points found in GPX file")
    
    print(f"Processing {len(trkpts)} track points from GPX file...")
    
    # Calculate cumulative distances
    cumulative_distance = 0
    route_data = []
    
    for i, trkpt in enumerate(trkpts):
        lat = float(trkpt.get('lat'))
        lon = float(trkpt.get('lon'))
        
        # Get elevation if available
        ele_elem = trkpt.find('ele', namespace)
        elevation = float(ele_elem.text) if ele_elem is not None else 0
        
        if i > 0:
            # Calculate distance from previous point
            prev_lat, prev_lon = route_data[-1]['lat'], route_data[-1]['lon']
            segment_distance = haversine_distance(prev_lat, prev_lon, lat, lon)
            cumulative_distance += segment_distance
        
        route_data.append({
            'lat': lat,
            'lon': lon,
            'elevation': elevation,
            'cumulative_distance_m': cumulative_distance
        })
    
    total_distance_km = cumulative_distance / 1000
    print(f"Total GPS route distance: {total_distance_km:.2f} km")
    
    return route_data

def map_csv_segments_to_gpx(csv_segments, route_data):
    """Map CSV segment boundaries to actual GPS track positions."""
    total_gpx_distance_km = route_data[-1]['cumulative_distance_m'] / 1000
    total_csv_distance_km = csv_segments[-1]['End_km']
    
    print(f"CSV total distance: {total_csv_distance_km:.1f} km")
    print(f"GPX total distance: {total_gpx_distance_km:.2f} km")
    
    # Create scaling factor to map CSV distances to GPS distances
    scale_factor = total_gpx_distance_km / total_csv_distance_km
    print(f"Scaling factor: {scale_factor:.4f}")
    
    mapped_segments = []
    
    for segment in csv_segments:
        # Scale the CSV distances to match the GPX route
        start_km_gpx = segment['Start_km'] * scale_factor
        end_km_gpx = segment['End_km'] * scale_factor
        
        # Convert to meters
        start_m_gpx = start_km_gpx * 1000
        end_m_gpx = end_km_gpx * 1000
        
        # Calculate actual distance for this segment
        distance_m = end_m_gpx - start_m_gpx
        
        mapped_segment = {
            'start_km_original': segment['Start_km'],
            'end_km_original': segment['End_km'],
            'start_km_gpx': start_km_gpx,
            'end_km_gpx': end_km_gpx,
            'distance_m': distance_m,
            'segment_name': segment['Segment'],
            'target_pace': segment['Target_Pace'],
            'terrain': segment['Terrain'],
            'elev_change': segment['Elev_Change_m']
        }
        
        mapped_segments.append(mapped_segment)
        
        print(f"Segment: {segment['Segment'][:30]:<30} | "
              f"Original: {segment['Start_km']:4.1f}-{segment['End_km']:4.1f}km | "
              f"GPX: {start_km_gpx:5.2f}-{end_km_gpx:5.2f}km | "
              f"Distance: {distance_m/1000:.2f}km")
    
    return mapped_segments

def parse_pace_range(pace_str):
    """Parse pace range string like '7:00-7:20/km' to average pace in seconds per km."""
    if not pace_str or '/' not in pace_str:
        return 480  # Default to 8:00/km if parsing fails
    
    pace_part = pace_str.split('/')[0]  # Remove '/km'
    
    if '-' in pace_part:
        # Handle range like '7:00-7:20'
        start_pace, end_pace = pace_part.split('-')
        start_seconds = parse_single_pace(start_pace)
        end_seconds = parse_single_pace(end_pace)
        return (start_seconds + end_seconds) // 2
    else:
        # Handle single pace
        return parse_single_pace(pace_part)

def parse_single_pace(pace_str):
    """Parse single pace string like '7:20' to seconds per km."""
    try:
        minutes, seconds = pace_str.split(':')
        return int(minutes) * 60 + int(seconds)
    except:
        return 480  # Default to 8:00/km if parsing fails

def pace_to_speed_mps(pace_seconds_per_km):
    """Convert pace in seconds per km to speed in meters per second."""
    if pace_seconds_per_km <= 0:
        return 3.0  # Default speed
    return 1000.0 / pace_seconds_per_km

def create_tcx_workout(csv_file, gpx_file, output_file):
    """Create a TCX workout file using GPX-based distances."""
    
    # Parse the GPX route
    route_data = parse_gpx_route(gpx_file)
    
    # Read CSV segments
    csv_segments = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_segments.append({
                'Start_km': float(row['Start_km']),
                'End_km': float(row['End_km']),
                'Elev_Change_m': row['Elev_Change_m'],
                'Terrain': row['Terrain'],
                'Target_Pace': row['Target_Pace'],
                'Segment': row['Segment']
            })
    
    # Map CSV segments to GPX distances
    mapped_segments = map_csv_segments_to_gpx(csv_segments, route_data)
    
    # Create TCX workout
    # Create root element
    root = ET.Element("TrainingCenterDatabase")
    root.set("xmlns", "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xsi:schemaLocation", "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd")
    
    # Create Workouts element
    workouts = ET.SubElement(root, "Workouts")
    
    # Create Workout element
    workout = ET.SubElement(workouts, "Workout")
    workout.set("Sport", "Running")
    
    # Workout name
    name = ET.SubElement(workout, "Name")
    name.text = "Squamish 50 Mile 14h Pacing (GPX-based)"
    
    # Create workout steps
    step_index = 0
    
    for segment in mapped_segments:
        try:
            distance_m = int(segment['distance_m'])
            
            target_pace = segment['target_pace']
            pace_seconds_per_km = parse_pace_range(target_pace)
            target_speed_mps = pace_to_speed_mps(pace_seconds_per_km)
            
            segment_name = segment['segment_name']
            
            # Create Step element
            step = ET.SubElement(workout, "Step")
            step.set("xsi:type", "Step_t")
            
            # Step ID
            step_id = ET.SubElement(step, "StepId")
            step_id.text = str(step_index)
            
            # Step Name - include GPX distance for reference
            step_name = ET.SubElement(step, "Name")
            step_name.text = f"{segment_name}"
            
            # Duration
            duration = ET.SubElement(step, "Duration")
            duration.set("xsi:type", "Distance_t")
            meters = ET.SubElement(duration, "Meters")
            meters.text = str(distance_m)
            
            # Intensity
            intensity = ET.SubElement(step, "Intensity")
            intensity.text = "Active"
            
            # Target - Speed
            target = ET.SubElement(step, "Target")
            target.set("xsi:type", "Speed_t")
            
            speed_zone = ET.SubElement(target, "SpeedZone")
            speed_zone.set("xsi:type", "CustomSpeedZone_t")
            
            # Target speed range (± 5%)
            low_speed = target_speed_mps * 0.95
            high_speed = target_speed_mps * 1.05
            
            view_as = ET.SubElement(speed_zone, "ViewAs")
            view_as.text = "Pace"
            
            low_in_meters_per_second = ET.SubElement(speed_zone, "LowInMetersPerSecond")
            low_in_meters_per_second.text = f"{low_speed:.3f}"
            
            high_in_meters_per_second = ET.SubElement(speed_zone, "HighInMetersPerSecond")
            high_in_meters_per_second.text = f"{high_speed:.3f}"
            
            step_index += 1
            
            print(f"Added step {step_index}: {segment_name} - {distance_m}m at {pace_seconds_per_km//60}:{pace_seconds_per_km%60:02d}/km (GPX-based)")
            
        except Exception as e:
            print(f"Error processing segment: {segment}, Error: {e}")
            continue
    
    # Create a pretty-printed XML string
    rough_string = ET.tostring(root, 'unicode')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    
    # Remove empty lines
    pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)
    
    print(f"\nSuccessfully created GPX-based TCX workout file: {output_file}")
    print(f"Total workout steps: {step_index}")
    print(f"Total distance: {route_data[-1]['cumulative_distance_m']/1000:.2f} km (based on actual GPS track)")
    print("\nThis workout uses distances calculated from the actual GPS track,")
    print("providing more accurate pacing zones based on real route geometry.")
    print("\nTo use this workout:")
    print("1. Upload the TCX file to Garmin Connect (connect.garmin.com)")
    print("2. Go to Training > Workouts and the workout should appear")
    print("3. Send the workout to your Garmin device")

def main():
    """Main function."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(script_dir, 'squamish50mile_pacing_14h.csv')
    gpx_file = os.path.join(script_dir, 'CMTR - Squamish 50 - 50-mile route (2025).gpx')
    output_file = os.path.join(script_dir, 'squamish50mile_workout.tcx')
    
    # Check if files exist
    if not os.path.exists(csv_file):
        print(f"Error: CSV file not found: {csv_file}")
        sys.exit(1)
    
    if not os.path.exists(gpx_file):
        print(f"Error: GPX file not found: {gpx_file}")
        sys.exit(1)
    
    try:
        create_tcx_workout(csv_file, gpx_file, output_file)
    except Exception as e:
        print(f"Error creating TCX file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()