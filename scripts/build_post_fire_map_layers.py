from pathlib import Path
import csv

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

WBD_GDB = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "hydrology"
    / "wbd"
    / "WBD_13_HU2_GDB"
    / "WBD_13_HU2_GDB.gdb"
)

HUC12_FC = str(
    WBD_GDB
    / "WBDHU12"
)

HYDROLOGIC_CONTEXT_GPKG = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hydrology"
    / "hydrologic_context.gpkg"
)

HYDROLOGIC_CONTEXT_FC = (
    str(HYDROLOGIC_CONTEXT_GPKG)
    + "\\hydrologic_context_huc12"
)

HYDROLOGIC_CONTEXT_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "hydrology"
    / "hydrologic_context_huc12.csv"
)

POST_FIRE_BY_UNIT_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "post_fire"
    / "post_fire_threat_by_unit.csv"
)

POST_FIRE_SUMMARY_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "post_fire"
    / "post_fire_threat_summary.csv"
)

POST_FIRE_RASTER = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "post_fire"
    / "post_fire_threat_statewide_class.tif"
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


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_GPKG = (
    PROCESSED_DIR
    / "post_fire_map_layers.gpkg"
)

PLANNING_OUTPUT = (
    str(OUTPUT_GPKG)
    + "\\planning_area"
)

INTERNAL_OUTPUT = (
    str(OUTPUT_GPKG)
    + "\\internal_huc12"
)

CONTEXT_OUTPUT = (
    str(OUTPUT_GPKG)
    + "\\connected_huc12"
)

TEMP_GDB = (
    PROCESSED_DIR
    / "post_fire_map_temp.gdb"
)


# ============================================================
# READ CONFIG
# ============================================================

with CONFIG_FILE.open(
    "r",
    encoding="utf-8"
) as f:

    config = yaml.safe_load(f)


PLANNING_NAME = (
    config[
        "planning_area"
    ][
        "name"
    ]
)

PLANNING_HUC10 = str(
    config[
        "planning_area"
    ][
        "huc"
    ][
        "id"
    ]
)

PLANNING_HUC_NAME = (
    config[
        "planning_area"
    ][
        "huc"
    ][
        "name"
    ]
)


# ============================================================
# START
# ============================================================

print()
print(
    "ConservationLens post-fire map-layer builder"
)
print(
    "============================================"
)
print()

print(
    f"Planning area: "
    f"{PLANNING_HUC10} — {PLANNING_HUC_NAME}"
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
    HUC12_FC
):

    raise FileNotFoundError(
        "WBD HUC12 dataset not found:\n"
        f"{HUC12_FC}"
    )


if not arcpy.Exists(
    HYDROLOGIC_CONTEXT_FC
):

    raise FileNotFoundError(
        "Hydrologic context layer not found:\n"
        f"{HYDROLOGIC_CONTEXT_FC}"
    )


if not HYDROLOGIC_CONTEXT_CSV.exists():

    raise FileNotFoundError(
        "Hydrologic context CSV not found:\n"
        f"{HYDROLOGIC_CONTEXT_CSV}"
    )


if not POST_FIRE_BY_UNIT_CSV.exists():

    raise FileNotFoundError(
        "Post-fire by-unit CSV not found:\n"
        f"{POST_FIRE_BY_UNIT_CSV}"
    )


if not POST_FIRE_SUMMARY_CSV.exists():

    raise FileNotFoundError(
        "Post-fire planning summary CSV not found:\n"
        f"{POST_FIRE_SUMMARY_CSV}"
    )


if not arcpy.Exists(
    str(POST_FIRE_RASTER)
):

    raise FileNotFoundError(
        "Classified post-fire raster not found:\n"
        f"{POST_FIRE_RASTER}"
    )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def delete_if_exists(path):

    if arcpy.Exists(
        path
    ):

        arcpy.management.Delete(
            path
        )


def add_text_field(
    fc,
    field_name,
    length=255
):

    existing = {
        field.name.lower()
        for field in arcpy.ListFields(
            fc
        )
    }

    if field_name.lower() not in existing:

        arcpy.management.AddField(
            fc,
            field_name,
            "TEXT",
            field_length=length
        )


def add_double_field(
    fc,
    field_name
):

    existing = {
        field.name.lower()
        for field in arcpy.ListFields(
            fc
        )
    }

    if field_name.lower() not in existing:

        arcpy.management.AddField(
            fc,
            field_name,
            "DOUBLE"
        )


def as_float(value):

    if value is None:
        return None

    value = str(
        value
    ).strip()

    if value == "":
        return None

    return float(
        value
    )


# ============================================================
# LOAD HYDROLOGIC RELATIONSHIPS
# ============================================================

hydrologic_relationships = {}


