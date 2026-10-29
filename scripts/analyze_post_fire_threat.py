from pathlib import Path
import csv
import re

import arcpy
import numpy as np
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

SOURCE_RASTER = str(
    PROJECT_ROOT
    / "data"
    / "raw"
    / "post_fire"
    / "nmfap"
    / "NMFAP.gdb"
    / "NMFAP2020_Threat_Postfire_DebrisFlowHazard_Annual"
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

POST_FIRE_ANALYSIS_GPKG = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "post_fire"
    / "post_fire_analysis_area.gpkg"
)

POST_FIRE_ANALYSIS_FC = (
    str(POST_FIRE_ANALYSIS_GPKG)
    + "\\post_fire_analysis_area"
)

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "post_fire"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "post_fire"
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
# OUTPUTS
# ============================================================

CLIPPED_RAW_RASTER = str(
    PROCESSED_DIR
    / "post_fire_threat_raw.tif"
)

CLASSIFIED_RASTER = str(
    PROCESSED_DIR
    / "post_fire_threat_statewide_class.tif"
)

STATEWIDE_BREAKS_CSV = (
    OUTPUT_DIR
    / "post_fire_statewide_breaks.csv"
)

PLANNING_SUMMARY_CSV = (
    OUTPUT_DIR
    / "post_fire_threat_summary.csv"
)

BY_UNIT_CSV = (
    OUTPUT_DIR
    / "post_fire_threat_by_unit.csv"
)

FINDINGS_CSV = (
    OUTPUT_DIR
    / "post_fire_threat_findings.csv"
)


# ============================================================
# TEMP WORKSPACE
# ============================================================

TEMP_GDB = (
    PROCESSED_DIR
    / "post_fire_analysis_temp.gdb"
)

if not arcpy.Exists(
    str(TEMP_GDB)
):

    arcpy.management.CreateFileGDB(
        str(PROCESSED_DIR),
        TEMP_GDB.name
    )


# ============================================================
# READ CONFIG
# ============================================================

with CONFIG_FILE.open(
    "r",
    encoding="utf-8"
) as f:

    config = yaml.safe_load(f)


planning_config = (
    config["planning_area"]
)

PLANNING_NAME = (
    planning_config["name"]
)

PLANNING_HUC10 = str(
    planning_config["huc"]["id"]
)

PLANNING_HUC_NAME = (
    planning_config["huc"]["name"]
)


# ============================================================
# START
# ============================================================

print()
print(
    "ConservationLens post-fire threat analysis"
)
print(
    "=========================================="
)
print()

print(
    "Decision stage: THREAT"
)

