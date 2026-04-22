import argparse
import datetime as dt
import calendar
import math
import re
from tychos_skyfield import baselib as T

def calendar_to_jd(year, month, day, hour=0, minute=0, second=0):
    """Meeus algorithm for Julian Date."""
    if month <= 2:
        year -= 1
        month += 12
        
    A = math.floor(year / 100)
    B = 2 - A + math.floor(A / 4)
    
    if year < 1582 or (year == 1582 and (month < 10 or (month == 10 and day < 15))):
        B = 0
        
    JD = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + B - 1524.5
    JD += (hour + minute / 60 + second / 3600) / 24.0
    return JD

def add_calendar_time(current_date, step_val, step_unit):
    """Forces calendar stepping (e.g., strict years/months) instead of physical fractions."""
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
            # Handle Feb 29 on non-leap years
            return current_date.replace(year=current_date.year + step_val, day=28)
    raise ValueError(f"Unsupported time unit: {step_unit}")

def parse_tychos_coord(coord_str):
    nums = [float(x) for x in re.findall(r"[-+]?(?:\d*\.\d+|\d+)", str(coord_str))]
    if len(nums) < 3:
        return 0.0
    sign = -1 if '-' in str(coord_str) else 1
    return sign * (abs(nums[0]) + (nums[1] / 60.0) + (nums[2] / 3600.0))

def format_ra(ra_hours):
    h = int(ra_hours)
    m_float = (ra_hours - h) * 60
    m = int(m_float)
    s = int(((m_float - m) * 60) + 0.5) # JS style rounding
    if s >= 60:
        s = 0; m += 1
    if m >= 60:
        m = 0; h += 1
    return f"{h:02d}h{m:02d}m{s:02d}s"

def format_dec(dec_degrees):
    sign = "-" if dec_degrees < 0 else ""
    dec_abs = abs(dec_degrees)
    d = int(dec_abs)
    m_float = (dec_abs - d) * 60
    m = int(m_float)
    s = int(((m_float - m) * 60) + 0.5) # JS style rounding
    if s >= 60:
        s = 0; m += 1
    if m >= 60:
        m = 0; d += 1
    return f"{sign}{d:02d}°{m:02d}'{s:02d}\""

def calculate_elongation(ra1_h, dec1_d, ra2_h, dec2_d):
    ra1_rad = math.radians(ra1_h * 15)
    dec1_rad = math.radians(dec1_d)
    ra2_rad = math.radians(ra2_h * 15)
    dec2_rad = math.radians(dec2_d)

    cos_elong = math.sin(dec1_rad) * math.sin(dec2_rad) + \
                math.cos(dec1_rad) * math.cos(dec2_rad) * math.cos(ra1_rad - ra2_rad)
    cos_elong = max(-1.0, min(1.0, cos_elong))
    return math.degrees(math.acos(cos_elong))

def main():
    parser = argparse.ArgumentParser(description="Generate Ephemerides Report for Planets.")
    parser.add_argument("--start", type=str, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--step-val", type=int, required=True, help="Magnitude of the step")
    parser.add_argument("--step-unit", type=str, choices=['days', 'weeks', 'months', 'years'], default='years')
    parser.add_argument("--planets", type=str, required=True)
    parser.add_argument("--output", type=str, default="ephemerides_report.txt")
    
    args = parser.parse_args()

    try:
        start_date = dt.datetime.strptime(args.start, "%Y-%m-%d")
        end_date = dt.datetime.strptime(args.end, "%Y-%m-%d")
    except ValueError:
        print("Error: Invalid date format. Please use YYYY-MM-DD.")
        return

    planets = [p.strip().capitalize() for p in args.planets.split(",")]
    system = T.TychosSystem()
    
    print(f"Calculating positions and saving to {args.output}...")
    
    with open(args.output, 'w', encoding='utf-8') as f:
        print("--- EPHEMERIDES REPORT ---", file=f)
        print(f"Generated on: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", file=f)
        print(f"Start Date: {args.start}", file=f)
        print(f"End Date: {args.end}", file=f)
        print(f"Step Size: {args.step_val} {args.step_unit}", file=f)
        print("-" * 38, file=f)
        
        for planet in planets:
            try:
                _ = system[planet]
            except KeyError:
                continue
                
            print(f"\nPLANET: {planet.upper()}", file=f)
            print(f"{'Date':<13}| {'Time':<11}| {'RA':<13}| {'Dec':<13}| {'Dist':<13}| {'Elongation'}", file=f)
            print("-" * 80, file=f)
            
            current_date = start_date
            while current_date <= end_date:
                # 1. Force Python to calculate the strict Julian Date for THIS calendar day
                jd = calendar_to_jd(current_date.year, current_date.month, current_date.day, 
                                    current_date.hour, current_date.minute, current_date.second)
                
                system.move_system(jd)
                
                p_ra_str, p_dec_str, p_dist = system[planet].radec_direct(system['Earth'], system['Polar_axis'], 'date')
                s_ra_str, s_dec_str, _ = system['Sun'].radec_direct(system['Earth'], system['Polar_axis'], 'date')
                
                p_ra_num = parse_tychos_coord(p_ra_str)
                p_dec_num = parse_tychos_coord(p_dec_str)
                s_ra_num = parse_tychos_coord(s_ra_str)
                s_dec_num = parse_tychos_coord(s_dec_str)
                
                elongation = calculate_elongation(s_ra_num, s_dec_num, p_ra_num, p_dec_num)
                dist_au = float(p_dist)
                
                date_fmt = current_date.strftime("%Y-%m-%d")
                time_fmt = current_date.strftime("%H:%M:%S")
                ra_fmt = format_ra(p_ra_num)
                dec_fmt = format_dec(p_dec_num)
                
                print(f"{date_fmt:<13}| {time_fmt:<11}| {ra_fmt:<13}| {dec_fmt:<13}| {dist_au:.2f} AU      | {elongation:.3f}°", file=f)
                
                # 2. Step forward cleanly by calendar year
                current_date = add_calendar_time(current_date, args.step_val, args.step_unit)

    print("Done!")

if __name__ == "__main__":
    main()