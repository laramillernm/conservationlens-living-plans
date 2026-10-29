from pathlib import Path
import arcpy


PROJECT_ROOT = Path(
    r"C:\Users\Lara\ConservationInsights\conservationlens-living-plans"
)

EL_RITO = (
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

HUC10 = str(WBD_GDB / "WBDHU10")
HUC8 = str(WBD_GDB / "WBDHU8")


print()
print("ConservationLens HUC context check")
print("==================================")
print()


# ------------------------------------------------------------
# TEMP GEODATABASE
# ------------------------------------------------------------

TEMP_GDB = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hydrology"
    / "huc_context_temp.gdb"
)

TEMP_GDB.parent.mkdir(
    parents=True,
    exist_ok=True
)

if not arcpy.Exists(str(TEMP_GDB)):
    arcpy.management.CreateFileGDB(
        str(TEMP_GDB.parent),
        TEMP_GDB.name
    )


# ------------------------------------------------------------
# CONVERT EL RITO GEOJSON
# ------------------------------------------------------------

el_rito_fc = str(
    TEMP_GDB / "el_rito_boundary"
)

if arcpy.Exists(el_rito_fc):
    arcpy.management.Delete(el_rito_fc)

arcpy.conversion.JSONToFeatures(
    str(EL_RITO),
    el_rito_fc
)


# ------------------------------------------------------------
# EL RITO TOTAL AREA
# ------------------------------------------------------------

el_rito_acres = 0

with arcpy.da.SearchCursor(
    el_rito_fc,
    ["SHAPE@"]
) as cursor:

    for geometry, in cursor:

        el_rito_acres += geometry.getArea(
            "GEODESIC",
            "ACRES"
        )


print(
    f"El Rito planning area: "
    f"{el_rito_acres:,.1f} acres"
)
print()


# ------------------------------------------------------------
# SELECT INTERSECTING HUC10S
# ------------------------------------------------------------

huc10_layer = "huc10_layer"

arcpy.management.MakeFeatureLayer(
    HUC10,
    huc10_layer
)

arcpy.management.SelectLayerByLocation(
    huc10_layer,
    "INTERSECT",
    el_rito_fc
)


selected_huc10_fc = str(
    TEMP_GDB / "selected_huc10"
)

if arcpy.Exists(selected_huc10_fc):
    arcpy.management.Delete(
        selected_huc10_fc
    )

arcpy.management.CopyFeatures(
    huc10_layer,
    selected_huc10_fc
)


# ------------------------------------------------------------
# INTERSECT WITH EL RITO
# ------------------------------------------------------------

overlap_fc = str(
    TEMP_GDB / "el_rito_huc10_overlap"
)

if arcpy.Exists(overlap_fc):
    arcpy.management.Delete(overlap_fc)

arcpy.analysis.Intersect(
    [
        el_rito_fc,
        selected_huc10_fc
    ],
    overlap_fc
)


# ------------------------------------------------------------
# CALCULATE OVERLAP
# ------------------------------------------------------------

results = []


with arcpy.da.SearchCursor(
    overlap_fc,
    [
        "HUC10",
        "NAME",
        "SHAPE@"
    ]
) as cursor:

    for (
        huc10_code,
        name,
        geometry
    ) in cursor:

        acres = geometry.getArea(
            "GEODESIC",
            "ACRES"
        )

        percent = (
            acres
            / el_rito_acres
            * 100
        )

        results.append(
            (
                str(huc10_code),
                name,
                acres,
                percent
            )
        )


results.sort(
    key=lambda x: x[2],
    reverse=True
)


print("HUC10 overlap with El Rito:")
print()


for (
    huc10_code,
    name,
    acres,
    percent
) in results:

    print(
        f"{huc10_code} — {name}"
    )

    print(
        f"  Overlap acres: "
        f"{acres:,.1f}"
    )

    print(
        f"  Percent of planning area: "
        f"{percent:.1f}%"
    )

    print()


# ------------------------------------------------------------
# DOMINANT HUC10
# ------------------------------------------------------------

if results:

    dominant = results[0]

    dominant_huc10 = dominant[0]
    dominant_name = dominant[1]

    parent_huc8 = (
        dominant_huc10[:8]
    )

    print("Dominant HUC10:")
    print(
        f"  {dominant_huc10} — "
        f"{dominant_name}"
    )

    print()

    print("Parent HUC8:")

    with arcpy.da.SearchCursor(
        HUC8,
        [
            "HUC8",
            "NAME"
        ]
    ) as cursor:

        for (
            huc8_code,
            huc8_name
        ) in cursor:

            if (
                str(huc8_code)
                == parent_huc8
            ):

                print(
                    f"  {huc8_code} — "
                    f"{huc8_name}"
                )


print()
print("Done.")