print(
    "Indicator: post_fire_erosion_threat"
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

required_arcpy_inputs = [
    SOURCE_RASTER,
    HUC12_FC,
    HYDROLOGIC_CONTEXT_FC,
    POST_FIRE_ANALYSIS_FC,
]


for item in required_arcpy_inputs:

    if not arcpy.Exists(
        item
    ):

        raise FileNotFoundError(
            f"Required dataset not found:\n{item}"
        )


if not PLANNING_BOUNDARY.exists():

    raise FileNotFoundError(
        "Planning boundary not found:\n"
        f"{PLANNING_BOUNDARY}"
    )


if not HYDROLOGIC_CONTEXT_CSV.exists():

    raise FileNotFoundError(
        "Hydrologic context CSV not found:\n"
        f"{HYDROLOGIC_CONTEXT_CSV}"
    )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_name(value):

    value = str(
        value
    )

    value = re.sub(
        r"[^A-Za-z0-9_]+",
        "_",
        value
    )

    return value[:50]


def delete_if_exists(path):

    if arcpy.Exists(
        path
    ):

        arcpy.management.Delete(
            path
        )


def raster_values(
    raster_path,
    include_zero=True
):

    array = (
        arcpy.RasterToNumPyArray(
            raster_path,
            nodata_to_value=-9999
        )
    )

    values = array[
        np.isfinite(
            array
        )
        & (
            array != -9999
        )
    ]

    if not include_zero:

        values = values[
            values > 0
        ]

    return values.astype(
        np.float64
    )


def clip_raster_to_polygon(
    in_raster,
    polygon_fc,
    out_raster
):

    delete_if_exists(
        out_raster
    )

    arcpy.management.Clip(
        in_raster=in_raster,
        rectangle="#",
        out_raster=out_raster,
        in_template_dataset=polygon_fc,
        nodata_value="-9999",
        clipping_geometry="ClippingGeometry",
        maintain_clipping_extent="NO_MAINTAIN_EXTENT"
    )


def summarize_class_values(
    class_values,
    raw_values
):

    valid_classes = (
        class_values[
            class_values >= 0
        ]
    )

    total_cells = len(
        valid_classes
    )

    if total_cells == 0:

        return None


    counts = {}

    for class_value in [
        0,
        1,
        2,
        3,
        4
    ]:

        counts[
            class_value
        ] = int(
            np.sum(
                valid_classes
                == class_value
            )
        )


    def pct(
        class_value
    ):

        return (
            counts[
                class_value
            ]
            / total_cells
            * 100.0
        )


    high_highest_count = (
        counts[3]
        + counts[4]
    )

    high_highest_pct = (
        high_highest_count
        / total_cells
        * 100.0
    )


    raw_valid = (
        raw_values[
            np.isfinite(
                raw_values
            )
            & (
                raw_values
                >= 0
            )
        ]
    )


    if len(
        raw_valid
    ) > 0:

        raw_mean = float(
            np.mean(
                raw_valid
            )
        )

        raw_median = float(
            np.median(
                raw_valid
            )
        )

        raw_p90 = float(
            np.percentile(
                raw_valid,
                90
            )
        )

        raw_max = float(
            np.max(
                raw_valid
            )
        )

    else:

        raw_mean = None
        raw_median = None
        raw_p90 = None
        raw_max = None


    return {
        "cell_count":
            total_cells,

        "zero_cells":
            counts[0],

        "lower_cells":
            counts[1],

        "moderate_cells":
            counts[2],

        "high_cells":
            counts[3],

        "highest_cells":
            counts[4],

        "zero_pct":
            pct(0),

        "lower_pct":
            pct(1),

        "moderate_pct":
            pct(2),

        "high_pct":
            pct(3),

        "highest_pct":
            pct(4),

        "high_highest_pct":
            high_highest_pct,

        "raw_mean":
            raw_mean,

        "raw_median":
            raw_median,

        "raw_p90":
            raw_p90,

        "raw_max":
            raw_max,
    }


# ============================================================
# READ HYDROLOGIC RELATIONSHIPS
# ============================================================

print(
    "Loading hydrologic relationships..."
)

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

        relationship = str(
            row.get(
                "relationship",
                ""
            )
        ).strip()


        if huc12_id:

            hydrologic_relationships[
                huc12_id
            ] = relationship


print(
    f"Hydrologic relationships loaded: "
    f"{len(hydrologic_relationships)}"
)


for (
    huc12_id,
    relationship
) in hydrologic_relationships.items():

    print(
        f"  {huc12_id}: "
        f"{relationship}"
    )


print()


# ============================================================
# STEP 1
# CALCULATE STATEWIDE NONZERO DISTRIBUTION
# ============================================================

print(
    "1. Calculating statewide nonzero distribution..."
)


state_values = raster_values(
    SOURCE_RASTER,
    include_zero=False
)


if len(
    state_values
) == 0:

    raise RuntimeError(
        "No nonzero statewide raster values were found."
    )


P50 = float(
    np.percentile(
        state_values,
        50
    )
)

P75 = float(
    np.percentile(
        state_values,
        75
    )
)

P90 = float(
    np.percentile(
        state_values,
        90
    )
)


print()
print(
    f"Statewide nonzero cells: "
    f"{len(state_values):,}"
)

print(
    f"P50: {P50:.6f}"
)

print(
    f"P75: {P75:.6f}"
)

print(
    f"P90: {P90:.6f}"
)

print()


# ============================================================
# WRITE STATEWIDE BREAKS
# ============================================================

with STATEWIDE_BREAKS_CSV.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.writer(
        f
    )

    writer.writerow(
        [
            "class_value",
            "class_name",
            "lower_bound",
            "upper_bound",
            "rule",
        ]
    )

    writer.writerow(
        [
            0,
            "Zero",
            0,
            0,
            "value = 0",
        ]
    )

    writer.writerow(
        [
            1,
            "Lower",
            0,
            P50,
            "0 < value <= statewide nonzero P50",
        ]
    )

    writer.writerow(
        [
            2,
            "Moderate",
            P50,
            P75,
            "P50 < value <= statewide nonzero P75",
        ]
    )

    writer.writerow(
        [
            3,
            "High",
            P75,
            P90,
            "P75 < value <= statewide nonzero P90",
        ]
    )

    writer.writerow(
        [
            4,
            "Highest",
            P90,
            1,
            "value > statewide nonzero P90",
        ]
    )


# ============================================================
# STEP 2
# CLIP RAW SOURCE TO POST-FIRE ANALYSIS AREA
# ============================================================

print(
    "2. Clipping threat surface to "
    "post-fire analysis area..."
)


clip_raster_to_polygon(
    SOURCE_RASTER,
    POST_FIRE_ANALYSIS_FC,
    CLIPPED_RAW_RASTER
)


# ============================================================
# STEP 3
# CLASSIFY USING STATEWIDE BREAKS
# ============================================================

print(
    "3. Creating statewide threat classes..."
)


source_raster = arcpy.Raster(
    CLIPPED_RAW_RASTER
)

source_desc = arcpy.Describe(
    CLIPPED_RAW_RASTER
)


raw_array = (
    arcpy.RasterToNumPyArray(
        CLIPPED_RAW_RASTER,
        nodata_to_value=-9999
    )
)


class_array = np.full(
    raw_array.shape,
    255,
    dtype=np.uint8
)


valid_mask = (
    np.isfinite(
        raw_array
    )
    & (
        raw_array
        != -9999
    )
)


class_array[
    valid_mask
    & (
        raw_array
        == 0
    )
] = 0


class_array[
    valid_mask
    & (
        raw_array
        > 0
    )
    & (
        raw_array
        <= P50
    )
] = 1


class_array[
    valid_mask
    & (
        raw_array
        > P50
    )
    & (
        raw_array
        <= P75
    )
] = 2


class_array[
    valid_mask
    & (
        raw_array
        > P75
    )
    & (
        raw_array
        <= P90
    )
] = 3


class_array[
    valid_mask
    & (
        raw_array
        > P90
    )
] = 4


lower_left = arcpy.Point(
    source_desc.extent.XMin,
    source_desc.extent.YMin
)


classified = (
    arcpy.NumPyArrayToRaster(
        class_array,
        lower_left,
        source_raster.meanCellWidth,
        source_raster.meanCellHeight,
        value_to_nodata=255
    )
)


delete_if_exists(
    CLASSIFIED_RASTER
)


classified.save(
    CLASSIFIED_RASTER
)


arcpy.management.DefineProjection(
    CLASSIFIED_RASTER,
    source_desc.spatialReference
)


print(
    f"Created:\n"
    f"{CLASSIFIED_RASTER}"
)

print()


# ============================================================
# STEP 4
# PREPARE PLANNING BOUNDARY
# ============================================================

planning_fc = str(
    TEMP_GDB
    / "planning_area"
)


delete_if_exists(
    planning_fc
)


arcpy.conversion.JSONToFeatures(
    str(
        PLANNING_BOUNDARY
    ),
    planning_fc
)


# ============================================================
# HELPER
# SUMMARIZE ONE POLYGON UNIT
# ============================================================

def summarize_polygon_unit(
    polygon_fc,
    unit_type,
    unit_id,
    unit_name,
    relationship
):

    safe_id = safe_name(
        f"{unit_type}_{unit_id}"
    )


    temp_raw = str(
        PROCESSED_DIR
        / f"_tmp_raw_{safe_id}.tif"
    )

    temp_class = str(
        PROCESSED_DIR
        / f"_tmp_class_{safe_id}.tif"
    )


    clip_raster_to_polygon(
        CLIPPED_RAW_RASTER,
        polygon_fc,
        temp_raw
    )

    clip_raster_to_polygon(
        CLASSIFIED_RASTER,
        polygon_fc,
        temp_class
    )


    raw_array = (
        arcpy.RasterToNumPyArray(
            temp_raw,
            nodata_to_value=-9999
        )
    )

    class_array = (
        arcpy.RasterToNumPyArray(
            temp_class,
            nodata_to_value=-1
        )
    )


    raw_values = (
        raw_array[
            np.isfinite(
                raw_array
            )
            & (
                raw_array
                != -9999
            )
        ]
    )

    class_values = (
        class_array[
            np.isfinite(
                class_array
            )
            & (
                class_array
                != -1
            )
        ]
    )


    stats = summarize_class_values(
        class_values,
        raw_values
    )


    delete_if_exists(
        temp_raw
    )

    delete_if_exists(
        temp_class
    )


    if stats is None:

        return None


    cell_area_sq_m = (
        source_raster.meanCellWidth
        * source_raster.meanCellHeight
    )

    sq_m_per_acre = (
        4046.8564224
    )


    stats.update(
        {
            "unit_type":
                unit_type,

            "unit_id":
                unit_id,

            "unit_name":
                unit_name,

            "relationship":
                relationship,

            "total_raster_acres":
                (
                    stats[
                        "cell_count"
                    ]
                    * cell_area_sq_m
                    / sq_m_per_acre
                ),

            "high_highest_acres":
                (
                    (
                        stats[
                            "high_cells"
                        ]
                        + stats[
                            "highest_cells"
                        ]
                    )
                    * cell_area_sq_m
                    / sq_m_per_acre
                ),
        }
    )


    return stats


# ============================================================
# STEP 5
# SUMMARIZE PLANNING AREA
# ============================================================

print(
    "4. Summarizing planning area..."
)


planning_stats = (
    summarize_polygon_unit(
        planning_fc,
        "planning_area",
        PLANNING_HUC10,
        PLANNING_HUC_NAME,
        "planning"
    )
)


if planning_stats is None:

    raise RuntimeError(
        "Unable to summarize planning-area threat."
    )


# ============================================================
# STEP 6
# SUMMARIZE INTERNAL HUC12 UNITS
# ============================================================

print(
    "5. Summarizing internal HUC12 units..."
)


unit_rows = []


field_lookup = {
    field.name.upper():
        field.name
    for field in arcpy.ListFields(
        HUC12_FC
    )
}


HUC12_FIELD = (
    field_lookup[
        "HUC12"
    ]
)

NAME_FIELD = (
    field_lookup[
        "NAME"
    ]
)


with arcpy.da.SearchCursor(
    HUC12_FC,
    [
        HUC12_FIELD,
        NAME_FIELD,
        "SHAPE@",
    ]
) as cursor:

    for (
        huc12_id,
        huc12_name,
        geometry
    ) in cursor:

        huc12_id = str(
            huc12_id
        )


        if not huc12_id.startswith(
            PLANNING_HUC10
        ):

            continue


        temp_fc = str(
            TEMP_GDB
            / safe_name(
                f"huc12_{huc12_id}"
            )
        )


        delete_if_exists(
            temp_fc
        )


        arcpy.management.CopyFeatures(
            [
                geometry
            ],
            temp_fc
        )


        stats = summarize_polygon_unit(
            temp_fc,
            "huc12",
            huc12_id,
            huc12_name,
            "inside_planning_area"
        )


        if stats:

            unit_rows.append(
                stats
            )


        delete_if_exists(
            temp_fc
        )


# ============================================================
# STEP 7
# SUMMARIZE CONNECTED EXTERNAL HUC12 UNITS
# ============================================================

print(
    "6. Summarizing connected external HUC12 units..."
)


context_field_lookup = {
    field.name.upper():
        field.name
    for field in arcpy.ListFields(
        HYDROLOGIC_CONTEXT_FC
    )
}


CONTEXT_HUC_FIELD = (
    context_field_lookup[
        "HUC12"
    ]
)

CONTEXT_NAME_FIELD = (
    context_field_lookup[
        "NAME"
    ]
)


with arcpy.da.SearchCursor(
    HYDROLOGIC_CONTEXT_FC,
    [
        CONTEXT_HUC_FIELD,
        CONTEXT_NAME_FIELD,
        "SHAPE@",
    ]
) as cursor:

    for (
        huc12_id,
        huc12_name,
        geometry
    ) in cursor:

        huc12_id = str(
            huc12_id
        )


        relationship = (
            hydrologic_relationships.get(
                huc12_id,
                "hydrologic_context"
            )
        )


        print(
            f"  {huc12_id} — "
            f"{huc12_name}: "
            f"{relationship}"
        )


        temp_fc = str(
            TEMP_GDB
            / safe_name(
                f"context_{huc12_id}"
            )
        )


        delete_if_exists(
            temp_fc
        )


        arcpy.management.CopyFeatures(
            [
                geometry
            ],
            temp_fc
        )


        stats = summarize_polygon_unit(
            temp_fc,
            "huc12",
            huc12_id,
            huc12_name,
            relationship
        )


        if stats:

            unit_rows.append(
                stats
            )


        delete_if_exists(
            temp_fc
        )


# ============================================================
# WRITE PLANNING SUMMARY
# ============================================================

summary_fields = [
    "unit_type",
    "unit_id",
    "unit_name",
    "relationship",
    "cell_count",
    "total_raster_acres",
    "raw_mean",
    "raw_median",
    "raw_p90",
    "raw_max",
    "zero_pct",
    "lower_pct",
    "moderate_pct",
    "high_pct",
    "highest_pct",
    "high_highest_pct",
    "high_highest_acres",
]


with PLANNING_SUMMARY_CSV.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=summary_fields
    )

    writer.writeheader()

    writer.writerow(
        {
            field:
                planning_stats.get(
                    field
                )
            for field in summary_fields
        }
    )


