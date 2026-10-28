"""
ConservationLens Living Plans
Analyze MTBS fire history for El Rito

Version 3.0

Purpose
-------
Use MTBS mapped fire perimeters to evaluate actual large-fire
disturbance inside the El Rito watershed and corroborate the
Karen Short FPA FOD fire-occurrence analysis.

This version distinguishes:

1. Cumulative mapped fire acres
   Every fire footprint is counted. If land burned twice,
   it contributes acreage twice.

2. Unique burned acres
   Land burned at least once, counted only once.

3. Repeat-burn acres
   Land intersected by two or more mapped fires.

4. Maximum mapped burn count
   Maximum number of mapped fires overlapping any location.

Included incident types
-----------------------
- Wildfire
- Wildland Fire Use

Excluded
--------
- Prescribed Fire
- Other

Comparison periods
------------------
Historical: 2005-2014
Recent:     2015-2024
"""

from pathlib import Path
import csv
import itertools
from collections import defaultdict
from datetime import datetime

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

DATASET_NAME = "MTBS Burned Area Boundaries"

METHOD_ID = "mtbs_fire_history_v3"

SCRIPT_VERSION = "3.0"

HISTORICAL_START = 2005
HISTORICAL_END = 2014

RECENT_START = 2015
RECENT_END = 2024

# Ignore microscopic geometry artifacts below this threshold.
MIN_OVERLAP_ACRES = 0.01


# ============================================================
# TEMPORARY WORKSPACE
# ============================================================

TEMP_GDB = (
    PROCESSED_DIR
    / "mtbs_temp.gdb"
)

if not arcpy.Exists(str(TEMP_GDB)):

    arcpy.management.CreateFileGDB(
        str(PROCESSED_DIR),
        "mtbs_temp.gdb"
    )


boundary_fc = str(
    TEMP_GDB
    / "el_rito_boundary"
)

selected_fc = str(
    TEMP_GDB
    / "mtbs_selected"
)

clipped_fc = str(
    TEMP_GDB
    / "mtbs_clipped"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def write_csv(path, fieldnames, rows):

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
        writer.writerows(rows)


def parse_year(date_text):

    if not date_text:
        return None

    try:

        return datetime.strptime(
            date_text,
            "%Y-%m-%d"
        ).year

    except ValueError:

        return None


def round_value(value, digits=2):

    if value is None:
        return ""

    return round(
        value,
        digits
    )


def percent_change(historical, recent):

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


def geodesic_acres(geometry):

    if geometry is None:
        return 0.0

    try:

        return geometry.getArea(
            "GEODESIC",
            "ACRES"
        )

    except Exception:

        return 0.0


def union_geometries(geometries):
    """
    Union a list of polygon geometries.

    Returns None if the input list is empty.
    """

    valid = [
        geom
        for geom in geometries
        if geom is not None
    ]

    if not valid:
        return None

    result = valid[0]

    for geom in valid[1:]:

        result = result.union(
            geom
        )

    return result


def polygon_intersection(geometries):
    """
    Return the polygon intersection of all supplied geometries.

    ArcPy intersect dimension 4 = polygon.
    """

    if not geometries:
        return None

    result = geometries[0]

    for geom in geometries[1:]:

        result = result.intersect(
            geom,
            4
        )

        if (
            result is None
            or geodesic_acres(result)
            <= MIN_OVERLAP_ACRES
        ):
            return None

    return result


def repeat_burn_geometry(geometries):
    """
    Calculate land covered by at least two fire polygons.

    Every pairwise overlap is calculated, then those overlap
    geometries are unioned so repeat-burn land is counted only once.
    """

    overlap_geometries = []

    for geom_a, geom_b in itertools.combinations(
        geometries,
        2
    ):

        overlap = polygon_intersection(
            [
                geom_a,
                geom_b
            ]
        )

        if overlap is None:
            continue

        acres = geodesic_acres(
            overlap
        )

        if acres > MIN_OVERLAP_ACRES:

            overlap_geometries.append(
                overlap
            )

    return union_geometries(
        overlap_geometries
    )


def maximum_overlap_count(geometries):
    """
    Determine the highest number of fire polygons overlapping
    anywhere in the analysis area.

    Because the El Rito MTBS set is small, an exact combination
    test is appropriate and transparent.
    """

    number_of_fires = len(
        geometries
    )

    if number_of_fires == 0:
        return 0

    if number_of_fires == 1:
        return 1

    # Work downward from all fires toward pairs.
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
                list(combo)
            )

            if intersection is None:
                continue

            acres = geodesic_acres(
                intersection
            )

            if acres > MIN_OVERLAP_ACRES:

                return overlap_count

    return 1


