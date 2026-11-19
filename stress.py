# Stress in the concrete slab, hour by hour.
#
# main.py works out dT for all 24 hours and saves it in output.csv. This
# program turns each dT into a stress and gives the stress ratio SR.
#
# It works in five steps:
#   1. ask for the slab and the load, and write down the rest from IRC:58
#   2. work out the numbers that do not change with the hour: how far the
#      slab reaches on to the ground, how much it is held down, and the
#      stress the wheel puts on it
#   3. for each hour, turn dT into a stress and add the wheel stress to it
#   4. divide by the strength of the concrete to get SR, and turn SR into
#      the number of loads the slab can take
#   5. do the same the way the code does it, and draw the graph
#
# It writes stress_output.csv and SR_vs_hour.png.

import math
import pandas as pd
import matplotlib.pyplot as plt


# ---- step 1: the slab, the concrete and the load ----

# Everything is in mm and MPa. That means k must be in MPa/mm, not MPa/m,
# so 40 MPa/m is written as 0.04 here.

# The slab thickness is asked for, because it is the one thing that changes
# from one road to another. It has to be the same thickness main.py was run
# with, because the dT in output.csv was worked out for that slab.
typed = input("Slab thickness in mm: ").strip()
if typed == "":
    print("No thickness was given, so there is nothing to work out.")
    exit()
h = float(typed)

# The wheel load is asked for too. IRC:58 Cl. 5.2 gives 50 kN, half of the
# 100 kN legal single axle, but a different axle means a different load.
typed = input("Wheel load in kN: ").strip()
if typed == "":
    print("No wheel load was given, so there is nothing to work out.")
    exit()
P = float(typed) * 1000         # kN typed in, newtons used inside

L = 4500         # joint spacing, mm              IRC:58 Cl. 7.1.3
W = 3500         # lane width, mm                 IRC:58 Cl. 6.2.6
E = 30000        # modulus of the concrete, MPa   IRC:58 Cl. 5.8.4.1
mu = 0.15        # Poisson's ratio                IRC:58 Cl. 5.8.4.1
alpha = 10e-6    # thermal expansion, per deg C   IRC:58 Cl. 5.8.5
fcr = 4.5        # flexural strength, MPa         IRC:58 Cl. 5.8.2
tyre = 0.8       # tyre pressure, MPa

curl = 5            # built-in curl, added at night
code_day = 15.8     # the one daytime dT the code gives
code_night = -(code_day / 2 + curl)

k_base = 0.04       # the subgrade modulus used for the table and the graph
k_list = [0.04, 0.06, 0.10, 0.20, 0.30]     # the same as 40 to 300 MPa/m
offsets = [0, 4]                            # the two daily mean offsets

a = math.sqrt(P / (math.pi * tyre))      # radius of the tyre print, mm

# the hourly dT worked out by main.py
model = pd.read_csv("output.csv")
hours = list(model["hour_IST"])
dT_model = list(model["dT"])

# The last depth column in output.csv is named after the bottom of the slab,
# so it says which thickness main.py was run with. If that is not the
# thickness asked for here, the dT values belong to a different slab.
bottom = ""
for name in model.columns:
    if name.startswith("T_"):
        bottom = name
ran_at = float(bottom[2:-2])
if abs(ran_at - h) > 0.5:
    print("output.csv holds the dT of a", round(ran_at), "mm slab, not", round(h), "mm.")
    print("Run main.py again with", round(h), "mm before running this.")
    exit()


# ---- step 2: the formulas ----

# how far the slab reaches out on to the ground below it
def stiffness_radius(k):
    return (E * h ** 3 / (12 * (1 - mu ** 2) * k)) ** 0.25


# Bradbury's coefficient: how much of the curling the slab's own weight holds down
def bradbury(side, l):
    x = side / (l * math.sqrt(8))
    top = math.sin(x) * math.cosh(x) + math.cos(x) * math.sinh(x)
    bottom = math.sin(2 * x) + math.sinh(2 * x)
    return 1 - 2 * top / bottom


# Westergaard wheel load at the edge, which pulls the bottom of the slab.
# a is smaller than 1.724 h here, so b is worked out this way.
def wheel_edge(l):
    b = math.sqrt(1.6 * a ** 2 + h ** 2) - 0.675 * h
    return 0.572 * P / h ** 2 * (4 * math.log10(l / b) + 0.359)


# Westergaard wheel load at the corner, which pulls the top of the slab
def wheel_corner(l):
    return 3 * P / h ** 2 * (1 - (a * math.sqrt(2) / l) ** 0.6)


# how many loads the slab can take at this stress ratio, IRC:58 Cl. 5.8.6
def repetitions(SR):
    if SR < 0.45:
        return "unlimited"
    if SR <= 0.55:
        return round((4.2577 / (SR - 0.4325)) ** 3.268)
    return round(10 ** ((0.9718 - SR) / 0.0828))


# the four numbers that depend only on the ground under the slab
def slab_numbers(k):
    l = stiffness_radius(k)
    return l, bradbury(L, l), wheel_edge(l), wheel_corner(l)


# ---- step 3: one hour, and one whole day ----

