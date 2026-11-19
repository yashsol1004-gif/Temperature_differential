# Temperature inside a concrete road slab

**Open it here: https://yashsol1004-gif.github.io/ThermoSlab/** &mdash; press
*Load the Greater Noida data* and the graphs and tables appear. Nothing to
install, and the subgrade modulus and the offset can be changed on the page.

## What this project does

During the day the sun heats the top of a road slab, so the top becomes hotter
than the bottom. At night the top cools faster, so the top becomes cooler. This
makes the slab bend: curling in the day, warping at night.

This program finds the temperature at different depths inside the slab for every
hour of one day, and then gives:

    dT = temperature at the top - temperature at the bottom

The project stops at dT. It does not calculate stresses.

## The data

The weather comes from `greater_noida_26may.csv`, downloaded from Open-Meteo
for 28.6467 N, 77.2748 E on 26 May 2026. It cannot be used as it is, for three
reasons:

1. **It is three small tables in one file.** First two rows about the place, then
   24 hourly rows of air temperature and wind, then one last row with the sun.
2. **The times are GMT, not IST.** The file says `utc_offset_seconds = 0`. You
   can see it in the numbers: the hottest reading sits at 09:00, which is really
   14:30 IST.
3. **The sun is given as one total for the whole day**, 24.67 MJ/m2. The model
   needs a value in W/m2 for every hour.

`prepare_data.py` sorts all three out and writes `weather_IST.csv`, which has the
four columns `main.py` needs:

- `hour_IST` - the hour, 00:00 to 23:00
- `air_temp_C` - air temperature in degrees C
- `solar_W_m2` - solar radiation in W/m2
- `wind_m_s` - wind speed in m/s

### Moving GMT on to IST

IST is 5 hours 30 minutes ahead of GMT, so every reading lands exactly halfway
between two IST clock hours. The value at a whole IST hour is therefore the
average of the two readings either side of it.

This is easy to check. `data.csv` already lists the air temperature in IST, and
the shifted values match it to within 0.05 degrees at all 24 hours, which is just
rounding. So the shift is right.

### Spreading the day's sun over the hours

The shape used is the height of the sun in the sky:

    cos(zenith) = sin(lat)*sin(tilt) + cos(lat)*cos(tilt)*cos(hour angle)

The whole shape is added up over the day, then scaled so the day comes to exactly
24.67 MJ/m2. That gives a peak of 803 W/m2 at 12.30 IST. Checking afterwards, the
24 hourly values still add up to 24.67 MJ/m2, so nothing was lost by taking them
one hour apart.

One limit: the 3.2 minutes in `prepare_data.py` is how far the sun runs ahead of
the clock in late May only. A different month needs a different number, or the
peak lands a few minutes out.

## The equations

Heat moving down through the slab:

    dT/dt = alpha * d2T/dz2

Thermal diffusivity:

    alpha = k / (rho * cp) = 8.15e-7 m2/s

Heat at the top surface:

    hc = 5.6 + 4.0 * wind
    q_net = 0.6 * solar - hc * (T_top - T_air) - 66

Finite difference equation, used for the points inside the slab:

    T(i, t+dt) = T(i, t) + r * [ T(i+1, t) - 2*T(i, t) + T(i-1, t) ]

## The values used

| Name | Value | Meaning |
|---|---|---|
| H | typed in when the program starts | slab thickness |
| k | 1.8 W/m.K | how well concrete carries heat |
| rho | 2400 kg/m3 | density of concrete |
| cp | 920 J/kg.K | specific heat of concrete |
| dz | about 10 mm | gap between the depth points, whatever the thickness |
| dt | 60 s / steps per minute | one time step, 60 s for a 320 mm slab |
| r | 0.122 for a 320 mm slab | the step is chosen to keep this at 0.4, and it must stay under 0.5 |

## How the code works

1. Read `weather_IST.csv` and check the solar and wind columns are there.
2. Work out alpha and r, and stop if r is more than 0.5.
3. Cut the slab into points about 10 mm apart and start them all at the average air
   temperature of the day.
4. Step forward one minute at a time. For each minute:
   - find the air, solar and wind values for that minute
   - work out hc and q_net at the surface
   - update the top point, then the inside points, then the bottom point
5. Repeat the same day 8 times, so the slab forgets the temperature it started
   at.
6. On the last day, save the temperatures every hour and write `output.csv`.

