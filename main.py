# Temperature inside a concrete road slab.
# The answer is dT = temperature at the top - temperature at the bottom.
#
# It works in four steps:
#   1. read the weather, one value per hour
#   2. work the weather out for every minute of the day, because the slab is
#      stepped forward one minute at a time
#   3. cut the slab into 17 points and step them all forward, minute by minute,
#      for 8 days
#   4. save the temperatures of the last day and write output.csv

import math
import pandas as pd

# The slab thickness is asked for, because it is the one thing that changes
# from one road to another. Nothing is assumed, so a number has to be typed.
typed = input("Slab thickness in mm: ").strip()
if typed == "":
    print("No thickness was given, so there is nothing to work out.")
    exit()
H = float(typed) / 1000         # mm typed in, metres used inside

# what concrete is like
k = 1.8         # conductivity, how well concrete carries heat, W/m.K
rho = 2400      # density, kg/m3
cp = 920        # specific heat, J/kg.K
absorb = 0.6    # how much of the sunlight the surface takes in
q_rad = 66      # heat lost to the night sky, W/m2

# The depth points are kept about 10 mm apart whatever the slab, so a thick
# slab simply gets more of them. A 320 mm slab gets 33, a 150 mm slab gets 16.
points = round(H * 1000 / 10) + 1
dz = H / (points - 1)   # 10 mm, or as near to it as divides evenly
days = 8        # the same day is repeated 8 times

alpha = k / (rho * cp)          # thermal diffusivity

# The method only works while r stays at 0.5 or less. With the points 10 mm
# apart a whole minute is slightly too long a step, so the minute is cut into
# as many smaller steps as it takes to bring r back to 0.4. Normally two.
per_minute = max(1, math.ceil(alpha * 60 / (0.4 * dz * dz)))
dt = 60 / per_minute            # seconds in one step
r = alpha * dt / (dz * dz)      # the number in the finite difference equation

print("slab thickness:", round(H * 1000), "mm, cut into", points,
      "points", round(dz * 1000, 2), "mm apart")
print("each minute is done in", per_minute,
      "step" + ("s" if per_minute > 1 else ""), "of", round(dt, 3), "seconds")

if per_minute > 240:
    print("A slab this thin would need", per_minute, "steps a minute, which is")
    print("too slow to run. Below about 12 mm this model cannot be used.")
    exit()


# ---- step 1: the weather ----

data = pd.read_csv("weather_IST.csv")

if "solar_W_m2" not in data.columns or "wind_m_s" not in data.columns:
    print("weather_IST.csv has no solar_W_m2 or wind_m_s column, so I cannot run.")
    print("Columns in the file:", list(data.columns))
    exit()

air = list(data["air_temp_C"])
solar = list(data["solar_W_m2"])
wind = list(data["wind_m_s"])

print("alpha =", alpha, "m2/s")
print("r =", round(r, 4), "- must be 0.5 or less for the method to work")


# ---- step 2: the weather for every minute ----

# The weather file gives one reading an hour, but the slab is stepped forward
# every minute. So for each minute we go part of the way from the reading
# before it to the reading after it. 10:15 is a quarter of the way from the
# 10:00 reading to the 11:00 one.

air_minute = []
sun_minute = []
wind_minute = []

for step in range(1440):                # 1440 minutes in a day
    t = (step + 1) / 60                 # the time of day in hours
    hour_now = int(t) % 24              # the hourly reading before it
    hour_next = (hour_now + 1) % 24     # and the one after it
    part = t - int(t)                   # how far between the two

    air_minute.append(air[hour_now] + part * (air[hour_next] - air[hour_now]))
    sun_minute.append(solar[hour_now] + part * (solar[hour_next] - solar[hour_now]))
    wind_minute.append(wind[hour_now] + part * (wind[hour_next] - wind[hour_now]))


# ---- step 3: step the slab forward ----

temp = [sum(air) / 24] * points     # start them all at the average air temperature
half_cell = rho * cp * dz / 2       # the heat held by the half thickness at the two faces

saved = {}
for day in range(days):
    for step in range(1440):

        # the wind for this minute, which does not change inside it
        wind_cooling = 5.6 + 4.0 * wind_minute[step]

        for sub in range(per_minute):
            # what is happening at the top surface right now
            heat_in = (absorb * sun_minute[step]
                       - wind_cooling * (temp[0] - air_minute[step])
                       - q_rad)

            later = list(temp)       # the temperatures one step from now

            # the top point: the sun and the air, plus the heat coming up from below
            later[0] = temp[0] + dt / half_cell * (heat_in + k * (temp[1] - temp[0]) / dz)

            # the points inside the slab: each one is pulled towards its two neighbours
            for i in range(1, points - 1):
                later[i] = temp[i] + r * (temp[i + 1] - 2 * temp[i] + temp[i - 1])

            # the bottom point: no heat crosses the bottom face
            later[points - 1] = (temp[points - 1]
                                 + dt / half_cell * (k * (temp[points - 2] - temp[points - 1]) / dz))

            temp = later

        # on the last day, keep the temperatures once an hour
        if day == days - 1 and (step + 1) % 60 == 0:
            saved[(step + 1) // 60 % 24] = temp


# ---- step 4: the answer ----

# Five of the points are saved: the top, the bottom, and the three evenly
# spaced in between. That is a quarter of the way down, half way, and three
# quarters of the way down, whatever the thickness.
depths = []
for part in [0, 1, 2, 3, 4]:
    depths.append(round((points - 1) * part / 4))

names = ["hour_IST", "air_temp_C"]
for i in depths:
    names.append("T_" + str(round(i * dz * 1000)) + "mm")
names.append("dT")

rows = []
for hour in range(24):
    temp = saved[hour]
    row = [data["hour_IST"][hour], air[hour]]
    for i in depths:
        row.append(round(temp[i], 2))
    row.append(round(temp[0] - temp[points - 1], 2))
    rows.append(row)

result = pd.DataFrame(rows, columns=names)
result.to_csv("output.csv", index=False)

print()
print(result.to_string(index=False))
print()
print("highest dT =", result["dT"].max(), "- daytime curling, top hotter")
print("lowest  dT =", result["dT"].min(), "- nighttime warping, top cooler")
