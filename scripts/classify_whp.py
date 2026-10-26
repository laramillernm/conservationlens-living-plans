from pathlib import Path
import csv
import arcpy
from arcpy.sa import Raster, Con

arcpy.CheckOutExtension("Spatial")

# --------------------------------------------------
# Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

WHP_RASTER = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "wildfire"
    / "el_rito_whp.tif"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "wildfire"
)

REPORT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "wildfire"
)

USFS_OUTPUT = OUTPUT_DIR / "el_rito_whp_usfs.tif"
LOCAL_OUTPUT = OUTPUT_DIR / "el_rito_whp_local.tif"

BREAKS_CSV = REPORT_DIR / "whp_class_breaks.csv"
SUMMARY_CSV = REPORT_DIR / "whp_class_summary.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

arcpy.env.overwriteOutput = True

if not WHP_RASTER.exists():
    raise FileNotFoundError(f"Missing WHP raster: {WHP_RASTER}")


# --------------------------------------------------
# Read raster values and counts
# --------------------------------------------------

print("Reading WHP value distribution...")

arcpy.management.BuildRasterAttributeTable(
    str(WHP_RASTER),
    "Overwrite"
)

values = []

with arcpy.da.SearchCursor(
    str(WHP_RASTER),
    ["Value", "Count"]
) as cursor:

    for value, count in cursor:

        # Exclude zero from percentile calculations.
        # We retain it in the raster but do not let large zero areas
        # control the local priority breaks.
        if value > 0:
            values.append((int(value), int(count)))


values.sort(key=lambda x: x[0])

total_cells = sum(count for value, count in values)


# --------------------------------------------------
# Weighted percentile function
# --------------------------------------------------

def weighted_percentile(data, percentile):

    target = total_cells * percentile

    cumulative = 0

    for value, count in data:

        cumulative += count

        if cumulative >= target:
            return value

    return data[-1][0]


# --------------------------------------------------
# National USFS percentile thresholds
# --------------------------------------------------

national_p44 = weighted_percentile(values, 0.44)
national_p67 = weighted_percentile(values, 0.67)
national_p84 = weighted_percentile(values, 0.84)
national_p95 = weighted_percentile(values, 0.95)


# --------------------------------------------------
# Local planning thresholds
# --------------------------------------------------

local_p50 = weighted_percentile(values, 0.50)
local_p75 = weighted_percentile(values, 0.75)
local_p90 = weighted_percentile(values, 0.90)


print("Calculated class breaks:")
print(f"National-style p44: {national_p44}")
print(f"National-style p67: {national_p67}")
print(f"National-style p84: {national_p84}")
print(f"National-style p95: {national_p95}")

print(f"Local p50: {local_p50}")
print(f"Local p75: {local_p75}")
print(f"Local p90: {local_p90}")


# --------------------------------------------------
# Create raster objects
# --------------------------------------------------

whp = Raster(str(WHP_RASTER))


# --------------------------------------------------
# USFS-style five-class raster
#
# 0 = No/zero WHP
# 1 = Very Low
# 2 = Low
# 3 = Moderate
# 4 = High
# 5 = Very High
# --------------------------------------------------

print("Creating USFS-style WHP classification...")

usfs = Con(
    whp == 0,
    0,
    Con(
        whp <= national_p44,
        1,
        Con(
            whp <= national_p67,
            2,
            Con(
                whp <= national_p84,
                3,
                Con(
                    whp <= national_p95,
                    4,
                    5
                )
            )
        )
    )
)

usfs.save(str(USFS_OUTPUT))


# --------------------------------------------------
# Local priority raster
#
# 0 = No/zero WHP
# 1 = Lower
# 2 = Moderate
# 3 = High
# 4 = Highest
# --------------------------------------------------

print("Creating local WHP priority classification...")

local = Con(
    whp == 0,
    0,
    Con(
        whp <= local_p50,
        1,
        Con(
            whp <= local_p75,
            2,
            Con(
                whp <= local_p90,
                3,
                4
            )
        )
    )
)

local.save(str(LOCAL_OUTPUT))


# --------------------------------------------------
# Write class break documentation
# --------------------------------------------------

