param(
  [string]$Root = (Get-Location).Path,
  [string]$OutFile = 'ordner.txt',
  [string[]]$ExcludeDirs = @(
    '.git',
    '.vs',
    '.vscode',
    '.bot_env',
    '__pycache__',
    '.pytest_cache',
    '.ruff_cache',
    '.mypy_cache',
    '.ipynb_checkpoints',
    'build',
    'dist'
  )
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# When calling this script via `pwsh -File ... -ExcludeDirs @('a','b','c')`, PowerShell may
# only bind the first value to `-ExcludeDirs` and bind the rest positionally (e.g. into `$Root`
# and `$OutFile`). Detect that situation and recover by moving those values back into `ExcludeDirs`.
if ($args.Count -gt 0) {
  $ExcludeDirs = @($ExcludeDirs) + @($args)
}

function LooksLikeMisboundDir([string]$Value) {
  if ([string]::IsNullOrWhiteSpace($Value)) { return $false }
  if ($Value -match '[\\/]' ) { return $false }
  if (-not ($Value.StartsWith('.'))) { return $false }
  return (Test-Path -LiteralPath $Value -PathType Container)
}

if (LooksLikeMisboundDir $Root) {
  $ExcludeDirs = @($ExcludeDirs) + @($Root)
  $Root = (Get-Location).Path
}

if (LooksLikeMisboundDir $OutFile) {
  $ExcludeDirs = @($ExcludeDirs) + @($OutFile)
  $OutFile = 'ordner.txt'
}

function Should-ExcludeDir([System.IO.DirectoryInfo]$Dir) {
  return $ExcludeDirs -contains $Dir.Name
}

function Write-Tree([string]$Path, [string]$Prefix = '') {
  $dirInfo = Get-Item -LiteralPath $Path -Force

  $children = @(Get-ChildItem -LiteralPath $Path -Force | Where-Object {
      if ($_.PSIsContainer) { -not (Should-ExcludeDir $_) } else { $true }
    } | Sort-Object @{Expression = { -not $_.PSIsContainer }; Ascending = $true}, Name)

  for ($i = 0; $i -lt $children.Count; $i++) {
    $child = $children[$i]
    $isLast = ($i -eq $children.Count - 1)

    $branch = if ($isLast) { '\\-- ' } else { '|-- ' }
    $line = $Prefix + $branch + $child.Name
    $script:Lines.Add($line) | Out-Null

    if ($child.PSIsContainer) {
      if ($isLast) {
        $nextPrefix = $Prefix + '    '
      }
      else {
        $nextPrefix = $Prefix + '|   '
      }
      Write-Tree -Path $child.FullName -Prefix $nextPrefix
    }
  }
}

$resolvedRoot = (Resolve-Path -LiteralPath $Root).Path
$resolvedOutFile = $OutFile
if (-not [System.IO.Path]::IsPathRooted($resolvedOutFile)) {
  $resolvedOutFile = Join-Path (Get-Location).Path $resolvedOutFile
}
if (Test-Path -LiteralPath $resolvedOutFile -PathType Container) {
  $resolvedOutFile = Join-Path $resolvedOutFile 'ordner.txt'
}

$script:Lines = New-Object System.Collections.Generic.List[string]
$script:Lines.Add($resolvedRoot) | Out-Null
Write-Tree -Path $resolvedRoot -Prefix ''

$script:Lines | Set-Content -LiteralPath $resolvedOutFile -Encoding utf8
Write-Host "Wrote $resolvedOutFile"