def calculate_spatial_metrics(period_records):
    """
    Calculate cumulative, unique, and repeat-burn acreage
    for a set of fire records.
    """

    if not period_records:

        return {
            "mapped_fires": 0,
            "cumulative_acres": 0.0,
            "unique_acres": 0.0,
            "repeat_burn_acres": 0.0,
            "single_burn_acres": 0.0,
            "maximum_burn_count": 0,
        }


    geometries = [
        record["geometry"]
        for record in period_records
    ]


    cumulative_acres = sum(
        record["acres_inside_el_rito"]
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


    max_burn_count = maximum_overlap_count(
        geometries
    )


    return {

        "mapped_fires":
            len(period_records),

        "cumulative_acres":
            cumulative_acres,

        "unique_acres":
            unique_acres,

        "repeat_burn_acres":
            repeat_acres,

        "single_burn_acres":
            single_burn_acres,

        "maximum_burn_count":
            max_burn_count,
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
                spatial["unique_acres"]
                / watershed_acres
                * 100
            )
            if watershed_acres
            else 0,

        "repeat_percent_watershed":
            (
                spatial["repeat_burn_acres"]
                / watershed_acres
                * 100
            )
            if watershed_acres
            else 0,
    })


    return spatial


# ============================================================
# CHECK INPUTS
# ============================================================

print()
print(
    "ConservationLens MTBS fire-history analysis"
)
print(
    "==========================================="
)
print()

print("MTBS source:")
print(MTBS_INPUT)
print()

print("El Rito boundary:")
print(EL_RITO_BOUNDARY)
print()


if not MTBS_INPUT.exists():

    raise FileNotFoundError(
        f"MTBS shapefile not found:\n"
        f"{MTBS_INPUT}"
    )


if not EL_RITO_BOUNDARY.exists():

    raise FileNotFoundError(
        f"El Rito boundary not found:\n"
        f"{EL_RITO_BOUNDARY}"
    )


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
    str(EL_RITO_BOUNDARY),
    boundary_fc
)


# ============================================================
# WATERSHED AREA
# ============================================================

watershed_acres = 0.0


