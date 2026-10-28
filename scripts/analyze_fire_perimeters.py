"""
ConservationLens Living Plans
Analyze standardized fire perimeter history for El Rito

Version 1.1

Purpose
-------
Analyze the canonical ConservationLens fire perimeter dataset rather
than any one source-specific dataset.

The canonical dataset may eventually include:
- MTBS national fire perimeters
- WFIGS recent fire perimeters
- locally supplied fire perimeters
- corrected or superseding fire perimeters

Analysis logic therefore remains unchanged when sources change.

Canonical input
---------------
data/processed/fire_history/
    fire_perimeters_current.gpkg/
        fire_perimeters_current

Required canonical fields
-------------------------
cl_fire_id
fire_name
fire_year
ignition_date
incident_type
source_id
source_name
source_type
verification_status
is_current
geometry

Comparison periods
------------------
Historical: 2005-2014
Recent:     2015-2024
"""

from pathlib import Path
import csv
import itertools
from collections import defaultdict

import arcpy


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(
    r"C:\Users\Lara\ConservationInsights\conservationlens-living-plans"
)


FIRE_PERIMETERS_GPKG = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "fire_history"
    / "fire_perimeters_current.gpkg"
)


FIRE_PERIMETERS = (
    str(FIRE_PERIMETERS_GPKG)
    + r"\fire_perimeters_current"
)


EL_RITO_BOUNDARY = (
    PROJECT_ROOT
    / "data"
    / "boundaries"
    / "el_rito_boundary.geojson"
)


PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "fire_history"
)


OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "fire_history"
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
# SETTINGS
# ============================================================

DATASET_NAME = (
    "ConservationLens Canonical Fire Perimeters"
)

METHOD_ID = (
    "fire_perimeter_history_v1"
)

SCRIPT_VERSION = "1.1"


HISTORICAL_START = 2005
HISTORICAL_END = 2014

RECENT_START = 2015
RECENT_END = 2024


MIN_OVERLAP_ACRES = 0.01


# ============================================================
# TEMPORARY WORKSPACE
# ============================================================

TEMP_GDB = (
    PROCESSED_DIR
    / "fire_perimeter_analysis_temp.gdb"
)


if not arcpy.Exists(
    str(TEMP_GDB)
):

    arcpy.management.CreateFileGDB(
        str(PROCESSED_DIR),
        "fire_perimeter_analysis_temp.gdb"
    )


boundary_fc = str(
    TEMP_GDB
    / "el_rito_boundary"
)


selected_fc = str(
    TEMP_GDB
    / "fire_perimeters_selected"
)


clipped_fc = str(
    TEMP_GDB
    / "fire_perimeters_clipped"
)


# ============================================================
# HELPERS
# ============================================================

def write_csv(
    path,
    fieldnames,
    rows
):

    with path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


def round_value(
    value,
    digits=2
):

    if value is None:
        return ""

    return round(
        value,
        digits
    )


def percent_change(
    historical,
    recent
):

    if historical in (
        None,
        0
    ):
        return None

    return (
        (
            recent
            - historical
        )
        / historical
        * 100
    )


def geodesic_acres(
    geometry
):

    if geometry is None:
        return 0.0

    try:

        return geometry.getArea(
            "GEODESIC",
            "ACRES"
        )

    except Exception:

        return 0.0


def union_geometries(
    geometries
):

    valid = [

        geometry

        for geometry in geometries

        if geometry is not None
    ]


    if not valid:
        return None


    result = valid[0]


    for geometry in valid[1:]:

        result = result.union(
            geometry
        )


    return result


def polygon_intersection(
    geometries
):

    if not geometries:
        return None


    result = geometries[0]


    for geometry in geometries[1:]:

        result = result.intersect(
            geometry,
            4
        )


        if result is None:
            return None


        if (
            geodesic_acres(
                result
            )
            <= MIN_OVERLAP_ACRES
        ):
            return None


    return result


