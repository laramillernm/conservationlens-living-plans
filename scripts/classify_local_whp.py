from pathlib import Path
import csv
import numpy as np
import arcpy


# --------------------------------------------------
# Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(
    r"C:\Users\Lara\ConservationInsights\conservationlens-living-plans"
)

WHP_INPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "wildfire"
    / "el_rito_whp.tif"
)

USFS_INPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "wildfire"
    / "el_rito_whp_usfs.tif"
)

LOCAL_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "wildfire"
    / "el_rito_whp_local.tif"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "wildfire"
)

BREAKS_CSV = (
    OUTPUT_DIR
    / "whp_local_breaks.csv"
)

SUMMARY_CSV = (
    OUTPUT_DIR
    / "whp_class_summary.csv"
)


# --------------------------------------------------
# Setup
# --------------------------------------------------

arcpy.env.overwriteOutput = True

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

print("Checking inputs...")

for path in [WHP_INPUT, USFS_INPUT]:

    if not path.exists():

        raise FileNotFoundError(
            f"Missing input:\n{path}"
        )

print("Inputs found.")


# --------------------------------------------------
# Read local WHP raster
# --------------------------------------------------

print("Reading local WHP raster...")

desc = arcpy.Describe(
    str(WHP_INPUT)
)

cell_width = desc.meanCellWidth
cell_height = desc.meanCellHeight

lower_left = arcpy.Point(
    desc.extent.XMin,
    desc.extent.YMin
)

spatial_reference = (
    desc.spatialReference
)


# --------------------------------------------------
# Convert raster to NumPy array
#
# ArcPy cannot put NaN directly into an integer
# raster array, so first use a numeric sentinel.
# --------------------------------------------------

NODATA_SENTINEL = -9999

array = arcpy.RasterToNumPyArray(
    str(WHP_INPUT),
    nodata_to_value=NODATA_SENTINEL
)

# Convert to floating point so NaN is allowed
array = array.astype(
    "float64"
)

# Convert the temporary NoData value to NaN
array[
    array == NODATA_SENTINEL
] = np.nan


# --------------------------------------------------
# Select valid WHP cells for percentile calculation
#
# Zero values are excluded so zero/non-hazard areas
# do not control the local percentile thresholds.
# --------------------------------------------------

valid_values = array[
    np.isfinite(array)
    & (array > 0)
]

if valid_values.size == 0:

    raise RuntimeError(
        "No valid WHP values greater than zero "
        "were found in the El Rito raster."
    )


# --------------------------------------------------
# Calculate local percentile thresholds
# --------------------------------------------------

print(
    "Calculating local WHP percentile thresholds..."
)

p50 = float(
    np.percentile(
        valid_values,
        50
    )
)

p75 = float(
    np.percentile(
        valid_values,
        75
    )
)

p90 = float(
    np.percentile(
        valid_values,
        90
    )
)

print(
    f"Local WHP 50th percentile: {p50}"
)

print(
    f"Local WHP 75th percentile: {p75}"
)

print(
    f"Local WHP 90th percentile: {p90}"
)


# --------------------------------------------------
# Create local priority classification
#
# 0 = Zero / No WHP
# 1 = Lower
# 2 = Moderate
# 3 = High
# 4 = Highest
#
# 255 = NoData
# --------------------------------------------------

print(
    "Creating local WHP priority classification..."
)

classified = np.full(
    array.shape,
    255,
    dtype=np.uint8
)

valid_mask = np.isfinite(
    array
)


# Zero WHP
classified[
    valid_mask
    & (array == 0)
] = 0


# Lower
# > 0 through 50th percentile
classified[
    valid_mask
    & (array > 0)
    & (array <= p50)
] = 1


# Moderate
# > 50th through 75th percentile
classified[
    valid_mask
    & (array > p50)
    & (array <= p75)
] = 2


# High
# > 75th through 90th percentile
classified[
    valid_mask
    & (array > p75)
    & (array <= p90)
] = 3


# Highest
# > 90th percentile
classified[
    valid_mask
    & (array > p90)
] = 4


# --------------------------------------------------
# Convert classified NumPy array back to raster
# --------------------------------------------------

print(
    "Writing local WHP priority raster..."
)

