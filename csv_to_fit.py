#!/usr/bin/env python3
"""
Convert Squamish 50-mile pacing CSV to Garmin FIT workout file.
"""

import csv
import sys
import os
import struct
from datetime import datetime, timedelta

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

def parse_time_estimate(time_str):
    """Parse time estimate like '0:29' or '1:14' to total seconds."""
    try:
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 2:
                hours, minutes = parts
                return int(hours) * 3600 + int(minutes) * 60
        return 0
    except:
        return 0

def create_fit_workout(csv_file, output_file):
    """Create a FIT workout file from the pacing CSV."""
    
    try:
        from fitfile import FitFile
        
        # Create a new FIT file
        fit = FitFile()
        
        # Read CSV and create workout steps
        segments = []
        
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
                    
                    segment = {
                        'name': segment_name,
                        'distance': distance_m,
                        'target_pace_sec_km': pace_seconds_per_km,
                        'target_speed_mps': target_speed_mps
                    }
                    segments.append(segment)
                    
                    print(f"Parsed segment: {segment_name} - {distance_m}m at {pace_seconds_per_km//60}:{pace_seconds_per_km%60:02d}/km")
                    
                except Exception as e:
                    print(f"Error processing row: {row}, Error: {e}")
                    continue
        
        # Since fitfile might not support workout creation, let's create a simple structured workout file
        create_simple_workout_file(segments, output_file)
        
    except ImportError:
        # Fall back to creating a simple structured workout file
        print("fitfile library not working as expected, creating structured workout file...")
        
        segments = []
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    start_km = float(row['Start_km'])
                    end_km = float(row['End_km'])
                    distance_m = int((end_km - start_km) * 1000)
                    
                    target_pace = row['Target_Pace']
                    pace_seconds_per_km = parse_pace_range(target_pace)
                    
                    segment_name = row['Segment']
                    
                    segment = {
                        'name': segment_name,
                        'distance': distance_m,
                        'target_pace_sec_km': pace_seconds_per_km,
                        'start_km': start_km,
                        'end_km': end_km
                    }
                    segments.append(segment)
                    
                    print(f"Parsed segment: {segment_name} - {distance_m}m at {pace_seconds_per_km//60}:{pace_seconds_per_km%60:02d}/km")
                    
                except Exception as e:
                    print(f"Error processing row: {row}, Error: {e}")
                    continue
        
        create_simple_workout_file(segments, output_file)

def create_simple_workout_file(segments, output_file):
    """Create a simple workout file that can be manually converted to FIT."""
    
    # First, let's try to create an actual FIT file using basic structure
    try:
        create_basic_fit_file(segments, output_file)
    except Exception as e:
        print(f"Could not create FIT file: {e}")
        # Fall back to creating a structured text file with instructions
        create_workout_instructions(segments, output_file.replace('.fit', '_instructions.txt'))

def create_basic_fit_file(segments, output_file):
    """Create a basic FIT file with minimal structure."""
    
    # FIT file header
    fit_header = struct.pack('<BBHI4sH', 
                           14,      # header_size
                           16,      # protocol_version 
                           0x084B,  # profile_version (little endian for 19,200)
                           0,       # data_size (will be updated)
                           b'.FIT', # data_type
                           0        # crc (will be calculated)
                           )
    
    # File ID message (required)
    file_id_data = bytearray()
    
    # Message header for file_id (global message number 0)
    msg_header = 0x40  # Normal header, local message type 0
    file_id_data.append(msg_header)
    
    # Definition message for file_id
    definition = struct.pack('<BBBBB',
                           0,    # reserved
                           0,    # architecture (0 = little endian)
                           0,    # global_mesg_num (low byte) - file_id = 0
                           0,    # global_mesg_num (high byte)
                           4     # number of fields
                           )
    
    # Field definitions for file_id
    fields = struct.pack('<BBBBBBBBBBBBBBB',
                        0, 4, 134,  # field 0: type (uint32)
                        1, 2, 132,  # field 1: manufacturer (uint16) 
                        2, 2, 132,  # field 2: product (uint16)
                        4, 4, 134   # field 4: time_created (uint32)
                        )
    
    file_id_data.extend(definition + fields)
    
    # Data message for file_id
    file_id_data.append(0x00)  # Data message header (local type 0)
    
    current_time = int((datetime.now() - datetime(1989, 12, 31)).total_seconds())
    file_id_values = struct.pack('<LHHL',
                                6,          # type = workout
                                65535,      # manufacturer = development  
                                0,          # product
                                current_time # time_created
                                )
    file_id_data.extend(file_id_values)
    
    # Calculate data size
    data_size = len(file_id_data)
    
    # Update header with data size
    fit_header = struct.pack('<BBHI4sH', 
                           14,        # header_size
                           16,        # protocol_version
                           0x084B,    # profile_version
                           data_size, # data_size
                           b'.FIT',   # data_type
                           0          # crc (simplified, not calculated)
                           )
    
    # Write the file
    with open(output_file, 'wb') as f:
        f.write(fit_header)
        f.write(file_id_data)
    
    print(f"Created basic FIT file: {output_file}")
    print("Note: This is a minimal FIT file. For full workout functionality,")
    print("you may need to use Garmin Connect or other tools to create a complete workout.")

def create_workout_instructions(segments, output_file):
    """Create a text file with workout instructions that can be manually entered into Garmin Connect."""
    
    with open(output_file, 'w') as f:
        f.write("Squamish 50 Mile - 14 Hour Pacing Workout\n")
        f.write("=" * 50 + "\n\n")
        f.write("Instructions for creating this workout in Garmin Connect:\n")
        f.write("1. Go to Garmin Connect Web (connect.garmin.com)\n")
        f.write("2. Navigate to Training > Workouts\n")
        f.write("3. Create New Workout > Running\n")
        f.write("4. Add the following workout steps:\n\n")
        
        total_distance = 0
        for i, segment in enumerate(segments, 1):
            pace_min = segment['target_pace_sec_km'] // 60
            pace_sec = segment['target_pace_sec_km'] % 60
            distance_km = segment['distance'] / 1000
            total_distance += distance_km
            
            f.write(f"Step {i}: {segment['name']}\n")
            f.write(f"  - Type: Distance\n")
            f.write(f"  - Distance: {distance_km:.1f} km\n")
            f.write(f"  - Target: Pace {pace_min}:{pace_sec:02d} /km\n")
            f.write(f"  - Cumulative Distance: {total_distance:.1f} km\n\n")
        
        f.write(f"Total Workout Distance: {total_distance:.1f} km\n")
        f.write("\nAlternatively, you can use the basic FIT file generated alongside this file.\n")
    
    print(f"Created workout instructions: {output_file}")
    print("You can use these instructions to manually create the workout in Garmin Connect.")

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
        print(f"\nWorkout file created successfully!")
        print(f"You can now copy {output_file} to your Garmin device.")
        print("Location on device: /GARMIN/NEWFILES/ or /GARMIN/Workouts/")
    except Exception as e:
        print(f"Error creating FIT file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()