def repeat_burn_geometry(
    geometries
):

    overlap_geometries = []


    for (
        geometry_a,
        geometry_b
    ) in itertools.combinations(
        geometries,
        2
    ):

        overlap = polygon_intersection(
            [
                geometry_a,
                geometry_b
            ]
        )


        if overlap is None:
            continue


        acres = geodesic_acres(
            overlap
        )


        if (
            acres
            > MIN_OVERLAP_ACRES
        ):

            overlap_geometries.append(
                overlap
            )


    return union_geometries(
        overlap_geometries
    )


def maximum_overlap_count(
    geometries
):

    number_of_fires = len(
        geometries
    )


    if number_of_fires == 0:
        return 0


    if number_of_fires == 1:
        return 1


    for overlap_count in range(
        number_of_fires,
        1,
        -1
    ):

        for combo in itertools.combinations(
            geometries,
            overlap_count
        ):

            intersection = polygon_intersection(
                list(
                    combo
                )
            )


            if intersection is None:
                continue


            acres = geodesic_acres(
                intersection
            )


            if (
                acres
                > MIN_OVERLAP_ACRES
            ):

                return overlap_count


    return 1


def calculate_spatial_metrics(
    period_records
):

    if not period_records:

        return {

            "mapped_fires":
                0,

            "cumulative_acres":
                0.0,

            "unique_acres":
                0.0,

            "repeat_burn_acres":
                0.0,

            "single_burn_acres":
                0.0,

            "maximum_burn_count":
                0,
        }


    geometries = [

        record["geometry"]

        for record in period_records
    ]


    cumulative_acres = sum(

        record[
            "acres_inside_el_rito"
        ]

        for record in period_records
    )


    unique_geometry = union_geometries(
        geometries
    )


    unique_acres = geodesic_acres(
        unique_geometry
    )


    repeat_geometry = repeat_burn_geometry(
        geometries
    )


    repeat_acres = geodesic_acres(
        repeat_geometry
    )


    single_burn_acres = max(
        0.0,
        unique_acres
        - repeat_acres
    )


    maximum_burn_count = (
        maximum_overlap_count(
            geometries
        )
    )


    return {

        "mapped_fires":
            len(
                period_records
            ),

        "cumulative_acres":
            cumulative_acres,

        "unique_acres":
            unique_acres,

        "repeat_burn_acres":
            repeat_acres,

        "single_burn_acres":
            single_burn_acres,

        "maximum_burn_count":
            maximum_burn_count,
    }


def period_stats(
    records,
    watershed_acres,
    start_year,
    end_year
):

    period_records = [

        record

        for record in records

        if (
            start_year
            <= record["fire_year"]
            <= end_year
        )
    ]


    spatial = calculate_spatial_metrics(
        period_records
    )


    spatial.update({

        "start_year":
            start_year,

        "end_year":
            end_year,

        "unique_percent_watershed":
            (
                spatial[
                    "unique_acres"
                ]
                / watershed_acres
                * 100
            )
            if watershed_acres
            else 0.0,

        "repeat_percent_watershed":
            (
                spatial[
                    "repeat_burn_acres"
                ]
                / watershed_acres
                * 100
            )
            if watershed_acres
            else 0.0,
    })


    return spatial


# ============================================================
# START
# ============================================================

print()
print(
    "ConservationLens fire perimeter analysis"
)
print(
    "========================================"
)
print()

print(
    "Canonical fire perimeter dataset:"
)

print(
    FIRE_PERIMETERS
)

print()

print(
    "El Rito boundary:"
)

print(
    EL_RITO_BOUNDARY
)

print()


# ============================================================
# CHECK INPUTS
# ============================================================

if not arcpy.Exists(
    FIRE_PERIMETERS
):

    raise FileNotFoundError(

        "Canonical fire perimeter dataset not found:\n"

        f"{FIRE_PERIMETERS}\n\n"

        "Run standardize_fire_perimeters.py first."
    )


if not EL_RITO_BOUNDARY.exists():

    raise FileNotFoundError(

        "El Rito boundary not found:\n"

        f"{EL_RITO_BOUNDARY}"
    )


# ============================================================
# VALIDATE CANONICAL SCHEMA
# ============================================================