with HYDROLOGIC_CONTEXT_CSV.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    reader = csv.DictReader(
        f
    )

    for row in reader:

        huc12_id = str(
            row.get(
                "huc12",
                ""
            )
        ).strip()

        if not huc12_id:
            continue


        hydrologic_relationships[
            huc12_id
        ] = {
            "relationship":
                str(
                    row.get(
                        "relationship",
                        ""
                    )
                ).strip(),

            "level":
                str(
                    row.get(
                        "level",
                        ""
                    )
                ).strip(),

            "related_huc12":
                str(
                    row.get(
                        "related_huc12",
                        ""
                    )
                ).strip(),

            "related_huc12_name":
                str(
                    row.get(
                        "related_huc12_name",
                        ""
                    )
                ).strip(),
        }


# ============================================================
# LOAD POST-FIRE UNIT STATISTICS
# ============================================================

unit_stats = {}


with POST_FIRE_BY_UNIT_CSV.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    reader = csv.DictReader(
        f
    )

    for row in reader:

        unit_id = str(
            row.get(
                "unit_id",
                ""
            )
        ).strip()

        if not unit_id:
            continue


        unit_stats[
            unit_id
        ] = {
            "high_pct":
                as_float(
                    row.get(
                        "high_pct"
                    )
                ),

            "highest_pct":
                as_float(
                    row.get(
                        "highest_pct"
                    )
                ),

            "high_highest_pct":
                as_float(
                    row.get(
                        "high_highest_pct"
                    )
                ),

            "high_highest_acres":
                as_float(
                    row.get(
                        "high_highest_acres"
                    )
                ),

            "raw_mean":
                as_float(
                    row.get(
                        "raw_mean"
                    )
                ),

            "raw_p90":
                as_float(
                    row.get(
                        "raw_p90"
                    )
                ),
        }


# ============================================================
# LOAD PLANNING-AREA STATISTICS
# ============================================================

planning_stats = None


with POST_FIRE_SUMMARY_CSV.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    reader = csv.DictReader(
        f
    )

    for row in reader:

        planning_stats = {
            "high_pct":
                as_float(
                    row.get(
                        "high_pct"
                    )
                ),

            "highest_pct":
                as_float(
                    row.get(
                        "highest_pct"
                    )
                ),

            "high_highest_pct":
                as_float(
                    row.get(
                        "high_highest_pct"
                    )
                ),

            "high_highest_acres":
                as_float(
                    row.get(
                        "high_highest_acres"
                    )
                ),

            "raw_mean":
                as_float(
                    row.get(
                        "raw_mean"
                    )
                ),

            "raw_p90":
                as_float(
                    row.get(
                        "raw_p90"
                    )
                ),
        }

        break


if planning_stats is None:

    raise RuntimeError(
        "Could not read planning-area post-fire summary."
    )


# ============================================================
# IDENTIFY INTERNAL HOTSPOT
# ============================================================

internal_stats = {
    unit_id:
        stats
    for (
        unit_id,
        stats
    ) in unit_stats.items()
    if unit_id.startswith(
        PLANNING_HUC10
    )
}


if internal_stats:

    HOTSPOT_HUC12 = max(
        internal_stats,
        key=lambda unit_id:
            internal_stats[
                unit_id
            ][
                "high_highest_pct"
            ]
    )

else:

    HOTSPOT_HUC12 = None


# ============================================================
# CREATE TEMP GDB
# ============================================================

if not arcpy.Exists(
    str(TEMP_GDB)
):

    arcpy.management.CreateFileGDB(
        str(PROCESSED_DIR),
        TEMP_GDB.name
    )


# ============================================================
# RECREATE OUTPUT GEOPACKAGE
# ============================================================

delete_if_exists(
    str(OUTPUT_GPKG)
)


arcpy.management.CreateSQLiteDatabase(
    str(OUTPUT_GPKG),
    "GEOPACKAGE"
)


# ============================================================
# BUILD PLANNING AREA LAYER
# ============================================================

print(
    "1. Building planning-area map layer..."
)


planning_temp = str(
    TEMP_GDB
    / "planning_area"
)


delete_if_exists(
    planning_temp
)


arcpy.conversion.JSONToFeatures(
    str(
        PLANNING_BOUNDARY
    ),
    planning_temp
)


arcpy.conversion.ExportFeatures(
    planning_temp,
    PLANNING_OUTPUT
)


add_text_field(
    PLANNING_OUTPUT,
    "map_role",
    50
)

add_text_field(
    PLANNING_OUTPUT,
    "unit_id",
    20
)

add_text_field(
    PLANNING_OUTPUT,
    "unit_name",
    100
)

add_text_field(
    PLANNING_OUTPUT,
    "relationship",
    50
)

add_text_field(
    PLANNING_OUTPUT,
    "map_label",
    255
)

