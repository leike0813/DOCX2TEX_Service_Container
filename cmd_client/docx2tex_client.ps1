Add-Type -AssemblyName System.Net.Http | Out-Null

function New-HttpClient {
param([int]$TimeoutSec = 180)
$hc = New-Object System.Net.Http.HttpClient
$hc.Timeout = [TimeSpan]::FromSeconds($TimeoutSec)
return $hc
}
function Add-StringPart {
param(
[Parameter(Mandatory=$true)][System.Net.Http.MultipartFormDataContent]$Form,
[Parameter(Mandatory=$true)][string]$Name,
[Parameter(Mandatory=$true)][string]$Value
)
$sc = New-Object System.Net.Http.StringContent($Value)
$Form.Add($sc, $Name)
}
function Add-FilePart {
param(
[Parameter(Mandatory=$true)][System.Net.Http.MultipartFormDataContent]$Form,
[Parameter(Mandatory=$true)][string]$Name,
[Parameter(Mandatory=$true)][string]$FilePath,
[string]$ContentType = "application/octet-stream"
)
$fi = Get-Item -LiteralPath $FilePath -ErrorAction Stop
$fs = [System.IO.File]::OpenRead($fi.FullName)
$sc = New-Object System.Net.Http.StreamContent($fs)
try {
$sc.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse($ContentType)
} catch {}
$Form.Add($sc, $Name, $fi.Name)
return $fs
}

function New-Docx2TexTask {
[CmdletBinding(DefaultParameterSetName="File")]
param(
[Parameter(Mandatory=$true)][string]$Server,

[Parameter(ParameterSetName="File", Mandatory=$true)][string]$File,
[Parameter(ParameterSetName="Url" , Mandatory=$true)][string]$Url,

[Parameter()][bool]$IncludeDebug = $false,
[Parameter()][bool]$ImgPostProc = $true,

[Parameter()][string]$Conf,
[Parameter()][string]$CustomXsl,
[Parameter()][string]$StyleMap,
[Parameter()][string]$MathTypeSource,
[Parameter()][string]$TableModel,
[Parameter()][string]$FontMapsZip,
[Parameter()][string]$CustomEvolve,
[Parameter()][string]$ImageDir,
[Parameter()][bool]$NoCache = $false,

[Parameter()][int]$TimeoutSec = 300
)
$endpoint = if ($NoCache) { "$Server/v1/nocache" } else { "$Server/v1/task" }
$hc = New-HttpClient -TimeoutSec $TimeoutSec
$form = New-Object System.Net.Http.MultipartFormDataContent
$streams = New-Object System.Collections.Generic.List[System.IDisposable]
try {
if ($PSCmdlet.ParameterSetName -eq "File") {
if (-not (Test-Path -LiteralPath $File)) { throw "File not found: $File" }
if (-not $File.ToLower().EndsWith(".docx")) { throw "Only .docx is supported: $File" }
$docStream = Add-FilePart -Form $form -Name "file" -FilePath $File -ContentType "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
$streams.Add($docStream) | Out-Null
} else {
Add-StringPart -Form $form -Name "url" -Value $Url
}
Add-StringPart -Form $form -Name "debug" -Value ($IncludeDebug.ToString().ToLower())
Add-StringPart -Form $form -Name "img_post_proc" -Value ($ImgPostProc.ToString().ToLower())
if ($Conf) {
if (-not (Test-Path -LiteralPath $Conf)) { throw "Conf not found: $Conf" }
$confStream = Add-FilePart -Form $form -Name "conf" -FilePath $Conf -ContentType "application/xml"
$streams.Add($confStream) | Out-Null
}
if ($CustomXsl) {
if (-not (Test-Path -LiteralPath $CustomXsl)) { throw "CustomXsl not found: $CustomXsl" }
$xslStream = Add-FilePart -Form $form -Name "custom_xsl" -FilePath $CustomXsl -ContentType "application/xml"
$streams.Add($xslStream) | Out-Null
}
if ($StyleMap) {
  Add-StringPart -Form $form -Name "StyleMap" -Value $StyleMap
}
if ($MathTypeSource) { Add-StringPart -Form $form -Name "MathTypeSource" -Value $MathTypeSource }
if ($TableModel) { Add-StringPart -Form $form -Name "TableModel" -Value $TableModel }
if ($FontMapsZip) {
  if (-not (Test-Path -LiteralPath $FontMapsZip)) { throw "FontMapsZip not found: $FontMapsZip" }
  $fmStream = Add-FilePart -Form $form -Name "FontMapsZip" -FilePath $FontMapsZip -ContentType "application/zip"
  $streams.Add($fmStream) | Out-Null
}
if ($CustomEvolve) {
if (-not (Test-Path -LiteralPath $CustomEvolve)) { throw "CustomEvolve not found: $CustomEvolve" }
$evolveStream = Add-FilePart -Form $form -Name "custom_evolve" -FilePath $CustomEvolve -ContentType "application/xml"
  $streams.Add($evolveStream) | Out-Null
}
if ($ImageDir) {
  Add-StringPart -Form $form -Name "image_dir" -Value $ImageDir
}

$resp = $hc.PostAsync($endpoint, $form).Result
$body = $resp.Content.ReadAsStringAsync().Result
if (-not $resp.IsSuccessStatusCode) { throw "HTTP $($resp.StatusCode) $body" }
    $json = $body | ConvertFrom-Json
    $taskId = if ($json.task_id) { $json.task_id } elseif ($json.data -and $json.data.task_id) { $json.data.task_id } else { $null }
    if (-not $taskId) { throw "Task id missing in response: $body" }
    $cacheKey = if ($json.cache_key) { $json.cache_key } else { $null }
    $cacheStatus = if ($json.cache_status) { $json.cache_status }
                   elseif ($json.cache_hit -eq $true) { 'HIT' }
                   elseif ($json.cache_hit -eq $false -and $json.cache_key) { 'MISS/BUILDING' }
                   else { 'N/A' }
    Write-Host ("cache_key={0} cache_status={1}" -f $cacheKey, $cacheStatus)
    [PSCustomObject]@{ TaskId = $taskId; CacheKey = $cacheKey; CacheStatus = $cacheStatus; Raw = $json }
} finally {
foreach ($s in $streams) { try { $s.Dispose() } catch {} }
try { $form.Dispose() } catch {}
try { $hc.Dispose() } catch {}
}
}

