from pathlib import Path
from datetime import datetime
import csv
import arcpy


# --------------------------------------------------
# PROJECT SETTINGS
# --------------------------------------------------

PROJECT_ROOT = Path(
    r"C:\Users\Lara\ConservationInsights\conservationlens-living-plans"
)

BASELINE_YEAR = 2020

BOUNDARY = (
    PROJECT_ROOT
    / "data"
    / "boundaries"
    / "el_rito_boundary.geojson"
)

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "fire_history"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "fire_history"
)

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

arcpy.env.overwriteOutput = True


# --------------------------------------------------
# LIVE WFIGS SERVICE
# --------------------------------------------------

SERVICE_URL = (
    r"https://services3.arcgis.com/"
    r"T4QMspbfLg3qTGWY/ArcGIS/rest/services/"
    r"WFIGS_Interagency_Perimeters/FeatureServer/0"
)

DATE_FIELD = "attr_FireDiscoveryDateTime"


# --------------------------------------------------
# CHECK INPUTS
# --------------------------------------------------

print("Checking inputs...")

if not BOUNDARY.exists():
    raise FileNotFoundError(
        f"Missing boundary:\n{BOUNDARY}"
    )

if not arcpy.Exists(SERVICE_URL):
    raise RuntimeError(
        "ArcGIS Pro cannot access the WFIGS service."
    )

print("Inputs found.")


# --------------------------------------------------
# CONVERT EL RITO GEOJSON
# --------------------------------------------------

scratch_gdb = arcpy.env.scratchGDB

boundary_fc = str(
    Path(scratch_gdb)
    / "el_rito_fire_history_boundary"
)

if arcpy.Exists(boundary_fc):
    arcpy.management.Delete(boundary_fc)

print("Converting El Rito boundary...")

arcpy.conversion.JSONToFeatures(
    str(BOUNDARY),
    boundary_fc
)


# --------------------------------------------------
# CREATE LIVE FEATURE LAYER
# --------------------------------------------------

print("Connecting to live WFIGS service...")

live_layer = "wfigs_live_layer"

if arcpy.Exists(live_layer):
    arcpy.management.Delete(live_layer)

arcpy.management.MakeFeatureLayer(
    SERVICE_URL,
    live_layer
)


# --------------------------------------------------
# SPATIAL SELECTION FIRST
#
# This avoids asking the remote server to process
# our date expression.
# --------------------------------------------------

print(
    "Selecting fire perimeters that intersect El Rito..."
)

arcpy.management.SelectLayerByLocation(
    live_layer,
    "INTERSECT",
    boundary_fc,
    selection_type="NEW_SELECTION"
)

spatial_count = int(
    arcpy.management.GetCount(
        live_layer
    ).getOutput(0)
)

print(
    f"Fire perimeter records intersecting El Rito: "
    f"{spatial_count}"
)


# --------------------------------------------------
# COPY LOCAL CANDIDATES
# --------------------------------------------------

candidate_fc = str(
    Path(scratch_gdb)
    / "el_rito_wfigs_candidates"
)

if arcpy.Exists(candidate_fc):
    arcpy.management.Delete(candidate_fc)

print("Copying El Rito candidate fires locally...")

arcpy.conversion.ExportFeatures(
    live_layer,
    candidate_fc
)


# --------------------------------------------------
# VERIFY DATE FIELD
# --------------------------------------------------

fields = [
    field.name
    for field in arcpy.ListFields(candidate_fc)
]

if DATE_FIELD not in fields:
    raise RuntimeError(
        f"Expected date field not found: {DATE_FIELD}"
    )


# --------------------------------------------------
# FILTER LOCALLY BY BASELINE YEAR
# --------------------------------------------------

print(
    f"Filtering fires discovered in "
    f"{BASELINE_YEAR} or later..."
)

keep_objectids = []

oid_field = arcpy.Describe(
    candidate_fc
).OIDFieldName


with arcpy.da.SearchCursor(
    candidate_fc,
    [
        oid_field,
        DATE_FIELD
    ]
) as cursor:

    for oid, discovery_date in cursor:

        if discovery_date is None:
            continue

        if discovery_date.year >= BASELINE_YEAR:
            keep_objectids.append(oid)


print(
    f"Fire records after baseline filter: "
    f"{len(keep_objectids)}"
)


# --------------------------------------------------
# CREATE LOCAL FILTERED LAYER
# --------------------------------------------------

candidate_layer = "candidate_fire_layer"

if arcpy.Exists(candidate_layer):
    arcpy.management.Delete(candidate_layer)

