<?xml version="1.0" encoding="UTF-8"?>
<!--

Part of verbapy https://github.com/galenus-verbatim/verbapy
Copyright (c) 2021 Nathalie Rousseau
MIT License https://opensource.org/licenses/mit-license.php


Specific Galenus, normalize line breaks.

-->
<xsl:transform version="1.1" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns="http://www.tei-c.org/ns/1.0" xmlns:tei="http://www.tei-c.org/ns/1.0" exclude-result-prefixes="tei" xmlns:ext="http://exslt.org/common" extension-element-prefixes="ext">
  <xsl:output encoding="UTF-8" method="xml" indent="yes" omit-xml-declaration="no"/>
  <xsl:variable name="vol1" select="/tei:TEI/tei:teiHeader/tei:fileDesc/tei:sourceDesc//tei:biblScope[@unit='ed1vol']"/>
  <xsl:variable name="vol2" select="/tei:TEI/tei:teiHeader/tei:fileDesc/tei:sourceDesc//tei:biblScope[@unit='ed2vol']"/>

  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()"/>
    </xsl:copy>
  </xsl:template>

  <!-- 
  <milestone unit="ed2page" n="2"/>
  -->

  <xsl:template match="tei:milestone">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:choose>
        <xsl:when test="@unit = 'ed1page' and $vol1 != '' and not(contains(@n, '.'))">
          <xsl:attribute name="n">
            <xsl:value-of select="$vol1"/>
            <xsl:text>.</xsl:text>
            <xsl:value-of select="@n"/>
          </xsl:attribute>
        </xsl:when>
        <xsl:when test="@unit = 'ed2page' and $vol2 != '' and not(contains(@n, '.'))">
          <xsl:attribute name="n">
            <xsl:value-of select="$vol2"/>
            <xsl:text>.</xsl:text>
            <xsl:value-of select="@n"/>
          </xsl:attribute>
        </xsl:when>
      </xsl:choose>
      <xsl:apply-templates/>
    </xsl:copy>
  </xsl:template>

</xsl:transform>
