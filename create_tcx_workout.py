#!/usr/bin/env python3
"""
Convert Squamish 50-mile pacing CSV to TCX workout file.
TCX files can be imported into Garmin Connect and then synced to devices.
"""

import csv
import sys
import os
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from xml.dom import minidom

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

def create_tcx_workout(csv_file, output_file):
    """Create a TCX workout file from the pacing CSV."""
    
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
    name.text = "Squamish 50 Mile 14h Pacing"
    
    # Read CSV and create workout steps
    step_index = 0
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                start_km = float(row['Start_km'])
                end_km = float(row['End_km'])
                distance_m = int((end_km - start_km) * 1000)  # Convert to meters
                
                target_pace = row['Target_Pace']
                pace_seconds_per_km = parse_pace_range(target_pace)
                target_speed_mps = pace_to_speed_mps(pace_seconds_per_km)
                
                segment_name = row['Segment']
                
                # Create Step element
                step = ET.SubElement(workout, "Step")
                step.set("xsi:type", "Step_t")
                
                # Step ID
                step_id = ET.SubElement(step, "StepId")
                step_id.text = str(step_index)
                
                # Step Name
                step_name = ET.SubElement(step, "Name")
                step_name.text = segment_name
                
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
                
                print(f"Added step {step_index}: {segment_name} - {distance_m}m at {pace_seconds_per_km//60}:{pace_seconds_per_km%60:02d}/km")
                
            except Exception as e:
                print(f"Error processing row: {row}, Error: {e}")
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
    
    print(f"\nSuccessfully created TCX workout file: {output_file}")
    print(f"Total workout steps: {step_index}")
    print("\nTo use this workout:")
    print("1. Upload the TCX file to Garmin Connect (connect.garmin.com)")
    print("2. Go to Training > Workouts and the workout should appear")
    print("3. Send the workout to your Garmin Fenix 6 Pro")

def main():
    """Main function."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(script_dir, 'squamish50mile_pacing_14h.csv')
    output_file = os.path.join(script_dir, 'squamish50mile_workout.tcx')
    
    if not os.path.exists(csv_file):
        print(f"Error: CSV file not found: {csv_file}")
        sys.exit(1)
    
    try:
        create_tcx_workout(csv_file, output_file)
    except Exception as e:
        print(f"Error creating TCX file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()