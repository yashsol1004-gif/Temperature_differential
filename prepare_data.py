# Turns the downloaded weather file into the simple file main.py needs.
#
# The downloaded file cannot be used as it is, for three reasons, so this
# program works in four steps:
#   1. read the file, which is really three small tables in one
#   2. move the times from GMT on to IST
#   3. spread the day's one sun total over the daylight hours
#   4. write weather_IST.csv, four plain columns, one row per hour

import csv
import math
import datetime

IN_FILE = "greater_noida_26may.csv"
OUT_FILE = "weather_IST.csv"


# ---- step 1: read the file ----

# there are blank lines between the three tables, so those are dropped
rows = []
for row in csv.reader(open(IN_FILE, encoding="utf-8-sig")):
    if row and "".join(row).strip() != "":
        rows.append(row)

# the first table is the place, the second is the 24 hourly rows,
# and the last row is the sun for the whole day
lat = float(rows[1][0])                 # 28.646748
lon = float(rows[1][1])                 # 77.2748
file_offset = float(rows[1][3]) / 3600  # how many hours ahead of GMT the times are
hourly = rows[3:27]                     # the 24 hourly rows
day_sun = float(rows[28][1]) * 1e6      # MJ/m2 for the whole day, changed to J/m2

date = hourly[0][0].split("T")[0]       # "2026-05-26"
year = int(date.split("-")[0])
month = int(date.split("-")[1])
day = int(date.split("-")[2])
day_number = datetime.date(year, month, day).timetuple().tm_yday

print("place:", lat, lon)
print("date:", date, "- day", day_number, "of the year")
print("hours read:", len(hourly), "- times are", file_offset, "hours ahead of GMT")
print("sun for the whole day:", day_sun / 1e6, "MJ/m2")

air_in = []
wind_in = []
for row in hourly:
    air_in.append(float(row[1]))
    wind_in.append(float(row[2]) / 3.6)     # km/h changed to m/s


# ---- step 2: GMT on to IST ----

# IST is 5.5 hours ahead of GMT. So the reading taken at GMT midnight is really
# the weather at 05:30 IST - half an hour off every IST clock hour. To get the
# weather at a whole IST hour we go halfway between the two readings either side
# of it, the same going between that main.py does with the minutes.

shift = 5.5 - file_offset


def value_at(values, h):
    x = (h - shift) % 24        # the same moment, counted on the file's clock
    i = int(x)                  # the reading before it
    gap = x - i                 # how far past that reading we are
    return values[i % 24] + gap * (values[(i + 1) % 24] - values[i % 24])


air = []
wind = []
for h in range(24):
    air.append(value_at(air_in, h))
    wind.append(value_at(wind_in, h))


# ---- step 3: one sun total spread over the hours ----

# The file gives 24.67 MJ/m2 for the whole day and nothing hour by hour. The sun
# is strongest when it is highest in the sky, so the height of the sun is used
# as the shape of the day, and that shape is then scaled until it adds up to the
# measured total.

tilt = math.radians(23.45 * math.sin(math.radians(360 / 365 * (284 + day_number))))
lat_rad = math.radians(lat)
noon = 12 + (82.5 - lon) * 4 / 60 - 3.2 / 60   # the time the sun is highest, IST
# 82.5 is the longitude IST is set by, and 3.2 minutes is how far the sun runs
# ahead of the clock in late May. A different month needs a different 3.2.


# how high the sun is at IST time t. Zero at night, 1 if straight overhead.
def sun_height(t):
    angle = math.radians(15 * (t % 24 - noon))      # how far round from noon
    high = (math.sin(lat_rad) * math.sin(tilt)
            + math.cos(lat_rad) * math.cos(tilt) * math.cos(angle))
    return max(high, 0.0)


# add the shape up over the whole day in 10 second steps
shape_sum = 0.0
for i in range(24 * 360):
    shape_sum += sun_height(i * 10 / 3600) * 10

# then scale it so the day comes to exactly the measured total
strength = day_sun / shape_sum

solar = []
for h in range(24):
    solar.append(strength * sun_height(h))

print("sun highest at", round(noon, 2), "IST, strongest", round(strength * sun_height(noon)), "W/m2")


# ---- step 4: write the tidy file ----

out = open(OUT_FILE, "w", newline="")
writer = csv.writer(out)
writer.writerow(["hour_IST", "air_temp_C", "solar_W_m2", "wind_m_s"])
for h in range(24):
    writer.writerow(["%02d:00" % h, round(air[h], 2), round(solar[h]), round(wind[h], 4)])
out.close()

print("written:", OUT_FILE, "- now run main.py")
