<#
.SYNOPSIS
    スペース区切りで3番目のトークンが "skill" で始まる行を抽出する

.USAGE
    .\extract_skill.ps1 -InputFile <入力ファイル> -OutputFile <出力ファイル>

.EXAMPLE
    .\extract_skill.ps1 -InputFile input.txt -OutputFile output.txt

.NOTE
    初回実行時にエラーが出る場合は以下を実行してから再試行：
    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
#>

param(
    [Parameter(Mandatory=$true)][string]$InputFile,
    [Parameter(Mandatory=$true)][string]$OutputFile
)

$results = Get-Content $InputFile | Where-Object {
    $parts = $_ -split " "
    $parts.Count -ge 3 -and $parts[2] -like "skill*"
}

$results | Set-Content $OutputFile
Write-Host "$($results.Count) 行抽出 → $OutputFile"
