from pathlib import Path
import csv
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

HYDROLOGY_OUTPUTS = (
    PROJECT_ROOT
    / "outputs"
    / "hydrology"
)

DETAIL_FILE = (
    HYDROLOGY_OUTPUTS
    / "hydrologic_context_huc12.csv"
)

SUMMARY_FILE = (
    HYDROLOGY_OUTPUTS
    / "hydrologic_context_summary.csv"
)

OUTPUT_FILE = (
    HYDROLOGY_OUTPUTS
    / "hydrologic_context_findings.csv"
)


# ============================================================
# READ CONFIG
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


planning_area = config["planning_area"]

PLANNING_NAME = planning_area["name"]

PLANNING_HUC_ID = str(
    planning_area["huc"]["id"]
)

PLANNING_HUC_NAME = (
    planning_area["huc"]["name"]
)

PARENT_HUC_ID = str(
    planning_area["huc"]["parent"]["id"]
)

PARENT_HUC_NAME = (
    planning_area["huc"]["parent"]["name"]
)


# ============================================================
# VALIDATE INPUT FILES
# ============================================================

if not DETAIL_FILE.exists():
    raise FileNotFoundError(
        f"Hydrologic context detail file not found:\n{DETAIL_FILE}"
    )

if not SUMMARY_FILE.exists():
    raise FileNotFoundError(
        f"Hydrologic context summary file not found:\n{SUMMARY_FILE}"
    )


# ============================================================
# READ DETAIL RECORDS
# ============================================================

records = []

with DETAIL_FILE.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    reader = csv.DictReader(f)

    for row in reader:
        records.append(row)


upstream_records = [
    row
    for row in records
    if row["relationship"] in {
        "immediate_upstream",
        "upstream",
    }
]

downstream_records = [
    row
    for row in records
    if row["relationship"] in {
        "immediate_downstream",
        "downstream",
    }
]


# ============================================================
# READ SUMMARY
# ============================================================

summary = {}

with SUMMARY_FILE.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    reader = csv.DictReader(f)

    for row in reader:
        summary[
            row["metric"]
        ] = row["value"]


planning_huc12_count = int(
    summary.get(
        "planning_huc12_count",
        0
    )
)

upstream_count = int(
    summary.get(
        "upstream_context_count",
        0
    )
)

downstream_count = int(
    summary.get(
        "downstream_context_count",
        0
    )
)


# ============================================================
# BUILD STANDARDIZED FINDINGS
# ============================================================

findings = []


# ------------------------------------------------------------
# FINDING 1
# INTERNAL HUC STRUCTURE
# ------------------------------------------------------------

findings.append(
    {
        "finding_id":
            "hydrologic_context_planning_huc_structure",

        "indicator_id":
            "hydrologic_context",

        "decision_stage":
            "connection",

        "finding_name":
            "Planning watershed has defined internal HUC12 structure",

        "question":
            "How is the planning area connected to surrounding watersheds?",

        "metric":
            "HUC12 units within planning HUC",

        "result":
            (
                f"{planning_huc12_count} HUC12 units occur within "
                f"{PLANNING_HUC_NAME} HUC10 {PLANNING_HUC_ID}."
            ),

        "interpretation":
            (
                f"The {PLANNING_NAME} planning area can be represented "
                f"as a connected HUC12 watershed network within the "
                f"{PLANNING_HUC_NAME} HUC10."
            ),

        "confidence":
            "high",

        "status":
            "supported",

        "evidence":
            (
                f"WBD identifies {planning_huc12_count} HUC12 units "
                f"within HUC10 {PLANNING_HUC_ID}."
            ),

        "caveat":
            (
                "HUC12 relationships provide a generalized watershed "
                "network. They do not represent detailed within-channel "
                "flow paths, travel time, sediment transport, or "
                "debris-flow runout."
            ),

        "source_ids":
            "wbd",
    }
)


# ------------------------------------------------------------
# FINDING 2
# EXTERNAL UPSTREAM CONNECTION
# ------------------------------------------------------------

if upstream_count == 0:

    findings.append(
        {
            "finding_id":
                "hydrologic_context_no_external_upstream",

            "indicator_id":
                "hydrologic_context",

            "decision_stage":
                "connection",

            "finding_name":
                "No immediate external upstream HUC12 connection identified",

            "question":
                "How is the planning area connected to surrounding watersheds?",

            "metric":
                "Immediate external upstream HUC12 count",

            "result":
                "0 immediate external upstream HUC12s",

            "interpretation":
                (
                    f"No HUC12 outside the {PLANNING_HUC_NAME} HUC10 "
                    f"was identified as draining directly into one of "
                    f"its internal HUC12 units under the current "
                    f"one-level WBD ToHUC rule."
                ),

            "confidence":
                "high",

            "status":
                "supported",

            "evidence":
                (
                    "The hydrologic-context selection returned zero "
                    "external HUC12 units whose ToHUC value points "
                    "directly into the planning HUC10."
                ),

            "caveat":
                (
                    "This finding applies only to the configured "
                    "one-level HUC12 network relationship. It does not "
                    "mean there are no broader regional hydrologic "
                    "influences or subsurface connections."
                ),

            "source_ids":
                "wbd",
        }
    )

