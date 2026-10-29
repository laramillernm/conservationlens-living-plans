from pathlib import Path
import arcpy


PROJECT_ROOT = Path(
    r"C:\Users\Lara\ConservationInsights\conservationlens-living-plans"
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

PLANNING_HUC10 = "1302010216"
PLANNING_NAME = "Rio del Oso-Rio Chama"

PARENT_HUC8 = "13020102"


print()
print("Test immediate-upstream HUC12 logic")
print("===================================")
print()

print(
    f"Planning HUC10: "
    f"{PLANNING_HUC10} — {PLANNING_NAME}"
)

print(
    f"Parent HUC8: {PARENT_HUC8}"
)

print()


# ------------------------------------------------------------
# FIND FIELD NAMES
# ------------------------------------------------------------

fields = {
    f.name.upper(): f.name
    for f in arcpy.ListFields(HUC12)
}

FIELD_HUC12 = fields["HUC12"]
FIELD_NAME = fields["NAME"]
FIELD_TOHUC = fields["TOHUC"]


# ------------------------------------------------------------
# HUC12S INSIDE PLANNING HUC10
# ------------------------------------------------------------

planning_huc12s = {}


with arcpy.da.SearchCursor(
    HUC12,
    [
        FIELD_HUC12,
        FIELD_NAME,
        FIELD_TOHUC,
    ]
) as cursor:

    for (
        huc12_code,
        name,
        tohuc
    ) in cursor:

        huc12_code = str(
            huc12_code
        )

        if huc12_code.startswith(
            PLANNING_HUC10
        ):

            planning_huc12s[
                huc12_code
            ] = {
                "name": name,
                "tohuc": (
                    str(tohuc)
                    if tohuc
                    else ""
                ),
            }


print(
    f"HUC12s inside planning HUC10: "
    f"{len(planning_huc12s)}"
)

print()


for code, info in sorted(
    planning_huc12s.items()
):

    print(
        f"{code} — {info['name']}"
    )

    print(
        f"  ToHUC: {info['tohuc']}"
    )

    print()


# ------------------------------------------------------------
# FIND EXTERNAL HUC12S WHOSE TOHUC
# POINTS INTO PLANNING HUC10
# ------------------------------------------------------------

external_upstream = []


with arcpy.da.SearchCursor(
    HUC12,
    [
        FIELD_HUC12,
        FIELD_NAME,
        FIELD_TOHUC,
    ]
) as cursor:

    for (
        huc12_code,
        name,
        tohuc
    ) in cursor:

        huc12_code = str(
            huc12_code
        )

        tohuc = (
            str(tohuc)
            if tohuc
            else ""
        )


        # only search within parent HUC8
        if not huc12_code.startswith(
            PARENT_HUC8
        ):
            continue


        # exclude HUC12s already inside planning HUC10
        if huc12_code.startswith(
            PLANNING_HUC10
        ):
            continue


        # keep candidates draining directly
        # into a planning HUC12
        if tohuc in planning_huc12s:

            external_upstream.append(
                (
                    huc12_code,
                    name,
                    tohuc,
                    planning_huc12s[
                        tohuc
                    ]["name"]
                )
            )


print()
print(
    "External HUC12s draining directly "
    "into planning HUC10:"
)

print()


if not external_upstream:

    print("None found.")

else:

    for (
        code,
        name,
        tohuc,
        receiving_name
    ) in sorted(
        external_upstream
    ):

        print(
            f"{code} — {name}"
        )

        print(
            f"  Drains to: "
            f"{tohuc} — "
            f"{receiving_name}"
        )

        print()


print()
print(
    f"Total external immediate upstream HUC12s: "
    f"{len(external_upstream)}"
)

print()
print("Done.")