# ============================================================
# WRITE BY-UNIT SUMMARY
# ============================================================

with BY_UNIT_CSV.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=summary_fields
    )

    writer.writeheader()

    for row in unit_rows:

        writer.writerow(
            {
                field:
                    row.get(
                        field
                    )
                for field in summary_fields
            }
        )


# ============================================================
# IDENTIFY KEY FINDINGS
# ============================================================

internal_rows = [
    row
    for row in unit_rows
    if row[
        "relationship"
    ]
    == "inside_planning_area"
]


context_rows = [
    row
    for row in unit_rows
    if row[
        "relationship"
    ]
    != "inside_planning_area"
]


if internal_rows:

    highest_internal = max(
        internal_rows,
        key=lambda row:
            row[
                "high_highest_pct"
            ]
    )

else:

    highest_internal = None


downstream_rows = [
    row
    for row in context_rows
    if "downstream"
    in str(
        row[
            "relationship"
        ]
    ).lower()
]


upstream_rows = [
    row
    for row in context_rows
    if "upstream"
    in str(
        row[
            "relationship"
        ]
    ).lower()
]


# ============================================================
# BUILD STANDARDIZED FINDINGS
# ============================================================

findings = []


# ------------------------------------------------------------
# FINDING 1
# PLANNING AREA SOURCE THREAT
# ------------------------------------------------------------

