"""Geração de PDF (ReportLab), DOCX (python-docx) e Excel (openpyxl) a partir de uma estrutura simples."""
from io import BytesIO
from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.utils import timezone

TIPOS = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def resposta(conteudo, formato, nome_base):
    r = HttpResponse(conteudo, content_type=TIPOS[formato])
    r["Content-Disposition"] = f'attachment; filename="{nome_base}.{formato}"'
    r["Cache-Control"] = "private, no-store"
    return r


def _texto(v):
    if v is None or v == "":
        return "—"
    if v is True:
        return "Sim"
    if v is False:
        return "Não"
    return str(v)


def _rodape_texto(usuario, demo):
    quando = timezone.localtime().strftime("%d/%m/%Y %H:%M")
    base = f"Gerado em {quando} por {usuario}" if usuario else f"Gerado em {quando}"
    return f"DADOS DE DEMONSTRAÇÃO · {base}" if demo else base


# ----------------------------------------------------------------------------- tabelas

def tabela_pdf(titulo, subtitulo, cabecalhos, linhas, usuario="", demo=False):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = BytesIO()
    estilos = getSampleStyleSheet()
    celula = ParagraphStyle("c", parent=estilos["BodyText"], fontSize=8, leading=10)
    cab = ParagraphStyle("h", parent=celula, textColor=colors.white, fontName="Helvetica-Bold")
    pagina = landscape(A4)
    doc = SimpleDocTemplate(buf, pagesize=pagina, leftMargin=1.2 * cm, rightMargin=1.2 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.5 * cm, title=titulo)
    elementos = [Paragraph(escape(titulo), estilos["Title"])]
    if subtitulo:
        elementos.append(Paragraph(escape(subtitulo), estilos["Normal"]))
    elementos.append(Spacer(1, 0.4 * cm))
    dados = [[Paragraph(escape(str(h)), cab) for h in cabecalhos]]
    for linha in linhas:
        dados.append([Paragraph(escape(_texto(c)), celula) for c in linha])
    if len(dados) == 1:
        dados.append([Paragraph("Nenhum registro.", celula)] + [""] * (len(cabecalhos) - 1))
    tabela = Table(dados, repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14274e")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f3f6")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b8bec9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elementos.append(tabela)
    rodape = _rodape_texto(usuario, demo)

    def desenhar(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.drawString(1.2 * cm, 0.8 * cm, rodape)
        canvas.drawRightString(pagina[0] - 1.2 * cm, 0.8 * cm, f"Página {doc_.page}")
        canvas.restoreState()

    doc.build(elementos, onFirstPage=desenhar, onLaterPages=desenhar)
    return buf.getvalue()


def tabela_xlsx(titulo, subtitulo, cabecalhos, linhas, usuario="", demo=False):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = titulo[:31].replace("/", "-")
    ws.append([titulo])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([subtitulo or ""])
    ws.append([_rodape_texto(usuario, demo)])
    ws.append([])
    ws.append(list(cabecalhos))
    for celula in ws[5]:
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = PatternFill("solid", fgColor="14274E")
        celula.alignment = Alignment(vertical="center", wrap_text=True)
    for linha in linhas:
        ws.append([_texto(c) for c in linha])
    for i, h in enumerate(cabecalhos, start=1):
        maior = max([len(str(h))] + [len(_texto(l[i - 1])) for l in linhas]) if linhas else len(str(h))
        ws.column_dimensions[get_column_letter(i)].width = min(max(maior + 2, 10), 60)
    ws.freeze_panes = "A6"
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def tabela_docx(titulo, subtitulo, cabecalhos, linhas, usuario="", demo=False):
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.shared import Pt

    doc = Document()
    secao = doc.sections[0]
    secao.orientation = WD_ORIENT.LANDSCAPE
    secao.page_width, secao.page_height = secao.page_height, secao.page_width
    doc.add_heading(titulo, level=1)
    if subtitulo:
        doc.add_paragraph(subtitulo)
    tabela = doc.add_table(rows=1, cols=len(cabecalhos))
    tabela.style = "Table Grid"
    for i, h in enumerate(cabecalhos):
        tabela.rows[0].cells[i].text = str(h)
        for run in tabela.rows[0].cells[i].paragraphs[0].runs:
            run.font.bold = True
    for linha in linhas:
        cels = tabela.add_row().cells
        for i, c in enumerate(linha):
            cels[i].text = _texto(c)
            for p in cels[i].paragraphs:
                for run in p.runs:
                    run.font.size = Pt(9)
    p = doc.add_paragraph(_rodape_texto(usuario, demo))
    for run in p.runs:
        run.font.size = Pt(8)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


EXPORTADORES_TABELA = {"pdf": tabela_pdf, "xlsx": tabela_xlsx, "docx": tabela_docx}


# ----------------------------------------------------------------------------- ficha individual
# `secoes` = [{"titulo": str, "itens": [(rótulo, valor)]}  ou  {"titulo": str, "cabecalhos": [...], "linhas": [[...]]}]

def ficha_pdf(titulo, secoes, foto_path=None, usuario="", demo=False):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = BytesIO()
    estilos = getSampleStyleSheet()
    celula = ParagraphStyle("c", parent=estilos["BodyText"], fontSize=9, leading=11)
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.6 * cm, title=titulo)
    elementos = []
    cabecalho = [Paragraph(escape(titulo), estilos["Title"])]
    if foto_path:
        try:
            elementos.append(Table([[Image(foto_path, width=3 * cm, height=4 * cm), cabecalho]], colWidths=[3.4 * cm, 13 * cm]))
        except Exception:
            elementos.extend(cabecalho)
    else:
        elementos.extend(cabecalho)
    for secao in secoes:
        elementos.append(Spacer(1, 0.4 * cm))
        elementos.append(Paragraph(escape(secao["titulo"]), estilos["Heading3"]))
        if "itens" in secao:
            dados = [[Paragraph(f"<b>{escape(k)}</b>", celula), Paragraph(escape(_texto(v)), celula)] for k, v in secao["itens"]]
            largura = [5 * cm, 11.4 * cm]
        else:
            cab = [Paragraph(f"<b>{escape(str(h))}</b>", celula) for h in secao["cabecalhos"]]
            dados = [cab] + [[Paragraph(escape(_texto(c)), celula) for c in linha] for linha in secao["linhas"]]
            if len(dados) == 1:
                dados.append([Paragraph("Nenhum registro.", celula)] + [""] * (len(cab) - 1))
            largura = None
        t = Table(dados, colWidths=largura, repeatRows=1 if "cabecalhos" in secao else 0)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b8bec9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ] + ([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e4e8f0"))] if "cabecalhos" in secao else [])))
        elementos.append(t)
    rodape = _rodape_texto(usuario, demo)

    def desenhar(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.drawString(1.8 * cm, 0.9 * cm, rodape)
        canvas.drawRightString(A4[0] - 1.8 * cm, 0.9 * cm, f"Página {doc_.page}")
        canvas.restoreState()

    doc.build(elementos, onFirstPage=desenhar, onLaterPages=desenhar)
    return buf.getvalue()


def ficha_docx(titulo, secoes, foto_path=None, usuario="", demo=False):
    from docx import Document
    from docx.shared import Cm, Pt

    doc = Document()
    doc.add_heading(titulo, level=1)
    if foto_path:
        try:
            doc.add_picture(foto_path, width=Cm(3))
        except Exception:
            pass
    for secao in secoes:
        doc.add_heading(secao["titulo"], level=2)
        if "itens" in secao:
            t = doc.add_table(rows=0, cols=2)
            t.style = "Table Grid"
            for k, v in secao["itens"]:
                cels = t.add_row().cells
                cels[0].text = str(k)
                cels[1].text = _texto(v)
                for run in cels[0].paragraphs[0].runs:
                    run.font.bold = True
        else:
            t = doc.add_table(rows=1, cols=len(secao["cabecalhos"]))
            t.style = "Table Grid"
            for i, h in enumerate(secao["cabecalhos"]):
                t.rows[0].cells[i].text = str(h)
                for run in t.rows[0].cells[i].paragraphs[0].runs:
                    run.font.bold = True
            for linha in secao["linhas"]:
                cels = t.add_row().cells
                for i, c in enumerate(linha):
                    cels[i].text = _texto(c)
            if not secao["linhas"]:
                doc.add_paragraph("Nenhum registro.")
    p = doc.add_paragraph(_rodape_texto(usuario, demo))
    for run in p.runs:
        run.font.size = Pt(8)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