else:

    upstream_names = "; ".join(
        f"{row['huc12']} — {row['huc12_name']}"
        for row in upstream_records
    )

    findings.append(
        {
            "finding_id":
                "hydrologic_context_external_upstream",

            "indicator_id":
                "hydrologic_context",

            "decision_stage":
                "connection",

            "finding_name":
                "Immediate external upstream watershed connections identified",

            "question":
                "How is the planning area connected to surrounding watersheds?",

            "metric":
                "Immediate external upstream HUC12 count",

            "result":
                f"{upstream_count} external upstream HUC12(s)",

            "interpretation":
                (
                    f"{upstream_count} HUC12 watershed unit(s) outside "
                    f"the planning HUC drain directly into the planning "
                    f"watershed under the configured WBD network rule."
                ),

            "confidence":
                "high",

            "status":
                "supported",

            "evidence":
                upstream_names,

            "caveat":
                (
                    "This represents a bounded HUC12 network relationship "
                    "and does not model detailed flow routing, sediment "
                    "transport, travel time, or debris-flow runout."
                ),

            "source_ids":
                "wbd",
        }
    )


# ------------------------------------------------------------
# FINDING 3
# IMMEDIATE DOWNSTREAM CONNECTION
# ------------------------------------------------------------

if downstream_count > 0:

    immediate_downstream = None

    for row in downstream_records:

        if row["relationship"] == "immediate_downstream":
            immediate_downstream = row
            break


    if immediate_downstream:

        downstream_huc = (
            immediate_downstream[
                "huc12"
            ]
        )

        downstream_name = (
            immediate_downstream[
                "huc12_name"
            ]
        )

        source_huc = (
            immediate_downstream[
                "related_huc12"
            ]
        )

        source_name = (
            immediate_downstream[
                "related_huc12_name"
            ]
        )


        findings.append(
            {
                "finding_id":
                    "hydrologic_context_downstream_connection",

                "indicator_id":
                    "hydrologic_context",

                "decision_stage":
                    "connection",

                "finding_name":
                    (
                        f"{PLANNING_HUC_NAME} drains directly to "
                        f"{downstream_name}"
                    ),

                "question":
                    "How is the planning area connected to surrounding watersheds?",

                "metric":
                    "Immediate downstream HUC12",

                "result":
                    (
                        f"{downstream_huc} — {downstream_name}"
                    ),

                "interpretation":
                    (
                        f"The planning watershed drains directly from "
                        f"{source_huc} — {source_name} into "
                        f"{downstream_huc} — {downstream_name}. "
                        f"This downstream unit is the first external "
                        f"HUC12 potentially connected to effects originating "
                        f"within the planning watershed."
                    ),

                "confidence":
                    "high",

                "status":
                    "supported",

                "evidence":
                    (
                        f"WBD ToHUC identifies {source_huc} "
                        f"as draining to {downstream_huc}."
                    ),

                "caveat":
                    (
                        "This is a watershed-network connection, not an "
                        "estimate of debris-flow runout, sediment delivery, "
                        "travel time, magnitude, or probability of impact."
                    ),

                "source_ids":
                    "wbd",
            }
        )


# ------------------------------------------------------------
# FINDING 4
# BOUNDED HYDROLOGIC CONTEXT
# ------------------------------------------------------------

findings.append(
    {
        "finding_id":
            "hydrologic_context_bounded_network",

        "indicator_id":
            "hydrologic_context",

        "decision_stage":
            "connection",

        "finding_name":
            "Hydrologic context is intentionally bounded",

        "question":
            "How is the planning area connected to surrounding watersheds?",

        "metric":
            "Configured hydrologic context rule",

        "result":
            (
                f"{upstream_count} upstream context unit(s); "
                f"{downstream_count} downstream context unit(s)"
            ),

        "interpretation":
            (
                "ConservationLens uses a bounded HUC12 network context "
                "rather than recursively extending the analysis through "
                "the entire watershed network."
            ),

        "confidence":
            "high",

        "status":
            "methodological",

        "evidence":
            (
                f"Planning HUC10 {PLANNING_HUC_ID} is evaluated within "
                f"parent HUC8 {PARENT_HUC_ID} — {PARENT_HUC_NAME}, "
                f"using the configured upstream and downstream levels."
            ),

        "caveat":
            (
                "The bounded context is a planning simplification. "
                "Additional hydrologic levels or event-specific routing "
                "may be appropriate for particular decisions."
            ),

        "source_ids":
            "wbd",
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
    "result",
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
print("ConservationLens hydrologic-context findings")
print("=============================================")
print()

print("Decision stage: CONNECTION")
print("Indicator: hydrologic_context")
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

print("Output:")
print(OUTPUT_FILE)