#!/usr/bin/env python3
"""
Convert Squamish 50-mile pacing CSV to FIT workout file using fit-tool.
"""

import csv
import sys
import os
from datetime import datetime
from fit_tool.fit_file import FitFile
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.workout_message import WorkoutMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage

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

def create_fit_workout(csv_file, output_file):
    """Create a FIT workout file from the pacing CSV."""
    
    # Create FIT file
    fit_file = FitFile()
    
    # Create file_id message
    file_id = FileIdMessage()
    file_id.type = 'workout'
    file_id.manufacturer = 'development'
    file_id.time_created = datetime.now()
    fit_file.add(file_id)
    
    # Create workout message
    workout = WorkoutMessage()
    workout.wkt_name = "Squamish 50 Mile 14h Pacing"
    workout.sport = 'running'
    workout.num_valid_steps = 0  # Will be updated
    
    # Read CSV and create workout steps
    steps = []
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
                
                # Create workout step
                step = WorkoutStepMessage()
                step.message_index = step_index
                step.wkt_step_name = segment_name[:15]  # Limit name length
                step.duration_type = 'distance'
                step.duration_value = distance_m
                step.target_type = 'speed'
                
                # Set speed zones (target speed ± 5%)
                target_speed_zone_low = int(target_speed_mps * 0.95 * 1000)  # Convert to mm/s
                target_speed_zone_high = int(target_speed_mps * 1.05 * 1000)  # Convert to mm/s
                
                step.custom_target_speed_low = target_speed_zone_low
                step.custom_target_speed_high = target_speed_zone_high
                step.intensity = 'active'
                
                steps.append(step)
                step_index += 1
                
                print(f"Added step {step_index}: {segment_name} - {distance_m}m at {pace_seconds_per_km//60}:{pace_seconds_per_km%60:02d}/km")
                
            except Exception as e:
                print(f"Error processing row: {row}, Error: {e}")
                continue
    
    # Update workout with total steps and add to file
    workout.num_valid_steps = len(steps)
    fit_file.add(workout)
    
    # Add all steps to file
    for step in steps:
        fit_file.add(step)
    
    # Write to file
    fit_file.to_file(output_file)
    
    print(f"\nSuccessfully created FIT workout file: {output_file}")
    print(f"Total workout steps: {len(steps)}")
    print("\nTo use this workout:")
    print("1. Copy the .fit file to your Garmin device's /GARMIN/NEWFILES/ folder")
    print("2. Or use Garmin Express to sync it")
    print("3. The workout will appear in your device's workouts menu")

def main():
    """Main function."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(script_dir, 'squamish50mile_pacing_14h.csv')
    output_file = os.path.join(script_dir, 'squamish50mile_workout.fit')
    
    if not os.path.exists(csv_file):
        print(f"Error: CSV file not found: {csv_file}")
        sys.exit(1)
    
    try:
        create_fit_workout(csv_file, output_file)
    except Exception as e:
        print(f"Error creating FIT file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()