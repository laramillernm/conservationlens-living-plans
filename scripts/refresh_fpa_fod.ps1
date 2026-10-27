# ============================================================
# ConservationLens Living Plans
# Refresh Karen Short FPA FOD fire-occurrence data
#
# Mode 2:
# live service -> local dated snapshot -> current local copy
#
# IMPORTANT:
# A failed refresh never overwrites the existing current data.
# ============================================================

$ErrorActionPreference = "Stop"


# ------------------------------------------------------------
# PROJECT SETTINGS
# ------------------------------------------------------------

$ProjectRoot = "C:\Users\Lara\ConservationInsights\conservationlens-living-plans"

$RawDir = Join-Path `
    $ProjectRoot `
    "data\raw\fire_history\fpa_fod"

$SnapshotDate = Get-Date -Format "yyyy-MM-dd"

$SnapshotDir = Join-Path `
    $RawDir `
    "snapshots\$SnapshotDate"

$CurrentFile = Join-Path `
    $RawDir `
    "fpa_fod_el_rito_current.geojson"

$SnapshotFile = Join-Path `
    $SnapshotDir `
    "fpa_fod_el_rito.geojson"

$MetadataFile = Join-Path `
    $RawDir `
    "fpa_fod_refresh.txt"


New-Item `
    -ItemType Directory `
    -Force `
    -Path $RawDir |
    Out-Null

New-Item `
    -ItemType Directory `
    -Force `
    -Path $SnapshotDir |
    Out-Null


# ------------------------------------------------------------
# KAREN SHORT FPA FOD CURRENT EDITION
# ------------------------------------------------------------

