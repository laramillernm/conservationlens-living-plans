from pathlib import Path
import csv


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(
    r"C:\Users\Lara\ConservationInsights\conservationlens-living-plans"
)

FIRE_HISTORY_OUTPUTS = (
    PROJECT_ROOT
    / "outputs"
    / "fire_history"
)

OUTPUT_FILE = (
    FIRE_HISTORY_OUTPUTS
    / "fire_regime_findings.csv"
)


# ============================================================
# CURRENT PROTOTYPE COMPARISON PERIODS
# These match prototype.yaml for now.
# ============================================================

HISTORICAL_PERIOD = "2005-2014"
RECENT_PERIOD = "2015-2024"


# ============================================================
# CURRENT VERIFIED RESULTS
#
# These values come from the completed FPA and canonical
# fire-perimeter analyses.
#
# Later this script can read the values directly from the
# metrics CSVs instead of storing them here.
# ============================================================

FPA_TOTAL_HISTORICAL = 509
FPA_TOTAL_RECENT = 336

FPA_LARGE_HISTORICAL = 2
FPA_LARGE_RECENT = 8

FPA_P90_HISTORICAL = 3.0
FPA_P90_RECENT = 10.0


MTBS_FIRE_HISTORICAL = 1
MTBS_FIRE_RECENT = 3

MTBS_UNIQUE_PCT_HISTORICAL = 3.71
MTBS_UNIQUE_PCT_RECENT = 6.06

MTBS_REPEAT_RECENT_ACRES = 13.7
MTBS_UNIQUE_RECENT_ACRES = 5237.8


# ============================================================
# HELPERS
# ============================================================

def percent_change(old_value, new_value):

    if old_value == 0:
        return None

    return (
        (new_value - old_value)
        / old_value
        * 100
    )


# ============================================================
# CALCULATIONS
# ============================================================

total_fire_change_pct = percent_change(
    FPA_TOTAL_HISTORICAL,
    FPA_TOTAL_RECENT
)

large_fire_change_pct = percent_change(
    FPA_LARGE_HISTORICAL,
    FPA_LARGE_RECENT
)

p90_change_pct = percent_change(
    FPA_P90_HISTORICAL,
    FPA_P90_RECENT
)

burned_pct_change = (
    MTBS_UNIQUE_PCT_RECENT
    - MTBS_UNIQUE_PCT_HISTORICAL
)


# ============================================================
# STANDARDIZED FINDINGS
# ============================================================

findings = []


# ------------------------------------------------------------
# FINDING 1
# LARGE-FIRE ACTIVITY
# ------------------------------------------------------------

findings.append(
    {
        "finding_id":
            "fire_regime_large_fire_increase",

        "indicator_id":
            "fire_regime_change",

        "decision_stage":
            "threat",

        "finding_name":
            "Large-fire activity increased",

        "question":
            "How has fire activity changed over time?",

        "metric":
            "Large-fire occurrence and mapped burned-area footprint",

        "historical_period":
            HISTORICAL_PERIOD,

        "recent_period":
            RECENT_PERIOD,

        "historical_value":
            (
                f"{FPA_LARGE_HISTORICAL} FPA fires >=1000 acres; "
                f"{MTBS_FIRE_HISTORICAL} MTBS fire intersecting El Rito; "
                f"{MTBS_UNIQUE_PCT_HISTORICAL:.2f}% unique watershed area burned"
            ),

        "recent_value":
            (
                f"{FPA_LARGE_RECENT} FPA fires >=1000 acres; "
                f"{MTBS_FIRE_RECENT} MTBS fires intersecting El Rito; "
                f"{MTBS_UNIQUE_PCT_RECENT:.2f}% unique watershed area burned"
            ),

        "change":
            (
                f"FPA >=1000-acre fires increased "
                f"{large_fire_change_pct:.0f}%; "
                f"unique mapped watershed area burned increased "
                f"{burned_pct_change:.2f} percentage points"
            ),

        "interpretation":
            (
                "Large-fire activity increased during 2015-2024, "
                "and a larger unique share of the El Rito watershed "
                "was affected by mapped fire."
            ),

        "confidence":
            "moderate_to_high",

        "status":
            "corroborated",

        "evidence":
            (
                f"FPA fires >=1000 acres increased from "
                f"{FPA_LARGE_HISTORICAL} to {FPA_LARGE_RECENT}. "
                f"MTBS mapped fires intersecting El Rito increased from "
                f"{MTBS_FIRE_HISTORICAL} to {MTBS_FIRE_RECENT}. "
                f"Unique mapped burned area increased from "
                f"{MTBS_UNIQUE_PCT_HISTORICAL:.2f}% to "
                f"{MTBS_UNIQUE_PCT_RECENT:.2f}% of the watershed."
            ),

        "caveat":
            (
                "FPA occurrence records may be influenced by reporting "
                "practices. MTBS represents mapped significant fires and "
                "is not a complete inventory of all fires."
            ),

        "source_ids":
            "fpa_fod+mtbs",
    }
)


# ------------------------------------------------------------
# FINDING 2
# TOTAL REPORTED FIRE OCCURRENCE
# ------------------------------------------------------------