arcpy.management.MakeFeatureLayer(
    candidate_fc,
    candidate_layer
)


if keep_objectids:

    oid_list = ",".join(
        str(x)
        for x in keep_objectids
    )

    where_clause = (
        f"{arcpy.AddFieldDelimiters(candidate_fc, oid_field)} "
        f"IN ({oid_list})"
    )

    arcpy.management.SelectLayerByAttribute(
        candidate_layer,
        "NEW_SELECTION",
        where_clause
    )

else:

    print(
        "No fires after the baseline year "
        "intersect the El Rito boundary."
    )


# --------------------------------------------------
# CREATE GEOPACKAGE
# --------------------------------------------------

gpkg = (
    PROCESSED_DIR
    / "el_rito_fire_history.gpkg"
)

if not arcpy.Exists(str(gpkg)):

    arcpy.management.CreateSQLiteDatabase(
        str(gpkg),
        "GEOPACKAGE"
    )


perimeter_output = (
    str(gpkg)
    + r"\fire_perimeters_since_baseline"
)


if arcpy.Exists(perimeter_output):
    arcpy.management.Delete(perimeter_output)


# --------------------------------------------------
# EXPORT FULL FIRE PERIMETERS
# --------------------------------------------------

if keep_objectids:

    print(
        "Saving fire perimeters since baseline..."
    )

    arcpy.conversion.ExportFeatures(
        candidate_layer,
        perimeter_output
    )


# --------------------------------------------------
# CLIP TO EL RITO
# --------------------------------------------------

clipped_output = (
    str(gpkg)
    + r"\fire_area_inside_el_rito"
)

if arcpy.Exists(clipped_output):
    arcpy.management.Delete(clipped_output)


if keep_objectids:

    print(
        "Clipping fire perimeters to El Rito..."
    )

    arcpy.analysis.Clip(
        perimeter_output,
        boundary_fc,
        clipped_output
    )


# --------------------------------------------------
# CALCULATE AREA INSIDE EL RITO
# --------------------------------------------------

total_acres = 0.0


if keep_objectids:

    fields = [
        f.name
        for f in arcpy.ListFields(
            clipped_output
        )
    ]

    if "CL_Acres" not in fields:

        arcpy.management.AddField(
            clipped_output,
            "CL_Acres",
            "DOUBLE"
        )


    arcpy.management.CalculateGeometryAttributes(
        clipped_output,
        [
            [
                "CL_Acres",
                "AREA_GEODESIC"
            ]
        ],
        area_unit="ACRES_US"
    )


    with arcpy.da.SearchCursor(
        clipped_output,
        ["CL_Acres"]
    ) as cursor:

        for row in cursor:

            if row[0] is not None:
                total_acres += row[0]


# --------------------------------------------------
# CREATE FIRE SUMMARY CSV
# --------------------------------------------------

summary_csv = (
    OUTPUT_DIR
    / "fire_history_summary.csv"
)


with open(
    summary_csv,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "geography",
        "baseline_year",
        "fire_perimeter_records",
        "affected_acres",
        "source",
        "refresh_date"
    ])

    writer.writerow([
        "El Rito",
        BASELINE_YEAR,
        len(keep_objectids),
        round(total_acres, 2),
        "WFIGS Interagency Fire Perimeters",
        datetime.now().isoformat()
    ])


# --------------------------------------------------
# WRITE REFRESH METADATA
# --------------------------------------------------

refresh_file = (
    OUTPUT_DIR
    / "fire_history_refresh.txt"
)


with open(
    refresh_file,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "source=WFIGS Interagency Fire Perimeters\n"
    )

    f.write(
        f"baseline_year={BASELINE_YEAR}\n"
    )

    f.write(
        f"date_field={DATE_FIELD}\n"
    )

    f.write(
        f"refresh_time={datetime.now().isoformat()}\n"
    )

    f.write(
        f"candidate_records={spatial_count}\n"
    )

    f.write(
        f"post_baseline_records={len(keep_objectids)}\n"
    )

    f.write(
        f"affected_acres={total_acres:.2f}\n"
    )


# --------------------------------------------------
# FINISHED
# --------------------------------------------------

print("")
print("Finished.")
print("")

print(
    f"Candidate perimeter records: "
    f"{spatial_count}"
)

print(
    f"Post-baseline fire records: "
    f"{len(keep_objectids)}"
)

print(
    f"Area affected inside El Rito: "
    f"{total_acres:,.1f} acres"
)

print(
    f"\nSummary:\n{summary_csv}"
)

print(
    f"\nRefresh metadata:\n{refresh_file}"
)