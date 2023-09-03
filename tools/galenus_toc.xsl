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
  <xsl:output encoding="UTF-8" method="xml" indent="no" omit-xml-declaration="no"/>
  <xsl:param name="name"/>
  <xsl:param name="path"/>
  <!--
  <xsl:strip-space elements="tei:div,tei:head,tei:l,tei:p,tei:quote "/>
  DO NOT <xsl:strip-space elements="*"/>, lose spaces between inlines
  -->
  <xsl:variable name="lf" select="'&#10;'"/> 
  
  <xsl:template match="/">
    <xsl:apply-templates mode="toc"/>
  </xsl:template>
  
  <xsl:template match="tei:text | tei:body" mode="toc">
    <xsl:apply-templates select="*" mode="toc"/>
  </xsl:template>
  
  <xsl:template match="tei:div" mode="toc">
    <xsl:choose>
      <xsl:when test="@type = 'edition'">
        <ul class="tree">
          <xsl:apply-templates select="tei:div" mode="toc"/>
        </ul>
      </xsl:when>
      <xsl:otherwise>
        <li>
          <a>
            <xsl:attribute name="href">
              <xsl:value-of select="$path"/>
            </xsl:attribute>
            <xsl:attribute name="id">
              <xsl:text>tree_</xsl:text>
              <xsl:call-template name="cts"/>
            </xsl:attribute>
            <xsl:call-template name="title"/>
          </a>
          <xsl:if test="tei:div">
            <ul>
              <xsl:apply-templates select="tei:div" mode="toc"/>
            </ul>
          </xsl:if>
        </li>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  
</xsl:transform>