findings.append(
    {
        "finding_id":
            "fire_regime_reported_occurrence_decline",

        "indicator_id":
            "fire_regime_change",

        "decision_stage":
            "threat",

        "finding_name":
            "Total reported fire occurrence declined",

        "question":
            "How has fire activity changed over time?",

        "metric":
            "Reported fire occurrence",

        "historical_period":
            HISTORICAL_PERIOD,

        "recent_period":
            RECENT_PERIOD,

        "historical_value":
            f"{FPA_TOTAL_HISTORICAL} reported fires",

        "recent_value":
            f"{FPA_TOTAL_RECENT} reported fires",

        "change":
            f"{total_fire_change_pct:.0f}%",

        "interpretation":
            (
                "Total reported fire occurrence declined during the "
                "recent comparison period even as indicators of larger "
                "fire activity increased."
            ),

        "confidence":
            "low_to_moderate",

        "status":
            "supported_with_caution",

        "evidence":
            (
                f"FPA reported {FPA_TOTAL_HISTORICAL} fires during "
                f"{HISTORICAL_PERIOD} and {FPA_TOTAL_RECENT} during "
                f"{RECENT_PERIOD}."
            ),

        "caveat":
            (
                "Reported fire counts may reflect changes in detection, "
                "reporting, database practices, or inclusion of small fires. "
                "This finding should not be interpreted by itself as a "
                "decline in wildfire threat."
            ),

        "source_ids":
            "fpa_fod",
    }
)


# ------------------------------------------------------------
# FINDING 3
# FIRE-SIZE DISTRIBUTION
# ------------------------------------------------------------

findings.append(
    {
        "finding_id":
            "fire_regime_upper_size_distribution_increase",

        "indicator_id":
            "fire_regime_change",

        "decision_stage":
            "threat",

        "finding_name":
            "Upper fire-size distribution increased",

        "question":
            "How has fire activity changed over time?",

        "metric":
            "90th percentile reported fire size",

        "historical_period":
            HISTORICAL_PERIOD,

        "recent_period":
            RECENT_PERIOD,

        "historical_value":
            f"{FPA_P90_HISTORICAL:.1f} acres",

        "recent_value":
            f"{FPA_P90_RECENT:.1f} acres",

        "change":
            f"{p90_change_pct:.0f}%",

        "interpretation":
            (
                "The upper end of the reported fire-size distribution "
                "shifted toward larger fires during the recent period."
            ),

        "confidence":
            "moderate",

        "status":
            "supported",

        "evidence":
            (
                f"The 90th-percentile reported fire size increased from "
                f"{FPA_P90_HISTORICAL:.1f} acres to "
                f"{FPA_P90_RECENT:.1f} acres."
            ),

        "caveat":
            (
                "Fire-size distributions are based on reported FPA records "
                "and may be affected by reporting practices."
            ),

        "source_ids":
            "fpa_fod",
    }
)


# ------------------------------------------------------------
# FINDING 4
# REPEAT BURNING
# ------------------------------------------------------------

repeat_share = (
    MTBS_REPEAT_RECENT_ACRES
    / MTBS_UNIQUE_RECENT_ACRES
    * 100
)


findings.append(
    {
        "finding_id":
            "fire_regime_repeat_burning_limited",

        "indicator_id":
            "fire_regime_change",

        "decision_stage":
            "threat",

        "finding_name":
            "Recent mapped burning was mostly new footprint",

        "question":
            "How has fire activity changed over time?",

        "metric":
            "Repeat-burn area",

        "historical_period":
            HISTORICAL_PERIOD,

        "recent_period":
            RECENT_PERIOD,

        "historical_value":
            "0 repeat-burn acres identified",

        "recent_value":
            f"{MTBS_REPEAT_RECENT_ACRES:.1f} repeat-burn acres",

        "change":
            (
                f"Repeat burning represents approximately "
                f"{repeat_share:.2f}% of recent unique mapped burned area"
            ),

        "interpretation":
            (
                "The recent increase in mapped burned area was driven "
                "primarily by new fire footprint rather than extensive "
                "repeat burning."
            ),

        "confidence":
            "high",

        "status":
            "supported",

        "evidence":
            (
                f"Recent unique mapped burned area was "
                f"{MTBS_UNIQUE_RECENT_ACRES:,.1f} acres, while only "
                f"{MTBS_REPEAT_RECENT_ACRES:.1f} acres were identified "
                f"as repeat-burn area."
            ),

        "caveat":
            (
                "Repeat-burning results are limited to the mapped MTBS "
                "fire perimeters represented in the canonical dataset."
            ),

        "source_ids":
            "mtbs",
    }
)


# ============================================================
# WRITE OUTPUT
# ============================================================

fieldnames = [
    "finding_id",
    "indicator_id",
    "decision_stage",
    "finding_name",
    "question",
    "metric",
    "historical_period",
    "recent_period",
    "historical_value",
    "recent_value",
    "change",
    "interpretation",
    "confidence",
    "status",
    "evidence",
    "caveat",
    "source_ids",
]


with OUTPUT_FILE.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(findings)


# ============================================================
# REPORT
# ============================================================

print()
print("ConservationLens fire-regime findings")
print("======================================")
print()

print(
    "Decision stage: THREAT"
)

print(
    "Indicator: fire_regime_change"
)

print()


for finding in findings:

    print(
        finding["finding_name"]
    )

    print(
        f"  Status: "
        f"{finding['status']}"
    )

    print(
        f"  Confidence: "
        f"{finding['confidence']}"
    )

    print(
        f"  Interpretation: "
        f"{finding['interpretation']}"
    )

    print()


print(
    f"Findings written: {len(findings)}"
)

print()

print(
    "Output:"
)

print(
    OUTPUT_FILE
)