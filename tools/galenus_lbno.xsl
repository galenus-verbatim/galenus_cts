<?xml version="1.0" encoding="UTF-8"?>
<!--

Part of verbapy https://github.com/galenus-verbatim/verbapy
Copyright (c) 2021 Nathalie Rousseau
MIT License https://opensource.org/licenses/mit-license.php


Specific Galenus, numbering line breaks.
This script suppose normalized <lb/>

-->
<xsl:transform version="1.1"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns="http://www.tei-c.org/ns/1.0"
  xmlns:tei="http://www.tei-c.org/ns/1.0"
  exclude-result-prefixes="tei"
  
  xmlns:ext="http://exslt.org/common" 
  extension-element-prefixes="ext"
>
  <xsl:output encoding="UTF-8" method="xml" indent="yes" omit-xml-declaration="no"/>
  <!--
  <xsl:strip-space elements="tei:div,tei:head,tei:l,tei:p,tei:quote "/>
  DO NOT <xsl:strip-space elements="*"/>, lose spaces between inlines
  -->
  <xsl:variable name="lf" select="'&#10;'"/> 
  <!-- A handle on each line breaks by its page to count lines -->
  <xsl:key name="line-by-page" match="tei:list[@rend='row'] | tei:l | tei:lb"
    use="generate-id(preceding::tei:pb[1])"/>
  
  <!-- First copy all -->
  <xsl:template match="node()|@*" mode="lb">
    <xsl:copy>
      <xsl:apply-templates select="node()|@*" mode="lb"/>
    </xsl:copy>
  </xsl:template>

  <xsl:template match="/">
    <xsl:apply-templates/>
  </xsl:template>
  
  <!-- numbering lines -->
  <xsl:template match="tei:lb | tei:l | tei:list">
    <xsl:variable name="id" select="generate-id(.)"/>
    <xsl:variable name="pb" select="generate-id(preceding::tei:pb[1])"/>
    <xsl:variable name="n">
      <xsl:for-each select="key('line-by-page', $pb)">
        <xsl:if test="generate-id(.) = $id">
          <xsl:value-of select="position()"/>
        </xsl:if>
      </xsl:for-each>
    </xsl:variable>
    <xsl:text>    </xsl:text>
    <xsl:copy>
      <xsl:if test="string(number($n)) != 'NaN'">
        <xsl:attribute name="n">
          <xsl:value-of select="$n"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:copy-of select="@*"/>
      <xsl:apply-templates select="node()"/>
    </xsl:copy>
  </xsl:template>
    

</xsl:transform>