findings.append(
    {
        "finding_id":
            "post_fire_threat_planning_area",

        "indicator_id":
            "post_fire_erosion_threat",

        "decision_stage":
            "threat",

        "finding_name":
            (
                "Post-fire source threat occurs "
                "within the planning watershed"
            ),

        "question":
            (
                "Where could post-fire effects originate?"
            ),

        "result":
            (
                f"{planning_stats['high_highest_pct']:.1f}% "
                f"of mapped cells in the planning area are "
                f"High or Highest relative to the statewide "
                f"nonzero distribution."
            ),

        "interpretation":
            (
                f"The {PLANNING_HUC_NAME} planning watershed "
                f"contains areas of elevated modeled annual "
                f"post-fire debris-flow threat."
            ),

        "confidence":
            "moderate",

        "status":
            "supported",

        "evidence":
            (
                "NMFAP 2020 annual post-fire debris-flow "
                "hazard classified using statewide nonzero "
                "percentile thresholds."
            ),

        "caveat":
            (
                "The layer identifies modeled source threat. "
                "It does not predict event-specific debris-flow "
                "runout, sediment delivery, travel distance, "
                "or downstream impact."
            ),

        "source_ids":
            "nmfap_postfire",
    }
)


# ------------------------------------------------------------
# FINDING 2
# INTERNAL CONCENTRATION
# ------------------------------------------------------------

