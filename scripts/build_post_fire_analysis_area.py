from pathlib import Path
import arcpy
import yaml


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(
    r"C:\Users\Lara\ConservationInsights\conservationlens-living-plans"
)

CONFIG_FILE = (
    PROJECT_ROOT
    / "config"
    / "prototype.yaml"
)

PLANNING_BOUNDARY = (
    PROJECT_ROOT
    / "data"
    / "boundaries"
    / "el_rito_boundary.geojson"
)

HYDROLOGIC_CONTEXT_GPKG = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hydrology"
    / "hydrologic_context.gpkg"
)

HYDROLOGIC_CONTEXT_LAYER = (
    str(HYDROLOGIC_CONTEXT_GPKG)
    + "\\hydrologic_context_huc12"
)

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "post_fire"
)

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)

TEMP_GDB = (
    PROCESSED_DIR
    / "post_fire_area_temp.gdb"
)

OUTPUT_GPKG = (
    PROCESSED_DIR
    / "post_fire_analysis_area.gpkg"
)

OUTPUT_LAYER = (
    str(OUTPUT_GPKG)
    + "\\post_fire_analysis_area"
)


# ============================================================
# READ CONFIG
# ============================================================

with CONFIG_FILE.open(
    "r",
    encoding="utf-8"
) as f:

    config = yaml.safe_load(f)


planning_name = (
    config["planning_area"]["name"]
)


print()
print(
    "ConservationLens post-fire analysis area builder"
)
print(
    "================================================"
)
print()

print(
    f"Planning area: {planning_name}"
)

print()


# ============================================================
# VALIDATE INPUTS
# ============================================================

if not PLANNING_BOUNDARY.exists():

    raise FileNotFoundError(
        "Planning boundary not found:\n"
        f"{PLANNING_BOUNDARY}"
    )


if not arcpy.Exists(
    HYDROLOGIC_CONTEXT_LAYER
):

    raise FileNotFoundError(
        "Hydrologic context layer not found:\n"
        f"{HYDROLOGIC_CONTEXT_LAYER}"
    )


# ============================================================
# CREATE TEMP GEODATABASE
# ============================================================

if not arcpy.Exists(
    str(TEMP_GDB)
):

    arcpy.management.CreateFileGDB(
        str(PROCESSED_DIR),
        TEMP_GDB.name
    )


# ============================================================
# CONVERT PLANNING BOUNDARY
# ============================================================

planning_fc = str(
    TEMP_GDB
    / "planning_area"
)

if arcpy.Exists(
    planning_fc
):

    arcpy.management.Delete(
        planning_fc
    )


arcpy.conversion.JSONToFeatures(
    str(PLANNING_BOUNDARY),
    planning_fc
)


planning_count = int(
    arcpy.management.GetCount(
        planning_fc
    )[0]
)

print(
    f"Planning-area features: "
    f"{planning_count}"
)


# ============================================================
# CHECK HYDROLOGIC CONTEXT
# ============================================================

context_count = int(
    arcpy.management.GetCount(
        HYDROLOGIC_CONTEXT_LAYER
    )[0]
)

print(
    f"Hydrologic context features: "
    f"{context_count}"
)

print()


# ============================================================
# MERGE PLANNING AREA + HYDROLOGIC CONTEXT
# ============================================================

merged_fc = str(
    TEMP_GDB
    / "post_fire_analysis_merge"
)

if arcpy.Exists(
    merged_fc
):

    arcpy.management.Delete(
        merged_fc
    )


merge_inputs = [
    planning_fc
]


if context_count > 0:

    merge_inputs.append(
        HYDROLOGIC_CONTEXT_LAYER
    )


arcpy.management.Merge(
    merge_inputs,
    merged_fc
)


# ============================================================
# DISSOLVE TO SINGLE ANALYSIS AREA
# ============================================================

dissolved_fc = str(
    TEMP_GDB
    / "post_fire_analysis_area"
)

if arcpy.Exists(
    dissolved_fc
):

    arcpy.management.Delete(
        dissolved_fc
    )


arcpy.management.Dissolve(
    merged_fc,
    dissolved_fc
)


# ============================================================
# CREATE OUTPUT GEOPACKAGE
# ============================================================

if arcpy.Exists(
    str(OUTPUT_GPKG)
):

    arcpy.management.Delete(
        str(OUTPUT_GPKG)
    )


arcpy.management.CreateSQLiteDatabase(
    str(OUTPUT_GPKG),
    "GEOPACKAGE"
)


# ============================================================
# EXPORT ANALYSIS AREA
# ============================================================

arcpy.conversion.ExportFeatures(
    dissolved_fc,
    OUTPUT_LAYER
)


# ============================================================
# CALCULATE TOTAL AREA
# ============================================================

total_acres = 0.0


with arcpy.da.SearchCursor(
    OUTPUT_LAYER,
    [
        "SHAPE@"
    ]
) as cursor:

    for geometry, in cursor:

        total_acres += geometry.getArea(
            "GEODESIC",
            "ACRES"
        )


# ============================================================
# REPORT
# ============================================================

print()
print(
    "Post-fire analysis area complete."
)

print()

print(
    f"Total area: "
    f"{total_acres:,.1f} acres"
)

print()

print(
    "Output:"
)

print(
    OUTPUT_LAYER
)

print()