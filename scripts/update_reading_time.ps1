param(
    [string]$BasePath = "."
)

$WPM = 200

function Compute-ReadingTime([string]$text){
    if ([string]::IsNullOrWhiteSpace($text)) { return 1 }
    $matches = [regex]::Matches($text, "\w+")
    $words = $matches.Count
    $minutes = [math]::Ceiling($words / $WPM)
    if ($minutes -lt 1) { $minutes = 1 }
    return $minutes
}

function Parse-FrontMatter([string]$content){
    $fmPattern = "(?s)^---\r?\n(.*?)\r?\n---\r?\n"
    $m = [regex]::Match($content, $fmPattern)
    if (-not $m.Success){
        return @{ fm=$null; body=$content }
    }
    return @{ fm=$m.Groups[1].Value; body=$content.Substring($m.Length) }
}

function FrontMatter-To-Hashtable([string]$fm){
    $h = @{}
    if (-not $fm) { return $h }
    $lines = $fm -split "\r?\n"
    foreach ($line in $lines){
        if ($line -match "^\s*$" -or $line -match "^\s*#") { continue }
        if ($line -match ":"){
            $parts = $line -split ":",2
            $k = $parts[0].Trim()
            $v = $parts[1].Trim()
            if ($v -match '^\[.*\]$'){
                $inner = $v.Trim('[',']') -split ',' | ForEach-Object { $_.Trim().Trim('"').Trim("'") }
                $h[$k] = $inner
            } elseif ($v -match '^(true|false)$'){
                $h[$k] = [bool]::Parse($v)
            } elseif ($v -match '^\d+$'){
                $h[$k] = [int]$v
            } else {
                $h[$k] = $v.Trim('"').Trim("'")
            }
        }
    }
    return $h
}

function Hashtable-To-FrontMatter([hashtable]$h){
    $lines = @()
    foreach ($k in $h.Keys){
        $v = $h[$k]
        if ($v -is [System.Array]){
            $items = $v | ForEach-Object { '"' + $_ + '"' }
            $lines += ('{0}: [{1}]' -f $k, ($items -join ','))
        } elseif ($v -is [bool]){
            $lines += ('{0}: {1}' -f $k, $v.ToString().ToLower())
        } elseif ($v -is [int]){
            $lines += ('{0}: {1}' -f $k, $v)
        } else {
            $lines += ('{0}: "{1}"' -f $k, $v)
        }
    }
    return ($lines -join "`n")
}

$base = Resolve-Path $BasePath
Write-Host "Processing folder: $base"
$files = Get-ChildItem -Path $base -Recurse -Filter *.md -File
if ($files.Count -eq 0){ Write-Host "No .md files found."; exit }

foreach ($f in $files){
    try{
        $content = Get-Content -Raw -Path $f.FullName -ErrorAction Stop
        $parsed = Parse-FrontMatter $content
        $fmText = $parsed.fm
        $body = $parsed.body
        if (-not $fmText){
            # build minimal frontmatter
            $firstLine = ($content -split "\r?\n")[0]
            $year = if ($f.Directory.Name -match '^\d{4}$') { $f.Directory.Name } else { "" }
            $fm = @{ title = $firstLine.Trim(); review_year = $year; film_year = ""; rating = ""; reading_time_min = Compute-ReadingTime $content; slug = $f.BaseName }
            $newFmText = Hashtable-To-FrontMatter $fm
            $newContent = "---`n$newFmText`n---`n`n" + $content
        } else {
            $h = FrontMatter-To-Hashtable $fmText
            $rt = Compute-ReadingTime $body
            $h['reading_time_min'] = $rt
            $newFmText = Hashtable-To-FrontMatter $h
            $newContent = "---`n$newFmText`n---`n`n" + $body
        }
        # backup
        $bak = $f.FullName + ".bak"
        Copy-Item -Path $f.FullName -Destination $bak -Force
        Set-Content -Path $f.FullName -Value $newContent -Encoding UTF8
        Write-Host "Updated $($f.FullName) (backup: $(Split-Path $bak -Leaf)) - reading_time_min=$($h['reading_time_min'] -or $fm.reading_time_min)"
    } catch {
        Write-Host "Error processing $($f.FullName): $_"
    }
}