$LayerUrl = `
"https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_FireOccurrenceCurrentEdition_01/MapServer/0"

$QueryUrl = "$LayerUrl/query"


# ------------------------------------------------------------
# RETRY FUNCTION
# ------------------------------------------------------------

function Invoke-RestWithRetry {

    param(
        [string]$Uri,
        [int]$MaxAttempts = 4
    )

    for ($Attempt = 1; $Attempt -le $MaxAttempts; $Attempt++) {

        try {

            return Invoke-RestMethod `
                -Uri $Uri `
                -Method Get `
                -ErrorAction Stop

        }
        catch {

            Write-Host ""
            Write-Host "Request attempt $Attempt failed:"
            Write-Host $_.Exception.Message

            if ($Attempt -eq $MaxAttempts) {

                throw `
                    "Unable to reach the FPA FOD service after $MaxAttempts attempts. Existing local data were NOT replaced."

            }

            Start-Sleep -Seconds (2 * $Attempt)

        }
    }
}


# ------------------------------------------------------------
# EL RITO BOUNDARY
# ------------------------------------------------------------

$BoundaryXMin = -106.32656831835307
$BoundaryYMin = 36.19707315294957
$BoundaryXMax = -106.122654668704
$BoundaryYMax = 36.615471739709925


# ------------------------------------------------------------
# 20 KM FIRE-LANDSCAPE CONTEXT
# ------------------------------------------------------------

$ContextBufferKm = 20

$LatBuffer = $ContextBufferKm / 111.0
$LonBuffer = $ContextBufferKm / 90.0

$XMin = $BoundaryXMin - $LonBuffer
$YMin = $BoundaryYMin - $LatBuffer
$XMax = $BoundaryXMax + $LonBuffer
$YMax = $BoundaryYMax + $LatBuffer


# ------------------------------------------------------------
# ESRI ENVELOPE — NAD83 / EPSG:4269
# ------------------------------------------------------------

$EnvelopeObject = @{

    xmin = $XMin
    ymin = $YMin
    xmax = $XMax
    ymax = $YMax

    spatialReference = @{
        wkid = 4269
    }
}

$Envelope = (
    $EnvelopeObject |
    ConvertTo-Json -Compress
)


Write-Host ""
Write-Host "Karen Short FPA FOD refresh"
Write-Host "==========================="
Write-Host ""

Write-Host "Context buffer: $ContextBufferKm km"
Write-Host "XMin: $XMin"
Write-Host "YMin: $YMin"
Write-Host "XMax: $XMax"
Write-Host "YMax: $YMax"
Write-Host ""


# ------------------------------------------------------------
# CHECK CURRENT SERVICE METADATA
# ------------------------------------------------------------

Write-Host "Checking current FPA FOD service..."

$MetadataUrl = "$LayerUrl`?f=json"

$ServiceMetadata = Invoke-RestWithRetry `
    -Uri $MetadataUrl

if ($null -ne $ServiceMetadata.error) {

    throw (
        "FPA FOD metadata service returned an error: " +
        ($ServiceMetadata.error | ConvertTo-Json -Compress)
    )
}

$LayerName = $ServiceMetadata.name

Write-Host "Connected."
Write-Host "Layer: $LayerName"
Write-Host ""


# ------------------------------------------------------------
# FIRST GET THE EXPECTED RECORD COUNT
# ------------------------------------------------------------

Write-Host "Checking number of records available..."

$CountParameters = @{

    f = "json"

    where = "1=1"

    geometry = $Envelope

    geometryType = "esriGeometryEnvelope"

    inSR = "4269"

    spatialRel = "esriSpatialRelIntersects"

    returnCountOnly = "true"
}


$CountQueryString = (
    $CountParameters.GetEnumerator() |
    ForEach-Object {

        $Key = $_.Key
        $Value = [string]$_.Value

        "$Key=$([uri]::EscapeDataString($Value))"
    }
) -join "&"


$CountUrl = "$QueryUrl`?$CountQueryString"

$CountResponse = Invoke-RestWithRetry `
    -Uri $CountUrl


if ($null -eq $CountResponse.count) {

    throw "The FPA FOD service did not return a valid record count."
}


$ExpectedCount = [int]$CountResponse.count

Write-Host "Expected records: $ExpectedCount"
Write-Host ""


# ------------------------------------------------------------
# FIELDS TO KEEP
# ------------------------------------------------------------

$OutFields = @(
    "fod_id",
    "fpa_id",
    "source_system_type",
    "source_system",
    "nwcg_reporting_agency",
    "nwcg_reporting_unit_name",
    "fire_name",
    "mtbs_id",
    "mtbs_fire_name",
    "fire_year",
    "discovery_date",
    "discovery_doy",
    "discovery_time",
    "nwcg_cause_classification",
    "nwcg_general_cause",
    "fire_size",
    "fire_size_class",
    "latitude",
    "longitude",
    "state",
    "county"
) -join ","


# ------------------------------------------------------------
# PAGINATED FEATURE DOWNLOAD
# ------------------------------------------------------------

$PageSize = 2000
$Offset = 0
$AllFeatures = @()


while ($Offset -lt $ExpectedCount) {

    Write-Host "Requesting records starting at offset $Offset..."


    $Parameters = @{

        f = "geojson"

        where = "1=1"

        geometry = $Envelope

        geometryType = "esriGeometryEnvelope"

        inSR = "4269"

        spatialRel = "esriSpatialRelIntersects"

        outFields = $OutFields

        returnGeometry = "true"

        outSR = "4326"

        resultOffset = "$Offset"

        resultRecordCount = "$PageSize"
    }


    $QueryString = (
        $Parameters.GetEnumerator() |
        ForEach-Object {

            $Key = $_.Key
            $Value = [string]$_.Value

            "$Key=$([uri]::EscapeDataString($Value))"
        }
    ) -join "&"


    $RequestUrl = "$QueryUrl`?$QueryString"


    $Response = Invoke-RestWithRetry `
        -Uri $RequestUrl


    if ($null -ne $Response.error) {

        throw (
            "FPA FOD query returned an error: " +
            ($Response.error | ConvertTo-Json -Compress)
        )
    }


    if ($null -eq $Response.features) {

        throw `
            "FPA FOD returned no features object. Existing current data were NOT replaced."
    }


    $Features = @(
        $Response.features
    )


    $Returned = $Features.Count

    Write-Host "Records returned this page: $Returned"


    if ($Returned -eq 0) {

        throw `
            "FPA FOD unexpectedly returned zero records before the expected count was reached."
    }


    $AllFeatures += $Features

    $Offset += $Returned
}


# ------------------------------------------------------------
# VALIDATE COMPLETE DOWNLOAD
# ------------------------------------------------------------

$RecordCount = $AllFeatures.Count


Write-Host ""
Write-Host "Expected records:   $ExpectedCount"
Write-Host "Downloaded records: $RecordCount"
Write-Host ""


if ($RecordCount -ne $ExpectedCount) {

    throw `
        "Record-count validation failed. Existing current data were NOT replaced."
}


# ------------------------------------------------------------
# BUILD GEOJSON
# ------------------------------------------------------------

$FeatureCollection = [ordered]@{

    type = "FeatureCollection"

    name = "fpa_fod_el_rito_fire_landscape"

    features = $AllFeatures
}


$JsonText = (
    $FeatureCollection |
    ConvertTo-Json -Depth 100
)


# ------------------------------------------------------------
# WRITE TEMPORARY FILE FIRST
# ------------------------------------------------------------

$TempFile = Join-Path `
    $RawDir `
    "fpa_fod_download_temp.geojson"


$JsonText |
    Set-Content `
        -Path $TempFile `
        -Encoding UTF8


# ------------------------------------------------------------
# ONLY AFTER VALIDATION:
# UPDATE CURRENT + SNAPSHOT
# ------------------------------------------------------------

Copy-Item `
    -Path $TempFile `
    -Destination $CurrentFile `
    -Force


Copy-Item `
    -Path $TempFile `
    -Destination $SnapshotFile `
    -Force


Remove-Item `
    -Path $TempFile `
    -Force


# ------------------------------------------------------------
# WRITE REFRESH METADATA
# ------------------------------------------------------------

$RefreshTime = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"


@"
source=Karen Short FPA FOD Current Edition
service=$LayerUrl
layer_name=$LayerName
refresh_time=$RefreshTime
context_buffer_km=$ContextBufferKm
record_count=$RecordCount
current_file=$CurrentFile
snapshot_file=$SnapshotFile
"@ |
    Set-Content `
        -Path $MetadataFile `
        -Encoding UTF8


# ------------------------------------------------------------
# DONE
# ------------------------------------------------------------

Write-Host ""
Write-Host "REFRESH SUCCESSFUL"
Write-Host "=================="
Write-Host ""

Write-Host "Karen Short FPA FOD records:"
Write-Host $RecordCount

Write-Host ""

Write-Host "Current dataset:"
Write-Host $CurrentFile

Write-Host ""

Write-Host "Dated snapshot:"
Write-Host $SnapshotFile