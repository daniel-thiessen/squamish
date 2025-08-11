# Squamish 50 Mile Race Data and Garmin Workout

This repository contains pacing data and tools for the Squamish 50 Mile ultramarathon race.

## Files

### Race Data
- `squamish50mile_pacing_14h.csv` - Detailed 14-hour pacing strategy broken down by segments
- `squamish50mile_aidstations_14h.md` - Aid station strategy and pacing notes
- `CMTR - Squamish 50 - 50-mile route (2025).gpx` - Official race route GPS track

### Garmin Workout Files (Generated)
- `squamish50mile_workout.tcx` - **Main workout file for Garmin devices**
- `GARMIN_WORKOUT_INSTRUCTIONS.md` - Comprehensive setup instructions
- `workout_summary.json` - Machine-readable workout data

### Tools
- `convert_pacing_to_garmin.py` - Converts CSV pacing data to Garmin-compatible formats

## Quick Start for Garmin Fenix 6 Pro Users

1. **Upload the workout** (easiest method):
   - Go to [Garmin Connect Web](https://connect.garmin.com)
   - Click the '+' button and select 'Import Data'
   - Upload `squamish50mile_workout.tcx`
   - Send to your device via Garmin Connect app

2. **For detailed instructions**: See `GARMIN_WORKOUT_INSTRUCTIONS.md`

## Workout Summary
- **Total Distance**: 80.5 km
- **Segments**: 14 paced segments
- **Pace Range**: 6:50 - 13:20 /km
- **Target Time**: 14 hours

## How to Regenerate Workout Files

If you modify the CSV data, run:
```bash
python3 convert_pacing_to_garmin.py
```

This will regenerate all the Garmin-compatible workout files.

## Race Strategy Overview

The 14-hour pacing plan accounts for:
- Early fatigue prevention
- Terrain-specific pace adjustments
- Aid station timing
- Sustainable effort distribution

See the detailed breakdown in `squamish50mile_aidstations_14h.md`.