from io import BytesIO
from decimal import Decimal
from django.http import HttpResponse
from django.contrib.staticfiles import finders

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
)


def pdf_tabla(
    nombre_archivo,
    titulo,
    subtitulo,
    columnas,
    filas,
    resumen=None,
    filtros=None,
    logo_relpath=None,
    nombre_empresa="BEMORE",

    # ✅ NUEVOS
    titulo_datos="Filtros aplicados",   # None = no mostrar título
    col_widths=None,                    # lista de anchos para tabla principal
    resumen_en_una_linea=False,         # True = resumen en una fila (caja única)
):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18,
        leftMargin=18,
        topMargin=18,
        bottomMargin=18,
    )

    styles = getSampleStyleSheet()

    style_normal = ParagraphStyle(
        "NormalCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.black,
        alignment=TA_LEFT,
    )

    style_empresa = ParagraphStyle(
        "Empresa",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=22,
        textColor=colors.black,
        alignment=TA_LEFT,
        spaceAfter=0,
        spaceBefore=0,
    )

    style_titulo = ParagraphStyle(
        "TituloReporte",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceAfter=8,
        spaceBefore=0,
    )

    style_subtitulo = ParagraphStyle(
        "Subtitulo",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.black,
        alignment=TA_LEFT,
        spaceAfter=6,
    )

    style_seccion = ParagraphStyle(
        "Seccion",
        parent=styles["Heading3"],
        fontName="Helvetica-BoldOblique",
        fontSize=11,
        leading=14,
        textColor=colors.black,
        alignment=TA_LEFT,
        spaceBefore=6,
        spaceAfter=6,
    )

    elementos = []

    # =========================================================
    # 1) ENCABEZADO: LOGO A LA IZQUIERDA + BEMORE AL LADO
    # =========================================================
    logo = None
    if logo_relpath:
        logo_path = finders.find(logo_relpath)
        if logo_path:
            logo = Image(logo_path, width=28 * mm, height=28 * mm)

    if logo:
        encabezado_data = [[logo, Paragraph(nombre_empresa, style_empresa)]]
        encabezado = Table(encabezado_data, colWidths=[34 * mm, 140 * mm])
    else:
        encabezado_data = [[Paragraph(nombre_empresa, style_empresa)]]
        encabezado = Table(encabezado_data, colWidths=[174 * mm])

    encabezado.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    elementos.append(encabezado)
    elementos.append(Spacer(1, 12))

    # =========================================================
    # 2) TITULO DEL REPORTE
    # =========================================================
    elementos.append(Paragraph(titulo, style_titulo))
    elementos.append(Spacer(1, 10))

    # =========================================================
    # 3) SUBTITULO (solo si existe)
    # =========================================================
    if subtitulo:
        subtitulo_limpio = str(subtitulo).strip()
        if subtitulo_limpio:
            elementos.append(Paragraph(subtitulo_limpio, style_subtitulo))
            elementos.append(Spacer(1, 8))

    # =========================================================
    # 4) DATOS / FILTROS (solo si hay valores reales)
    # =========================================================
    filtros_visibles = []
    if filtros:
        for row in filtros:
            if not row:
                continue
            # si es fila tipo ["Etiqueta","Valor"] o ["dato1","dato2"]
            row_clean = [str(x).strip() for x in row]
            # oculta filas completamente vacías
            if all(v in ("", "—", "-", "None", "null") for v in row_clean):
                continue
            filtros_visibles.append(row_clean)

    if filtros_visibles:
        # ✅ si titulo_datos es None, NO mostramos "Filtros aplicados"
        if titulo_datos:
            elementos.append(Paragraph(titulo_datos, style_seccion))

        ncols = max(len(r) for r in filtros_visibles)
        # normalizamos filas a ncols
        norm = []
        for r in filtros_visibles:
            r2 = r[:]
            while len(r2) < ncols:
                r2.append("")
            norm.append(r2)

        # ancho por defecto para 2 columnas (como tu layout)
        if ncols == 2:
            cw = [90 * mm, 90 * mm]
        else:
            # fallback proporcional
            ancho_total = 180 * mm
            cw = [ancho_total / ncols] * ncols

        tabla_filtros = Table(norm, colWidths=cw, hAlign="LEFT")
        tabla_filtros.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elementos.append(tabla_filtros)
        elementos.append(Spacer(1, 12))

    # =========================================================
    # 5) RESUMEN
    # =========================================================
    if resumen:
        elementos.append(Paragraph("Resumen", style_seccion))

        if resumen_en_una_linea:
            # resumen debe venir como: [[ "Total: ...", "Pagado: ...", "Saldo: ..." ]]
            tabla_resumen = Table(
                resumen,
                colWidths=[60 * mm, 60 * mm, 60 * mm],
                hAlign="LEFT",
            )
        else:
            tabla_resumen = Table(
                resumen,
                colWidths=[75 * mm, 105 * mm],
                hAlign="LEFT",
            )

        tabla_resumen.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elementos.append(tabla_resumen)
        elementos.append(Spacer(1, 14))

    # =========================================================
    # 6) TABLA PRINCIPAL
    # =========================================================
    data = [columnas] + filas

    # Si no te pasan col_widths, usamos el cálculo simple de antes
    if col_widths is None:
        total_cols = len(columnas)
        ancho_total = 180 * mm
        col_width = ancho_total / total_cols
        col_widths = [col_width] * total_cols

    tabla = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    elementos.append(tabla)

    doc.build(elementos)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{nombre_archivo}.pdf"'
    response.write(pdf)
    return response