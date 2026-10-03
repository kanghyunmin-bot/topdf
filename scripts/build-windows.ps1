$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
function Fetch-Verified($url,$path,$sha) {
 if ((Test-Path $path) -and (Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sha) { Remove-Item $path -Force }
 if (!(Test-Path $path)) {
  & curl.exe -fL --retry 5 --retry-all-errors --connect-timeout 30 $url -o $path
  if ($LASTEXITCODE -ne 0) { throw "Download failed: $url" }
 }
 if ((Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sha) { throw "SHA256 mismatch: $path" }
}
New-Item -ItemType Directory -Force build/windows,downloads,dist | Out-Null
Fetch-Verified 'https://download.documentfoundation.org/libreoffice/stable/26.2.6/win/x86_64/LibreOffice_26.2.6_Win_x86-64.msi' 'downloads/LibreOffice_26.2.6_Win_x86-64.msi' 'f9877032fd908beb9c0ddf06df4af5c2e85f419c42e14876c4cce5aae5fb2660'

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
python scripts/prepare-fonts.py
python scripts/build-hwp-gothic.py --target x86_64-pc-windows-msvc
if ($LASTEXITCODE -ne 0) { throw 'Modified HWP engine build failed' }
Copy-Item build/hwp-gothic-src/target/x86_64-pc-windows-msvc/release/hwp.exe "$out/Engines/hwp.exe"
New-Item -ItemType Directory -Force "$out/Engines/LibreOffice/share/fonts/truetype" | Out-Null
Copy-Item Engines/FallbackFonts/*.ttf "$out/Engines/LibreOffice/share/fonts/truetype" -Force
# Keep conversion filters, every vendor font, dictionaries and hyphenation.
$lo = "$out/Engines/LibreOffice"
foreach ($relative in @('help','share/gallery','share/template','share/basic','share/Scripts','share/wizards','program/python-core-3.12.12','share/extensions/nlpsolver')) {
 $path=Join-Path $lo $relative
 if (Test-Path $path) { Remove-Item $path -Recurse -Force }
}
Get-ChildItem "$lo/program" -Directory -Filter 'python-core-*' | Remove-Item -Recurse -Force
Get-ChildItem "$lo/share/config" -Filter 'images_*.zip' | Where-Object { $_.Name -notin @('images_colibre.zip','images_colibre_dark.zip') } | Remove-Item -Force
Get-ChildItem "$lo/share/extensions" -Recurse -File | Where-Object { $_.Name -match '^th(es)?_.*\.(dat|idx)$' } | Remove-Item -Force
# Remove editing-only spelling dictionaries while preserving all hyphenation data.
Get-ChildItem "$lo/share/extensions" -Recurse -File | Where-Object { $_.Extension -in @('.dic','.aff') } | Remove-Item -Force
# Localized UI labels are unnecessary in the headless renderer. Locale/layout libraries remain.
Get-ChildItem "$lo/program/resource" -Directory | Where-Object { $_.Name -notin @('en-US','en','ko') } | Remove-Item -Recurse -Force
Get-ChildItem "$lo/share/registry/res" -Filter 'registry_*.xcd' | Where-Object { $_.Name -notin @('registry_en-US.xcd','registry_ko.xcd') } | Remove-Item -Force
Get-ChildItem $lo -Filter '*.msi' -File | Remove-Item -Force
# MSI administrative extraction keeps VC runtime DLLs in System64 instead of installing them.
# Preserve the vendor's exact DLL bytes beside each native executable for clean offline PCs.
$crt = Join-Path $out 'Engines/LibreOffice/System64'
if (!(Test-Path $crt)) { throw 'Vendor x64 C runtime payload missing' }
Get-ChildItem $crt -Filter '*.dll' -File | ForEach-Object {
 Copy-Item $_.FullName "$out/Engines/LibreOffice/program" -Force
 Copy-Item $_.FullName "$out/Engines" -Force
}

Remove-Item $crt -Recurse -Force
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
TopDF 1.0.0-rc.4 Windows x64 — unsigned preview
Windows 10 2004 or newer / Windows 11. No Office installation or cloud conversion API required.
Extract this folder before launching TopDF.exe. Do not run from inside a ZIP viewer.
Use the app's context-menu button to register PDF conversion for the current user. Windows 11 may show it under Show more options.
TopDF source: MIT. Engines and dependencies retain their own licenses; see Licenses.
Desktop engine corresponding sources: https://github.com/kanghyunmin-bot/topdf/releases/download/v1.0.0-rc.1/TopDF-1.0.0-rc.1-sources.zip
No Windows publisher certificate / SmartScreen reputation has been obtained. Native runner conversion tests do not replace interactive installation and printing tests on a separate Windows PC.
'@ | Set-Content "$out/READ-ME-FIRST.txt" -Encoding utf8


# NTFS transparent LZX compression preserves every remaining executable byte.
& compact.exe /C /S:$out /I /F /EXE:LZX "*"
if ($LASTEXITCODE -ne 0) { throw 'NTFS application compression failed' }
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class TopDFStorage {
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
 static extern uint GetCompressedFileSizeW(string file, out uint high);
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
 static extern bool GetDiskFreeSpaceW(string root, out uint sectors, out uint bytes, out uint free, out uint total);
 public static long AllocationUnit(string root) {
  uint sectors, bytes, free, total;
  if(!GetDiskFreeSpaceW(root,out sectors,out bytes,out free,out total))throw new System.ComponentModel.Win32Exception();
  return (long)sectors*bytes;
 }
 public static long Size(string file) {
  // WOF LZX stores its compressed payload in an NTFS alternate stream.
  // Querying only the transparent default stream returns its logical size.
  uint high; uint low=GetCompressedFileSizeW(file+":WofCompressedData",out high);
  if(low!=uint.MaxValue || Marshal.GetLastWin32Error()==0)return ((long)high<<32)|low;
  low=GetCompressedFileSizeW(file,out high);
  if(low==uint.MaxValue && Marshal.GetLastWin32Error()!=0)throw new System.ComponentModel.Win32Exception();return ((long)high<<32)|low;
 }
}
'@
$bytes=(Get-ChildItem $out -Recurse -File | Measure-Object -Property Length -Sum).Sum
Write-Output "Windows logical payload: $bytes bytes"
$cluster=[TopDFStorage]::AllocationUnit([System.IO.Path]::GetPathRoot($out))
$allocated=(Get-ChildItem $out -Recurse -File | ForEach-Object { [long]([Math]::Ceiling([TopDFStorage]::Size($_.FullName)/$cluster)*$cluster) } | Measure-Object -Sum).Sum
Write-Output "Windows WOF/NTFS payload: $allocated bytes"
@{ version='1.0.0-rc.4'; logical_file_bytes=$bytes; installed_allocated_bytes=$allocated; limit_bytes=500000000; allocation_unit_bytes=$cluster; measurement='compressed stream bytes rounded up to NTFS allocation units; filesystem metadata excluded'; compression='NTFS transparent LZX; required on installation' } | ConvertTo-Json | Set-Content "$out/size-report.json"
if ($allocated -gt 500000000) { throw "Windows app exceeds 500 MB on NTFS: $allocated" }