def one_hour(dT, offset, Cx, load_edge, load_corner):
    dT = dT + offset
    if dT < 0:
        dT = dT - curl          # night, so the built-in curl is added on

    thermal = Cx * E * alpha * dT / 2

    edge = load_edge + thermal          # both of these pull the bottom
    corner = load_corner - thermal      # both of these pull the top

    # a minus answer means the concrete is being squeezed, not pulled
    if edge < 0:
        edge = 0
    if corner < 0:
        corner = 0

    return {"dT": dT, "thermal": thermal, "edge": edge, "corner": corner}


# all 24 hours, for one subgrade modulus and one offset
def one_day(k, offset):
    l, Cx, load_edge, load_corner = slab_numbers(k)
    day = []
    for i in range(24):
        day.append(one_hour(dT_model[i], offset, Cx, load_edge, load_corner))
    return day


# ---- step 4: the stress ratios ----

# the stress ratio for every hour, either at the "edge" or at the "corner"
def ratios(day, place):
    out = []
    for hour in day:
        out.append(hour[place] / fcr)
    return out


# the biggest stress ratio of the day, and the hour it happens
def worst(day, place):
    SR = ratios(day, place)
    top = max(SR)
    return top, hours[SR.index(top)]


l, Cx, load_edge, load_corner = slab_numbers(k_base)

print("subgrade modulus used for the table and graph:", round(k_base * 1000), "MPa/m")
print("tyre print radius a =", round(a, 1), "mm")
print("l =", round(l, 1), "mm, so L/l =", round(L / l, 2), "and W/l =", round(W / l, 2))
print("Cx =", round(Cx, 3), " Cy =", round(bradbury(W, l), 3))
print("wheel load on its own:", round(load_edge, 3), "MPa at the edge,",
      round(load_corner, 3), "MPa at the corner")

rows = []
for offset in offsets:
    day = one_day(k_base, offset)
    SR_edge = ratios(day, "edge")
    SR_corner = ratios(day, "corner")

    for i in range(24):
        hour = day[i]
        rows.append([offset, hours[i], dT_model[i], round(hour["dT"], 2),
                     round(hour["thermal"], 3), round(hour["edge"], 3),
                     round(SR_edge[i], 3), repetitions(SR_edge[i]),
                     round(hour["corner"], 3), round(SR_corner[i], 3),
                     repetitions(SR_corner[i])])

    top_edge, when_edge = worst(day, "edge")
    top_corner, when_corner = worst(day, "corner")
    print()
    print("offset", offset, "degrees:")
    print("  worst edge SR  ", round(top_edge, 3), "at", when_edge)
    print("  worst corner SR", round(top_corner, 3), "at", when_corner)

result = pd.DataFrame(rows, columns=["offset_C", "hour_IST", "dT_model_C", "dT_used_C",
                                     "thermal_MPa", "edge_MPa", "SR_edge", "N_edge",
                                     "corner_MPa", "SR_corner", "N_corner"])
result.to_csv("stress_output.csv", index=False)


# ---- step 5: the code's way, the other subgrades, and the graph ----

# the same slab worked out the way the code does it, with one dT for the whole day
code_edge = load_edge + Cx * E * alpha * code_day / 2
code_corner = load_corner - Cx * E * alpha * code_night / 2
print()
print("the code's way, one dT for the whole day:")
print("  day, dT =", code_day, "gives edge SR", round(code_edge / fcr, 3))
print("  night, dT =", code_night, "gives corner SR", round(code_corner / fcr, 3))

# what happens if the subgrade turns out to be stiffer
print()
print("if the subgrade modulus is different:")
for k in k_list:
    for offset in offsets:
        day = one_day(k, offset)
        top_edge, when_edge = worst(day, "edge")
        top_corner, when_corner = worst(day, "corner")
        print("  k =", round(k * 1000), "MPa/m, offset", offset,
              ": edge SR", round(top_edge, 3), "at", when_edge,
              ", corner SR", round(top_corner, 3), "at", when_corner)

# the graph of SR against the hour
plt.style.use("dark_background")
plt.figure(figsize=(10, 6))
colour = ["#4da3ff", "#ff9f40"]

for n in range(len(offsets)):
    offset = offsets[n]
    day = one_day(k_base, offset)
    plt.plot(range(24), ratios(day, "edge"), "-o", markersize=4,
             color=colour[n], label="edge, bottom, offset +" + str(offset))
    plt.plot(range(24), ratios(day, "corner"), "--s", markersize=4,
             color=colour[n], label="corner, top, offset +" + str(offset))

plt.axhline(code_edge / fcr, color="#ff5c5c", linewidth=1, label="code, day edge")
plt.axhline(code_corner / fcr, color="#5cff9d", linewidth=1, label="code, night corner")
plt.axhline(0.45, color="grey", linewidth=1, linestyle=":", label="SR 0.45, no damage below")

# the two six hour windows the code itself uses
plt.axvspan(10, 16, color="#ff5c5c", alpha=0.08)
plt.axvspan(0, 6, color="#5cff9d", alpha=0.08)

plt.xticks(range(24))
plt.xlim(0, 23)
plt.ylim(0, None)
plt.xlabel("hour of day, IST")
plt.ylabel("stress ratio SR")
plt.title("Stress ratio hour by hour, " + str(round(h)) + " mm slab, k = "
          + str(round(k_base * 1000)) + " MPa/m")
plt.grid(alpha=0.2)
plt.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=3)
plt.tight_layout()
plt.savefig("SR_vs_hour.png", dpi=150)

print()
print("written: stress_output.csv and SR_vs_hour.png")
