<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns="http://www.w3.org/1999/xhtml">
	<xsl:output method="html" indent="yes" encoding="utf-8"
		doctype-public="-//W3C//DTD XHTML 1.0 Strict//EN" version="1.0"
		doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd" />

	<xsl:template match="/">
		<html>
			<head>
				<title>Elenco delle misure effettuate</title>
			</head>

			<body>
				<xsl:apply-templates />
			</body>
		</html>
	</xsl:template>

	<xsl:template match="content">
		<h3>Prospetto delle misure</h3>
		<xsl:apply-templates />
	</xsl:template>

	<xsl:template match="measure">

		<p>
			Inizio misurazione:
			<b>
				<xsl:value-of select="@start" />
			</b>
		</p>
		<p>
			Server:
			<b>
				<xsl:value-of select="header/server/@id" />
			</b>
		</p>
		<xsl:value-of select="value" />
	</xsl:template>

</xsl:stylesheet>