required_fields = {

    "cl_fire_id",

    "fire_name",

    "fire_year",

    "ignition_date",

    "incident_type",

    "source_id",

    "source_name",

    "source_type",

    "verification_status",

    "is_current",
}


available_fields = {

    field.name

    for field in arcpy.ListFields(
        FIRE_PERIMETERS
    )
}


missing_fields = (
    required_fields
    - available_fields
)


if missing_fields:

    raise ValueError(

        "Canonical fire perimeter dataset is missing "
        "required fields:\n"

        + ", ".join(
            sorted(
                missing_fields
            )
        )
    )


print(
    "Canonical schema validated."
)

print()


# ============================================================
# PREPARE EL RITO BOUNDARY
# ============================================================

print(
    "Preparing El Rito boundary..."
)


if arcpy.Exists(
    boundary_fc
):

    arcpy.management.Delete(
        boundary_fc
    )


arcpy.conversion.JSONToFeatures(
    str(
        EL_RITO_BOUNDARY
    ),
    boundary_fc
)


# ============================================================
# WATERSHED AREA
# ============================================================

watershed_acres = 0.0


with arcpy.da.SearchCursor(
    boundary_fc,
    [
        "SHAPE@"
    ]
) as cursor:

    for row in cursor:

        watershed_acres += geodesic_acres(
            row[0]
        )


print(
    f"El Rito watershed acres: "
    f"{watershed_acres:,.1f}"
)

print()


# ============================================================
# SELECT CURRENT WILDFIRE RECORDS
# ============================================================

print(
    "Selecting current wildfire perimeters intersecting El Rito..."
)


fire_layer = (
    "canonical_fire_perimeters_layer"
)


if arcpy.Exists(
    fire_layer
):

    arcpy.management.Delete(
        fire_layer
    )


arcpy.management.MakeFeatureLayer(
    FIRE_PERIMETERS,
    fire_layer
)


# ------------------------------------------------------------
# ONLY CURRENT RECORDS
# ------------------------------------------------------------

arcpy.management.SelectLayerByAttribute(
    fire_layer,
    "NEW_SELECTION",
    "is_current = 1"
)


# ------------------------------------------------------------
# WILDFIRE + WILDLAND FIRE USE
# ------------------------------------------------------------

arcpy.management.SelectLayerByAttribute(
    fire_layer,
    "SUBSET_SELECTION",
    (
        "incident_type IN "
        "('Wildfire', 'Wildland Fire Use')"
    )
)


# ------------------------------------------------------------
# INTERSECT EL RITO
# ------------------------------------------------------------

arcpy.management.SelectLayerByLocation(
    fire_layer,
    "INTERSECT",
    boundary_fc,
    selection_type="SUBSET_SELECTION"
)


selected_count = int(
    arcpy.management.GetCount(
        fire_layer
    )[0]
)


print(
    "Canonical wildfire perimeters intersecting El Rito: "
    f"{selected_count}"
)

print()


if selected_count == 0:

    raise ValueError(
        "No current wildfire perimeters intersect El Rito."
    )


# ============================================================
# SAVE SELECTED RECORDS
# ============================================================

if arcpy.Exists(
    selected_fc
):

    arcpy.management.Delete(
        selected_fc
    )


arcpy.management.CopyFeatures(
    fire_layer,
    selected_fc
)


# ============================================================
# CLIP TO EL RITO
# ============================================================

print(
    "Clipping canonical fire perimeters to El Rito..."
)


if arcpy.Exists(
    clipped_fc
):

    arcpy.management.Delete(
        clipped_fc
    )


arcpy.analysis.Clip(
    selected_fc,
    boundary_fc,
    clipped_fc
)


# ============================================================
# READ CANONICAL FIRE RECORDS
# ============================================================

fields = [

    "cl_fire_id",

    "fire_name",

    "fire_year",

    "ignition_date",

    "incident_type",

    "source_id",

    "source_name",

    "source_type",

    "verification_status",

    "is_current",

    "SHAPE@",
]


records = []


