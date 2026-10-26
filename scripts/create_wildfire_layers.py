from pathlib import Path
import arcpy


# --------------------------------------------------
# Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BP_INPUT = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "wildfire"
    / "wrc"
    / "extracted"
    / "NM"
    / "BP_NM.tif"
)

WHP_INPUT = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "wildfire"
    / "wrc"
    / "extracted"
    / "NM"
    / "WHP_NM.tif"
)

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

BP_OUTPUT = OUTPUT_DIR / "el_rito_bp.tif"
WHP_OUTPUT = OUTPUT_DIR / "el_rito_whp.tif"


# --------------------------------------------------
# Settings
# --------------------------------------------------

arcpy.env.overwriteOutput = True

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# Check that inputs exist
# --------------------------------------------------

for path in [BP_INPUT, WHP_INPUT, BOUNDARY]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input: {path}")


# --------------------------------------------------
# Convert GeoJSON boundary
# --------------------------------------------------

scratch_gdb = arcpy.env.scratchGDB
boundary_fc = str(Path(scratch_gdb) / "el_rito_boundary")

if arcpy.Exists(boundary_fc):
    arcpy.management.Delete(boundary_fc)

print("Converting El Rito boundary...")

arcpy.conversion.JSONToFeatures(
    str(BOUNDARY),
    boundary_fc
)


# --------------------------------------------------
# Clip Burn Probability
# --------------------------------------------------

print("Clipping Burn Probability...")

arcpy.management.Clip(
    in_raster=str(BP_INPUT),
    rectangle="#",
    out_raster=str(BP_OUTPUT),
    in_template_dataset=boundary_fc,
    nodata_value="#",
    clipping_geometry="ClippingGeometry",
    maintain_clipping_extent="NO_MAINTAIN_EXTENT"
)


# --------------------------------------------------
# Clip Wildfire Hazard Potential
# --------------------------------------------------

print("Clipping Wildfire Hazard Potential...")

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
print(f"Burn Probability output: {BP_OUTPUT}")
print(f"WHP output: {WHP_OUTPUT}")