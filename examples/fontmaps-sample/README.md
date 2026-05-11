Sample fontmaps for testing custom-font-maps-dir

What this is
- Minimal fontmap files to verify the server’s FontMapsZip handling and docx2tex’s custom-font-maps-dir option.
- These files are deliberately tiny; they do not aim for completeness.

How to use
- Zip this folder and pass it as -FontMapsZip in the test script or as FontMapsZip in the API:
  - PowerShell: Invoke-Docx2Tex -Server http://127.0.0.1:8000 -File .\demo.docx -FontMapsZip .\test\fontmaps-sample.zip -IncludeDebug:$true
  - Or zip manually (the archive should contain the XML files at the root or within this directory).

Notes
- docx2tex resolves the font name from (in order) @mathtype-name, @docx-name, or the filename (underscores become spaces).
- Provided samples:
  - Symbol_Sample.xml (mathtype-name="Symbol"): maps '+' to ⊕, ',' to ◆, phi slot to ★
  - MT_Symbol_Sample.xml (mathtype-name="MT Symbol"): maps '+' to ⊗, '=' to ≠
  - MathType_MTCode_Sample.xml (mathtype-name="MathType MTCode"): maps '+' to ⊕, '=' to ≡, '-' to −
  - Wingdings_Sample.xml (docx-name="Wingdings"): maps '+', ',', '=' to visible glyphs
- To see effects, your DOCX must actually use those fonts (e.g., MathType equations, or text styled with Symbol/Wingdings).
