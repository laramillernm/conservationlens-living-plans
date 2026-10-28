"""
ConservationLens Living Plans
Standardize fire perimeter data into the canonical ConservationLens schema.

Version 1.0

Current source adapter
----------------------
MTBS Burned Area Boundaries

Purpose
-------
Convert source-specific fire perimeter data into a standard schema so
downstream analysis does not depend on MTBS-specific field names.

Future sources can be added as additional adapters without changing
the canonical output schema.

Current canonical output
------------------------
data/processed/fire_history/fire_perimeters_current.gpkg

Important
---------
This script does not yet merge multiple sources or resolve conflicts.
Version 1.0 establishes the canonical schema using MTBS as the first
source adapter.
"""

from pathlib import Path
from datetime import datetime
import uuid

import arcpy


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(
    r"C:\Users\Lara\ConservationInsights\conservationlens-living-plans"
)

MTBS_INPUT = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "fire_history"
    / "mtbs"
    / "extracted"
    / "mtbs_perims_DD.shp"
)

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "fire_history"
)

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_GPKG = (
    PROCESSED_DIR
    / "fire_perimeters_current.gpkg"
)


# ============================================================
# SOURCE SETTINGS
# ============================================================

SOURCE_ID = "mtbs"

SOURCE_NAME = "MTBS Burned Area Boundaries"

SOURCE_TYPE = "national"

VERIFICATION_STATUS = "source_authoritative"

INGESTED_DATE = datetime.now().strftime(
    "%Y-%m-%d"
)


# ============================================================
# CANONICAL FIELD DEFINITIONS
# ============================================================

CANONICAL_FIELDS = [
    (
        "cl_fire_id",
        "TEXT",
        100
    ),
    (
        "fire_name",
        "TEXT",
        150
    ),
    (
        "fire_year",
        "LONG",
        None
    ),
    (
        "ignition_date",
        "DATE",
        None
    ),
    (
        "incident_type",
        "TEXT",
        50
    ),
    (
        "source_id",
        "TEXT",
        50
    ),
    (
        "source_record_id",
        "TEXT",
        150
    ),
    (
        "source_name",
        "TEXT",
        150
    ),
    (
        "source_type",
        "TEXT",
        50
    ),
    (
        "source_date",
        "DATE",
        None
    ),
    (
        "ingested_date",
        "DATE",
        None
    ),
    (
        "verification_status",
        "TEXT",
        50
    ),
    (
        "supersedes_id",
        "TEXT",
        100
    ),
    (
        "is_current",
        "SHORT",
        None
    ),
    (
        "notes",
        "TEXT",
        500
    ),
]


# ============================================================
# HELPERS
# ============================================================

def parse_iso_date(value):

    if not value:
        return None

    try:

        return datetime.strptime(
            value,
            "%Y-%m-%d"
        )

    except ValueError:

        return None


def build_cl_fire_id(
    source_id,
    source_record_id
):

    if source_record_id:

        return (
            f"{source_id}_"
            f"{source_record_id}"
        )

    return (
        f"{source_id}_"
        f"{uuid.uuid4().hex}"
    )


# ============================================================
# CHECK SOURCE
# ============================================================

print()
print(
    "ConservationLens fire perimeter standardization"
)
print(
    "==============================================="
)
print()

print(
    "Source:"
)

print(
    MTBS_INPUT
)

print()


if not MTBS_INPUT.exists():

    raise FileNotFoundError(
        f"MTBS source not found:\n"
        f"{MTBS_INPUT}"
    )


# ============================================================
# REMOVE OLD OUTPUT
# ============================================================

if OUTPUT_GPKG.exists():

    OUTPUT_GPKG.unlink()


# ============================================================
# CREATE EMPTY CANONICAL FEATURE CLASS
# ============================================================

print(
    "Creating canonical fire perimeter dataset..."
)


source_description = arcpy.Describe(
    str(MTBS_INPUT)
)

source_sr = source_description.spatialReference


temp_gdb = (
    PROCESSED_DIR
    / "standardize_temp.gdb"
)


