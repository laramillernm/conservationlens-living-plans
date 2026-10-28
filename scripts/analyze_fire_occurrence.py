"""
ConservationLens Living Plans
Analyze Karen Short FPA FOD fire occurrence data

Purpose
-------
Analyze reported wildfire occurrence patterns in the El Rito fire landscape
and create transparent, rule-based findings suitable for automated reporting.

Source refresh
--------------
The source data are refreshed separately by:
    refresh_fpa_fod.ps1

This script:
1. reads the validated local current GeoJSON
2. calculates fire-occurrence metrics
3. compares recent and historical periods
4. applies explicit interpretation rules
5. writes findings with evidence, confidence, caveats, and provenance

Important
---------
FPA FOD represents reported fire-occurrence points, not mapped burn footprints.
Changes in reporting practices can affect occurrence counts through time.
Perimeter-based datasets such as MTBS should be used as corroborating evidence.
"""

from pathlib import Path
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import median


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(
    r"C:\Users\Lara\ConservationInsights\conservationlens-living-plans"
)

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "fire_history"
    / "fpa_fod"
    / "fpa_fod_el_rito_current.geojson"
)

REFRESH_METADATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "fire_history"
    / "fpa_fod"
    / "fpa_fod_refresh.txt"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "fire_history"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# ANALYSIS SETTINGS
# ============================================================

CONTEXT_BUFFER_KM = 20

DATASET_NAME = "Karen Short FPA FOD"

METHOD_ID = "fire_regime_occurrence_v1"

SCRIPT_VERSION = "1.0"

LARGE_FIRE_THRESHOLD_ACRES = 1000


