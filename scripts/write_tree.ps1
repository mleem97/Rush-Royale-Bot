param(
  [string]$Root = (Get-Location).Path,
  [string]$OutFile = (Join-Path (Get-Location).Path 'ordner.txt'),
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
$script:Lines = New-Object System.Collections.Generic.List[string]
$script:Lines.Add($resolvedRoot) | Out-Null
Write-Tree -Path $resolvedRoot -Prefix ''

$script:Lines | Set-Content -LiteralPath $OutFile -Encoding utf8
Write-Host "Wrote $OutFile"