from io import BytesIO
from decimal import Decimal
from django.http import HttpResponse
from django.contrib.staticfiles import finders

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
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
    titulo_datos=None,                 # None = no mostrar título
    col_widths=None,                   # lista de anchos para tabla principal
    resumen_en_una_linea=False,        # True = resumen en una fila (caja única)
    repeat_header=False,               # True = repetir header con filtros en páginas adicionales
):
    buffer = BytesIO()

    # ✅ Márgenes seguros para impresión (en mm)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin= 25 * mm,
        bottomMargin=18 * mm,
    )

    # ✅ Ancho útil real de la página (evita que se mochen tablas)
    ancho_util = doc.width

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
    # 1) ENCABEZADO: LOGO A LA IZQUIERDA + EMPRESA AL LADO
    # =========================================================
    logo = None
    if logo_relpath:
        logo_path = finders.find(logo_relpath)
        if logo_path:
            logo = Image(logo_path, width=28 * mm, height=28 * mm)

    if logo:
        encabezado_data = [[logo, Paragraph(nombre_empresa, style_empresa)]]
        encabezado = Table(encabezado_data, colWidths=[34 * mm, ancho_util - (34 * mm)])
    else:
        encabezado_data = [[Paragraph(nombre_empresa, style_empresa)]]
        encabezado = Table(encabezado_data, colWidths=[ancho_util])

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
    # 2) TÍTULO
    # =========================================================
    elementos.append(Paragraph(titulo, style_titulo))
    elementos.append(Spacer(1, 10))

    # =========================================================
    # 3) SUBTITULO (si existe)
    # =========================================================
    if subtitulo:
        subtitulo_limpio = str(subtitulo).strip()
        if subtitulo_limpio:
            elementos.append(Paragraph(subtitulo_limpio, style_subtitulo))
            elementos.append(Spacer(1, 8))

    # =========================================================
    # 4) DATOS / FILTROS
    # =========================================================
    filtros_visibles = []
    filtro_lineas = []
    page_header_lines = []

    def _celda_label_valor(cell):
        if isinstance(cell, (list, tuple)) and len(cell) == 2:
            etiqueta = str(cell[0]).strip()
            valor = str(cell[1]).strip()
            return f"{etiqueta}: {valor}"
        return str(cell).strip()

    if filtros:
        for row in filtros:
            if not row:
                continue
            if isinstance(row, str):
                texto = row.strip()
                if texto:
                    filtro_lineas.append(texto)
                    page_header_lines.append(texto)
                continue
            if isinstance(row, (list, tuple)) and len(row) == 1:
                texto = _celda_label_valor(row[0])
                if texto:
                    filtro_lineas.append(texto)
                    page_header_lines.append(texto)
                continue

            row_clean = []
            for x in row:
                row_clean.append(_celda_label_valor(x))

            if all(v in ("", "—", "-", "None", "null") for v in row_clean):
                continue

            filtros_visibles.append(row)
            for c in row_clean:
                if c:
                    page_header_lines.append(c)

    if filtro_lineas or filtros_visibles or page_header_lines:
        if titulo_datos:
            elementos.append(Paragraph(titulo_datos, style_seccion))

        if filtro_lineas:
            style_filtro_text = ParagraphStyle(
                "FiltroTexto",
                parent=style_normal,
                fontSize=9,
                leading=12,
                alignment=TA_LEFT,
                spaceAfter=3,
            )
            for linea in filtro_lineas:
                elementos.append(Paragraph(linea, style_filtro_text))
            elementos.append(Spacer(1, 6))

        if filtros_visibles:
            ncols = max(len(r) for r in filtros_visibles)

            def _formatear_celda_filtros(cell):
                if isinstance(cell, (list, tuple)) and len(cell) == 2:
                    etiqueta = str(cell[0]).strip()
                    valor = str(cell[1]).strip()
                    return Paragraph(f"<b>{etiqueta}:</b> {valor}", style_normal)
                if isinstance(cell, Paragraph):
                    return cell
                return Paragraph(str(cell), style_normal)

            norm = []
            for r in filtros_visibles:
                r2 = []
                for cell in r:
                    r2.append(_formatear_celda_filtros(cell))
                while len(r2) < ncols:
                    r2.append("")
                norm.append(r2)

            # ✅ colWidths usando ancho útil real
            if ncols == 2:
                cw = [ancho_util / 2, ancho_util / 2]
            else:
                cw = [ancho_util / ncols] * ncols

            tabla_filtros = Table(norm, colWidths=cw, hAlign="CENTER")
            tabla_filtros.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            elementos.append(tabla_filtros)
            elementos.append(Spacer(1, 12))

    # =========================================================
    # 5) RESUMEN
    # =========================================================
    if resumen:
        elementos.append(Paragraph("Resumen", style_seccion))

        if resumen_en_una_linea:
            # resumen = [[ "Total: ..." ]] (1 celda) o [[ "...", "...", "..." ]]
            ncols = len(resumen[0]) if resumen and resumen[0] else 1

            # Si viene multilinea con saltos, lo convertimos a Paragraph
            if ncols == 1 and isinstance(resumen[0][0], str) and "\n" in resumen[0][0]:
                resumen[0][0] = Paragraph(resumen[0][0].replace("\n", "<br/>"), style_normal)

            # ✅ Si solo 1 columna -> una caja completa (ancho útil)
            if ncols == 1:
                colWidths = [ancho_util]
            else:
                colWidths = [ancho_util / ncols] * ncols

            tabla_resumen = Table(
                resumen,
                colWidths=colWidths,
                hAlign="CENTER",
            )
        else:
            ncols = max(len(r) for r in resumen)
            if ncols == 1:
                col_widths_resumen = [ancho_util]
            elif ncols == 2:
                col_widths_resumen = [ancho_util * 0.42, ancho_util * 0.58]
            else:
                col_widths_resumen = [ancho_util / ncols] * ncols

            tabla_resumen = Table(
                resumen,
                colWidths=col_widths_resumen,
                hAlign="CENTER",
            )

        tabla_resumen.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elementos.append(tabla_resumen)
        elementos.append(Spacer(1, 14))

    # =========================================================
    # 6) TABLA PRINCIPAL
    # =========================================================
    data = [columnas] + filas

    # ✅ Si no pasan col_widths, calculamos según ancho útil real
    if col_widths is None:
        total_cols = len(columnas)
        col_widths = [ancho_util / total_cols] * total_cols

    tabla = Table(data, colWidths=col_widths, repeatRows=1, hAlign="CENTER")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.0),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    elementos.append(tabla)

    # =========================================================
    # 7) HEADER EN PÁGINAS SIGUIENTES + NÚMERO DE PÁGINA
    # =========================================================
    def _dibujar_page(canvas, doc, header=False):
        canvas.saveState()
        canvas.setFont("Helvetica", 9)

        # ✅ Header en páginas siguientes, dentro del margen (sin línea negra)
        if header and page_header_lines:
            y = A4[1] - 18 * mm         # ✅ baja el texto (más seguro para imprimir)
            line_gap = 5 * mm

            for line in page_header_lines:
                canvas.drawString(doc.leftMargin, y, line)
                y -= line_gap

        # Número de página
        page_num = f"Página {canvas.getPageNumber()}"
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(A4[0] - doc.rightMargin, doc.bottomMargin - 6 * mm, page_num)

        canvas.restoreState()


    if repeat_header:
        doc.build(
            elementos,
            onFirstPage=lambda canvas, doc: _dibujar_page(canvas, doc, header=False),
            onLaterPages=lambda canvas, doc: _dibujar_page(canvas, doc, header=True),
        )
    else:
        doc.build(
            elementos,
            onFirstPage=lambda canvas, doc: _dibujar_page(canvas, doc, header=False),
            onLaterPages=lambda canvas, doc: _dibujar_page(canvas, doc, header=False),
        )

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{nombre_archivo}.pdf"'
    response.write(pdf)
    return response