function Get-Docx2TexTask {
param(
[Parameter(Mandatory=$true)][string]$Server,
[Parameter(Mandatory=$true)][string]$TaskId,
[int]$TimeoutSec = 120
)
$hc = New-HttpClient -TimeoutSec $TimeoutSec
try {
$resp = $hc.GetAsync("$Server/v1/task/$TaskId").Result
$body = $resp.Content.ReadAsStringAsync().Result
if (-not $resp.IsSuccessStatusCode) { throw "HTTP $($resp.StatusCode) $body" }
return ($body | ConvertFrom-Json)
} finally { try { $hc.Dispose() } catch {} }
}

function Wait-Docx2TexTask {
param(
[Parameter(Mandatory=$true)][string]$Server,
[Parameter(Mandatory=$true)][string]$TaskId,
[int]$PollIntervalSec = 2,
[int]$TimeoutSec = 900
)
$start = Get-Date
while ($true) {
$st = Get-Docx2TexTask -Server $Server -TaskId $TaskId
$state = $st.data.state
Write-Host ("[{0}] state={1}" -f (Get-Date), $state)
if ($state -in @('done','failed')) { return $st }
Start-Sleep -Seconds $PollIntervalSec
if ((Get-Date) -gt $start.AddSeconds($TimeoutSec)) { throw "Timeout waiting for task $TaskId" }
}
}

function Get-Docx2TexResult {
param(
[Parameter(Mandatory=$true)][string]$Server,
[Parameter(Mandatory=$true)][string]$TaskId,
[Parameter(Mandatory=$true)][string]$OutFile,
[int]$TimeoutSec = 300
)
$hc = New-HttpClient -TimeoutSec $TimeoutSec
try {
$resp = $hc.GetAsync("$Server/v1/task/$TaskId/result").Result
if ($resp.StatusCode -eq 409) {
$msg = $resp.Content.ReadAsStringAsync().Result
throw "Task not ready (409): $msg"
}
$resp.EnsureSuccessStatusCode() | Out-Null
$bytes = $resp.Content.ReadAsByteArrayAsync().Result

$outDir = Split-Path -Parent $OutFile
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
  New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
[System.IO.File]::WriteAllBytes($OutFile, $bytes)
return $OutFile
} finally { try { $hc.Dispose() } catch {} }
}

