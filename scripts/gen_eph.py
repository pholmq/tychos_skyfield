import argparse
import datetime as dt
import math
import calendar
from tychos_skyfield import baselib as T

def get_julian_day(date_time):
    """Obtain Julian Day for a given datetime."""
    ref = dt.datetime(2000, 6, 21, 12, 0, 0)
    julian_day = (date_time - ref).total_seconds() / 24 / 3600 + 2451717.0
    return julian_day

def format_ra(ra_hours):
    """Converts decimal hours to HHhMMmSSs string."""
    h = int(ra_hours)
    m_float = (ra_hours - h) * 60
    m = int(m_float)
    s = round((m_float - m) * 60)
    
    if s == 60:
        s = 0
        m += 1
    if m == 60:
        m = 0
        h += 1
        
    return f"{h:02d}h{m:02d}m{s:02d}s"

def format_dec(dec_degrees):
    """Converts decimal degrees to DD°MM'SS\" string."""
    sign = "-" if dec_degrees < 0 else ""
    dec_abs = abs(dec_degrees)
    d = int(dec_abs)
    m_float = (dec_abs - d) * 60
    m = int(m_float)
    s = round((m_float - m) * 60)
    
    if s == 60:
        s = 0
        m += 1
    if m == 60:
        m = 0
        d += 1
        
    return f"{sign}{d:02d}°{m:02d}'{s:02d}\""

def calculate_elongation(ra1_h, dec1_d, ra2_h, dec2_d):
    """Calculates angular separation (elongation) between two celestial objects."""
    ra1_rad = math.radians(ra1_h * 15)
    dec1_rad = math.radians(dec1_d)
    ra2_rad = math.radians(ra2_h * 15)
    dec2_rad = math.radians(dec2_d)

    cos_elong = math.sin(dec1_rad) * math.sin(dec2_rad) + \
                math.cos(dec1_rad) * math.cos(dec2_rad) * math.cos(ra1_rad - ra2_rad)
    
    cos_elong = max(-1.0, min(1.0, cos_elong))
    return math.degrees(math.acos(cos_elong))

def add_time_step(current_date, step_val, step_unit):
    """Adds a specific interval to a datetime object, handling calendar boundaries."""
    if step_unit == 'days':
        return current_date + dt.timedelta(days=step_val)
    elif step_unit == 'weeks':
        return current_date + dt.timedelta(weeks=step_val)
    elif step_unit == 'months':
        month = current_date.month - 1 + step_val
        year = current_date.year + month // 12
        month = month % 12 + 1
        day = min(current_date.day, calendar.monthrange(year, month)[1])
        return current_date.replace(year=year, month=month, day=day)
    elif step_unit == 'years':
        try:
            return current_date.replace(year=current_date.year + step_val)
        except ValueError:
            return current_date.replace(year=current_date.year + step_val, day=28)
    else:
        raise ValueError(f"Unsupported time unit: {step_unit}")

def main():
    parser = argparse.ArgumentParser(description="Generate Ephemerides Report for Planets.")
    parser.add_argument("--start", type=str, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--step-val", type=int, required=True, help="Magnitude of the step")
    parser.add_argument("--step-unit", type=str, choices=['days', 'weeks', 'months', 'years'], default='years', help="Unit for the step (days, weeks, months, years)")
    parser.add_argument("--planets", type=str, required=True, help="Comma-separated planets (e.g., 'Mercury,Venus')")
    
    args = parser.parse_args()

    try:
        start_date = dt.datetime.strptime(args.start, "%Y-%m-%d")
        end_date = dt.datetime.strptime(args.end, "%Y-%m-%d")
    except ValueError:
        print("Error: Invalid date format. Please use YYYY-MM-DD.")
        return

    planets = [p.strip().capitalize() for p in args.planets.split(",")]
    
    system = T.TychosSystem()
    
    print("\n--- EPHEMERIDES REPORT ---")
    print(f"Generated on: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Start Date: {args.start}")
    print(f"End Date: {args.end}")
    print(f"Step Size: {args.step_val} {args.step_unit}")
    print("-" * 38)
    
    for planet in planets:
        try:
            _ = system[planet]
        except KeyError:
            print(f"\nPLANET: {planet.upper()} (Not found in system)")
            continue
            
        print(f"\nPLANET: {planet.upper()}")
        print(f"{'Date':<13}| {'Time':<11}| {'RA':<13}| {'Dec':<13}| {'Dist':<13}| {'Elongation'}")
        print("-" * 80)
        
        current_date = start_date
        while current_date <= end_date:
            jd = get_julian_day(current_date)
            system.move_system(jd)
            
            p_ra, p_dec, p_dist = system[planet].radec_direct(system['Earth'], system['Polar_axis'], 'date')
            s_ra, s_dec, _ = system['Sun'].radec_direct(system['Earth'], system['Polar_axis'], 'date')
            
            elongation = calculate_elongation(s_ra, s_dec, p_ra, p_dec)
            dist_au = p_dist / 100.0
            
            date_fmt = current_date.strftime("%Y-%m-%d")
            time_fmt = current_date.strftime("%H:%M:%S")
            ra_fmt = format_ra(p_ra)
            dec_fmt = format_dec(p_dec)
            
            print(f"{date_fmt:<13}| {time_fmt:<11}| {ra_fmt:<13}| {dec_fmt:<13}| {dist_au:.2f} AU      | {elongation:.3f}°")
            
            current_date = add_time_step(current_date, args.step_val, args.step_unit)

if __name__ == "__main__":
    main()