Two things I assumed: no heat crosses the bottom face of the slab, and 8
repeats of the day is enough. I checked the second one by trying 12 repeats,
and the answer only changed by 0.01 degrees.

## What dT means

- dT is **positive**: the top is hotter than the bottom. This happens in the
  afternoon. The top expands more, so the slab edges press down. This is
  daytime curling.
- dT is **negative**: the top is cooler than the bottom. This happens in the
  early morning. The top shrinks more, so the edges lift up. This is nighttime
  warping.

## The answer

Running it on the real 26 May weather:

| | dT | time |
|---|---|---|
| Highest (daytime curling) | **+11.61 C** | 13:00 IST |
| Lowest (nighttime warping) | **-8.36 C** | 05:00 IST |

`data.csv` holds the older model's answers for the same day, so the two can be
compared:

| | mine | older model | difference |
|---|---|---|---|
| Highest dT | +11.61 at 13:00 | +11.50 at 14:00 | 0.11 C, one hour |
| Lowest dT | -8.36 at 05:00 | -6.92 at 05:00 | 1.44 C, same hour |

The daytime figures agree closely. The night figures do not, and the reason is
the one simplification I made: I treat the bottom of the slab as insulated, while
the older model continues 2 m down into the soil. At night the soil carries heat
away from the bottom of the slab, so its bottom cools and dT is less negative.
Mine traps that heat, so my night dT is about 1.4 degrees too negative. Daytime
dT is set by the hot surface, which both models handle the same way, so daytime
agrees.

## How to run it

With Python, two steps:

    pip install pandas
    python prepare_data.py
    python main.py
    python stress.py

`main.py` asks for the slab thickness in mm before it does anything, and
`stress.py` asks for the thickness and the wheel load in kN. Nothing is assumed,
so the numbers have to be typed. Give both programs the same thickness, because
the dT in `output.csv` belongs to the slab `main.py` was run with, and
`stress.py` stops if they do not match. The results saved here were run at
320 mm and 50 kN.

The depth points are kept about 10 mm apart whatever the slab, so a 320 mm slab
gets 33 of them and a 150 mm slab gets 16. With that spacing a whole minute is
slightly too long a step, so each minute is done in two steps of 30 seconds,
which keeps r at 0.24. The step is worked out from the spacing, so it changes by
itself if the slab does. The results saved here were run at 320 mm.

Using 10 mm points rather than a fixed count was checked against 33, 17 and 9
points: the dT came out the same to within 0.01 degrees, and the stress ratios
to within 0.001. The answer comes from the physics, not from the spacing.

`prepare_data.py` reads the downloaded file and writes `weather_IST.csv`.
`main.py` reads that and writes `output.csv`.

In a browser, open `index.html`, either from the link at the top of this page or
by double clicking the file. It asks for three things: the slab thickness in mm,
the wheel load in kN, and a weather CSV. Press **Start** and everything appears. No Python needed, and
the page does the same three conversions for itself, saying at the top which ones
it did.

The page then does the stress as well, in the **Stress in the slab** section.
Four boxes can be changed - the subgrade modulus k, the daily mean offset, the
flexural strength and the wheel load - and the answer is worked out again as
soon as one is changed, so k and the offset can be tried out without editing any
code. I checked the page against `stress.py` at k = 40, 100 and 300 MPa/m and at
both offsets, and the two agree to the last decimal.

The page is not fussy about layout. It hunts down the file for the row of column
names, then looks for a heading containing:

- `hour`, `time` or `date` for the hour
- `air_temp` or `temperature` for the air temperature
- `solar`, `shortwave`, `radiation` or `ghi` for hourly solar radiation
- `radiation_sum` for a whole day solar total, if there is no hourly column
- `wind` for the wind speed
- `latitude`, `longitude` and `utc_offset` for the place and the clock

If the wind heading mentions km/h it is changed to m/s. If the file says what
clock it uses, the times are moved on to IST. If a needed column is missing, the
page says which one and lists the columns it did find, instead of guessing.

I checked the page against six files: the downloaded export, `weather_IST.csv`,
`example_weather.csv`, an export already in IST with hourly solar, `data.csv`,
and a file with only 23 rows. The first four give answers, and the ones that give
the same weather give the same dT to the last decimal. The last two are refused
with a message saying why.

## From dT to stress

