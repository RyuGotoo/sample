$word = New-Object -ComObject Word.Application
$word.Visible = $false
$folder = "C:\path\to\your\folder"
Get-ChildItem -Path $folder -Filter *.doc | ForEach-Object {
    $docx = $_.FullName -replace '\.doc$', '.docx'
    $doc = $word.Documents.Open($_.FullName)
    $doc.SaveAs([ref] $docx, [ref] 16)  # 16 = wdFormatXMLDocument
    $doc.Close()
}
$word.Quit()
