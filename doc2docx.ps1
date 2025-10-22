# Wordをバックグラウンドで起動
$word = New-Object -ComObject Word.Application
$word.Visible = $false

# 処理するフォルダを指定
$folder = "C:\path\to\your\folder"

# .doc ファイルをすべて取得して処理
Get-ChildItem -Path $folder -Filter *.doc | ForEach-Object {
    $source = $_.FullName
    $target = $source -replace '\.doc$', '.docx'

    Write-Host "🔄 $($_.Name) を処理中..." -ForegroundColor Yellow

    try {
        $doc = $word.Documents.Open($source)
        $doc.SaveAs([ref] $target, [ref] 16)  # 16 = wdFormatXMLDocument (.docx)
        $doc.Close()
        Write-Host "✅ $($_.Name) の docx 化に成功！" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ $($_.Name) の変換でエラー: $_" -ForegroundColor Red
    }
}

$word.Quit()

Write-Host "🎉 すべての処理が完了しました。" -ForegroundColor Cyan
