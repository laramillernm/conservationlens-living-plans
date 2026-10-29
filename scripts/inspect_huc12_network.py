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

PLANNING_HUC10 = "1302010211"
PARENT_HUC8 = "13020102"


print()
print("ConservationLens HUC12 network inspection")
print("==========================================")
print()


# ------------------------------------------------------------
# SHOW AVAILABLE FIELDS
# ------------------------------------------------------------

print("HUC12 fields:")
print()

for field in arcpy.ListFields(HUC12):
    print(field.name)

print()


# ------------------------------------------------------------
# IDENTIFY HUC12S INSIDE EL RITO HUC10
# ------------------------------------------------------------

planning_huc12s = []


with arcpy.da.SearchCursor(
    HUC12,
    [
        "HUC12",
        "NAME",
        "TOHUC"
    ]
) as cursor:

    for (
        huc12_code,
        name,
        tohuc
    ) in cursor:

        huc12_code = str(huc12_code)

        if huc12_code.startswith(
            PLANNING_HUC10
        ):

            planning_huc12s.append(
                (
                    huc12_code,
                    name,
                    str(tohuc)
                    if tohuc
                    else ""
                )
            )


planning_huc12s.sort()


print(
    f"HUC12s within El Rito HUC10 "
    f"{PLANNING_HUC10}:"
)
print()


for (
    huc12_code,
    name,
    tohuc
) in planning_huc12s:

    print(
        f"{huc12_code} — {name}"
    )

    print(
        f"  ToHUC: {tohuc}"
    )

    print()


print(
    f"Total HUC12s in planning HUC10: "
    f"{len(planning_huc12s)}"
)

print()
print("Done.")