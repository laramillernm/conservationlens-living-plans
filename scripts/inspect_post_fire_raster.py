from pathlib import Path
import arcpy
import numpy as np


PROJECT_ROOT = Path(
    r"C:\Users\Lara\ConservationInsights\conservationlens-living-plans"
)

RASTER_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "post_fire"
    / "nmfap"
    / "NMFAP.gdb"
    / "NMFAP2020_Threat_Postfire_DebrisFlowHazard_Annual"
)

raster_path = str(RASTER_PATH)


print()
print("ConservationLens post-fire threat inspection")
print("============================================")
print()


if not arcpy.Exists(raster_path):
    raise FileNotFoundError(
        f"Raster not found:\n{raster_path}"
    )


desc = arcpy.Describe(raster_path)
sr = desc.spatialReference


print("Raster:")
print(raster_path)
print()

print(f"Spatial reference: {sr.name}")
print(f"EPSG / factory code: {sr.factoryCode}")
print(f"Cell width: {desc.meanCellWidth}")
print(f"Cell height: {desc.meanCellHeight}")

print()

print("Extent:")
print(f"  XMin: {desc.extent.XMin}")
print(f"  YMin: {desc.extent.YMin}")
print(f"  XMax: {desc.extent.XMax}")
print(f"  YMax: {desc.extent.YMax}")

print()
print("Reading raster values...")


array = arcpy.RasterToNumPyArray(
    raster_path,
    nodata_to_value=np.nan
)

values = array[
    np.isfinite(array)
]


if values.size == 0:
    raise RuntimeError(
        "Raster contains no valid numeric cells."
    )


print()
print(f"Valid cells: {values.size:,}")
print(f"Minimum: {np.min(values)}")
print(f"Maximum: {np.max(values)}")
print(f"Mean: {np.mean(values):.4f}")
print(f"Median: {np.median(values):.4f}")

print()


unique_values = np.unique(values)

print(
    f"Unique value count: "
    f"{len(unique_values):,}"
)

print()


if len(unique_values) <= 50:

    print("Unique values:")

    for value in unique_values:
        print(value)

else:

    print(
        "Raster has many unique values."
    )

    print()
    print("Percentiles:")

    for percentile in [
        10,
        25,
        50,
        75,
        90,
        95,
        99,
    ]:

        value = np.percentile(
            values,
            percentile
        )

        print(
            f"  P{percentile}: "
            f"{value:.6f}"
        )


print()
print("Inspection complete.")