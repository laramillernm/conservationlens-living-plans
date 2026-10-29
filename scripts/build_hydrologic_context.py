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

WBD_GDB = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "hydrology"
    / "wbd"
    / "WBD_13_HU2_GDB"
    / "WBD_13_HU2_GDB.gdb"
)

HUC12 = str(
    WBD_GDB / "WBDHU12"
)

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hydrology"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "hydrology"
)

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# READ CONFIGURATION
# ============================================================

if not CONFIG_FILE.exists():
    raise FileNotFoundError(
        f"Configuration file not found:\n{CONFIG_FILE}"
    )


with CONFIG_FILE.open(
    "r",
    encoding="utf-8"
) as f:

    config = yaml.safe_load(f)


planning_area = config[
    "planning_area"
]

planning_huc = planning_area[
    "huc"
]

hydrologic_config = (
    config[
        "analysis_areas"
    ][
        "hydrologic_context"
    ]
)


PLANNING_HUC_UNIT = (
    planning_huc[
        "unit"
    ].lower()
)

PLANNING_HUC_ID = str(
    planning_huc[
        "id"
    ]
)

PLANNING_HUC_NAME = (
    planning_huc[
        "name"
    ]
)


PARENT_HUC_UNIT = (
    planning_huc[
        "parent"
    ][
        "unit"
    ].lower()
)

PARENT_HUC_ID = str(
    planning_huc[
        "parent"
    ][
        "id"
    ]
)

PARENT_HUC_NAME = (
    planning_huc[
        "parent"
    ][
        "name"
    ]
)


UPSTREAM_LEVELS = int(
    hydrologic_config.get(
        "upstream_levels",
        1
    )
)

DOWNSTREAM_LEVELS = int(
    hydrologic_config.get(
        "downstream_levels",
        1
    )
)

INCLUDE_RELATIONSHIPS = (
    hydrologic_config.get(
        "include",
        []
    )
)


# ============================================================
# CURRENT VERSION LIMIT
# ============================================================

if PLANNING_HUC_UNIT != "huc10":

    raise NotImplementedError(
        "This prototype version currently supports "
        "HUC10 planning areas only.\n"
        f"Configured planning unit: {PLANNING_HUC_UNIT}"
    )


if PARENT_HUC_UNIT != "huc8":

    raise NotImplementedError(
        "This prototype version currently expects "
        "a HUC8 parent for a HUC10 planning area.\n"
        f"Configured parent unit: {PARENT_HUC_UNIT}"
    )


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_GPKG = (
    PROCESSED_DIR
    / "hydrologic_context.gpkg"
)

UPSTREAM_LAYER = (
    str(OUTPUT_GPKG)
    + "\\immediate_upstream_huc12"
)

DOWNSTREAM_LAYER = (
    str(OUTPUT_GPKG)
    + "\\immediate_downstream_huc12"
)

CONTEXT_LAYER = (
    str(OUTPUT_GPKG)
    + "\\hydrologic_context_huc12"
)

DETAIL_CSV = (
    OUTPUT_DIR
    / "hydrologic_context_huc12.csv"
)

SUMMARY_CSV = (
    OUTPUT_DIR
    / "hydrologic_context_summary.csv"
)


# ============================================================
# START
# ============================================================

print()
print(
    "ConservationLens hydrologic context builder"
)
print(
    "=========================================="
)
print()

print(
    "Configuration loaded from:"
)

print(
    CONFIG_FILE
)

print()

print(
    f"Planning {PLANNING_HUC_UNIT.upper()}: "
    f"{PLANNING_HUC_ID} — "
    f"{PLANNING_HUC_NAME}"
)

print(
    f"Parent {PARENT_HUC_UNIT.upper()}: "
    f"{PARENT_HUC_ID} — "
    f"{PARENT_HUC_NAME}"
)

print(
    f"Upstream levels: "
    f"{UPSTREAM_LEVELS}"
)

print(
    f"Downstream levels: "
    f"{DOWNSTREAM_LEVELS}"
)

print()


# ============================================================
# VALIDATE INPUT
# ============================================================

if not arcpy.Exists(
    HUC12
):

    raise FileNotFoundError(
        f"HUC12 feature class not found:\n{HUC12}"
    )


