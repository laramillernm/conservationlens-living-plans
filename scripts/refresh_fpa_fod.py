from pathlib import Path
from datetime import datetime
import json
import urllib.parse
import urllib.request

import arcpy


# --------------------------------------------------
# PROJECT SETTINGS
# --------------------------------------------------

PROJECT_ROOT = Path(
    r"C:\Users\Lara\ConservationInsights\conservationlens-living-plans"
)

BOUNDARY = (
    PROJECT_ROOT
    / "data"
    / "boundaries"
    / "el_rito_boundary.geojson"
)

RAW_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "fire_history"
    / "fpa_fod"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "fire_history"
)

RAW_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

arcpy.env.overwriteOutput = True


# --------------------------------------------------
# FOREST SERVICE CURRENT-EDITION SERVICE
# --------------------------------------------------

LAYER_URL = (
    "https://apps.fs.usda.gov/arcx/rest/services/"
    "EDW/EDW_FireOccurrenceCurrentEdition_01/"
    "MapServer/0"
)

QUERY_URL = LAYER_URL + "/query"

MAX_RECORDS = 2000


# --------------------------------------------------
# CHECK BOUNDARY
# --------------------------------------------------

if not BOUNDARY.exists():
    raise FileNotFoundError(
        f"Missing El Rito boundary:\n{BOUNDARY}"
    )


# --------------------------------------------------
# CONVERT EL RITO BOUNDARY
# --------------------------------------------------

scratch_gdb = arcpy.env.scratchGDB

boundary_fc = str(
    Path(scratch_gdb)
    / "el_rito_fpa_boundary"
)

if arcpy.Exists(boundary_fc):
    arcpy.management.Delete(boundary_fc)

print("Converting El Rito boundary...")

arcpy.conversion.JSONToFeatures(
    str(BOUNDARY),
    boundary_fc
)


# --------------------------------------------------
# PROJECT BOUNDARY TO NAD83 / EPSG:4269
#
# FPA FOD service uses EPSG:4269
# --------------------------------------------------

nad83 = arcpy.SpatialReference(4269)

boundary_geom = None

with arcpy.da.SearchCursor(
    boundary_fc,
    ["SHAPE@"]
) as cursor:

    for row in cursor:
        boundary_geom = row[0]
        break


if boundary_geom is None:
    raise RuntimeError(
        "El Rito boundary contains no geometry."
    )


boundary_nad83 = boundary_geom.projectAs(
    nad83
)

extent = boundary_nad83.extent

geometry_envelope = (
    f"{extent.XMin},"
    f"{extent.YMin},"
    f"{extent.XMax},"
    f"{extent.YMax}"
)

print("El Rito query extent:")
print(geometry_envelope)


# --------------------------------------------------
# DOWNLOAD SERVICE METADATA
# --------------------------------------------------

print("Reading current FPA FOD service metadata...")

metadata_url = (
    LAYER_URL
    + "?f=json"
)

with urllib.request.urlopen(
    metadata_url
) as response:

    metadata = json.load(response)


layer_name = metadata.get(
    "name",
    "Unknown"
)

layer_description = metadata.get(
    "description",
    ""
)

print(
    f"Current layer: {layer_name}"
)


# --------------------------------------------------
# PAGE THROUGH SPATIAL QUERY
# --------------------------------------------------

all_features = []

offset = 0

print(
    "Querying FPA FOD fire occurrences "
    "inside the El Rito area..."
)


while True:

    params = {

        "f": "geojson",

        "where": "1=1",

        "geometry": geometry_envelope,

        "geometryType":
            "esriGeometryEnvelope",

        "inSR": "4269",

        "spatialRel":
            "esriSpatialRelIntersects",

        "outFields": (
            "fpa_id,"
            "fire_year,"
            "discovery_date,"
            "discovery_doy,"
            "fire_size,"
            "fire_size_class,"
            "fire_name,"
            "nwcg_cause_classification,"
            "nwcg_general_cause,"
            "latitude,"
            "longitude,"
            "state,"
            "county,"
            "mtbs_id,"
            "mtbs_fire_name"
        ),

        "returnGeometry": "true",

        "outSR": "4269",

        "resultOffset": offset,

        "resultRecordCount": MAX_RECORDS

    }


    query_string = urllib.parse.urlencode(
        params
    )

    request_url = (
        QUERY_URL
        + "?"
        + query_string
    )


    print(
        f"Requesting records "
        f"{offset + 1}–"
        f"{offset + MAX_RECORDS}..."
    )


    with urllib.request.urlopen(
        request_url
    ) as response:

        page = json.load(response)


    if "error" in page:

        raise RuntimeError(
            "FPA FOD service returned an error:\n"
            + json.dumps(
                page["error"],
                indent=2
            )
        )


    features = page.get(
        "features",
        []
    )


    if not features:
        break


    all_features.extend(
        features
    )


    print(
        f"Received {len(features)} records."
    )


    if len(features) < MAX_RECORDS:
        break


    offset += MAX_RECORDS