with arcpy.da.SearchCursor(
    clipped_fc,
    fields
) as cursor:

    for row in cursor:

        (
            cl_fire_id,
            fire_name,
            fire_year,
            ignition_date,
            incident_type,
            source_id,
            source_name,
            source_type,
            verification_status,
            is_current,
            geometry,
        ) = row


        if fire_year is None:
            continue


        acres_inside = geodesic_acres(
            geometry
        )


        percent_of_watershed = (
            acres_inside
            / watershed_acres
            * 100
        )


        records.append({

            "cl_fire_id":
                cl_fire_id,

            "fire_name":
                fire_name,

            "fire_year":
                int(
                    fire_year
                ),

            "ignition_date":
                ignition_date,

            "incident_type":
                incident_type,

            "source_id":
                source_id,

            "source_name":
                source_name,

            "source_type":
                source_type,

            "verification_status":
                verification_status,

            "is_current":
                is_current,

            "geometry":
                geometry,

            "acres_inside_el_rito":
                acres_inside,

            "percent_of_watershed":
                percent_of_watershed,
        })


if not records:

    raise ValueError(
        "No valid canonical fire records remained after clipping."
    )


records.sort(
    key=lambda record: (
        record["fire_year"],
        record["fire_name"] or ""
    )
)


MIN_YEAR = min(
    record["fire_year"]
    for record in records
)


MAX_YEAR = max(
    record["fire_year"]
    for record in records
)


print(
    f"Valid canonical fire records: "
    f"{len(records)}"
)

print(
    "Mapped fire period present in El Rito: "
    f"{MIN_YEAR}-{MAX_YEAR}"
)

print()


# ============================================================
# SOURCE SUMMARY
# ============================================================

source_counts = defaultdict(
    int
)


for record in records:

    key = (

        record[
            "source_id"
        ],

        record[
            "source_name"
        ],

        record[
            "source_type"
        ],
    )


    source_counts[
        key
    ] += 1


print(
    "Sources represented:"
)


for (
    source_id,
    source_name,
    source_type
), count in sorted(
    source_counts.items()
):

    print(

        f"  {source_id}: "

        f"{count} fire(s) "

        f"[{source_type}]"
    )


print()


# ============================================================
# DETAIL OUTPUT
# ============================================================

detail_file = (
    OUTPUT_DIR
    / "fire_perimeter_detail.csv"
)


detail_rows = []


for record in records:

    ignition_date = (
        record[
            "ignition_date"
        ]
    )


    if ignition_date:

        ignition_date = (
            ignition_date.strftime(
                "%Y-%m-%d"
            )
        )


    detail_rows.append({

        "cl_fire_id":
            record[
                "cl_fire_id"
            ],

        "fire_name":
            record[
                "fire_name"
            ],

        "fire_year":
            record[
                "fire_year"
            ],

        "ignition_date":
            ignition_date,

        "incident_type":
            record[
                "incident_type"
            ],

        "source_id":
            record[
                "source_id"
            ],

        "source_name":
            record[
                "source_name"
            ],

        "source_type":
            record[
                "source_type"
            ],

        "verification_status":
            record[
                "verification_status"
            ],

        "acres_inside_el_rito":
            round_value(
                record[
                    "acres_inside_el_rito"
                ]
            ),

        "percent_of_watershed":
            round_value(
                record[
                    "percent_of_watershed"
                ],
                2
            ),
    })


write_csv(
    detail_file,
    list(
        detail_rows[
            0
        ].keys()
    ),
    detail_rows
)


# ============================================================
# ANNUAL SUMMARY
# ============================================================

by_year = defaultdict(
    list
)


for record in records:

    by_year[
        record[
            "fire_year"
        ]
    ].append(
        record
    )


annual_rows = []


for year in range(
    MIN_YEAR,
    MAX_YEAR + 1
):

    year_records = (
        by_year.get(
            year,
            []
        )
    )


    metrics = calculate_spatial_metrics(
        year_records
    )


    annual_rows.append({

        "year":
            year,

        "mapped_fires":
            metrics[
                "mapped_fires"
            ],

        "cumulative_mapped_fire_acres":
            round_value(
                metrics[
                    "cumulative_acres"
                ]
            ),

        "unique_burned_acres":
            round_value(
                metrics[
                    "unique_acres"
                ]
            ),

        "repeat_burn_acres":
            round_value(
                metrics[
                    "repeat_burn_acres"
                ]
            ),

        "maximum_burn_count":
            metrics[
                "maximum_burn_count"
            ],
    })