`stress.py` is the second half of the work. It takes the hourly dT from
`output.csv` and turns it into a stress, then into a stress ratio.

### The parameters used

| Name | Value | Where it comes from |
|---|---|---|
| h | typed in when the program starts | slab thickness, nothing is assumed |
| L, W | 4500 mm, 3500 mm | IRC:58 Cl. 7.1.3 and 6.2.6 |
| E, mu | 30000 MPa, 0.15 | IRC:58 Cl. 5.8.4.1 |
| alpha | 10 x 10^-6 per C | IRC:58 Cl. 5.8.5 |
| fcr | 4.5 MPa | IRC:58 Cl. 5.8.2 |
| P | typed in when the program starts | IRC:58 Cl. 5.2 gives 50 kN, half a 100 kN axle |
| a | worked out from P | the 0.8 MPa tyre pressure, so 141 mm for a 50 kN wheel |
| k | 40 to 300 MPa/m, all tried | **not yet fixed** - see below |

The subgrade modulus k is the one value still open. It needs a CBR and a
subbase, read off IRC:58 Tables 2 to 4. Until that is picked, the program runs
five values from 40 to 300 MPa/m and prints the answer for each, so nothing is
blocked. The hourly table and the graph use 40 MPa/m.

### The equations

Radius of relative stiffness:

    l = [ E h^3 / (12 (1 - mu^2) k) ]^(1/4)

Bradbury's coefficient, with lambda = side / (l sqrt(8)):

    C = 1 - 2 (sin l cosh l + cos l sinh l) / (sin 2l + sinh 2l)

This is the closed form of the Bradbury chart in Huang. Written this way there
is no tan term, so nothing blows up near L/l = 4.4.

Wheel load, Westergaard, with b = sqrt(1.6 a^2 + h^2) - 0.675 h:

    edge   = 0.572 P / h^2 x [ 4 log10(l/b) + 0.359 ]
    corner = 3 P / h^2 x [ 1 - (a sqrt(2) / l)^0.6 ]

Thermal, Bradbury, for every hour, with the sign of dT kept:

    thermal = Cx E alpha dT / 2

### Adding them up

The two stresses are added where they pull the same fibre of the slab.

- **Edge, bottom of the slab.** The wheel load and a positive dT both put the
  bottom in tension, so they add in the daytime: `edge + thermal`.
- **Corner, top of the slab.** The wheel load and a negative dT both put the
  top in tension, so they add at night: `corner - thermal`, and thermal is
  negative at night, so the total grows.

A negative total means compression, and is set to zero. At any hour where dT is
negative the extra 5 C built-in curl is added, as the code requires.

Then `SR = total / fcr`, and SR gives the allowed repetitions N by IRC:58
Cl. 5.8.6. Below SR = 0.45 there is no fatigue damage at all.

### The answer

With k = 40 MPa/m, l is 1203 mm, so L/l = 3.74 and W/l = 2.91, giving
Cx = 0.365 and Cy = 0.163. The wheel load alone gives 1.109 MPa at the edge
and 0.966 MPa at the corner.

| | offset 0 | offset +4 C |
|---|---|---|
| worst edge SR | 0.388 at 13:00 | 0.436 at 13:00 |
| worst corner SR | 0.377 at 05:00 | 0.329 at 05:00 |

The code, using one dT for the whole day, gives SR = 0.439 at the edge
(dT = +15.8 C) and SR = 0.372 at the corner (dT = -12.9 C).

Three things come out of this:

1. **The worst hours are 13:00 and 05:00**, not the middle of the code's
   10:00 to 16:00 and 00:00 to 06:00 windows. The edge curve is above 0.36 for
   about six hours, from 11:00 to 16:00, which does line up with the code's
   window. The night corner curve is flat from 00:00 to 06:00, so the code's
   night window is the right one.
2. **The daily mean offset decides which case governs.** With no offset the
   edge and corner are nearly equal, 0.388 against 0.377. With +4 C the day gets
   worse and the night gets better, because the offset makes the night dT less
   negative. This is why both are reported instead of one.
3. **k matters more than the offset.** Going from 40 to 300 MPa/m pushes the
   worst SR from about 0.39 to about 0.68. At 100 MPa/m and above the night
   corner governs when there is no offset. So k has to be settled before any
   number here is quoted as final.

No SR reaches 0.45 at k = 40 MPa/m, so N is unlimited and there is no fatigue
damage. Damage only begins at the stiffer subgrades.

