<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  version="2.0"
  xmlns:dbk="http://docbook.org/ns/docbook"
  xpath-default-namespace="http://docbook.org/ns/docbook">

  <!-- Identity transform -->
  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()"/>
    </xsl:copy>
  </xsl:template>

  <!-- Force root hub xml:lang to zh-CN; keep any child-level xml:lang values -->
  <xsl:template match="/hub">
    <xsl:copy>
      <xsl:apply-templates select="@* except @xml:lang"/>
      <xsl:attribute name="xml:lang">zh-CN</xsl:attribute>
      <xsl:apply-templates select="node()"/>
    </xsl:copy>
  </xsl:template>

</xsl:stylesheet>