if highest_internal:

    findings.append(
        {
            "finding_id":
                "post_fire_threat_internal_concentration",

            "indicator_id":
                "post_fire_erosion_threat",

            "decision_stage":
                "threat",

            "finding_name":
                (
                    "Elevated post-fire source threat is "
                    "concentrated within specific HUC12s"
                ),

            "question":
                (
                    "Where within the planning watershed "
                    "is post-fire source threat concentrated?"
                ),

            "result":
                (
                    f"{highest_internal['unit_id']} — "
                    f"{highest_internal['unit_name']} has "
                    f"{highest_internal['high_highest_pct']:.1f}% "
                    f"of mapped cells in the statewide "
                    f"High or Highest classes."
                ),

            "interpretation":
                (
                    f"{highest_internal['unit_name']} has the "
                    f"greatest concentration of statewide High "
                    f"and Highest post-fire source threat among "
                    f"internal HUC12 units."
                ),

            "confidence":
                "moderate",

            "status":
                "supported",

            "evidence":
                (
                    "Statewide-classified NMFAP annual "
                    "post-fire debris-flow threat summarized "
                    "by internal HUC12."
                ),

            "caveat":
                (
                    "Threat concentration does not by itself "
                    "indicate downstream consequence or "
                    "treatment priority."
                ),

            "source_ids":
                "nmfap_postfire+wbd",
        }
    )