### What this part assumes

- dT is the plain top minus bottom temperature, not the equivalent linear
  gradient. The real profile is curved, so this slightly overstates dT.
- Bradbury gives no corner coefficient, so Cx is used at the corner too. This
  is the usual approximation, but it is an approximation.
- No cumulative fatigue damage is worked out, because that needs a design
  traffic figure.

## Files

Three programs run one after the other. Each one writes a file, and the next one
reads it, so every step can be opened and checked on its own.

    weather downloaded  ->  prepare_data.py  ->  weather_IST.csv
    weather_IST.csv     ->  main.py          ->  output.csv
    output.csv          ->  stress.py        ->  stress_output.csv + the graph

### The chain

| File | What it is | What it does | The point of it |
|---|---|---|---|
| `greater_noida_26may.csv` | the weather, downloaded | nothing, it is never edited | real measured weather for 26 May 2026, not made up |
| `prepare_data.py` | program 1 | splits the three tables in the file, moves the times from GMT to IST, and spreads the day's sun total over the hours | the downloaded file cannot be used as it is, and this says exactly what was changed |
| `weather_IST.csv` | made by program 1 | holds the tidy weather: hour, air temperature, sun, wind | the input to the heat model, in four plain columns |
| `main.py` | program 2 | solves heat flow down through the slab, minute by minute, and gives the temperature at five depths every hour | this is where dT comes from |
| `output.csv` | made by program 2 | the 24 hourly temperatures and dT | the main result of the first half |
| `stress.py` | program 3 | turns each hour's dT into a stress, adds the wheel load stress, and gives SR and the allowed repetitions N | this is where the answer to the research question comes from |
| `stress_output.csv` | made by program 3 | 48 rows: 24 hours for each of the two offsets | every number in the paper can be traced back to a row here |
| `SR_vs_hour.png` | made by program 3 | the graph of SR against the hour | the main figure: the peaks are at 13:00 and 05:00, not in the middle of the code's windows |
| `index.html` | the browser version | does both calculations in a browser, with boxes to change k, the offset, the strength and the load | nothing has to be installed, and k can be changed in front of anyone who asks |

### Kept for checking

| File | What it is | Why it is still here |
|---|---|---|
| `data.csv` | an earlier, more detailed model's answers for the same day | the two models are compared in this README, and they agree in the day |
| `example_weather.csv` | a small made up weather file | used to test that the browser page reads a plain file as well as a downloaded one |
| `README.md` | this file | the method, the values, the answers and the assumptions, all written down |

### If someone asks about the code

Each program says at the top what it does, in steps, and the steps are marked
in the code with lines like `# ---- step 2: the weather for every minute ----`.
So the four or five lines at the top of a file are the whole explanation, and
the markers show where each one happens.

**`prepare_data.py`** - the downloaded file is three small tables in one, the
times are GMT, and the sun is given as one total for the day. Step 1 reads the
three tables. Step 2 moves the times on to IST, which needs going halfway
between two readings because IST is 5.5 hours ahead and every reading lands
half an hour off the clock. Step 3 spreads the day's sun total over the hours,
using the height of the sun in the sky as the shape. Step 4 writes the tidy
file.

**`main.py`** - heat is let into the top of the slab and allowed to move down
through it. The slab is cut into points about 10 mm apart, and every point is
stepped forward one minute at a time. Step 2 works out the weather for each of
the 1440 minutes first, so that the loop in step 3 is only about the heat.
Inside that loop there are three lines: the top point, which the sun and the
wind act on, the points inside, each pulled towards its two neighbours, and the
bottom point, where no heat crosses. The day is repeated 8 times so the slab
forgets the temperature it was started at.

**`stress.py`** - this is the textbook method, one formula at a time. `l` says
how far the slab reaches out on to the ground below. Bradbury's `C` says how
much of the curling the slab's own weight holds down. Westergaard's two
formulas give the stress from the wheel. Then for every hour, the temperature
stress is worked out from dT and added to the wheel stress - added at the edge
in the day, added at the corner at night, because that is where the two pull
the same face of the slab. Dividing by the strength of the concrete gives SR.

### If someone asks "what do I run?"

    python prepare_data.py
    python main.py
    python stress.py

Or open `index.html` and choose the weather file, which does both calculations
without installing anything.