function Invoke-Docx2Tex {
[CmdletBinding(DefaultParameterSetName="File")]
param(
[Parameter(Mandatory=$true)][string]$Server,

[Parameter(ParameterSetName="File", Mandatory=$true)][string]$File,
[Parameter(ParameterSetName="Url" , Mandatory=$true)][string]$Url,

[string]$OutFile = $(Join-Path $PWD ("result_{0}.zip" -f ([Guid]::NewGuid().ToString("n").Substring(0,8)))),

[bool]$IncludeDebug = $false,
[bool]$ImgPostProc = $true,

[string]$Conf,
[string]$CustomXsl,
[string]$StyleMap,
[string]$CustomEvolve,
[string]$MathTypeSource,
[string]$TableModel,
[string]$FontMapsZip,
[string]$ImageDir,

[bool]$NoCache = $false,
[int]$PollIntervalSec = 2,
[int]$TimeoutSec = 900
)

$task = if ($PSCmdlet.ParameterSetName -eq "File") {
New-Docx2TexTask -Server $Server -File $File -IncludeDebug:$IncludeDebug -ImgPostProc:$ImgPostProc -Conf $Conf -CustomXsl $CustomXsl -CustomEvolve $CustomEvolve -StyleMap $StyleMap -MathTypeSource $MathTypeSource -TableModel $TableModel -FontMapsZip $FontMapsZip -NoCache:$NoCache -ImageDir $ImageDir
} else {
New-Docx2TexTask -Server $Server -Url $Url -IncludeDebug:$IncludeDebug -ImgPostProc:$ImgPostProc -Conf $Conf -CustomXsl $CustomXsl -CustomEvolve $CustomEvolve -StyleMap $StyleMap -MathTypeSource $MathTypeSource -TableModel $TableModel -FontMapsZip $FontMapsZip -NoCache:$NoCache -ImageDir $ImageDir
}

if (-not $task.TaskId) { throw "Task creation failed (no TaskId returned)." }

$st = Wait-Docx2TexTask -Server $Server -TaskId $task.TaskId -PollIntervalSec $PollIntervalSec -TimeoutSec $TimeoutSec
if ($st.data.state -ne 'done') { throw "Task failed: $($st.data.err_msg)" }
$zip = Get-Docx2TexResult -Server $Server -TaskId $task.TaskId -OutFile $OutFile
  [PSCustomObject]@{ TaskId = $task.TaskId; CacheKey = $task.CacheKey; CacheStatus = $task.CacheStatus; State = $st.data.state; Zip = (Resolve-Path $zip).Path }
}

# Dry-run helper: build effective XSLs only and download as ZIP
function Invoke-Docx2TexDryRun {
param(
  [Parameter(Mandatory=$true)][string]$Server,

  [string]$Conf,
  [string]$CustomEvolve,
  [string]$StyleMap,

  [string]$OutFile = $(Join-Path $PWD ("dryrun_{0}.zip" -f ([Guid]::NewGuid().ToString("n").Substring(0,8)))),
  [int]$TimeoutSec = 300
)

$endpoint = "$Server/v1/dryrun"
$hc = New-HttpClient -TimeoutSec $TimeoutSec
$form = New-Object System.Net.Http.MultipartFormDataContent
$streams = New-Object System.Collections.Generic.List[System.IDisposable]
try {
  if ($Conf) {
    if (-not (Test-Path -LiteralPath $Conf)) { throw "Conf not found: $Conf" }
    $s = Add-FilePart -Form $form -Name "conf" -FilePath $Conf -ContentType "application/xml"; $streams.Add($s) | Out-Null
  }
  if ($CustomEvolve) {
    if (-not (Test-Path -LiteralPath $CustomEvolve)) { throw "CustomEvolve not found: $CustomEvolve" }
    $s = Add-FilePart -Form $form -Name "custom_evolve" -FilePath $CustomEvolve -ContentType "application/xml"; $streams.Add($s) | Out-Null
  }
  if ($StyleMap) {
    Add-StringPart -Form $form -Name "StyleMap" -Value $StyleMap
  }

  $resp = $hc.PostAsync($endpoint, $form).Result
  $bytes = $resp.Content.ReadAsByteArrayAsync().Result
  if (-not $resp.IsSuccessStatusCode) {
    $msg = try { [System.Text.Encoding]::UTF8.GetString($bytes) } catch { "" }
    throw "HTTP $($resp.StatusCode) $msg"
  }

  $basePath = (Get-Location).ProviderPath
  if ([System.IO.Path]::IsPathRooted($OutFile)) {
    $outFullPath = [System.IO.Path]::GetFullPath($OutFile)
  } else {
    $outFullPath = [System.IO.Path]::GetFullPath((Join-Path $basePath $OutFile))
  }
  $outDir = Split-Path -Parent $outFullPath
  if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
  }
  [System.IO.File]::WriteAllBytes($outFullPath, $bytes)
  Write-Host ("DryRun ZIP -> {0}" -f $outFullPath)
  return $outFullPath
}
finally {
  foreach ($s in $streams) { try { $s.Dispose() } catch {} }
  try { $form.Dispose() } catch {}
  try { $hc.Dispose() } catch {}
}
}