SIZE_BANDS = [
    ("<10 acres", 0, 10),
    ("10-99 acres", 10, 100),
    ("100-999 acres", 100, 1000),
    (">=1,000 acres", 1000, math.inf),
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def normalize_properties(properties):

    return {
        str(key).lower(): value
        for key, value in properties.items()
    }


def get_value(properties, field_name):

    return properties.get(
        field_name.lower()
    )


def safe_float(value):

    if value in (
        None,
        "",
        "null"
    ):
        return None

    try:
        return float(value)

    except (
        TypeError,
        ValueError
    ):
        return None


def safe_int(value):

    if value in (
        None,
        "",
        "null"
    ):
        return None

    try:
        return int(
            float(value)
        )

    except (
        TypeError,
        ValueError
    ):
        return None


def fire_size_band(size):

    if size is None:
        return "Unknown"

    for (
        label,
        lower,
        upper
    ) in SIZE_BANDS:

        if (
            lower
            <= size
            < upper
        ):
            return label

    return "Unknown"


def decade_label(year):

    start = (
        year // 10
    ) * 10

    return f"{start}s"


def month_from_doy(
    year,
    doy
):

    if (
        year is None
        or doy is None
    ):
        return None

    try:

        date = (
            datetime(
                year,
                1,
                1
            )
            + timedelta(
                days=doy - 1
            )
        )

        return date.month

    except (
        ValueError,
        OverflowError
    ):
        return None


def percentile(
    values,
    percentile_value
):

    clean_values = sorted(
        value
        for value in values
        if value is not None
    )

    if not clean_values:
        return None

    if len(clean_values) == 1:
        return clean_values[0]

    position = (
        len(clean_values) - 1
    ) * percentile_value / 100

    lower_index = math.floor(
        position
    )

    upper_index = math.ceil(
        position
    )

    if (
        lower_index
        == upper_index
    ):
        return clean_values[
            lower_index
        ]

    lower_value = clean_values[
        lower_index
    ]

    upper_value = clean_values[
        upper_index
    ]

    fraction = (
        position
        - lower_index
    )

    return (
        lower_value
        + (
            upper_value
            - lower_value
        )
        * fraction
    )


def write_csv(
    path,
    fieldnames,
    rows
):

    with path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
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


def read_refresh_metadata():

    metadata = {}

    if not REFRESH_METADATA_FILE.exists():
        return metadata

    with REFRESH_METADATA_FILE.open(
        "r",
        encoding="utf-8-sig"
    ) as file:

        for line in file:

            line = line.strip()

            if (
                not line
                or "=" not in line
            ):
                continue

            key, value = line.split(
                "=",
                1
            )

            metadata[
                key.strip()
            ] = value.strip()

    return metadata


# ============================================================
# READ SOURCE DATA
# ============================================================

print()
print(
    "ConservationLens fire-occurrence analysis"
)
print(
    "========================================="
)
print()

print("Input:")
print(INPUT_FILE)
print()


if not INPUT_FILE.exists():

    raise FileNotFoundError(
        f"FPA FOD current dataset not found:\n"
        f"{INPUT_FILE}\n\n"
        "Run refresh_fpa_fod.ps1 first."
    )


with INPUT_FILE.open(
    "r",
    encoding="utf-8-sig"
) as source_file:

    geojson = json.load(
        source_file
    )


features = geojson.get(
    "features",
    []
)


if not features:

    raise ValueError(
        "The FPA FOD GeoJSON contains no features."
    )


print(
    f"Source records: "
    f"{len(features):,}"
)


# ============================================================
# STANDARDIZE RECORDS
# ============================================================

records = []


for feature in features:

    properties = normalize_properties(
        feature.get(
            "properties",
            {}
        )
    )

    geometry = (
        feature.get("geometry")
        or {}
    )

    coordinates = (
        geometry.get("coordinates")
        or [None, None]
    )


    fire_year = safe_int(
        get_value(
            properties,
            "fire_year"
        )
    )

    discovery_doy = safe_int(
        get_value(
            properties,
            "discovery_doy"
        )
    )

    fire_size = safe_float(
        get_value(
            properties,
            "fire_size"
        )
    )

    month = month_from_doy(
        fire_year,
        discovery_doy
    )


    record = {

        "fod_id":
            get_value(
                properties,
                "fod_id"
            ),

        "fpa_id":
            get_value(
                properties,
                "fpa_id"
            ),

        "fire_name":
            get_value(
                properties,
                "fire_name"
            ),

        "fire_year":
            fire_year,

        "discovery_doy":
            discovery_doy,

        "discovery_month":
            month,

        "fire_size_acres":
            fire_size,

        "size_band":
            fire_size_band(
                fire_size
            ),

        "fpa_size_class":
            get_value(
                properties,
                "fire_size_class"
            ),

        "cause_classification":
            get_value(
                properties,
                "nwcg_cause_classification"
            ),

        "general_cause":
            get_value(
                properties,
                "nwcg_general_cause"
            ),

        "state":
            get_value(
                properties,
                "state"
            ),

        "county":
            get_value(
                properties,
                "county"
            ),

        "mtbs_id":
            get_value(
                properties,
                "mtbs_id"
            ),

        "longitude":
            (
                coordinates[0]
                if len(coordinates) >= 2
                else None
            ),

        "latitude":
            (
                coordinates[1]
                if len(coordinates) >= 2
                else None
            ),
    }


    if fire_year is not None:

        records.append(
            record
        )


if not records:

    raise ValueError(
        "No records contained a valid fire_year."
    )


years = sorted(
    record["fire_year"]
    for record in records
)


MIN_YEAR = min(
    years
)

MAX_YEAR = max(
    years
)


print(
    f"Valid fire records: "
    f"{len(records):,}"
)

print(
    f"Analysis period: "
    f"{MIN_YEAR}-{MAX_YEAR}"
)

print()


refresh_metadata = (
    read_refresh_metadata()
)

refresh_date = (
    refresh_metadata.get(
        "refresh_time",
        ""
    )
)

source_layer = (
    refresh_metadata.get(
        "layer_name",
        ""
    )
)


# ============================================================
# DETAIL OUTPUT
# ============================================================

detail_file = (
    OUTPUT_DIR
    / "fire_occurrence_detail.csv"
)


detail_fields = [
    "fod_id",
    "fpa_id",
    "fire_name",
    "fire_year",
    "discovery_doy",
    "discovery_month",
    "fire_size_acres",
    "size_band",
    "fpa_size_class",
    "cause_classification",
    "general_cause",
    "state",
    "county",
    "mtbs_id",
    "longitude",
    "latitude",
]


write_csv(
    detail_file,
    detail_fields,
    records
)


# ============================================================
# ANNUAL SUMMARY
# ============================================================

records_by_year = defaultdict(
    list
)


for record in records:

    records_by_year[
        record["fire_year"]
    ].append(
        record
    )


annual_rows = []


for year in range(
    MIN_YEAR,
    MAX_YEAR + 1
):

    year_records = (
        records_by_year.get(
            year,
            []
        )
    )

    sizes = [
        record["fire_size_acres"]
        for record in year_records
        if record[
            "fire_size_acres"
        ] is not None
    ]

    size_counts = Counter(
        record["size_band"]
        for record in year_records
    )


    annual_rows.append({

        "year":
            year,

        "reported_fires":
            len(
                year_records
            ),

        "fires_lt_10_acres":
            size_counts[
                "<10 acres"
            ],

        "fires_10_99_acres":
            size_counts[
                "10-99 acres"
            ],

        "fires_100_999_acres":
            size_counts[
                "100-999 acres"
            ],

        "fires_ge_1000_acres":
            size_counts[
                ">=1,000 acres"
            ],

        "median_fire_size_acres":
            round_value(
                median(sizes)
                if sizes
                else None
            ),

        "p90_fire_size_acres":
            round_value(
                percentile(
                    sizes,
                    90
                )
            ),

        "max_fire_size_acres":
            round_value(
                max(sizes)
                if sizes
                else None
            ),
    })


annual_file = (
    OUTPUT_DIR
    / "fire_occurrence_annual.csv"
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

records_by_decade = defaultdict(
    list
)


for record in records:

    decade = decade_label(
        record["fire_year"]
    )

    records_by_decade[
        decade
    ].append(
        record
    )


decade_rows = []


for decade in sorted(
    records_by_decade
):

    decade_records = (
        records_by_decade[
            decade
        ]
    )

    sizes = [
        record["fire_size_acres"]
        for record in decade_records
        if record[
            "fire_size_acres"
        ] is not None
    ]

    size_counts = Counter(
        record["size_band"]
        for record in decade_records
    )

    decade_start = min(
        record["fire_year"]
        for record in decade_records
    )

    decade_end = max(
        record["fire_year"]
        for record in decade_records
    )

    years_present = (
        decade_end
        - decade_start
        + 1
    )


    decade_rows.append({

        "decade":
            decade,

        "years_in_dataset":
            years_present,

        "reported_fires":
            len(
                decade_records
            ),

        "average_reported_fires_per_year":
            round_value(
                len(
                    decade_records
                )
                / years_present
            ),

        "fires_lt_10_acres":
            size_counts[
                "<10 acres"
            ],

        "fires_10_99_acres":
            size_counts[
                "10-99 acres"
            ],

        "fires_100_999_acres":
            size_counts[
                "100-999 acres"
            ],

        "fires_ge_1000_acres":
            size_counts[
                ">=1,000 acres"
            ],

        "median_fire_size_acres":
            round_value(
                median(sizes)
                if sizes
                else None
            ),

        "p90_fire_size_acres":
            round_value(
                percentile(
                    sizes,
                    90
                )
            ),

        "max_fire_size_acres":
            round_value(
                max(sizes)
                if sizes
                else None
            ),
    })


decade_file = (
    OUTPUT_DIR
    / "fire_occurrence_decade.csv"
)


write_csv(
    decade_file,
    list(
        decade_rows[0].keys()
    ),
    decade_rows
)


# ============================================================
# RECENT VS PREVIOUS 10-YEAR PERIOD
# ============================================================

recent_end = MAX_YEAR
recent_start = MAX_YEAR - 9

previous_end = recent_start - 1
previous_start = previous_end - 9


period_definitions = [

    (
        "historical",
        previous_start,
        previous_end
    ),

    (
        "recent",
        recent_start,
        recent_end
    ),
]


period_metrics = {}


for (
    period_name,
    start_year,
    end_year
) in period_definitions:

    period_records = [

        record

        for record in records

        if (
            start_year
            <= record["fire_year"]
            <= end_year
        )
    ]


    sizes = [

        record["fire_size_acres"]

        for record in period_records

        if record[
            "fire_size_acres"
        ] is not None
    ]


    size_counts = Counter(
        record["size_band"]
        for record in period_records
    )


    years_count = (
        end_year
        - start_year
        + 1
    )


    period_metrics[
        period_name
    ] = {

        "start_year":
            start_year,

        "end_year":
            end_year,

        "reported_fires":
            len(
                period_records
            ),

        "fires_per_year":
            len(
                period_records
            )
            / years_count,

        "fires_lt_10":
            size_counts[
                "<10 acres"
            ],

        "fires_10_99":
            size_counts[
                "10-99 acres"
            ],

        "fires_100_999":
            size_counts[
                "100-999 acres"
            ],

        "fires_ge_1000":
            size_counts[
                ">=1,000 acres"
            ],

        "median_size":
            (
                median(sizes)
                if sizes
                else None
            ),

        "p90_size":
            percentile(
                sizes,
                90
            ),

        "max_size":
            (
                max(sizes)
                if sizes
                else None
            ),
    }


historical = (
    period_metrics[
        "historical"
    ]
)

recent = (
    period_metrics[
        "recent"
    ]
)


# ============================================================
# STANDARDIZED METRICS TABLE
#
# This is the machine-readable evidence layer.
# ============================================================

metric_definitions = [

    (
        "reported_fire_frequency",
        "Reported Fire Frequency",
        "fires/year",
        historical[
            "fires_per_year"
        ],
        recent[
            "fires_per_year"
        ],
    ),

    (
        "small_fire_occurrence",
        "Small Fire Occurrence",
        "fires <10 acres / 10-year period",
        historical[
            "fires_lt_10"
        ],
        recent[
            "fires_lt_10"
        ],
    ),

    (
        "medium_fire_occurrence",
        "10-99 Acre Fire Occurrence",
        "fires / 10-year period",
        historical[
            "fires_10_99"
        ],
        recent[
            "fires_10_99"
        ],
    ),

    (
        "large_fire_occurrence",
        "Large Fire Occurrence",
        "fires >=1,000 acres / 10-year period",
        historical[
            "fires_ge_1000"
        ],
        recent[
            "fires_ge_1000"
        ],
    ),

    (
        "upper_tail_fire_size",
        "Upper-Tail Fire Size",
        "90th percentile acres",
        historical[
            "p90_size"
        ],
        recent[
            "p90_size"
        ],
    ),

    (
        "median_fire_size",
        "Median Fire Size",
        "acres",
        historical[
            "median_size"
        ],
        recent[
            "median_size"
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

    change = (
        recent_value
        - historical_value
        if (
            historical_value
            is not None
            and recent_value
            is not None
        )
        else None
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

        "source_layer":
            source_layer,

        "historical_period":
            (
                f"{historical['start_year']}-"
                f"{historical['end_year']}"
            ),

        "recent_period":
            (
                f"{recent['start_year']}-"
                f"{recent['end_year']}"
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
                change
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

        "refresh_date":
            refresh_date,
    })


metrics_file = (
    OUTPUT_DIR
    / "fire_regime_metrics.csv"
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
#
# This is the interpretation layer.
#
# Statements below are generated from explicit rules,
# not free-form AI interpretation.
# ============================================================

findings = []


def add_finding(
    finding_id,
    indicator_name,
    statement,
    evidence,
    confidence,
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

        "caveat":
            caveat,

        "corroboration":
            corroboration,

        "dataset":
            DATASET_NAME,

        "historical_period":
            (
                f"{historical['start_year']}-"
                f"{historical['end_year']}"
            ),

        "recent_period":
            (
                f"{recent['start_year']}-"
                f"{recent['end_year']}"
            ),

        "method_id":
            METHOD_ID,

        "script_version":
            SCRIPT_VERSION,

        "refresh_date":
            refresh_date,
    })


# ------------------------------------------------------------
# LARGE FIRE FREQUENCY RULE
# ------------------------------------------------------------

historical_large = (
    historical[
        "fires_ge_1000"
    ]
)

recent_large = (
    recent[
        "fires_ge_1000"
    ]
)


if (
    historical_large > 0
    and recent_large
    >= historical_large * 2
):

    large_statement = (
        "Large reported fires occurred substantially more "
        "frequently during the recent comparison period."
    )

elif (
    recent_large
    > historical_large
):

    large_statement = (
        "Large reported fires occurred more frequently "
        "during the recent comparison period."
    )

elif (
    recent_large
    < historical_large
):

    large_statement = (
        "Large reported fires occurred less frequently "
        "during the recent comparison period."
    )

else:

    large_statement = (
        "Large reported fire occurrence was unchanged "
        "between the two comparison periods."
    )


large_change_pct = percent_change(
    historical_large,
    recent_large
)


large_evidence = (

    f"{historical_large} reported fires "
    f">={LARGE_FIRE_THRESHOLD_ACRES:,} acres occurred during "
    f"{historical['start_year']}-{historical['end_year']}, "
    f"compared with {recent_large} during "
    f"{recent['start_year']}-{recent['end_year']}."
)


if large_change_pct is not None:

    large_evidence += (
        f" This represents a "
        f"{round(large_change_pct, 1)}% change."
    )


add_finding(

    finding_id=
        "large_fire_frequency_change",

    indicator_name=
        "Large Fire Occurrence",

    statement=
        large_statement,

    evidence=
        large_evidence,

    confidence=
        "Moderate",

    caveat=
        "FPA FOD records reported fire occurrences. "
        "Changes in reporting practices may affect counts "
        "through time, and fire points do not represent "
        "mapped burned footprints.",

    corroboration=
        "Compare with MTBS mapped burned area and fire-perimeter history.",
)


# ------------------------------------------------------------
# UPPER-TAIL FIRE SIZE RULE
# ------------------------------------------------------------

historical_p90 = (
    historical[
        "p90_size"
    ]
)

recent_p90 = (
    recent[
        "p90_size"
    ]
)


if (
    historical_p90 is not None
    and recent_p90 is not None
):

    if (
        recent_p90
        >= historical_p90 * 2
    ):

        p90_statement = (
            "The upper end of the reported fire-size "
            "distribution increased substantially."
        )

    elif (
        recent_p90
        > historical_p90
    ):

        p90_statement = (
            "The upper end of the reported fire-size "
            "distribution increased."
        )

    elif (
        recent_p90
        < historical_p90
    ):

        p90_statement = (
            "The upper end of the reported fire-size "
            "distribution decreased."
        )

    else:

        p90_statement = (
            "The upper end of the reported fire-size "
            "distribution was unchanged."
        )


    p90_evidence = (

        f"The 90th-percentile reported fire size changed "
        f"from {round(historical_p90, 2)} acres during "
        f"{historical['start_year']}-{historical['end_year']} "
        f"to {round(recent_p90, 2)} acres during "
        f"{recent['start_year']}-{recent['end_year']}."
    )


    add_finding(

        finding_id=
            "upper_tail_fire_size_change",

        indicator_name=
            "Upper-Tail Fire Size",

        statement=
            p90_statement,

        evidence=
            p90_evidence,

        confidence=
            "Moderate",

        caveat=
            "Reported final fire size is suitable for examining "
            "the distribution of reported occurrence sizes, but "
            "does not replace mapped perimeter analysis.",

        corroboration=
            "Compare with MTBS burned-area and perimeter trends.",
    )


# ------------------------------------------------------------
# TOTAL OCCURRENCE RULE
# ------------------------------------------------------------

historical_frequency = (
    historical[
        "fires_per_year"
    ]
)

recent_frequency = (
    recent[
        "fires_per_year"
    ]
)


frequency_pct = percent_change(
    historical_frequency,
    recent_frequency
)


if (
    recent_frequency
    < historical_frequency
):

    occurrence_statement = (
        "Total reported fire occurrence declined."
    )

elif (
    recent_frequency
    > historical_frequency
):

    occurrence_statement = (
        "Total reported fire occurrence increased."
    )

else:

    occurrence_statement = (
        "Total reported fire occurrence was unchanged."
    )


occurrence_evidence = (

    f"Average reported occurrence changed from "
    f"{round(historical_frequency, 1)} fires per year during "
    f"{historical['start_year']}-{historical['end_year']} "
    f"to {round(recent_frequency, 1)} fires per year during "
    f"{recent['start_year']}-{recent['end_year']}."
)


if frequency_pct is not None:

    occurrence_evidence += (
        f" This represents a "
        f"{round(frequency_pct, 1)}% change."
    )


add_finding(

    finding_id=
        "reported_fire_frequency_change",

    indicator_name=
        "Reported Fire Frequency",

    statement=
        occurrence_statement,

    evidence=
        occurrence_evidence,

    confidence=
        "Low to Moderate",

    caveat=
        "Changes in reported fire counts may reflect differences "
        "in detection, reporting, agency records, or database "
        "practices in addition to actual changes in fire occurrence.",

    corroboration=
        "Do not interpret this metric alone as a change in wildfire hazard.",
)


# ------------------------------------------------------------
# COMBINED INTERPRETATION RULE
# ------------------------------------------------------------

if (
    recent_frequency
    < historical_frequency
    and recent_large
    > historical_large
):

    combined_statement = (
        "Total reported fire occurrence declined while "
        "large-fire occurrence increased."
    )

    combined_evidence = (

        f"Reported occurrence declined from "
        f"{round(historical_frequency, 1)} to "
        f"{round(recent_frequency, 1)} fires per year, "
        f"while fires >={LARGE_FIRE_THRESHOLD_ACRES:,} acres "
        f"increased from {historical_large} to {recent_large}."
    )


    add_finding(

        finding_id=
            "fire_regime_distribution_shift",

        indicator_name=
            "Fire Regime Change",

        statement=
            combined_statement,

        evidence=
            combined_evidence,

        confidence=
            "Moderate",

        caveat=
            "This finding describes a change in the distribution "
            "of reported fire occurrences. It does not by itself "
            "establish that overall wildfire hazard or watershed "
            "risk increased.",

        corroboration=
            "Use MTBS to test whether mapped burned area and repeat "
            "burning show a corresponding landscape-level change.",
    )


# ============================================================
# FINDINGS OUTPUT
# ============================================================

findings_file = (
    OUTPUT_DIR
    / "fire_regime_findings.csv"
)


write_csv(
    findings_file,
    list(
        findings[0].keys()
    ),
    findings
)


# ============================================================
# PROVENANCE / SUMMARY OUTPUT
# ============================================================

summary_rows = [

    {
        "metric":
            "analysis_area",

        "value":
            "El Rito fire landscape"
    },

    {
        "metric":
            "context_buffer_km",

        "value":
            CONTEXT_BUFFER_KM
    },

    {
        "metric":
            "dataset",

        "value":
            DATASET_NAME
    },

    {
        "metric":
            "source_layer",

        "value":
            source_layer
    },

    {
        "metric":
            "source_refresh_date",

        "value":
            refresh_date
    },

    {
        "metric":
            "source_records",

        "value":
            len(records)
    },

    {
        "metric":
            "source_period",

        "value":
            f"{MIN_YEAR}-{MAX_YEAR}"
    },

    {
        "metric":
            "historical_comparison_period",

        "value":
            (
                f"{historical['start_year']}-"
                f"{historical['end_year']}"
            )
    },

    {
        "metric":
            "recent_comparison_period",

        "value":
            (
                f"{recent['start_year']}-"
                f"{recent['end_year']}"
            )
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

        "value":
            "FPA FOD represents reported fire-occurrence points. "
            "Counts and trends may be influenced by reporting practices."
    },
]


summary_file = (
    OUTPUT_DIR
    / "fire_occurrence_summary.csv"
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

print(
    "Analysis complete."
)

print()

print(
    "Trust and provenance outputs:"
)

print(
    metrics_file
)

print(
    findings_file
)

print(
    summary_file
)

print()

print(
    f"Rule-based findings created: "
    f"{len(findings)}"
)

print()

print(
    "Important: findings describe reported fire-occurrence "
    "patterns and do not automatically imply a change in "
    "wildfire hazard or watershed risk."
)