with open(BREAKS_CSV, "w", newline="") as csvfile:

    fieldnames = [
        "classification",
        "class_name",
        "lower_percentile",
        "upper_percentile",
        "upper_whp_value"
    ]

    writer = csv.DictWriter(
        csvfile,
        fieldnames=fieldnames
    )

    writer.writeheader()

    writer.writerows([
        {
            "classification": "USFS-style",
            "class_name": "Very Low",
            "lower_percentile": 0,
            "upper_percentile": 44,
            "upper_whp_value": national_p44
        },
        {
            "classification": "USFS-style",
            "class_name": "Low",
            "lower_percentile": 44,
            "upper_percentile": 67,
            "upper_whp_value": national_p67
        },
        {
            "classification": "USFS-style",
            "class_name": "Moderate",
            "lower_percentile": 67,
            "upper_percentile": 84,
            "upper_whp_value": national_p84
        },
        {
            "classification": "USFS-style",
            "class_name": "High",
            "lower_percentile": 84,
            "upper_percentile": 95,
            "upper_whp_value": national_p95
        },
        {
            "classification": "USFS-style",
            "class_name": "Very High",
            "lower_percentile": 95,
            "upper_percentile": 100,
            "upper_whp_value": ""
        },

        {
            "classification": "Local",
            "class_name": "Lower",
            "lower_percentile": 0,
            "upper_percentile": 50,
            "upper_whp_value": local_p50
        },
        {
            "classification": "Local",
            "class_name": "Moderate",
            "lower_percentile": 50,
            "upper_percentile": 75,
            "upper_whp_value": local_p75
        },
        {
            "classification": "Local",
            "class_name": "High",
            "lower_percentile": 75,
            "upper_percentile": 90,
            "upper_whp_value": local_p90
        },
        {
            "classification": "Local",
            "class_name": "Highest",
            "lower_percentile": 90,
            "upper_percentile": 100,
            "upper_whp_value": ""
        }
    ])


# --------------------------------------------------
# Summarize classified rasters
# --------------------------------------------------

print("Summarizing classified rasters...")

cell_size_x = float(
    arcpy.management.GetRasterProperties(
        str(WHP_RASTER),
        "CELLSIZEX"
    ).getOutput(0)
)

cell_size_y = float(
    arcpy.management.GetRasterProperties(
        str(WHP_RASTER),
        "CELLSIZEY"
    ).getOutput(0)
)

cell_area_sq_m = cell_size_x * cell_size_y

SQ_METERS_PER_ACRE = 4046.8564224


class_labels = {

    "USFS-style": {
        0: "Zero / No WHP",
        1: "Very Low",
        2: "Low",
        3: "Moderate",
        4: "High",
        5: "Very High"
    },

    "Local": {
        0: "Zero / No WHP",
        1: "Lower",
        2: "Moderate",
        3: "High",
        4: "Highest"
    }
}


summary_rows = []


for classification, raster_path in [
    ("USFS-style", USFS_OUTPUT),
    ("Local", LOCAL_OUTPUT)
]:

    arcpy.management.BuildRasterAttributeTable(
        str(raster_path),
        "Overwrite"
    )

    rows = []

    total = 0

    with arcpy.da.SearchCursor(
        str(raster_path),
        ["Value", "Count"]
    ) as cursor:

        for value, count in cursor:

            value = int(value)
            count = int(count)

            total += count

            rows.append((value, count))

    for value, count in rows:

        acres = (
            count
            * cell_area_sq_m
            / SQ_METERS_PER_ACRE
        )

        percent = (
            count
            / total
            * 100
        )

        summary_rows.append(
            {
                "classification": classification,
                "class_value": value,
                "class_name":
                    class_labels[classification].get(
                        value,
                        "Unknown"
                    ),
                "cell_count": count,
                "acres": acres,
                "percent": percent
            }
        )


with open(SUMMARY_CSV, "w", newline="") as csvfile:

    fieldnames = [
        "classification",
        "class_value",
        "class_name",
        "cell_count",
        "acres",
        "percent"
    ]

    writer = csv.DictWriter(
        csvfile,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(summary_rows)


print("Finished.")
print(f"USFS-style raster: {USFS_OUTPUT}")
print(f"Local priority raster: {LOCAL_OUTPUT}")
print(f"Class breaks: {BREAKS_CSV}")
print(f"Class summary: {SUMMARY_CSV}")

arcpy.CheckInExtension("Spatial")