annual_file = (
    OUTPUT_DIR
    / "fire_perimeter_annual.csv"
)


write_csv(
    annual_file,
    list(
        annual_rows[
            0
        ].keys()
    ),
    annual_rows
)


# ============================================================
# DECADE SUMMARY
# ============================================================

by_decade = defaultdict(
    list
)


for record in records:

    decade_start = (
        record[
            "fire_year"
        ]
        // 10
    ) * 10


    decade = (
        f"{decade_start}s"
    )


    by_decade[
        decade
    ].append(
        record
    )


decade_rows = []


for decade in sorted(
    by_decade
):

    metrics = calculate_spatial_metrics(
        by_decade[
            decade
        ]
    )


    decade_rows.append({

        "decade":
            decade,

        "mapped_fires":
            metrics[
                "mapped_fires"
            ],

        "cumulative_mapped_fire_acres":
            round_value(
                metrics[
                    "cumulative_acres"
                ]
            ),

        "unique_burned_acres":
            round_value(
                metrics[
                    "unique_acres"
                ]
            ),

        "repeat_burn_acres":
            round_value(
                metrics[
                    "repeat_burn_acres"
                ]
            ),

        "maximum_burn_count":
            metrics[
                "maximum_burn_count"
            ],
    })


decade_file = (
    OUTPUT_DIR
    / "fire_perimeter_decade.csv"
)


write_csv(
    decade_file,
    list(
        decade_rows[
            0
        ].keys()
    ),
    decade_rows
)


# ============================================================
# FIXED PERIOD COMPARISON
# ============================================================

historical = period_stats(
    records,
    watershed_acres,
    HISTORICAL_START,
    HISTORICAL_END
)


recent = period_stats(
    records,
    watershed_acres,
    RECENT_START,
    RECENT_END
)


# ============================================================
# ALL-YEARS METRICS
# ============================================================

all_years = calculate_spatial_metrics(
    records
)


all_years_unique_pct = (
    all_years[
        "unique_acres"
    ]
    / watershed_acres
    * 100
)


all_years_repeat_pct = (
    all_years[
        "repeat_burn_acres"
    ]
    / watershed_acres
    * 100
)


# ============================================================
# REPEAT-BURN SUMMARY
# ============================================================

repeat_summary_rows = [

    {
        "metric":
            "cumulative_mapped_fire_acres",

        "value":
            round_value(
                all_years[
                    "cumulative_acres"
                ]
            ),

        "unit":
            "acres",
    },

    {
        "metric":
            "unique_acres_burned_at_least_once",

        "value":
            round_value(
                all_years[
                    "unique_acres"
                ]
            ),

        "unit":
            "acres",
    },

    {
        "metric":
            "unique_percent_watershed_burned",

        "value":
            round_value(
                all_years_unique_pct,
                2
            ),

        "unit":
            "percent",
    },

    {
        "metric":
            "repeat_burn_acres_2plus",

        "value":
            round_value(
                all_years[
                    "repeat_burn_acres"
                ]
            ),

        "unit":
            "acres",
    },

    {
        "metric":
            "repeat_burn_percent_watershed",

        "value":
            round_value(
                all_years_repeat_pct,
                2
            ),

        "unit":
            "percent",
    },

    {
        "metric":
            "maximum_mapped_burn_count",

        "value":
            all_years[
                "maximum_burn_count"
            ],

        "unit":
            "mapped fires",
    },
]


repeat_summary_file = (
    OUTPUT_DIR
    / "fire_perimeter_repeat_burn_summary.csv"
)


write_csv(
    repeat_summary_file,
    [
        "metric",
        "value",
        "unit"
    ],
    repeat_summary_rows
)


# ============================================================
# STANDARDIZED METRICS
# ============================================================