with arcpy.da.SearchCursor(
    boundary_fc,
    ["SHAPE@"]
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
# SELECT MTBS FIRES
# ============================================================

print(
    "Selecting MTBS perimeters intersecting El Rito..."
)


mtbs_layer = "mtbs_layer"


if arcpy.Exists(
    mtbs_layer
):

    arcpy.management.Delete(
        mtbs_layer
    )


arcpy.management.MakeFeatureLayer(
    str(MTBS_INPUT),
    mtbs_layer
)


arcpy.management.SelectLayerByLocation(
    mtbs_layer,
    "INTERSECT",
    boundary_fc
)


candidate_count = int(
    arcpy.management.GetCount(
        mtbs_layer
    )[0]
)


print(
    f"All MTBS perimeters intersecting El Rito: "
    f"{candidate_count}"
)


# ============================================================
# FILTER INCIDENT TYPE
# ============================================================

incident_clause = (
    "incid_type IN "
    "('Wildfire', 'Wildland Fire Use')"
)


arcpy.management.SelectLayerByAttribute(
    mtbs_layer,
    "SUBSET_SELECTION",
    incident_clause
)


wildfire_count = int(
    arcpy.management.GetCount(
        mtbs_layer
    )[0]
)


print(
    "Wildfire / Wildland Fire Use perimeters: "
    f"{wildfire_count}"
)

print()


if wildfire_count == 0:

    raise ValueError(
        "No wildfire MTBS perimeters intersect El Rito."
    )


if arcpy.Exists(
    selected_fc
):

    arcpy.management.Delete(
        selected_fc
    )


arcpy.management.CopyFeatures(
    mtbs_layer,
    selected_fc
)


# ============================================================
# CLIP TO EL RITO
# ============================================================

print(
    "Clipping MTBS perimeters to El Rito..."
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
# READ / STANDARDIZE FIRE RECORDS
#
# Group by event_id so a fire is not accidentally counted twice
# if a future MTBS source contains multiple features for one event.
# ============================================================

fields = [
    "event_id",
    "incid_name",
    "incid_type",
    "map_prog",
    "asmnt_type",
    "burnbndac",
    "ig_date",
    "SHAPE@",
]


events = {}


with arcpy.da.SearchCursor(
    clipped_fc,
    fields
) as cursor:

    for row in cursor:

        (
            event_id,
            incident_name,
            incident_type,
            map_program,
            assessment_type,
            total_fire_acres,
            ignition_date,
            geometry,
        ) = row


        fire_year = parse_year(
            ignition_date
        )


        if fire_year is None:
            continue


        if event_id not in events:

            events[event_id] = {

                "event_id":
                    event_id,

                "incident_name":
                    incident_name,

                "incident_type":
                    incident_type,

                "ignition_date":
                    ignition_date,

                "fire_year":
                    fire_year,

                "mtbs_total_fire_acres":
                    total_fire_acres,

                "map_program":
                    map_program,

                "assessment_type":
                    assessment_type,

                "geometry":
                    geometry,
            }

        else:

            # Merge multiple pieces belonging to the same MTBS event.
            events[event_id]["geometry"] = (
                events[event_id]["geometry"].union(
                    geometry
                )
            )


records = []


for event in events.values():

    geometry = event[
        "geometry"
    ]

    acres_inside = geodesic_acres(
        geometry
    )

    event[
        "acres_inside_el_rito"
    ] = acres_inside

    event[
        "percent_of_watershed"
    ] = (
        acres_inside
        / watershed_acres
        * 100
    )

    records.append(
        event
    )


if not records:

    raise ValueError(
        "No valid MTBS fire records remained after clipping."
    )


records.sort(
    key=lambda r: (
        r["fire_year"],
        r["incident_name"] or ""
    )
)


MIN_YEAR = min(
    r["fire_year"]
    for r in records
)

MAX_YEAR = max(
    r["fire_year"]
    for r in records
)


print(
    f"Valid unique MTBS fires: "
    f"{len(records)}"
)

print(
    f"Mapped fire period present in El Rito: "
    f"{MIN_YEAR}-{MAX_YEAR}"
)

print()


# ============================================================
# DETAIL OUTPUT
# ============================================================

detail_file = (
    OUTPUT_DIR
    / "mtbs_fire_history_detail.csv"
)


detail_rows = []


for r in records:

    detail_rows.append({

        "event_id":
            r["event_id"],

        "incident_name":
            r["incident_name"],

        "incident_type":
            r["incident_type"],

        "ignition_date":
            r["ignition_date"],

        "fire_year":
            r["fire_year"],

        "mtbs_total_fire_acres":
            round_value(
                r["mtbs_total_fire_acres"]
            ),

        "acres_inside_el_rito":
            round_value(
                r["acres_inside_el_rito"]
            ),

        "percent_of_watershed":
            round_value(
                r["percent_of_watershed"],
                2
            ),

        "map_program":
            r["map_program"],

        "assessment_type":
            r["assessment_type"],
    })


write_csv(
    detail_file,
    list(
        detail_rows[0].keys()
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
        record["fire_year"]
    ].append(
        record
    )


annual_rows = []


for year in range(
    MIN_YEAR,
    MAX_YEAR + 1
):

    year_records = by_year.get(
        year,
        []
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
    / "mtbs_fire_history_annual.csv"
)


write_csv(
    annual_file,
    list(
        annual_rows[0].keys()
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
        record["fire_year"]
        // 10
    ) * 10

    by_decade[
        f"{decade_start}s"
    ].append(
        record
    )


decade_rows = []


for decade in sorted(
    by_decade
):

    decade_records = by_decade[
        decade
    ]

    metrics = calculate_spatial_metrics(
        decade_records
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
    / "mtbs_fire_history_decade.csv"
)


write_csv(
    decade_file,
    list(
        decade_rows[0].keys()
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
# ALL-YEARS FOOTPRINT / REPEAT BURN
# ============================================================

all_years = calculate_spatial_metrics(
    records
)


all_years_unique_pct = (
    all_years["unique_acres"]
    / watershed_acres
    * 100
)

all_years_repeat_pct = (
    all_years["repeat_burn_acres"]
    / watershed_acres
    * 100
)


# ============================================================
# FIRE FOOTPRINT SUMMARY
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
    / "mtbs_repeat_burn_summary.csv"
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
        historical["mapped_fires"],
        recent["mapped_fires"],
    ),

    (
        "cumulative_mapped_fire_area",
        "Cumulative Mapped Fire Area",
        "acres",
        historical["cumulative_acres"],
        recent["cumulative_acres"],
    ),

    (
        "unique_burned_area",
        "Unique Burned Area",
        "acres",
        historical["unique_acres"],
        recent["unique_acres"],
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
    / "mtbs_fire_regime_metrics.csv"
)


write_csv(
    metrics_file,
    list(
        metrics_rows[0].keys()
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
    corroboration,
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

        "corroboration":
            corroboration,

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
# MAPPED LARGE-FIRE OCCURRENCE
# ------------------------------------------------------------

historical_fires = historical[
    "mapped_fires"
]

recent_fires = recent[
    "mapped_fires"
]


if (
    historical_fires > 0
    and recent_fires
    >= historical_fires * 2
):

    fire_statement = (
        "MTBS-mapped large-fire occurrence increased "
        "substantially during the recent comparison period."
    )

elif recent_fires > historical_fires:

    fire_statement = (
        "MTBS-mapped large-fire occurrence increased "
        "during the recent comparison period."
    )

elif recent_fires < historical_fires:

    fire_statement = (
        "MTBS-mapped large-fire occurrence decreased "
        "during the recent comparison period."
    )

else:

    fire_statement = (
        "MTBS-mapped large-fire occurrence was unchanged."
    )


add_finding(

    finding_id=
        "mtbs_large_fire_frequency",

    indicator_name=
        "Mapped Large Fire Occurrence",

    statement=
        fire_statement,

    evidence=(
        f"{historical_fires} MTBS-mapped fires intersected "
        f"El Rito during {HISTORICAL_START}-{HISTORICAL_END}, "
        f"compared with {recent_fires} during "
        f"{RECENT_START}-{RECENT_END}."
    ),

    confidence=
        "High",

    status=
        "Independent corroborating evidence",

    caveat=(
        "MTBS focuses on significant mapped fires and does "
        "not represent the complete population of small fires."
    ),

    corroboration=(
        "Compare with FPA FOD reported large-fire occurrence."
    ),
)


# ------------------------------------------------------------
# UNIQUE BURNED AREA
# ------------------------------------------------------------

historical_unique = historical[
    "unique_acres"
]

recent_unique = recent[
    "unique_acres"
]


if recent_unique > historical_unique:

    unique_statement = (
        "The unique area of El Rito affected by mapped "
        "large fires increased during the recent period."
    )

elif recent_unique < historical_unique:

    unique_statement = (
        "The unique area of El Rito affected by mapped "
        "large fires decreased during the recent period."
    )

else:

    unique_statement = (
        "The unique area of El Rito affected by mapped "
        "large fires was unchanged."
    )


add_finding(

    finding_id=
        "mtbs_unique_burned_area_change",

    indicator_name=
        "Unique Mapped Burned Area",

    statement=
        unique_statement,

    evidence=(
        f"Unique mapped burned area changed from "
        f"{historical_unique:,.1f} acres "
        f"({historical['unique_percent_watershed']:.2f}% "
        f"of the watershed) during "
        f"{HISTORICAL_START}-{HISTORICAL_END} to "
        f"{recent_unique:,.1f} acres "
        f"({recent['unique_percent_watershed']:.2f}%) during "
        f"{RECENT_START}-{RECENT_END}."
    ),

    confidence=
        "High",

    status=
        "Independent corroborating evidence",

    caveat=(
        "MTBS represents significant mapped fire perimeters. "
        "Unique acreage is calculated from polygon unions and "
        "therefore does not double-count overlapping fires."
    ),

    corroboration=(
        "Use with FPA FOD large-fire occurrence trends."
    ),
)


# ------------------------------------------------------------
# REPEAT BURNING
# ------------------------------------------------------------

recent_repeat = recent[
    "repeat_burn_acres"
]


if recent_repeat > MIN_OVERLAP_ACRES:

    repeat_statement = (
        "Repeat burning occurred within El Rito during "
        "the recent comparison period."
    )

else:

    repeat_statement = (
        "No meaningful overlap among MTBS-mapped fires was "
        "identified within El Rito during the recent period."
    )


add_finding(

    finding_id=
        "mtbs_repeat_burning",

    indicator_name=
        "Repeat Burning",

    statement=
        repeat_statement,

    evidence=(
        f"{recent_repeat:,.1f} acres were affected by two or "
        f"more MTBS-mapped fires during "
        f"{RECENT_START}-{RECENT_END}. "
        f"The maximum mapped burn count at any location was "
        f"{recent['maximum_burn_count']}."
    ),

    confidence=
        "High",

    status=
        "Spatially derived evidence",

    caveat=(
        "Repeat burning is based on overlap among MTBS-mapped "
        "significant fire perimeters and does not include "
        "unmapped small fires."
    ),

    corroboration=(
        "Can later be combined with burn-severity data to assess "
        "the ecological significance of repeated fire."
    ),
)


# ============================================================
# FINDINGS OUTPUT
# ============================================================

findings_file = (
    OUTPUT_DIR
    / "mtbs_fire_regime_findings.csv"
)


write_csv(
    findings_file,
    list(
        findings[0].keys()
    ),
    findings
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
            "source_file",

        "value":
            str(MTBS_INPUT)
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
            "unique_mtbs_fires_intersecting_el_rito",

        "value":
            len(records)
    },

    {
        "metric":
            "first_mapped_fire_year_present",

        "value":
            MIN_YEAR
    },

    {
        "metric":
            "last_mapped_fire_year_present",

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
            "interpretation_rule",

        "value":
            "Rule-based; no free-form interpretation used."
    },

    {
        "metric":
            "limitation",

        "value":(
            "MTBS focuses on significant mapped fires. "
            "Small fires not mapped by MTBS are not represented."
        )
    },
]


summary_file = (
    OUTPUT_DIR
    / "mtbs_fire_history_summary.csv"
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
# SAVE PROCESSED CLIPPED FIRE LAYER
# ============================================================

output_gpkg = (
    PROCESSED_DIR
    / "el_rito_mtbs_fires.gpkg"
)


if output_gpkg.exists():

    output_gpkg.unlink()


arcpy.conversion.ExportFeatures(
    clipped_fc,
    str(output_gpkg)
)


# ============================================================
# FINISHED
# ============================================================

print()
print(
    "MTBS analysis complete."
)

print()

print(
    f"Unique mapped fires intersecting El Rito: "
    f"{len(records)}"
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
    f"  Cumulative acres: "
    f"{historical['cumulative_acres']:,.1f}"
)

print(
    f"  Unique acres burned: "
    f"{historical['unique_acres']:,.1f}"
)

print(
    f"  Unique watershed area burned: "
    f"{historical['unique_percent_watershed']:.2f}%"
)

print(
    f"  Repeat-burn acres: "
    f"{historical['repeat_burn_acres']:,.1f}"
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
    f"  Cumulative acres: "
    f"{recent['cumulative_acres']:,.1f}"
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

print(
    f"  Maximum mapped burn count: "
    f"{recent['maximum_burn_count']}"
)

print()

print(
    "All MTBS years:"
)

print(
    f"  Unique acres burned at least once: "
    f"{all_years['unique_acres']:,.1f}"
)

print(
    f"  Percent of watershed burned at least once: "
    f"{all_years_unique_pct:.2f}%"
)

print(
    f"  Repeat-burn acres: "
    f"{all_years['repeat_burn_acres']:,.1f}"
)

print(
    f"  Maximum mapped burn count: "
    f"{all_years['maximum_burn_count']}"
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
    summary_file,
]:

    print(path)