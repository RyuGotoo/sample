# Wordをバックグラウンドで起動
$word = New-Object -ComObject Word.Application
$word.Visible = $false

# 変換したいフォルダを指定
$folder = "C:\path\to\your\folder"

# .docファイルをすべて処理
Get-ChildItem -Path $folder -Filter *.doc | ForEach-Object {
    $source = $_.FullName
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($_.FullName)
    $docxPath = Join-Path $folder ($baseName + ".docx")
    $htmlPath = Join-Path $folder ($baseName + ".htm")

    Write-Host "🔄 $($_.Name) を処理中..." -ForegroundColor Yellow

    try {
        $doc = $word.Documents.Open($source)

        # DOCXとして保存 (16 = wdFormatXMLDocument)
        $doc.SaveAs([ref] $docxPath, [ref] 16)
        Write-Host "✅ $($_.Name) の docx 化に成功" -ForegroundColor Green

        # Filtered HTMLとして保存 (10 = wdFormatFilteredHTML)
        $doc.SaveAs([ref] $htmlPath, [ref] 10)
        Write-Host "🌐 $($_.Name) の HTML 化に成功" -ForegroundColor Cyan

        $doc.Close()
    }
    catch {
        Write-Host "❌ $($_.Name) の変換でエラー: $_" -ForegroundColor Red
    }
}

$word.Quit()
Write-Host "🎉 すべての処理が完了しました。" -ForegroundColor Magenta
