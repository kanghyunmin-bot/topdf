$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
function Fetch-Verified($url,$path,$sha) {
 if (!(Test-Path $path)) { Invoke-WebRequest -Uri $url -OutFile $path }
 if ((Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sha) { throw "SHA256 mismatch: $path" }
}
New-Item -ItemType Directory -Force build/windows,downloads,dist | Out-Null
Fetch-Verified 'https://download.documentfoundation.org/libreoffice/stable/26.2.6/win/x86_64/LibreOffice_26.2.6_Win_x86-64.msi' 'downloads/LibreOffice_26.2.6_Win_x86-64.msi' 'f9877032fd908beb9c0ddf06df4af5c2e85f419c42e14876c4cce5aae5fb2660'
Fetch-Verified 'https://github.com/STAIxBWLB/hwp-cli/releases/download/v1.3.1/hwp-v1.3.1-x86_64-pc-windows-msvc.zip' 'downloads/hwp-v1.3.1-x86_64-pc-windows-msvc.zip' '307422ebe4c739d825baa6e29fbc3d93e23eb2b15949afb374f4ee0feea9b741'
$extract = Join-Path $root 'build/windows/lo-msi'
New-Item -ItemType Directory -Force $extract | Out-Null
$p = Start-Process msiexec.exe -ArgumentList @('/a',"`"$root\downloads\LibreOffice_26.2.6_Win_x86-64.msi`"",'/qn',"TARGETDIR=`"$extract`"") -Wait -PassThru
if ($p.ExitCode -ne 0) { throw "MSI extraction failed: $($p.ExitCode)" }
$out = Join-Path $root 'build/windows/app'
dotnet publish platforms/windows/TopDF/TopDF.csproj -c Release -r win-x64 --self-contained true -o $out
if ($LASTEXITCODE -ne 0) { throw 'dotnet publish failed' }
New-Item -ItemType Directory -Force "$out/Engines" | Out-Null
$program = Get-ChildItem $extract -Filter soffice.com -Recurse | Select-Object -First 1
if (!$program) { throw 'LibreOffice program folder was not extracted' }
Copy-Item (Split-Path (Split-Path $program.FullName -Parent) -Parent) "$out/Engines/LibreOffice" -Recurse -Force
Expand-Archive downloads/hwp-v1.3.1-x86_64-pc-windows-msvc.zip build/windows/hwp -Force
$hwp = Get-ChildItem build/windows/hwp -Filter hwp.exe -Recurse | Select-Object -First 1
Copy-Item $hwp.FullName "$out/Engines/hwp.exe"
# MSI administrative extraction keeps VC runtime DLLs in System64 instead of installing them.
# Preserve the vendor's exact DLL bytes beside each native executable for clean offline PCs.
$crt = Join-Path $out 'Engines/LibreOffice/System64'
if (!(Test-Path $crt)) { throw 'Vendor x64 C runtime payload missing' }
Get-ChildItem $crt -Filter '*.dll' -File | ForEach-Object {
 Copy-Item $_.FullName "$out/Engines/LibreOffice/program" -Force
 Copy-Item $_.FullName "$out/Engines" -Force
}

Copy-Item Assets/AppIcon.ico,LICENSE $out
Copy-Item legal "$out/Licenses" -Recurse -Force
Copy-Item docs "$out/Help" -Recurse -Force
# Preserve notices from every NuGet package used by the build, including PDFsharp and .NET runtime packages.
$nuget = Join-Path $env:USERPROFILE '.nuget/packages'
$asset = Get-Content platforms/windows/TopDF/obj/project.assets.json -Raw | ConvertFrom-Json
$deps = @()
foreach ($lib in $asset.libraries.PSObject.Properties) {
 if ($lib.Value.type -ne 'package') { continue }
 $parts=$lib.Name.Split('/');$dir=Join-Path $nuget "$($parts[0].ToLowerInvariant())/$($parts[1])"
 $target=Join-Path $out "Licenses/nuget/$($parts[0])/$($parts[1])";New-Item -ItemType Directory -Force $target | Out-Null
 Get-ChildItem $dir -Recurse -File | Where-Object { $_.Name -match '^(LICENSE|NOTICE|COPYING|THIRD.?PARTY)' -or $_.Extension -eq '.nuspec' } | ForEach-Object {
  $relative = [System.IO.Path]::GetRelativePath($dir,$_.FullName)
  $notice = Join-Path $target $relative
  New-Item -ItemType Directory -Force (Split-Path $notice -Parent) | Out-Null
  Copy-Item $_.FullName $notice -Force
 }
 $deps += @{ name=$parts[0];version=$parts[1];source="https://www.nuget.org/packages/$($parts[0])/$($parts[1])" }
}
# Include redistributable .NET runtime notices from the official SDK distribution.
$dotnetRoot = Split-Path (Get-Command dotnet).Source -Parent
Get-ChildItem $dotnetRoot -File | Where-Object { $_.Name -match '^(LICENSE|NOTICE|COPYING|THIRD.?PARTY)' } | ForEach-Object {
 $runtimeNotices = Join-Path $out 'Licenses/dotnet-runtime'
 New-Item -ItemType Directory -Force $runtimeNotices | Out-Null
 Copy-Item $_.FullName $runtimeNotices -Force
}
Copy-Item "$out/TopDF.deps.json" "$out/Licenses/dotnet-dependencies.json"
$deps | ConvertTo-Json -Depth 5 | Set-Content "$out/Licenses/nuget-packages.json" -Encoding utf8
@'
TopDF 1.0.0-rc.2 Windows x64 — unsigned preview
Windows 10 2004 or newer / Windows 11. No Office installation or cloud conversion API required.
Extract this folder before launching TopDF.exe. Do not run from inside a ZIP viewer.
Use the app's context-menu button to register PDF conversion for the current user. Windows 11 may show it under Show more options.
TopDF source: MIT. Engines and dependencies retain their own licenses; see Licenses.
Desktop engine corresponding sources: https://github.com/kanghyunmin-bot/topdf/releases/download/v1.0.0-rc.1/TopDF-1.0.0-rc.1-sources.zip
No Windows publisher certificate / SmartScreen reputation has been obtained. Native runner conversion tests do not replace interactive installation and printing tests on a separate Windows PC.
'@ | Set-Content "$out/READ-ME-FIRST.txt" -Encoding utf8