add_double_field(
    PLANNING_OUTPUT,
    "high_pct"
)

add_double_field(
    PLANNING_OUTPUT,
    "highest_pct"
)

add_double_field(
    PLANNING_OUTPUT,
    "high_highest_pct"
)

add_double_field(
    PLANNING_OUTPUT,
    "high_highest_acres"
)


with arcpy.da.UpdateCursor(
    PLANNING_OUTPUT,
    [
        "map_role",
        "unit_id",
        "unit_name",
        "relationship",
        "map_label",
        "high_pct",
        "highest_pct",
        "high_highest_pct",
        "high_highest_acres",
    ]
) as cursor:

    for row in cursor:

        row[0] = (
            "planning_area"
        )

        row[1] = (
            PLANNING_HUC10
        )

        row[2] = (
            PLANNING_HUC_NAME
        )

        row[3] = (
            "planning"
        )

        row[4] = (
            f"{PLANNING_HUC_NAME}\n"
            f"{planning_stats['high_highest_pct']:.1f}% "
            f"High + Highest"
        )

        row[5] = (
            planning_stats[
                "high_pct"
            ]
        )

        row[6] = (
            planning_stats[
                "highest_pct"
            ]
        )

        row[7] = (
            planning_stats[
                "high_highest_pct"
            ]
        )

        row[8] = (
            planning_stats[
                "high_highest_acres"
            ]
        )

        cursor.updateRow(
            row
        )


# ============================================================
# BUILD INTERNAL HUC12 LAYER
# ============================================================

print(
    "2. Building internal HUC12 map layer..."
)


internal_temp = str(
    TEMP_GDB
    / "internal_huc12"
)


delete_if_exists(
    internal_temp
)


where_clause = (
    f"HUC12 LIKE "
    f"'{PLANNING_HUC10}%'"
)


arcpy.analysis.Select(
    HUC12_FC,
    internal_temp,
    where_clause
)


arcpy.conversion.ExportFeatures(
    internal_temp,
    INTERNAL_OUTPUT
)


add_text_field(
    INTERNAL_OUTPUT,
    "map_role",
    50
)

add_text_field(
    INTERNAL_OUTPUT,
    "relationship",
    50
)

add_text_field(
    INTERNAL_OUTPUT,
    "threat_label",
    50
)

add_text_field(
    INTERNAL_OUTPUT,
    "map_label",
    255
)

add_double_field(
    INTERNAL_OUTPUT,
    "high_pct"
)

add_double_field(
    INTERNAL_OUTPUT,
    "highest_pct"
)

add_double_field(
    INTERNAL_OUTPUT,
    "high_highest_pct"
)

add_double_field(
    INTERNAL_OUTPUT,
    "high_highest_acres"
)


internal_fields = {
    field.name.lower():
        field.name
    for field in arcpy.ListFields(
        INTERNAL_OUTPUT
    )
}

INTERNAL_HUC_FIELD = (
    internal_fields[
        "huc12"
    ]
)

INTERNAL_NAME_FIELD = (
    internal_fields[
        "name"
    ]
)


with arcpy.da.UpdateCursor(
    INTERNAL_OUTPUT,
    [
        INTERNAL_HUC_FIELD,
        INTERNAL_NAME_FIELD,
        "map_role",
        "relationship",
        "threat_label",
        "map_label",
        "high_pct",
        "highest_pct",
        "high_highest_pct",
        "high_highest_acres",
    ]
) as cursor:

    for row in cursor:

        huc12_id = str(
            row[0]
        )

        huc12_name = str(
            row[1]
        )

        stats = unit_stats.get(
            huc12_id
        )


        if stats is None:

            continue


        if (
            HOTSPOT_HUC12
            and huc12_id
            == HOTSPOT_HUC12
        ):

            map_role = (
                "planning_hotspot"
            )

            threat_label = (
                "Highest internal concentration"
            )

        else:

            map_role = (
                "planning_huc12"
            )

            threat_label = (
                "Internal planning watershed"
            )


        row[2] = (
            map_role
        )

        row[3] = (
            "inside_planning_area"
        )

        row[4] = (
            threat_label
        )

        row[5] = (
            f"{huc12_name}\n"
            f"{stats['high_highest_pct']:.1f}% "
            f"High + Highest"
        )

        row[6] = (
            stats[
                "high_pct"
            ]
        )

        row[7] = (
            stats[
                "highest_pct"
            ]
        )

        row[8] = (
            stats[
                "high_highest_pct"
            ]
        )

        row[9] = (
            stats[
                "high_highest_acres"
            ]
        )


        cursor.updateRow(
            row
        )


# ============================================================
# BUILD CONNECTED HUC12 LAYER
# ============================================================