metric_definitions = [

    (
        "mapped_large_fire_count",
        "Mapped Large Fire Count",
        "fires / 10-year period",
        historical[
            "mapped_fires"
        ],
        recent[
            "mapped_fires"
        ],
    ),

    (
        "cumulative_mapped_fire_area",
        "Cumulative Mapped Fire Area",
        "acres",
        historical[
            "cumulative_acres"
        ],
        recent[
            "cumulative_acres"
        ],
    ),

    (
        "unique_burned_area",
        "Unique Burned Area",
        "acres",
        historical[
            "unique_acres"
        ],
        recent[
            "unique_acres"
        ],
    ),

    (
        "unique_watershed_area_burned",
        "Unique Watershed Area Burned",
        "percent of watershed",
        historical[
            "unique_percent_watershed"
        ],
        recent[
            "unique_percent_watershed"
        ],
    ),

    (
        "repeat_burn_area",
        "Repeat-Burn Area",
        "acres burned 2+ times",
        historical[
            "repeat_burn_acres"
        ],
        recent[
            "repeat_burn_acres"
        ],
    ),

    (
        "maximum_burn_count",
        "Maximum Mapped Burn Count",
        "mapped fires",
        historical[
            "maximum_burn_count"
        ],
        recent[
            "maximum_burn_count"
        ],
    ),
]


metrics_rows = []


for (
    metric_id,
    metric_name,
    unit,
    historical_value,
    recent_value
) in metric_definitions:

    absolute_change = (
        recent_value
        - historical_value
    )


    pct_change = percent_change(
        historical_value,
        recent_value
    )


    metrics_rows.append({

        "metric_id":
            metric_id,

        "metric_name":
            metric_name,

        "dataset":
            DATASET_NAME,

        "historical_period":
            (
                f"{HISTORICAL_START}-"
                f"{HISTORICAL_END}"
            ),

        "recent_period":
            (
                f"{RECENT_START}-"
                f"{RECENT_END}"
            ),

        "historical_value":
            round_value(
                historical_value
            ),

        "recent_value":
            round_value(
                recent_value
            ),

        "absolute_change":
            round_value(
                absolute_change
            ),

        "percent_change":
            round_value(
                pct_change,
                1
            ),

        "unit":
            unit,

        "method_id":
            METHOD_ID,

        "script_version":
            SCRIPT_VERSION,
    })


metrics_file = (
    OUTPUT_DIR
    / "fire_perimeter_metrics.csv"
)


write_csv(
    metrics_file,
    list(
        metrics_rows[
            0
        ].keys()
    ),
    metrics_rows
)


# ============================================================
# RULE-BASED FINDINGS
# ============================================================

findings = []


def add_finding(
    finding_id,
    indicator_name,
    statement,
    evidence,
    confidence,
    status,
    caveat,
):

    findings.append({

        "finding_id":
            finding_id,

        "indicator_name":
            indicator_name,

        "question":
            "What has changed since the planning baseline?",

        "statement":
            statement,

        "evidence":
            evidence,

        "confidence":
            confidence,

        "status":
            status,

        "caveat":
            caveat,

        "dataset":
            DATASET_NAME,

        "historical_period":
            (
                f"{HISTORICAL_START}-"
                f"{HISTORICAL_END}"
            ),

        "recent_period":
            (
                f"{RECENT_START}-"
                f"{RECENT_END}"
            ),

        "method_id":
            METHOD_ID,

        "script_version":
            SCRIPT_VERSION,
    })


# ------------------------------------------------------------
# LARGE FIRE OCCURRENCE
# ------------------------------------------------------------

historical_fires = (
    historical[
        "mapped_fires"
    ]
)


recent_fires = (
    recent[
        "mapped_fires"
    ]
)


if (
    historical_fires > 0
    and recent_fires
    >= historical_fires * 2
):

    statement = (
        "Mapped large-fire occurrence increased substantially "
        "during the recent comparison period."
    )


elif (
    recent_fires
    > historical_fires
):

    statement = (
        "Mapped large-fire occurrence increased "
        "during the recent comparison period."
    )


elif (
    recent_fires
    < historical_fires
):

    statement = (
        "Mapped large-fire occurrence decreased "
        "during the recent comparison period."
    )


else:

    statement = (
        "Mapped large-fire occurrence was unchanged."
    )