field_lookup = {

    field.name.upper():
        field.name

    for field in arcpy.ListFields(
        HUC12
    )
}


for required in [
    "HUC12",
    "NAME",
    "TOHUC",
]:

    if required not in field_lookup:

        raise ValueError(
            f"Required field not found: "
            f"{required}"
        )


FIELD_HUC12 = (
    field_lookup[
        "HUC12"
    ]
)

FIELD_NAME = (
    field_lookup[
        "NAME"
    ]
)

FIELD_TOHUC = (
    field_lookup[
        "TOHUC"
    ]
)


# ============================================================
# STEP 1
# READ ALL HUC12 RECORDS WITHIN PARENT HUC8
# ============================================================

huc12_records = {}


with arcpy.da.SearchCursor(
    HUC12,
    [
        FIELD_HUC12,
        FIELD_NAME,
        FIELD_TOHUC,
        "SHAPE@",
    ]
) as cursor:

    for (
        huc12_code,
        name,
        tohuc,
        geometry
    ) in cursor:

        huc12_code = str(
            huc12_code
        )

        if not huc12_code.startswith(
            PARENT_HUC_ID
        ):
            continue

        huc12_records[
            huc12_code
        ] = {

            "name":
                name,

            "tohuc":
                (
                    str(tohuc)
                    if tohuc
                    else ""
                ),

            "geometry":
                geometry,
        }


print(
    f"HUC12s available within parent "
    f"HUC8: {len(huc12_records)}"
)

print()


# ============================================================
# STEP 2
# FIND HUC12S INSIDE PLANNING HUC10
# ============================================================

planning_huc12s = {

    code:
        info

    for (
        code,
        info
    ) in huc12_records.items()

    if code.startswith(
        PLANNING_HUC_ID
    )
}


if not planning_huc12s:

    raise RuntimeError(
        "No HUC12s were found inside "
        f"{PLANNING_HUC_ID}."
    )


print(
    f"HUC12s inside planning HUC10: "
    f"{len(planning_huc12s)}"
)

print()


# ============================================================
# STEP 3
# FIND IMMEDIATE EXTERNAL UPSTREAM HUC12S
# ============================================================

upstream_context = []


if (
    "immediate_upstream_huc12"
    in INCLUDE_RELATIONSHIPS
):

    for (
        code,
        info
    ) in huc12_records.items():

        # exclude HUC12s already inside planning HUC10
        if code.startswith(
            PLANNING_HUC_ID
        ):
            continue


        # candidate drains directly into a planning HUC12
        if (
            info["tohuc"]
            in planning_huc12s
        ):

            receiving_code = (
                info["tohuc"]
            )

            upstream_context.append(
                {
                    "relationship":
                        "immediate_upstream",

                    "level":
                        1,

                    "huc12":
                        code,

                    "name":
                        info["name"],

                    "tohuc":
                        receiving_code,

                    "related_huc12":
                        receiving_code,

                    "related_huc12_name":
                        planning_huc12s[
                            receiving_code
                        ][
                            "name"
                        ],

                    "geometry":
                        info[
                            "geometry"
                        ],
                }
            )


# ============================================================
# OPTIONAL RECURSIVE UPSTREAM LEVELS
# ============================================================

if (
    UPSTREAM_LEVELS > 1
    and upstream_context
):

    selected_upstream_codes = {
        item["huc12"]
        for item in upstream_context
    }

    previous_level_codes = set(
        selected_upstream_codes
    )


    for level in range(
        2,
        UPSTREAM_LEVELS + 1
    ):

        new_level = []


        for (
            code,
            info
        ) in huc12_records.items():

            if code.startswith(
                PLANNING_HUC_ID
            ):
                continue


            if code in selected_upstream_codes:
                continue


            if (
                info["tohuc"]
                in previous_level_codes
            ):

                receiving_code = (
                    info["tohuc"]
                )

                receiving_name = (
                    huc12_records[
                        receiving_code
                    ][
                        "name"
                    ]
                )

                new_level.append(
                    {
                        "relationship":
                            "upstream",

                        "level":
                            level,

                        "huc12":
                            code,

                        "name":
                            info[
                                "name"
                            ],

                        "tohuc":
                            receiving_code,

                        "related_huc12":
                            receiving_code,

                        "related_huc12_name":
                            receiving_name,

                        "geometry":
                            info[
                                "geometry"
                            ],
                    }
                )


        if not new_level:
            break


        upstream_context.extend(
            new_level
        )


        previous_level_codes = {
            item["huc12"]
            for item in new_level
        }


        selected_upstream_codes.update(
            previous_level_codes
        )


