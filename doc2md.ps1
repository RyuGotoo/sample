#Requires -Version 5.1
<#
.SYNOPSIS
    指定ディレクトリ内の .doc / .docx ファイルを Markdown に変換します。

.DESCRIPTION
    1. .doc  → Word COM で .docx に変換
    2. .docx → pandoc で .md に変換

.PARAMETER InputDir
    変換対象ファイルが存在するディレクトリのパス（サブフォルダは対象外）

.EXAMPLE
    .\Convert-ToMarkdown.ps1 -InputDir "C:\Users\user\Documents\reports"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$InputDir
)

# -------------------------------------------------------
# pandoc.exe の絶対パス（環境に合わせて変更してください）
# -------------------------------------------------------
$PandocExe = "C:\Program Files\Pandoc\pandoc.exe"

# -------------------------------------------------------
# 入力チェック
# -------------------------------------------------------
if (-not (Test-Path -LiteralPath $InputDir -PathType Container)) {
    Write-Error "ディレクトリが見つかりません: $InputDir"
    exit 1
}

if (-not (Test-Path -LiteralPath $PandocExe -PathType Leaf)) {
    Write-Error "pandoc.exe が見つかりません: $PandocExe"
    exit 1
}

$InputDir = (Resolve-Path -LiteralPath $InputDir).Path

# doc から変換した一時 docx を追跡（後で削除するため）
$tempDocxFiles = [System.Collections.Generic.List[string]]::new()

# -------------------------------------------------------
# Step 1: .doc → .docx (Word COM)
# -------------------------------------------------------
$docFiles = Get-ChildItem -LiteralPath $InputDir -Filter "*.doc" -File |
    Where-Object { $_.Extension -eq ".doc" }  # .docx を除外

if ($docFiles.Count -gt 0) {
    Write-Host "[Step 1] .doc → .docx 変換を開始します ($($docFiles.Count) 件)"

    try {
        $word = New-Object -ComObject Word.Application
        $word.Visible = $false
        $word.DisplayAlerts = 0  # wdAlertsNone

        foreach ($docFile in $docFiles) {
            $docxPath = [System.IO.Path]::ChangeExtension($docFile.FullName, ".docx")
            Write-Host "  変換中: $($docFile.Name) → $([System.IO.Path]::GetFileName($docxPath))"
            try {
                $doc = $word.Documents.Open($docFile.FullName, $false, $true)  # ReadOnly
                # wdFormatXMLDocument = 12
                $doc.SaveAs2([ref]$docxPath, [ref]12)
                $doc.Close($false)
                $tempDocxFiles.Add($docxPath)
            }
            catch {
                Write-Warning "  失敗: $($docFile.Name) - $_"
            }
        }
    }
    finally {
        if ($null -ne $word) {
            $word.Quit()
            [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
        }
    }
}
else {
    Write-Host "[Step 1] .doc ファイルなし。スキップします。"
}

# -------------------------------------------------------
# Step 2: .docx → .md (pandoc)
# -------------------------------------------------------
$docxFiles = Get-ChildItem -LiteralPath $InputDir -Filter "*.docx" -File

if ($docxFiles.Count -gt 0) {
    Write-Host "[Step 2] .docx → .md 変換を開始します ($($docxFiles.Count) 件)"

    foreach ($docxFile in $docxFiles) {
        $mdPath = [System.IO.Path]::ChangeExtension($docxFile.FullName, ".md")
        Write-Host "  変換中: $($docxFile.Name) → $([System.IO.Path]::GetFileName($mdPath))"
        try {
            & $PandocExe $docxFile.FullName -o $mdPath
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "  pandoc がエラーを返しました (終了コード: $LASTEXITCODE): $($docxFile.Name)"
            }
        }
        catch {
            Write-Warning "  失敗: $($docxFile.Name) - $_"
        }
    }
}
else {
    Write-Host "[Step 2] .docx ファイルなし。スキップします。"
}

# -------------------------------------------------------
# Step 3: 一時 .docx を削除
# -------------------------------------------------------
if ($tempDocxFiles.Count -gt 0) {
    Write-Host "[Step 3] 一時 .docx ファイルを削除します ($($tempDocxFiles.Count) 件)"
    foreach ($tmp in $tempDocxFiles) {
        if (Test-Path -LiteralPath $tmp) {
            Remove-Item -LiteralPath $tmp -Force
            Write-Host "  削除: $([System.IO.Path]::GetFileName($tmp))"
        }
    }
}

Write-Host "完了しました。"
