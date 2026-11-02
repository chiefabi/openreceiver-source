# Startet je Testfall einen frischen uxplay.exe mit festem PIN und führt den Kopplungstest dagegen aus.
# Aufruf:  test-pairing.ps1 -Exe <uxplay.exe> -DllDirs <Ordner;Ordner> [-PluginDir <Ordner>] [-Pin 1234] [-Port 7124]
param(
    [Parameter(Mandatory)][string]$Exe,
    [Parameter(Mandatory)][string]$DllDirs,
    [string]$PluginDir = '',
    [string]$Pin = '1234',
    [int]$Port = 7124
)
$py  = Join-Path $PSScriptRoot 'pair_setup_pin_test.py'
$tmp = $env:TEMP

function Invoke-Case([string]$Title, [string]$ClientPin, [string[]]$ClientArgs) {
    $log = Join-Path $tmp 'uxplay-pairtest.log'; $err = Join-Path $tmp 'uxplay-pairtest.err'
    Remove-Item $log, $err -ErrorAction SilentlyContinue
    $old = @{ PATH = $env:PATH; GP = $env:GST_PLUGIN_PATH; GS = $env:GST_PLUGIN_SYSTEM_PATH_1_0; GR = $env:GST_REGISTRY_1_0 }
    $env:PATH = $DllDirs + ';' + $env:PATH
    if ($PluginDir) { $env:GST_PLUGIN_PATH = $PluginDir; $env:GST_PLUGIN_SYSTEM_PATH_1_0 = $PluginDir }
    $env:GST_REGISTRY_1_0 = Join-Path $tmp 'pairtest-registry.bin'
    # UxPlay belegt Basisport, +1, +2; der RTSP-Server (Kopplung) lauscht auf Basisport + 1 = $Port
    $p = Start-Process $Exe -ArgumentList "-n pairtest -nh -pin $Pin -p $($Port - 1) -vs 0 -as 0 -key `"$tmp\pairtest-key.pem`"" `
         -PassThru -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError $err
    $env:PATH = $old.PATH; $env:GST_PLUGIN_PATH = $old.GP; $env:GST_PLUGIN_SYSTEM_PATH_1_0 = $old.GS; $env:GST_REGISTRY_1_0 = $old.GR

    $up = $false
    for ($i = 0; $i -lt 80 -and -not $p.HasExited; $i++) {
        try { $c = New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1', $Port); $c.Close(); $up = $true; break } catch { Start-Sleep -Milliseconds 250 }
    }
    if (-not $up) { Write-Host "FEHLER: uxplay lauscht nicht auf Port $Port"; Get-Content $log, $err -ErrorAction SilentlyContinue | Out-Host; if (-not $p.HasExited) { $p.Kill() }; return 3 }
    Start-Sleep -Milliseconds 500   # der Test-Client verbindet sich selbst; die Prüf-Verbindung oben zählt nicht als Sitzung

    Write-Host "== $Title"
    python -I $py $Port $ClientPin @ClientArgs | Out-Host
    $rc = $LASTEXITCODE
    Start-Sleep -Milliseconds 400
    if (-not $p.HasExited) { $p.Kill(); $p.WaitForExit(3000) | Out-Null }
    Write-Host "   uxplay-Meldungen:"
    Get-Content $log, $err -ErrorAction SilentlyContinue | Select-String 'pair-setup-pin|Authentication|ERROR' | ForEach-Object { Write-Host ('     ' + $_.Line.Trim()) }
    Remove-Item (Join-Path $tmp 'pairtest-key.pem'), (Join-Path $tmp 'pairtest-registry.bin') -ErrorAction SilentlyContinue
    return $rc
}

$r1 = Invoke-Case "Test 1: richtiger PIN ($Pin) - Kopplung muss gelingen" $Pin @()
$r2 = Invoke-Case "Test 2: falscher PIN - muss abgelehnt werden" '9999' @('--expect-fail')
Write-Host ("GESAMT: " + $(if ($r1 -eq 0 -and $r2 -eq 0) { 'BESTANDEN' } else { "NICHT BESTANDEN (richtiger PIN: $r1, falscher PIN: $r2)" }))
exit ([int]($r1 -ne 0 -or $r2 -ne 0))