# ============================================================
# STEP 4
# FIND IMMEDIATE DOWNSTREAM HUC12
# ============================================================

downstream_context = []


if (
    "immediate_downstream_huc12"
    in INCLUDE_RELATIONSHIPS
):

    for (
        planning_code,
        info
    ) in planning_huc12s.items():

        tohuc = (
            info["tohuc"]
        )


        if not tohuc:
            continue


        # If ToHUC points outside planning HUC10,
        # this is an outlet HUC12.
        if not tohuc.startswith(
            PLANNING_HUC_ID
        ):

            downstream_info = (
                huc12_records.get(
                    tohuc
                )
            )


            if downstream_info:

                downstream_context.append(
                    {
                        "relationship":
                            "immediate_downstream",

                        "level":
                            1,

                        "huc12":
                            tohuc,

                        "name":
                            downstream_info[
                                "name"
                            ],

                        "tohuc":
                            downstream_info[
                                "tohuc"
                            ],

                        "related_huc12":
                            planning_code,

                        "related_huc12_name":
                            info[
                                "name"
                            ],

                        "geometry":
                            downstream_info[
                                "geometry"
                            ],
                    }
                )


# ============================================================
# REMOVE DUPLICATE DOWNSTREAM RECORDS
# ============================================================

unique_downstream = {}


for item in downstream_context:

    unique_downstream[
        item["huc12"]
    ] = item


downstream_context = list(
    unique_downstream.values()
)


# ============================================================
# OPTIONAL ADDITIONAL DOWNSTREAM LEVELS
# ============================================================

if (
    DOWNSTREAM_LEVELS > 1
    and downstream_context
):

    selected_downstream_codes = {
        item["huc12"]
        for item in downstream_context
    }


    current_code = (
        downstream_context[
            0
        ][
            "huc12"
        ]
    )


    for level in range(
        2,
        DOWNSTREAM_LEVELS + 1
    ):

        current_info = (
            huc12_records.get(
                current_code
            )
        )


        if not current_info:
            break


        next_code = (
            current_info[
                "tohuc"
            ]
        )


        if not next_code:
            break


        if next_code in selected_downstream_codes:
            break


        next_info = (
            huc12_records.get(
                next_code
            )
        )


        if not next_info:
            break


        downstream_context.append(
            {
                "relationship":
                    "downstream",

                "level":
                    level,

                "huc12":
                    next_code,

                "name":
                    next_info[
                        "name"
                    ],

                "tohuc":
                    next_info[
                        "tohuc"
                    ],

                "related_huc12":
                    current_code,

                "related_huc12_name":
                    current_info[
                        "name"
                    ],

                "geometry":
                    next_info[
                        "geometry"
                    ],
            }
        )


        selected_downstream_codes.add(
            next_code
        )

        current_code = next_code


# ============================================================
# REPORT
# ============================================================

print(
    "Upstream hydrologic context:"
)

print()


if not upstream_context:

    print(
        "None found."
    )

else:

    for item in upstream_context:

        print(
            f"Level {item['level']}: "
            f"{item['huc12']} — "
            f"{item['name']}"
        )

        print(
            f"  Drains to: "
            f"{item['related_huc12']} — "
            f"{item['related_huc12_name']}"
        )

        print()


print(
    "Downstream hydrologic context:"
)

print()


if not downstream_context:

    print(
        "None found."
    )

else:

    for item in downstream_context:

        print(
            f"Level {item['level']}: "
            f"{item['huc12']} — "
            f"{item['name']}"
        )

        print(
            f"  Receives from: "
            f"{item['related_huc12']} — "
            f"{item['related_huc12_name']}"
        )

        print()


# ============================================================
# STEP 5
# CREATE GEOPACKAGE
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