# ------------------------------------------------------------
# FINDING 3
# UPSTREAM CONTEXT
# ------------------------------------------------------------

if upstream_rows:

    names = "; ".join(
        [
            (
                f"{row['unit_id']} — "
                f"{row['unit_name']}"
            )
            for row in upstream_rows
        ]
    )


    findings.append(
        {
            "finding_id":
                "post_fire_threat_upstream_context",

            "indicator_id":
                "post_fire_erosion_threat",

            "decision_stage":
                "connection",

            "finding_name":
                (
                    "External upstream source areas are "
                    "hydrologically connected to the planning area"
                ),

            "question":
                (
                    "Can post-fire source threat originate "
                    "outside the planning area and drain into it?"
                ),

            "result":
                names,

            "interpretation":
                (
                    "The configured upstream HUC12 context "
                    "contains external source areas that drain "
                    "directly toward the planning watershed."
                ),

            "confidence":
                "high",

            "status":
                "supported",

            "evidence":
                (
                    "WBD HUC12 ToHUC relationships combined "
                    "with NMFAP post-fire source threat."
                ),

            "caveat":
                (
                    "Hydrologic network connection does not "
                    "establish actual debris-flow runout or "
                    "sediment delivery."
                ),

            "source_ids":
                "nmfap_postfire+wbd",
        }
    )

else:

    findings.append(
        {
            "finding_id":
                "post_fire_threat_upstream_context",

            "indicator_id":
                "post_fire_erosion_threat",

            "decision_stage":
                "connection",

            "finding_name":
                (
                    "No immediate external upstream HUC12 "
                    "source area was identified"
                ),

            "question":
                (
                    "Can post-fire source threat originate "
                    "outside the planning area and drain into it?"
                ),

            "result":
                (
                    "No external immediate-upstream HUC12 "
                    "was identified under the configured "
                    "one-level WBD relationship."
                ),

            "interpretation":
                (
                    "For the current El Rito prototype, the "
                    "immediate post-fire source analysis is "
                    "focused primarily within the planning "
                    "watershed rather than an external upstream "
                    "HUC12."
                ),

            "confidence":
                "high",

            "status":
                "supported",

            "evidence":
                (
                    "Configured WBD HUC12 hydrologic context."
                ),

            "caveat":
                (
                    "This does not mean there is no upstream "
                    "terrain or source threat within El Rito. "
                    "It means no external immediate-upstream "
                    "HUC12 was identified under the current "
                    "bounded network rule."
                ),

            "source_ids":
                "wbd",
        }
    )


# ------------------------------------------------------------
# FINDING 4
# DOWNSTREAM CONNECTION
# ------------------------------------------------------------

