#!/usr/bin/env python3
"""
Convert Squamish 50-mile pacing CSV to formats compatible with Garmin Fenix 6 Pro.
Generates both TCX workout file and comprehensive instructions.
"""

import csv
import sys
import os
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from xml.dom import minidom
import json

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
    segments_data = []
    
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
                
                # Store segment data for other outputs
                segment_data = {
                    'step': step_index + 1,
                    'name': segment_name,
                    'start_km': start_km,
                    'end_km': end_km,
                    'distance_m': distance_m,
                    'distance_km': distance_m / 1000,
                    'target_pace_str': target_pace,
                    'target_pace_sec_km': pace_seconds_per_km,
                    'target_speed_mps': target_speed_mps,
                    'pace_min_km': f"{pace_seconds_per_km//60}:{pace_seconds_per_km%60:02d}"
                }
                segments_data.append(segment_data)
                
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
    
    return segments_data

def create_garmin_connect_instructions(segments_data, output_file, csv_file):
    """Create detailed instructions for manual workout creation in Garmin Connect."""
    
    with open(output_file, 'w') as f:
        f.write("# Squamish 50 Mile - 14 Hour Pacing Workout for Garmin Fenix 6 Pro\n\n")
        f.write("## Multiple Ways to Get This Workout on Your Device\n\n")
        
        f.write("### Method 1: Upload TCX File (Recommended)\n")
        f.write("1. Go to [Garmin Connect Web](https://connect.garmin.com)\n")
        f.write("2. Sign in to your account\n")
        f.write("3. Click the '+' button and select 'Import Data'\n")
        f.write("4. Upload the `squamish50mile_workout.tcx` file\n")
        f.write("5. The workout will appear in Training > Workouts\n")
        f.write("6. Send to your Fenix 6 Pro via Garmin Connect app\n\n")
        
        f.write("### Method 2: Manual Creation in Garmin Connect\n")
        f.write("1. Go to [Garmin Connect Web](https://connect.garmin.com)\n")
        f.write("2. Navigate to Training > Workouts\n")
        f.write("3. Click 'Create Workout'\n")
        f.write("4. Choose 'Running' as the sport\n")
        f.write("5. Name the workout: 'Squamish 50 Mile 14h Pacing'\n")
        f.write("6. Add the following workout steps:\n\n")
        
        total_distance = 0
        for segment in segments_data:
            total_distance += segment['distance_km']
            f.write(f"**Step {segment['step']}: {segment['name']}**\n")
            f.write(f"- Duration: Distance - {segment['distance_km']:.1f} km\n")
            f.write(f"- Target: Pace - {segment['pace_min_km']} /km\n")
            f.write(f"- Cumulative: {total_distance:.1f} km\n\n")
        
        f.write(f"**Total Workout Distance: {total_distance:.1f} km**\n\n")
        
        f.write("### Method 3: Direct File Transfer (Advanced)\n")
        f.write("1. Connect your Fenix 6 Pro to computer via USB\n")
        f.write("2. Copy the .fit file (when available) to `/GARMIN/NEWFILES/`\n")
        f.write("3. Safely eject the device\n")
        f.write("4. The workout will appear in your device's workout menu\n\n")
        
        f.write("### Using the Workout on Your Fenix 6 Pro\n")
        f.write("1. On your watch, go to: Menu > Training > Workouts\n")
        f.write("2. Select 'Squamish 50 Mile 14h Pacing'\n")
        f.write("3. Press START to begin the workout\n")
        f.write("4. The watch will guide you through each segment with pace targets\n")
        f.write("5. You'll get alerts when transitioning between segments\n\n")
        
        f.write("### Pace Target Details\n")
        f.write("| Segment | Distance (km) | Target Pace | Terrain |\n")
        f.write("|---------|---------------|-------------|----------|\n")
        
        for segment in segments_data:
            terrain = ""
            with open(csv_file, 'r') as csvf:
                reader = csv.DictReader(csvf)
                for row in reader:
                    if row['Segment'] == segment['name']:
                        terrain = row.get('Terrain', '')
                        break
            
            f.write(f"| {segment['name'][:30]} | {segment['distance_km']:.1f} | {segment['pace_min_km']} /km | {terrain} |\n")
        
        f.write("\n### Tips for Race Day\n")
        f.write("- Start the workout when you begin the race\n")
        f.write("- The pace targets are guidelines - adjust based on conditions\n")
        f.write("- Use the lap button to manually advance segments if needed\n")
        f.write("- Monitor your heart rate and perceived effort\n")
        f.write("- Save and upload your activity after the race\n")

def create_json_summary(segments_data, output_file):
    """Create a JSON summary of the workout data."""
    
    workout_summary = {
        "workout_name": "Squamish 50 Mile 14h Pacing",
        "sport": "running",
        "total_distance_km": sum(s['distance_km'] for s in segments_data),
        "total_steps": len(segments_data),
        "created_date": datetime.now().isoformat(),
        "segments": segments_data
    }
    
    with open(output_file, 'w') as f:
        json.dump(workout_summary, f, indent=2)

def main():
    """Main function."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(script_dir, 'squamish50mile_pacing_14h.csv')
    
    if not os.path.exists(csv_file):
        print(f"Error: CSV file not found: {csv_file}")
        sys.exit(1)
    
    try:
        print("Creating Garmin-compatible workout files from CSV data...")
        print("=" * 60)
        
        # Create TCX workout file
        tcx_file = os.path.join(script_dir, 'squamish50mile_workout.tcx')
        segments_data = create_tcx_workout(csv_file, tcx_file)
        print(f"✓ Created TCX workout file: {tcx_file}")
        
        # Create detailed instructions
        instructions_file = os.path.join(script_dir, 'GARMIN_WORKOUT_INSTRUCTIONS.md')
        create_garmin_connect_instructions(segments_data, instructions_file, csv_file)
        print(f"✓ Created instructions file: {instructions_file}")
        
        # Create JSON summary
        json_file = os.path.join(script_dir, 'workout_summary.json')
        create_json_summary(segments_data, json_file)
        print(f"✓ Created JSON summary: {json_file}")
        
        print("\n" + "=" * 60)
        print("SUCCESS! Files created for Garmin Fenix 6 Pro:")
        print(f"- {tcx_file} (Upload to Garmin Connect)")
        print(f"- {instructions_file} (Detailed setup instructions)")
        print(f"- {json_file} (Workout data summary)")
        
        print(f"\nWorkout Summary:")
        print(f"- Total Distance: {sum(s['distance_km'] for s in segments_data):.1f} km")
        print(f"- Total Segments: {len(segments_data)}")
        print(f"- Pace Range: {min(s['target_pace_sec_km'] for s in segments_data)//60}:{min(s['target_pace_sec_km'] for s in segments_data)%60:02d} - {max(s['target_pace_sec_km'] for s in segments_data)//60}:{max(s['target_pace_sec_km'] for s in segments_data)%60:02d} /km")
        
        print("\n🏃‍♂️ Ready for the Squamish 50! Follow the instructions in GARMIN_WORKOUT_INSTRUCTIONS.md")
        
    except Exception as e:
        print(f"Error creating workout files: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()