local_raster = (
    arcpy.NumPyArrayToRaster(
        classified,
        lower_left,
        cell_width,
        cell_height,
        255
    )
)

local_raster.save(
    str(LOCAL_OUTPUT)
)

arcpy.management.DefineProjection(
    str(LOCAL_OUTPUT),
    spatial_reference
)

print(
    f"Created:\n{LOCAL_OUTPUT}"
)


# --------------------------------------------------
# Write local breakpoints CSV
# --------------------------------------------------

print(
    "Writing local classification breakpoints..."
)

with open(
    BREAKS_CSV,
    "w",
    newline=""
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "class_value",
        "class_name",
        "percentile_range",
        "lower_whp_value",
        "upper_whp_value"
    ])

    writer.writerow([
        0,
        "Zero / No WHP",
        "Not included",
        0,
        0
    ])

    writer.writerow([
        1,
        "Lower",
        "0-50",
        ">0",
        p50
    ])

    writer.writerow([
        2,
        "Moderate",
        "50-75",
        p50,
        p75
    ])

    writer.writerow([
        3,
        "High",
        "75-90",
        p75,
        p90
    ])

    writer.writerow([
        4,
        "Highest",
        "90-100",
        p90,
        ""
    ])


# --------------------------------------------------
# Function to summarize a classified raster
# --------------------------------------------------

SQ_METERS_PER_ACRE = 4046.8564224


def summarize_raster(
    raster_path,
    classification_name,
    labels,
    nodata_value
):

    print(
        f"Summarizing {classification_name}..."
    )

    raster_desc = arcpy.Describe(
        str(raster_path)
    )

    cell_area_sq_m = (
        raster_desc.meanCellWidth
        * raster_desc.meanCellHeight
    )

    raster_array = (
        arcpy.RasterToNumPyArray(
            str(raster_path),
            nodata_to_value=nodata_value
        )
    )

    valid_array = raster_array[
        raster_array != nodata_value
    ]

    values, counts = np.unique(
        valid_array,
        return_counts=True
    )

    total_count = int(
        counts.sum()
    )

    rows = []

    for value, count in zip(
        values,
        counts
    ):

        value = int(value)
        count = int(count)

        acres = (
            count
            * cell_area_sq_m
            / SQ_METERS_PER_ACRE
        )

        percent = (
            count
            / total_count
            * 100
        )

        rows.append({
            "classification":
                classification_name,

            "class_value":
                value,

            "class_name":
                labels.get(
                    value,
                    "Unknown"
                ),

            "cell_count":
                count,

            "acres":
                acres,

            "percent":
                percent
        })

    return rows


# --------------------------------------------------
# Class labels
# --------------------------------------------------

usfs_labels = {

    1: "Very Low",
    2: "Low",
    3: "Moderate",
    4: "High",
    5: "Very High",
    6: "Non-burnable",
    7: "Water"

}


local_labels = {

    0: "Zero / No WHP",
    1: "Lower",
    2: "Moderate",
    3: "High",
    4: "Highest"

}


# --------------------------------------------------
# Summarize USFS national classification
# and local priority classification
# --------------------------------------------------

print(
    "Creating national and local summary..."
)

summary_rows = []


summary_rows.extend(

    summarize_raster(
        USFS_INPUT,
        "USFS National",
        usfs_labels,
        -9999
    )

)


summary_rows.extend(

    summarize_raster(
        LOCAL_OUTPUT,
        "Local Priority",
        local_labels,
        255
    )

)


# --------------------------------------------------
# Write summary CSV
# --------------------------------------------------

with open(
    SUMMARY_CSV,
    "w",
    newline=""
) as f:

    fieldnames = [

        "classification",
        "class_value",
        "class_name",
        "cell_count",
        "acres",
        "percent"

    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()

    writer.writerows(
        summary_rows
    )


# --------------------------------------------------
# Finished
# --------------------------------------------------

print("")
print("Finished.")
print("")

print(
    f"Local WHP raster:\n"
    f"{LOCAL_OUTPUT}"
)

print(
    f"\nLocal breakpoints:\n"
    f"{BREAKS_CSV}"
)

print(
    f"\nClass summary:\n"
    f"{SUMMARY_CSV}"
)