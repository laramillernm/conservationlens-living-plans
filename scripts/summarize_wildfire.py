from pathlib import Path
import arcpy


# --------------------------------------------------
# Project root
# --------------------------------------------------

PROJECT_ROOT = Path(
    r"C:\Users\Lara\ConservationInsights\conservationlens-living-plans"
)


# --------------------------------------------------
# Input paths
# --------------------------------------------------

WHP_INPUT = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "wildfire"
    / "wrc"
    / "extracted"
    / "Data"
    / "whp2023_GeoTIF"
    / "whp2023_cls_conus.tif"
)

BOUNDARY = (
    PROJECT_ROOT
    / "data"
    / "boundaries"
    / "el_rito_boundary.geojson"
)


# --------------------------------------------------
# Output paths
# --------------------------------------------------

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "wildfire"
)

WHP_OUTPUT = (
    OUTPUT_DIR
    / "el_rito_whp_usfs.tif"
)


# --------------------------------------------------
# Setup
# --------------------------------------------------

arcpy.env.overwriteOutput = True

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# Check inputs
# --------------------------------------------------

print("Checking input files...")

print(f"WHP input: {WHP_INPUT}")
print(f"Boundary: {BOUNDARY}")

if not WHP_INPUT.exists():
    raise FileNotFoundError(
        f"WHP raster not found:\n{WHP_INPUT}"
    )

if not BOUNDARY.exists():
    raise FileNotFoundError(
        f"Boundary not found:\n{BOUNDARY}"
    )

print("Input files found.")


# --------------------------------------------------
# Convert GeoJSON boundary to temporary feature class
# --------------------------------------------------

scratch_gdb = arcpy.env.scratchGDB

boundary_fc = str(
    Path(scratch_gdb)
    / "el_rito_boundary_usfs"
)

if arcpy.Exists(boundary_fc):
    arcpy.management.Delete(boundary_fc)

print("Converting El Rito boundary...")

arcpy.conversion.JSONToFeatures(
    in_json_file=str(BOUNDARY),
    out_features=boundary_fc
)


# --------------------------------------------------
# Report coordinate systems
# --------------------------------------------------

whp_sr = arcpy.Describe(
    str(WHP_INPUT)
).spatialReference

boundary_sr = arcpy.Describe(
    boundary_fc
).spatialReference

print(
    f"WHP coordinate system: "
    f"{whp_sr.name}"
)

print(
    f"Boundary coordinate system: "
    f"{boundary_sr.name}"
)


# --------------------------------------------------
# Clip classified USFS WHP raster
# --------------------------------------------------

print(
    "Clipping national USFS "
    "WHP classification to El Rito..."
)

arcpy.management.Clip(
    in_raster=str(WHP_INPUT),
    rectangle="#",
    out_raster=str(WHP_OUTPUT),
    in_template_dataset=boundary_fc,
    nodata_value="#",
    clipping_geometry="ClippingGeometry",
    maintain_clipping_extent="NO_MAINTAIN_EXTENT"
)


# --------------------------------------------------
# Confirm output
# --------------------------------------------------

if not WHP_OUTPUT.exists():
    raise RuntimeError(
        "The clipping operation finished "
        "but the output raster was not found."
    )


print("Finished.")
print(
    f"USFS WHP output:\n{WHP_OUTPUT}"
)
