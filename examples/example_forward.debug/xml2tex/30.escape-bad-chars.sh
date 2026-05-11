#!/bin/bash
cmd=$(cat <<EOF
 /D:/%E8%BD%AF%E4%BB%B6/docx2tex/saxon/saxon.sh -xsl:file:///D:/%E8%BD%AF%E4%BB%B6/docx2tex/TMP/example_forward.debug/xml2tex/30.escape-bad-chars.from-memory.xslt -im:escape-bad-chars -s:/D:/%E8%BD%AF%E4%BB%B6/docx2tex/TMP/example_forward.debug/xml2tex/30.escape-bad-chars.input -o:/D:/%E8%BD%AF%E4%BB%B6/docx2tex/TMP/example_forward.debug/xml2tex/30.escape-bad-chars.output 
EOF
) && echo $cmd && eval $cmd