print(
    "3. Building connected HUC12 map layer..."
)


arcpy.conversion.ExportFeatures(
    HYDROLOGIC_CONTEXT_FC,
    CONTEXT_OUTPUT
)


add_text_field(
    CONTEXT_OUTPUT,
    "map_role",
    50
)

add_text_field(
    CONTEXT_OUTPUT,
    "relationship",
    50
)

add_text_field(
    CONTEXT_OUTPUT,
    "map_label",
    255
)

add_text_field(
    CONTEXT_OUTPUT,
    "related_id",
    20
)

add_text_field(
    CONTEXT_OUTPUT,
    "related_name",
    100
)

add_double_field(
    CONTEXT_OUTPUT,
    "high_pct"
)

add_double_field(
    CONTEXT_OUTPUT,
    "highest_pct"
)

add_double_field(
    CONTEXT_OUTPUT,
    "high_highest_pct"
)

add_double_field(
    CONTEXT_OUTPUT,
    "high_highest_acres"
)


context_fields = {
    field.name.lower():
        field.name
    for field in arcpy.ListFields(
        CONTEXT_OUTPUT
    )
}

CONTEXT_HUC_FIELD = (
    context_fields[
        "huc12"
    ]
)

CONTEXT_NAME_FIELD = (
    context_fields[
        "name"
    ]
)


with arcpy.da.UpdateCursor(
    CONTEXT_OUTPUT,
    [
        CONTEXT_HUC_FIELD,
        CONTEXT_NAME_FIELD,
        "map_role",
        "relationship",
        "map_label",
        "related_id",
        "related_name",
        "high_pct",
        "highest_pct",
        "high_highest_pct",
        "high_highest_acres",
    ]
) as cursor:

    for row in cursor:

        huc12_id = str(
            row[0]
        )

        huc12_name = str(
            row[1]
        )


        relationship_info = (
            hydrologic_relationships.get(
                huc12_id,
                {}
            )
        )


        relationship = (
            relationship_info.get(
                "relationship",
                "hydrologic_context"
            )
        )


        stats = unit_stats.get(
            huc12_id
        )


        if (
            "upstream"
            in relationship.lower()
        ):

            map_role = (
                "connected_upstream"
            )

            relationship_label = (
                "Immediate upstream"
            )

        elif (
            "downstream"
            in relationship.lower()
        ):

            map_role = (
                "connected_downstream"
            )

            relationship_label = (
                "Immediate downstream"
            )

        else:

            map_role = (
                "connected_context"
            )

            relationship_label = (
                "Hydrologic context"
            )


        row[2] = (
            map_role
        )

        row[3] = (
            relationship
        )


        if stats:

            row[4] = (
                f"{huc12_name}\n"
                f"{relationship_label}\n"
                f"{stats['high_highest_pct']:.1f}% "
                f"High + Highest"
            )

            row[7] = (
                stats[
                    "high_pct"
                ]
            )

            row[8] = (
                stats[
                    "highest_pct"
                ]
            )

            row[9] = (
                stats[
                    "high_highest_pct"
                ]
            )

            row[10] = (
                stats[
                    "high_highest_acres"
                ]
            )

        else:

            row[4] = (
                f"{huc12_name}\n"
                f"{relationship_label}"
            )


        row[5] = (
            relationship_info.get(
                "related_huc12",
                ""
            )
        )

        row[6] = (
            relationship_info.get(
                "related_huc12_name",
                ""
            )
        )


        cursor.updateRow(
            row
        )


# ============================================================
# REPORT
# ============================================================

print()
print(
    "Post-fire map layers complete"
)
print(
    "============================="
)

print()

print(
    "Map-ready raster:"
)

print(
    POST_FIRE_RASTER
)

print()

print(
    "Map-ready vector layers:"
)

print(
    PLANNING_OUTPUT
)

print(
    INTERNAL_OUTPUT
)

print(
    CONTEXT_OUTPUT
)

print()


if HOTSPOT_HUC12:

    hotspot_stats = (
        unit_stats[
            HOTSPOT_HUC12
        ]
    )

    print(
        "Internal hotspot:"
    )

    print(
        f"  {HOTSPOT_HUC12}"
    )

    print(
        f"  High + Highest: "
        f"{hotspot_stats['high_highest_pct']:.1f}%"
    )

    print()


downstream_ids = [
    huc12_id
    for (
        huc12_id,
        info
    ) in hydrologic_relationships.items()
    if "downstream"
    in info[
        "relationship"
    ].lower()
]


if downstream_ids:

    print(
        "Downstream map context:"
    )

    for huc12_id in downstream_ids:

        print(
            f"  {huc12_id}"
        )

    print()


print(
    "GeoPackage:"
)

print(
    OUTPUT_GPKG
)

print()