add_finding(

    finding_id=
        "fire_perimeter_frequency_change",

    indicator_name=
        "Mapped Large Fire Occurrence",

    statement=
        statement,

    evidence=(

        f"{historical_fires} mapped fire perimeter(s) "
        f"intersected El Rito during "
        f"{HISTORICAL_START}-{HISTORICAL_END}, "

        f"compared with {recent_fires} during "
        f"{RECENT_START}-{RECENT_END}."
    ),

    confidence=
        "High",

    status=
        "Canonical perimeter evidence",

    caveat=(

        "The result reflects the current ConservationLens "
        "canonical fire perimeter dataset. Coverage depends "
        "on the national and local sources currently incorporated."
    ),
)


# ------------------------------------------------------------
# UNIQUE BURNED AREA
# ------------------------------------------------------------

historical_unique = (
    historical[
        "unique_acres"
    ]
)


recent_unique = (
    recent[
        "unique_acres"
    ]
)


if (
    recent_unique
    > historical_unique
):

    statement = (
        "The unique area of El Rito affected by mapped fire "
        "increased during the recent comparison period."
    )


elif (
    recent_unique
    < historical_unique
):

    statement = (
        "The unique area of El Rito affected by mapped fire "
        "decreased during the recent comparison period."
    )


else:

    statement = (
        "The unique area of El Rito affected by mapped fire "
        "was unchanged."
    )


add_finding(

    finding_id=
        "fire_perimeter_unique_area_change",

    indicator_name=
        "Unique Mapped Burned Area",

    statement=
        statement,

    evidence=(

        f"Unique mapped burned area changed from "
        f"{historical_unique:,.1f} acres "

        f"({historical['unique_percent_watershed']:.2f}% "
        f"of the watershed) during "
        f"{HISTORICAL_START}-{HISTORICAL_END} "

        f"to {recent_unique:,.1f} acres "

        f"({recent['unique_percent_watershed']:.2f}%) during "
        f"{RECENT_START}-{RECENT_END}."
    ),

    confidence=
        "High",

    status=
        "Canonical perimeter evidence",

    caveat=(

        "Unique acreage is derived from the current canonical "
        "perimeter dataset and will change if additional or "
        "corrected local perimeter data are incorporated."
    ),
)


# ------------------------------------------------------------
# REPEAT BURNING
# ------------------------------------------------------------

recent_repeat = (
    recent[
        "repeat_burn_acres"
    ]
)


if (
    recent_repeat
    > MIN_OVERLAP_ACRES
):

    statement = (
        "Repeat burning occurred within El Rito during "
        "the recent comparison period."
    )


else:

    statement = (
        "No meaningful repeat-burn overlap was identified "
        "during the recent comparison period."
    )


add_finding(

    finding_id=
        "fire_perimeter_repeat_burning",

    indicator_name=
        "Repeat Burning",

    statement=
        statement,

    evidence=(

        f"{recent_repeat:,.1f} acres were affected by "
        f"two or more mapped fire perimeters during "
        f"{RECENT_START}-{RECENT_END}. "

        f"The maximum mapped burn count was "
        f"{recent['maximum_burn_count']}."
    ),

    confidence=
        "High",

    status=
        "Spatially derived canonical evidence",

    caveat=(

        "Repeat burning represents overlap among perimeter "
        "records currently included in ConservationLens. "
        "Missing local fires could cause repeat burning "
        "to be underestimated."
    ),
)


# ============================================================
# FINDINGS OUTPUT
# ============================================================

findings_file = (
    OUTPUT_DIR
    / "fire_perimeter_findings.csv"
)


write_csv(
    findings_file,
    list(
        findings[
            0
        ].keys()
    ),
    findings
)


# ============================================================
# SOURCE PROVENANCE OUTPUT
# ============================================================

source_rows = []


for (
    source_id,
    source_name,
    source_type
), count in sorted(
    source_counts.items()
):

    source_rows.append({

        "source_id":
            source_id,

        "source_name":
            source_name,

        "source_type":
            source_type,

        "records_intersecting_el_rito":
            count,
    })