if not arcpy.Exists(
    str(temp_gdb)
):

    arcpy.management.CreateFileGDB(
        str(PROCESSED_DIR),
        "standardize_temp.gdb"
    )


canonical_fc = str(
    temp_gdb
    / "fire_perimeters_current"
)


if arcpy.Exists(
    canonical_fc
):

    arcpy.management.Delete(
        canonical_fc
    )


arcpy.management.CreateFeatureclass(
    str(temp_gdb),
    "fire_perimeters_current",
    "POLYGON",
    spatial_reference=source_sr
)


for (
    field_name,
    field_type,
    field_length
) in CANONICAL_FIELDS:

    if field_length:

        arcpy.management.AddField(
            canonical_fc,
            field_name,
            field_type,
            field_length=field_length
        )

    else:

        arcpy.management.AddField(
            canonical_fc,
            field_name,
            field_type
        )


# ============================================================
# MTBS SOURCE ADAPTER
# ============================================================

print(
    "Standardizing MTBS records..."
)


source_fields = [
    "event_id",
    "incid_name",
    "incid_type",
    "ig_date",
    "burnbndac",
    "map_prog",
    "asmnt_type",
    "SHAPE@",
]


target_fields = [
    "cl_fire_id",
    "fire_name",
    "fire_year",
    "ignition_date",
    "incident_type",
    "source_id",
    "source_record_id",
    "source_name",
    "source_type",
    "source_date",
    "ingested_date",
    "verification_status",
    "supersedes_id",
    "is_current",
    "notes",
    "SHAPE@",
]


record_count = 0


with arcpy.da.SearchCursor(
    str(MTBS_INPUT),
    source_fields
) as search_cursor:

    with arcpy.da.InsertCursor(
        canonical_fc,
        target_fields
    ) as insert_cursor:

        for row in search_cursor:

            (
                event_id,
                incident_name,
                incident_type,
                ignition_date_text,
                burn_boundary_acres,
                map_program,
                assessment_type,
                geometry,
            ) = row


            ignition_date = parse_iso_date(
                ignition_date_text
            )


            fire_year = (
                ignition_date.year
                if ignition_date
                else None
            )


            cl_fire_id = build_cl_fire_id(
                SOURCE_ID,
                event_id
            )


            notes = (
                f"Original MTBS burnbndac="
                f"{burn_boundary_acres}; "
                f"map_prog={map_program}; "
                f"asmnt_type={assessment_type}"
            )


            insert_cursor.insertRow(
                (
                    cl_fire_id,
                    incident_name,
                    fire_year,
                    ignition_date,
                    incident_type,
                    SOURCE_ID,
                    event_id,
                    SOURCE_NAME,
                    SOURCE_TYPE,
                    None,
                    datetime.now(),
                    VERIFICATION_STATUS,
                    None,
                    1,
                    notes,
                    geometry,
                )
            )


            record_count += 1


# ============================================================
# EXPORT TO GEOPACKAGE
# ============================================================

print(
    f"Standardized records: "
    f"{record_count:,}"
)

print()

print(
    "Writing canonical GeoPackage..."
)


arcpy.conversion.ExportFeatures(
    canonical_fc,
    str(OUTPUT_GPKG)
)


# ============================================================
# VALIDATE OUTPUT
# ============================================================

output_count = int(
    arcpy.management.GetCount(
        str(OUTPUT_GPKG)
    )[0]
)


if output_count != record_count:

    raise ValueError(
        "Canonical output record count does not match source "
        "standardization count."
    )


# ============================================================
# FINISHED
# ============================================================

print()
print(
    "Standardization complete."
)

print()

print(
    "Canonical fire perimeter dataset:"
)

print(
    OUTPUT_GPKG
)

print()

print(
    f"Records written: "
    f"{output_count:,}"
)

print()

print(
    "Current source adapters:"
)

print(
    "  MTBS"
)

print()

print(
    "Future local, WFIGS, or corrected perimeter sources "
    "can be mapped into this same canonical schema."
)