def export_codes(
    codes,
    output_layer
):

    if not codes:
        return


    layer_name = (
        "temporary_huc12_selection"
    )


    if arcpy.Exists(
        layer_name
    ):

        arcpy.management.Delete(
            layer_name
        )


    arcpy.management.MakeFeatureLayer(
        HUC12,
        layer_name
    )


    sql_values = ", ".join(
        f"'{code}'"
        for code in sorted(
            set(codes)
        )
    )


    where_clause = (
        f"{arcpy.AddFieldDelimiters(HUC12, FIELD_HUC12)} "
        f"IN ({sql_values})"
    )


    arcpy.management.SelectLayerByAttribute(
        layer_name,
        "NEW_SELECTION",
        where_clause
    )


    arcpy.conversion.ExportFeatures(
        layer_name,
        output_layer
    )


upstream_codes = [
    item["huc12"]
    for item in upstream_context
]

downstream_codes = [
    item["huc12"]
    for item in downstream_context
]


export_codes(
    upstream_codes,
    UPSTREAM_LAYER
)

export_codes(
    downstream_codes,
    DOWNSTREAM_LAYER
)


combined_codes = sorted(
    set(
        upstream_codes
        + downstream_codes
    )
)


export_codes(
    combined_codes,
    CONTEXT_LAYER
)


# ============================================================
# STEP 6
# WRITE DETAIL CSV
# ============================================================

with DETAIL_CSV.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.writer(f)

    writer.writerow(
        [
            "planning_huc_unit",
            "planning_huc_id",
            "planning_huc_name",
            "parent_huc_unit",
            "parent_huc_id",
            "parent_huc_name",
            "relationship",
            "level",
            "huc12",
            "huc12_name",
            "tohuc",
            "related_huc12",
            "related_huc12_name",
        ]
    )


    for item in (
        upstream_context
        + downstream_context
    ):

        writer.writerow(
            [
                PLANNING_HUC_UNIT,
                PLANNING_HUC_ID,
                PLANNING_HUC_NAME,
                PARENT_HUC_UNIT,
                PARENT_HUC_ID,
                PARENT_HUC_NAME,
                item[
                    "relationship"
                ],
                item[
                    "level"
                ],
                item[
                    "huc12"
                ],
                item[
                    "name"
                ],
                item[
                    "tohuc"
                ],
                item[
                    "related_huc12"
                ],
                item[
                    "related_huc12_name"
                ],
            ]
        )


# ============================================================
# STEP 7
# WRITE SUMMARY CSV
# ============================================================

with SUMMARY_CSV.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.writer(f)

    writer.writerow(
        [
            "metric",
            "value",
        ]
    )

    writer.writerow(
        [
            "planning_huc_unit",
            PLANNING_HUC_UNIT,
        ]
    )

    writer.writerow(
        [
            "planning_huc_id",
            PLANNING_HUC_ID,
        ]
    )

    writer.writerow(
        [
            "planning_huc_name",
            PLANNING_HUC_NAME,
        ]
    )

    writer.writerow(
        [
            "parent_huc_unit",
            PARENT_HUC_UNIT,
        ]
    )

    writer.writerow(
        [
            "parent_huc_id",
            PARENT_HUC_ID,
        ]
    )

    writer.writerow(
        [
            "parent_huc_name",
            PARENT_HUC_NAME,
        ]
    )

    writer.writerow(
        [
            "planning_huc12_count",
            len(
                planning_huc12s
            ),
        ]
    )

    writer.writerow(
        [
            "upstream_levels_requested",
            UPSTREAM_LEVELS,
        ]
    )

    writer.writerow(
        [
            "downstream_levels_requested",
            DOWNSTREAM_LEVELS,
        ]
    )

    writer.writerow(
        [
            "upstream_context_count",
            len(
                upstream_context
            ),
        ]
    )

    writer.writerow(
        [
            "downstream_context_count",
            len(
                downstream_context
            ),
        ]
    )

    writer.writerow(
        [
            "combined_context_count",
            len(
                combined_codes
            ),
        ]
    )


# ============================================================
# FINISHED
# ============================================================

print()
print(
    "Hydrologic context build complete."
)

print()

print(
    f"Upstream context count: "
    f"{len(upstream_context)}"
)

print(
    f"Downstream context count: "
    f"{len(downstream_context)}"
)

print(
    f"Combined context count: "
    f"{len(combined_codes)}"
)

print()

print(
    "Outputs:"
)

print(
    OUTPUT_GPKG
)

print(
    DETAIL_CSV
)

print(
    SUMMARY_CSV
)