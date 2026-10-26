from pathlib import Path
import arcpy

# --------------------------------------------------
# Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

WHP_FOLDER = Path(
    r"C:\Users\Lara\ConservationInsights\conservationlens-living-plans"
    r"\data\raw\wildfire\wrc\extracted\Data\whp2023_GeoTIF"
)

WHP_INPUT = WHP_FOLDER / "whp2023_cls_conus.tif"

BOUNDARY = (
    PROJECT_ROOT
    / "data"
    / "boundaries"
    / "el_rito_boundary.geojson"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "wildfire"
)

WHP_OUTPUT = OUTPUT_DIR / "el_rito_whp_usfs.tif"


# --------------------------------------------------
# Setup
# --------------------------------------------------

arcpy.env.overwriteOutput = True
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# Check inputs
# --------------------------------------------------

if not WHP_INPUT.exists():
    raise FileNotFoundError(f"Missing WHP raster: {WHP_INPUT}")

if not BOUNDARY.exists():
    raise FileNotFoundError(f"Missing boundary: {BOUNDARY}")


# --------------------------------------------------
# Convert GeoJSON boundary to temporary feature class
# --------------------------------------------------

scratch_gdb = arcpy.env.scratchGDB
boundary_fc = str(Path(scratch_gdb) / "el_rito_boundary_usfs")

if arcpy.Exists(boundary_fc):
    arcpy.management.Delete(boundary_fc)

print("Converting El Rito boundary...")

arcpy.conversion.JSONToFeatures(
    str(BOUNDARY),
    boundary_fc
)


# --------------------------------------------------
# Clip USFS classified WHP raster
# --------------------------------------------------

print("Clipping national USFS WHP classification...")

arcpy.management.Clip(
    in_raster=str(WHP_INPUT),
    rectangle="#",
    out_raster=str(WHP_OUTPUT),
    in_template_dataset=boundary_fc,
    nodata_value="#",
    clipping_geometry="ClippingGeometry",
    maintain_clipping_extent="NO_MAINTAIN_EXTENT"
)


print("Finished.")
print(f"USFS WHP output: {WHP_OUTPUT}")