if downstream_rows:

    downstream = (
        downstream_rows[0]
    )


    findings.append(
        {
            "finding_id":
                "post_fire_threat_downstream_connection",

            "indicator_id":
                "post_fire_erosion_threat",

            "decision_stage":
                "connection",

            "finding_name":
                (
                    f"Post-fire effects originating in "
                    f"{PLANNING_HUC_NAME} are hydrologically "
                    f"connected downstream"
                ),

            "question":
                (
                    "Where could effects originating in the "
                    "planning watershed continue downstream?"
                ),

            "result":
                (
                    f"{downstream['unit_id']} — "
                    f"{downstream['unit_name']}"
                ),

            "interpretation":
                (
                    f"The {PLANNING_HUC_NAME} watershed drains "
                    f"to {downstream['unit_name']}, making that "
                    f"HUC12 the first external downstream unit "
                    f"potentially connected to post-fire effects "
                    f"originating within the planning watershed."
                ),

            "confidence":
                "high",

            "status":
                "supported",

            "evidence":
                (
                    "WBD HUC12 downstream relationship combined "
                    "with mapped NMFAP post-fire source threat."
                ),

            "caveat":
                (
                    "This identifies hydrologic connection, "
                    "not event-specific debris-flow runout, "
                    "sediment delivery, impact magnitude, "
                    "travel time, or probability of damage."
                ),

            "source_ids":
                "nmfap_postfire+wbd",
        }
    )


# ============================================================
# WRITE FINDINGS
# ============================================================

finding_fields = [
    "finding_id",
    "indicator_id",
    "decision_stage",
    "finding_name",
    "question",
    "result",
    "interpretation",
    "confidence",
    "status",
    "evidence",
    "caveat",
    "source_ids",
]


with FINDINGS_CSV.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=finding_fields
    )

    writer.writeheader()

    writer.writerows(
        findings
    )


# ============================================================
# REPORT RESULTS
# ============================================================

print()
print(
    "Post-fire analysis complete"
)
print(
    "==========================="
)

print()

print(
    "Statewide classes:"
)

print(
    "  0 = Zero"
)

print(
    f"  1 = Lower: >0 to {P50:.6f}"
)

print(
    f"  2 = Moderate: "
    f"{P50:.6f} to {P75:.6f}"
)

print(
    f"  3 = High: "
    f"{P75:.6f} to {P90:.6f}"
)

print(
    f"  4 = Highest: "
    f">{P90:.6f}"
)

print()

print(
    f"{PLANNING_HUC_NAME}:"
)

print(
    f"  High: "
    f"{planning_stats['high_pct']:.1f}%"
)

print(
    f"  Highest: "
    f"{planning_stats['highest_pct']:.1f}%"
)

print(
    f"  High + Highest: "
    f"{planning_stats['high_highest_pct']:.1f}%"
)

print()


if highest_internal:

    print(
        "Highest internal HUC12 concentration:"
    )

    print(
        f"  {highest_internal['unit_id']} — "
        f"{highest_internal['unit_name']}"
    )

    print(
        f"  High + Highest: "
        f"{highest_internal['high_highest_pct']:.1f}%"
    )

    print()


if upstream_rows:

    print(
        "Immediate upstream connections:"
    )

    for row in upstream_rows:

        print(
            f"  {row['unit_id']} — "
            f"{row['unit_name']}"
        )

    print()

else:

    print(
        "Immediate upstream connections:"
    )

    print(
        "  None identified."
    )

    print()


if downstream_rows:

    print(
        "Immediate downstream connection:"
    )

    for row in downstream_rows:

        print(
            f"  {row['unit_id']} — "
            f"{row['unit_name']}"
        )

    print()


print(
    f"Findings written: "
    f"{len(findings)}"
)

print()

print(
    "Outputs:"
)

print(
    STATEWIDE_BREAKS_CSV
)

print(
    CLIPPED_RAW_RASTER
)

print(
    CLASSIFIED_RASTER
)

print(
    PLANNING_SUMMARY_CSV
)

print(
    BY_UNIT_CSV
)

print(
    FINDINGS_CSV
)

print()