source_summary_file = (
    OUTPUT_DIR
    / "fire_perimeter_source_summary.csv"
)


write_csv(
    source_summary_file,
    [
        "source_id",
        "source_name",
        "source_type",
        "records_intersecting_el_rito",
    ],
    source_rows
)


# ============================================================
# SUMMARY / PROVENANCE
# ============================================================

summary_rows = [

    {
        "metric":
            "dataset",

        "value":
            DATASET_NAME
    },

    {
        "metric":
            "canonical_input",

        "value":
            FIRE_PERIMETERS
    },

    {
        "metric":
            "watershed_acres",

        "value":
            round_value(
                watershed_acres
            )
    },

    {
        "metric":
            "canonical_fire_records_intersecting_el_rito",

        "value":
            len(
                records
            )
    },

    {
        "metric":
            "source_count",

        "value":
            len(
                source_counts
            )
    },

    {
        "metric":
            "first_fire_year_present",

        "value":
            MIN_YEAR
    },

    {
        "metric":
            "last_fire_year_present",

        "value":
            MAX_YEAR
    },

    {
        "metric":
            "historical_comparison_period",

        "value":
            (
                f"{HISTORICAL_START}-"
                f"{HISTORICAL_END}"
            )
    },

    {
        "metric":
            "recent_comparison_period",

        "value":
            (
                f"{RECENT_START}-"
                f"{RECENT_END}"
            )
    },

    {
        "metric":
            "all_years_unique_burned_acres",

        "value":
            round_value(
                all_years[
                    "unique_acres"
                ]
            )
    },

    {
        "metric":
            "all_years_unique_percent_watershed",

        "value":
            round_value(
                all_years_unique_pct,
                2
            )
    },

    {
        "metric":
            "all_years_repeat_burn_acres",

        "value":
            round_value(
                all_years[
                    "repeat_burn_acres"
                ]
            )
    },

    {
        "metric":
            "all_years_maximum_burn_count",

        "value":
            all_years[
                "maximum_burn_count"
            ]
    },

    {
        "metric":
            "method_id",

        "value":
            METHOD_ID
    },

    {
        "metric":
            "script_version",

        "value":
            SCRIPT_VERSION
    },

    {
        "metric":
            "architecture_note",

        "value":(
            "Analysis uses canonical ConservationLens fields "
            "rather than source-specific fields."
        )
    },
]


summary_file = (
    OUTPUT_DIR
    / "fire_perimeter_summary.csv"
)


write_csv(
    summary_file,
    [
        "metric",
        "value"
    ],
    summary_rows
)


# ============================================================
# FINISHED
# ============================================================

print()
print(
    "Fire perimeter analysis complete."
)

print()

print(
    "Historical period:"
)

print(
    f"  {HISTORICAL_START}-{HISTORICAL_END}"
)

print(
    f"  Fires: "
    f"{historical['mapped_fires']}"
)

print(
    f"  Unique acres burned: "
    f"{historical['unique_acres']:,.1f}"
)

print(
    f"  Unique watershed area burned: "
    f"{historical['unique_percent_watershed']:.2f}%"
)

print()

print(
    "Recent period:"
)

print(
    f"  {RECENT_START}-{RECENT_END}"
)

print(
    f"  Fires: "
    f"{recent['mapped_fires']}"
)

print(
    f"  Unique acres burned: "
    f"{recent['unique_acres']:,.1f}"
)

print(
    f"  Unique watershed area burned: "
    f"{recent['unique_percent_watershed']:.2f}%"
)

print(
    f"  Repeat-burn acres: "
    f"{recent['repeat_burn_acres']:,.1f}"
)

print()

print(
    "Sources represented:"
)


for (
    source_id,
    source_name,
    source_type
), count in sorted(
    source_counts.items()
):

    print(

        f"  {source_id}: "

        f"{count} record(s) "

        f"[{source_type}]"
    )


print()

print(
    "Outputs:"
)


for path in [

    detail_file,

    annual_file,

    decade_file,

    repeat_summary_file,

    metrics_file,

    findings_file,

    source_summary_file,

    summary_file,
]:

    print(
        path
    )