"""
ConservationLens Living Plans
Standardize fire perimeter data into the canonical ConservationLens schema.

Version 1.2

Current source adapters
-----------------------
1. MTBS Burned Area Boundaries
2. Optional local fire perimeter source

The local adapter remains inactive when no local dataset is present.

Canonical output
----------------
data/processed/fire_history/
    fire_perimeters_current.gpkg/
        fire_perimeters_current
"""

from pathlib import Path
from datetime import datetime
import csv
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

LOCAL_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "fire_history"
    / "local"
)

LOCAL_MAPPING_FILE = (
    PROJECT_ROOT
    / "config"
    / "local_fire_perimeter_mapping.csv"
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

LOCAL_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_GPKG = (
    PROCESSED_DIR
    / "fire_perimeters_current.gpkg"
)

OUTPUT_LAYER_NAME = "fire_perimeters_current"

OUTPUT_LAYER = (
    str(OUTPUT_GPKG)
    + "\\"
    + OUTPUT_LAYER_NAME
)


# ============================================================
# CANONICAL SCHEMA
# ============================================================

CANONICAL_FIELDS = [

    ("cl_fire_id", "TEXT", 150),

    ("fire_name", "TEXT", 150),

    ("fire_year", "LONG", None),

    ("ignition_date", "DATE", None),

    ("incident_type", "TEXT", 50),

    ("source_id", "TEXT", 50),

    ("source_record_id", "TEXT", 150),

    ("source_name", "TEXT", 150),

    ("source_type", "TEXT", 50),

    ("source_date", "DATE", None),

    ("ingested_date", "DATE", None),

    ("verification_status", "TEXT", 50),

    ("supersedes_id", "TEXT", 150),

    ("is_current", "SHORT", None),

    ("notes", "TEXT", 500),
]


# ============================================================
# HELPERS
# ============================================================

def parse_iso_date(value):

    if not value:
        return None

    if isinstance(value, datetime):
        return value

    for date_format in [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%Y/%m/%d",
    ]:

        try:

            return datetime.strptime(
                str(value),
                date_format
            )

        except ValueError:
            continue

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


def read_local_mapping():

    mapping = {}

    if not LOCAL_MAPPING_FILE.exists():
        return mapping

    with LOCAL_MAPPING_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            canonical_field = (
                row["canonical_field"].strip()
            )

            local_field = (
                row["local_field"].strip()
            )

            if local_field:

                mapping[
                    canonical_field
                ] = local_field

    return mapping


def find_local_dataset():
    """
    Return the first supported local dataset found.

    Supported prototype formats:
    - Shapefile
    - GeoJSON
    - GeoPackage

    We deliberately do not guess among multiple datasets.
    """

    supported_files = []

    for path in LOCAL_DIR.iterdir():

        if path.name.startswith("."):
            continue

        if path.suffix.lower() in {
            ".shp",
            ".geojson",
            ".gpkg",
        }:

            supported_files.append(
                path
            )

    if len(supported_files) == 0:

        return None

    if len(supported_files) > 1:

        raise ValueError(
            "More than one local fire perimeter dataset was found.\n"
            "Keep only one prototype local perimeter source in:\n"
            f"{LOCAL_DIR}"
        )

    return supported_files[0]


# ============================================================
# START
# ============================================================

print()
print(
    "ConservationLens fire perimeter standardization"
)
print(
    "==============================================="
)
print()


if not MTBS_INPUT.exists():

    raise FileNotFoundError(
        f"MTBS source not found:\n{MTBS_INPUT}"
    )


# ============================================================
# TEMPORARY CANONICAL FEATURE CLASS
# ============================================================

TEMP_GDB = (
    PROCESSED_DIR
    / "standardize_temp.gdb"
)

if not arcpy.Exists(
    str(TEMP_GDB)
):

    arcpy.management.CreateFileGDB(
        str(PROCESSED_DIR),
        "standardize_temp.gdb"
    )


canonical_fc = str(
    TEMP_GDB
    / "fire_perimeters_current"
)

if arcpy.Exists(
    canonical_fc
):

    arcpy.management.Delete(
        canonical_fc
    )


source_sr = (
    arcpy.Describe(
        str(MTBS_INPUT)
    ).spatialReference
)


arcpy.management.CreateFeatureclass(
    str(TEMP_GDB),
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


# ============================================================
# ADAPTER 1 — MTBS
# ============================================================

print(
    "Standardizing MTBS records..."
)


mtbs_source_fields = [

    "event_id",
    "incid_name",
    "incid_type",
    "ig_date",
    "burnbndac",
    "map_prog",
    "asmnt_type",
    "SHAPE@",
]


mtbs_count = 0


with arcpy.da.InsertCursor(
    canonical_fc,
    target_fields
) as insert_cursor:

    with arcpy.da.SearchCursor(
        str(MTBS_INPUT),
        mtbs_source_fields
    ) as search_cursor:

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
                "mtbs",
                event_id
            )


            notes = (

                f"Original MTBS burnbndac="
                f"{burn_boundary_acres}; "

                f"map_prog="
                f"{map_program}; "

                f"asmnt_type="
                f"{assessment_type}"
            )


            insert_cursor.insertRow(
                (

                    cl_fire_id,

                    incident_name,

                    fire_year,

                    ignition_date,

                    incident_type,

                    "mtbs",

                    event_id,

                    "MTBS Burned Area Boundaries",

                    "national",

                    None,

                    datetime.now(),

                    "source_authoritative",

                    None,

                    1,

                    notes,

                    geometry,
                )
            )


            mtbs_count += 1


print(
    f"MTBS records standardized: "
    f"{mtbs_count:,}"
)

print()


# ============================================================
# ADAPTER 2 — OPTIONAL LOCAL DATA
# ============================================================

local_dataset = find_local_dataset()


if local_dataset is None:

    print(
        "No local fire perimeter dataset found."
    )

    print(
        "Continuing with national sources only."
    )

    print()

    local_count = 0


else:

    print(
        "Local fire perimeter dataset found:"
    )

    print(
        local_dataset
    )

    print()


    local_mapping = read_local_mapping()


    required_mappings = {
        "fire_year",
        "incident_type",
    }


    missing_mapping = (
        required_mappings
        - set(
            local_mapping.keys()
        )
    )


    if missing_mapping:

        raise ValueError(

            "Local dataset found, but required local-field "
            "mappings are missing:\n"

            + ", ".join(
                sorted(
                    missing_mapping
                )
            )

            + "\n\nUpdate:\n"

            + str(
                LOCAL_MAPPING_FILE
            )
        )


    # --------------------------------------------------------
    # CONVERT GEOJSON IF NECESSARY
    # --------------------------------------------------------

    local_source = str(
        local_dataset
    )


    if (
        local_dataset.suffix.lower()
        == ".geojson"
    ):

        local_temp_fc = str(
            TEMP_GDB
            / "local_fire_source"
        )

        if arcpy.Exists(
            local_temp_fc
        ):

            arcpy.management.Delete(
                local_temp_fc
            )

        arcpy.conversion.JSONToFeatures(
            str(local_dataset),
            local_temp_fc
        )

        local_source = (
            local_temp_fc
        )


    # --------------------------------------------------------
    # REPROJECT LOCAL DATA INTO CANONICAL CRS IF NECESSARY
    # --------------------------------------------------------

    local_sr = (
        arcpy.Describe(
            local_source
        ).spatialReference
    )


    if (
        local_sr.factoryCode
        != source_sr.factoryCode
    ):

        projected_local = str(
            TEMP_GDB
            / "local_fire_projected"
        )

        if arcpy.Exists(
            projected_local
        ):

            arcpy.management.Delete(
                projected_local
            )

        arcpy.management.Project(
            local_source,
            projected_local,
            source_sr
        )

        local_source = (
            projected_local
        )


    # --------------------------------------------------------
    # CHECK LOCAL FIELDS
    # --------------------------------------------------------

    available_local_fields = {

        field.name

        for field in arcpy.ListFields(
            local_source
        )
    }


    for (
        canonical_field,
        local_field
    ) in local_mapping.items():

        if (
            local_field
            not in available_local_fields
        ):

            raise ValueError(

                f"Mapped local field '{local_field}' "
                f"for canonical field '{canonical_field}' "
                "was not found in the local dataset."
            )


    # --------------------------------------------------------
    # BUILD SEARCH FIELD LIST
    # --------------------------------------------------------

    mapped_fields = {

        canonical:
            local

        for (
            canonical,
            local
        ) in local_mapping.items()
    }


    local_search_fields = list(
        dict.fromkeys(
            mapped_fields.values()
        )
    )

    local_search_fields.append(
        "SHAPE@"
    )


    local_count = 0


    with arcpy.da.InsertCursor(
        canonical_fc,
        target_fields
    ) as insert_cursor:

        with arcpy.da.SearchCursor(
            local_source,
            local_search_fields
        ) as search_cursor:

            for row in search_cursor:

                row_values = dict(
                    zip(
                        local_search_fields,
                        row
                    )
                )


                fire_name = (
                    row_values.get(
                        mapped_fields.get(
                            "fire_name"
                        )
                    )
                    if mapped_fields.get(
                        "fire_name"
                    )
                    else None
                )


                raw_fire_year = (
                    row_values.get(
                        mapped_fields[
                            "fire_year"
                        ]
                    )
                )


                try:

                    fire_year = int(
                        raw_fire_year
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    fire_year = None


                ignition_date = None

                if mapped_fields.get(
                    "ignition_date"
                ):

                    ignition_date = parse_iso_date(

                        row_values.get(
                            mapped_fields[
                                "ignition_date"
                            ]
                        )
                    )


                incident_type = (
                    row_values.get(
                        mapped_fields[
                            "incident_type"
                        ]
                    )
                )


                source_record_id = None

                if mapped_fields.get(
                    "source_record_id"
                ):

                    source_record_id = (
                        row_values.get(
                            mapped_fields[
                                "source_record_id"
                            ]
                        )
                    )


                geometry = row_values[
                    "SHAPE@"
                ]


                cl_fire_id = build_cl_fire_id(
                    "local",
                    source_record_id
                )


                insert_cursor.insertRow(
                    (

                        cl_fire_id,

                        fire_name,

                        fire_year,

                        ignition_date,

                        incident_type,

                        "local",

                        source_record_id,

                        local_dataset.stem,

                        "local",

                        None,

                        datetime.now(),

                        "local_verified",

                        None,

                        1,

                        (
                            "Locally supplied fire perimeter; "
                            f"original file={local_dataset.name}"
                        ),

                        geometry,
                    )
                )


                local_count += 1


    print(
        f"Local records standardized: "
        f"{local_count:,}"
    )

    print()


# ============================================================
# CREATE CANONICAL GEOPACKAGE
# ============================================================

print(
    "Writing canonical GeoPackage..."
)


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


arcpy.conversion.ExportFeatures(
    canonical_fc,
    OUTPUT_LAYER
)


# ============================================================
# VALIDATE
# ============================================================

if not arcpy.Exists(
    OUTPUT_LAYER
):

    raise RuntimeError(
        "Canonical output layer was not created."
    )


output_count = int(
    arcpy.management.GetCount(
        OUTPUT_LAYER
    )[0]
)


expected_count = (
    mtbs_count
    + local_count
)


if (
    output_count
    != expected_count
):

    raise ValueError(

        "Canonical output validation failed.\n"

        f"Expected records: "
        f"{expected_count:,}\n"

        f"Written records: "
        f"{output_count:,}"
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
    OUTPUT_LAYER
)

print()

print(
    "Sources ingested:"
)

print(
    f"  MTBS: "
    f"{mtbs_count:,}"
)

print(
    f"  Local: "
    f"{local_count:,}"
)

print()

print(
    f"Total canonical records: "
    f"{output_count:,}"
)