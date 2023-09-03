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
  <xsl:output encoding="UTF-8" method="xml" indent="yes" omit-xml-declaration="yes"/>
  <xsl:param name="name"/>
  <xsl:param name="path"/>
  <!--
  <xsl:strip-space elements="tei:div,tei:head,tei:l,tei:p,tei:quote "/>
  DO NOT <xsl:strip-space elements="*"/>, lose spaces between inlines
  -->
  <xsl:variable name="lf" select="'&#10;'"/> 
  
  <xsl:template match="/">
    <section>
      <h2>[<xsl:value-of select="$name"/>] <xsl:value-of select="/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title"/></h2>
      <xsl:apply-templates select="/tei:TEI/tei:text/*" mode="toc"/>
    </section>
  </xsl:template>
  
  <xsl:template match="*" mode="toc">
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
          <a target="_blank">
            <xsl:attribute name="href">
              <xsl:value-of select="$path"/>
              <xsl:text>#</xsl:text>
              <xsl:text>urn:cts:greekLit:</xsl:text>
              <xsl:value-of select="$name"/>
              <xsl:text>:</xsl:text>
              <xsl:value-of select="substring(@xml:id, 2)"/>
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
  
  <!-- Title for toc. -->
  <xsl:template name="title">
    <xsl:choose>
      <xsl:when test="@type='textpart'  and (@subtype='chapter' or @subtype='section')">
        <xsl:variable name="label">
          <xsl:choose>
            <xsl:when test="@subtype='chapter'">Capitulum </xsl:when>
            <xsl:when test="@subtype='section'">Sectio </xsl:when>
          </xsl:choose>
        </xsl:variable>
        <xsl:choose>
          <xsl:when test="@n and number(@n) &gt; 0">
            <xsl:value-of select="$label"/>
            <xsl:value-of select="@n"/>
          </xsl:when>
          <xsl:when test="@n and @n != ''">
            <xsl:value-of select="@n"/>
          </xsl:when>
          <xsl:otherwise>
            <xsl:value-of select="$label"/>
            <xsl:number/>
          </xsl:otherwise>
        </xsl:choose>
        <xsl:choose>
          <!-- Title in chapter are not systematic, reason why the prefix “Capitulum” is useful -->
          <xsl:when test="tei:head">
            <xsl:text>. </xsl:text>
            <xsl:value-of select="tei:head"/>
          </xsl:when>
          <xsl:when test="./tei:p/tei:label[@type='head']">
            <xsl:text>. </xsl:text>
            <xsl:value-of select="normalize-space(./tei:p/tei:label[@type='head'])"/>
          </xsl:when>
        </xsl:choose>
      </xsl:when>
      <xsl:when test="tei:head">
        <xsl:value-of select="normalize-space(tei:head)"/>
      </xsl:when>
      <xsl:when test="./tei:label[@type='head']">
        <xsl:value-of select="normalize-space(./tei:label[@type='head'])"/>
      </xsl:when>
      <xsl:when test="./tei:p/tei:label[@type='head']">
        <xsl:value-of select="normalize-space(./tei:p/tei:label[@type='head'])"/>
      </xsl:when>
      <xsl:when test="@type='textpart' and (@subtype='chapter' or @subtype='section')">
        <xsl:variable name="label">
          <xsl:choose>
            <xsl:when test="@subtype='chapter'">Capitulum </xsl:when>
            <xsl:when test="@subtype='section'">Sectio </xsl:when>
          </xsl:choose>
        </xsl:variable>
        <xsl:choose>
          <xsl:when test="number(@n) &gt; 0">
            <xsl:value-of select="$label"/>
            <xsl:value-of select="@n"/>
          </xsl:when>
          <xsl:when test="@n and @n != ''">
            <xsl:value-of select="@n"/>
          </xsl:when>
          <xsl:otherwise>
            <xsl:value-of select="$label"/>
            <xsl:number/>
          </xsl:otherwise>
        </xsl:choose>
        <xsl:if test="./tei:p/tei:label[@type='head']">
          <xsl:text>. </xsl:text>
          <xsl:value-of select="normalize-space(./tei:p/tei:label[@type='head'])"/>
        </xsl:if>
      </xsl:when>
      <xsl:when test="@n and tei:div[@type='textpart'][@subtype='chapter']">
        <xsl:text>Liber </xsl:text>
        <xsl:value-of select="@n"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="translate(@xml:id, '_', ':')"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  
</xsl:transform>