print("")
print(
    f"Total candidate FPA FOD records "
    f"returned: {len(all_features)}"
)


# --------------------------------------------------
# BUILD ONE GEOJSON FEATURE COLLECTION
# --------------------------------------------------

feature_collection = {

    "type": "FeatureCollection",

    "name": "fpa_fod_el_rito",

    "crs": {
        "type": "name",
        "properties": {
            "name":
                "urn:ogc:def:crs:EPSG::4269"
        }
    },

    "features": all_features
}


# --------------------------------------------------
# CREATE DATED SNAPSHOT
# --------------------------------------------------

snapshot_date = datetime.now().strftime(
    "%Y-%m-%d"
)

SNAPSHOT_DIR = (
    RAW_DIR
    / "snapshots"
    / snapshot_date
)

SNAPSHOT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

snapshot_geojson = (
    SNAPSHOT_DIR
    / "fpa_fod_el_rito.geojson"
)


with open(
    snapshot_geojson,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        feature_collection,
        f
    )


print(
    f"Dated GeoJSON snapshot saved:\n"
    f"{snapshot_geojson}"
)


# --------------------------------------------------
# UPDATE CURRENT GEOJSON COPY
# --------------------------------------------------

current_geojson = (
    RAW_DIR
    / "fpa_fod_el_rito_current.geojson"
)


with open(
    current_geojson,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        feature_collection,
        f
    )


# --------------------------------------------------
# CONVERT TO CURRENT GEOPACKAGE
# --------------------------------------------------

current_gpkg = (
    RAW_DIR
    / "fpa_fod_el_rito_current.gpkg"
)


if not arcpy.Exists(
    str(current_gpkg)
):

    arcpy.management.CreateSQLiteDatabase(
        str(current_gpkg),
        "GEOPACKAGE"
    )


current_layer = (
    str(current_gpkg)
    + r"\fire_occurrences"
)


if arcpy.Exists(
    current_layer
):

    arcpy.management.Delete(
        current_layer
    )


if len(all_features) > 0:

    print(
        "Converting current snapshot "
        "to GeoPackage..."
    )

    temp_fc = str(
        Path(scratch_gdb)
        / "fpa_fod_current"
    )


    if arcpy.Exists(
        temp_fc
    ):

        arcpy.management.Delete(
            temp_fc
        )


    arcpy.conversion.JSONToFeatures(
        str(current_geojson),
        temp_fc
    )


    arcpy.conversion.ExportFeatures(
        temp_fc,
        current_layer
    )


# --------------------------------------------------
# WRITE REFRESH METADATA
# --------------------------------------------------

metadata_file = (
    OUTPUT_DIR
    / "fpa_fod_refresh.txt"
)


with open(
    metadata_file,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "source=USDA Forest Service FPA FOD Current Edition\n"
    )

    f.write(
        f"layer_name={layer_name}\n"
    )

    f.write(
        f"service_url={LAYER_URL}\n"
    )

    f.write(
        f"refresh_time="
        f"{datetime.now().isoformat()}\n"
    )

    f.write(
        f"record_count="
        f"{len(all_features)}\n"
    )

    f.write(
        f"snapshot="
        f"{snapshot_geojson}\n"
    )

    f.write(
        f"current_geojson="
        f"{current_geojson}\n"
    )

    f.write(
        f"current_geopackage="
        f"{current_gpkg}\n"
    )


# --------------------------------------------------
# FINISHED
# --------------------------------------------------

print("")
print("Finished.")
print("")

print(
    f"FPA FOD records in El Rito area: "
    f"{len(all_features)}"
)

print(
    f"\nDated snapshot:\n"
    f"{snapshot_geojson}"
)

print(
    f"\nCurrent GeoJSON:\n"
    f"{current_geojson}"
)

print(
    f"\nCurrent GeoPackage:\n"
    f"{current_gpkg}"
)

print(
    f"\nRefresh metadata:\n"
    f"{metadata_file}"
)
