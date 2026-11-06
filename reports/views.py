from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from audit.services import registrar
from core.params import get_param
from core.permissions import exige
from recruits.models import ChecklistDocumento, DadosSaude, Recruta
from recruits.services import montar_timeline, totais

from . import exporters
from .builders import RELATORIOS, registrar_exportacao


def _formato(request):
    formato = request.GET.get("formato", "pdf")
    if formato not in exporters.TIPOS:
        raise Http404("Formato inválido.")
    return formato


@exige("ver")
def index(request):
    if request.turma is None:
        return render(request, "core/sem_turma.html")
    return render(request, "reports/index.html", {
        "relatorios": [
            {"chave": c, "titulo": t, "descricao": d, "extra": e} for c, (t, d, e, _f) in RELATORIOS.items()
        ],
        "hoje": timezone.localdate(),
    })


@exige("ver")
def relatorio(request, chave):
    if request.turma is None or chave not in RELATORIOS:
        raise Http404
    formato = _formato(request)
    _titulo, _desc, _extra, funcao = RELATORIOS[chave]
    titulo, subtitulo, cabecalhos, linhas = funcao(request)
    registrar_exportacao(chave, formato)
    conteudo = exporters.EXPORTADORES_TABELA[formato](
        titulo, subtitulo, cabecalhos, linhas,
        usuario=str(request.user), demo=get_param("modo_demo") == "1",
    )
    return exporters.resposta(conteudo, formato, f"{chave}-{timezone.localdate():%Y%m%d}")


def _secoes_ficha(recruta, escolhidas):
    secoes = []
    if "dados" in escolhidas:
        t = totais(recruta)
        secoes.append({"titulo": "Dados do recruta", "itens": [
            ("Número", f"{recruta.numero:03d}"), ("Nome completo", recruta.nome_completo),
            ("Nome de guerra", recruta.nome_guerra), ("Pelotão", recruta.get_pelotao_display()),
            ("Grupo", recruta.grupo), ("SARAM", recruta.saram), ("CPF", recruta.cpf_formatado),
            ("Data de nascimento", recruta.data_nascimento.strftime("%d/%m/%Y") if recruta.data_nascimento else ""),
            ("Telefone", recruta.telefone), ("E-mail", recruta.email_pessoal),
            ("Pai", recruta.nome_pai), ("Mãe", recruta.nome_mae),
            ("Telefone do responsável", recruta.telefone_responsavel), ("Endereço", recruta.endereco),
            ("Situação atual", recruta.situacao_atual.nome if recruta.situacao_atual else "No GSD"),
        ]})
        secoes.append({"titulo": "Totais", "itens": [
            ("Idas ao GSAU-YS", t["idas"]), ("Dias dispensado", t["dias_dispensado"]),
            ("Fatos observados", f'{t["fatos_total"]} ({t["fatos_positivos"]} positivos, {t["fatos_negativos"]} negativos)'),
            ("Punições", t["punicoes"]),
        ]})
    if "saude" in escolhidas:
        saude = DadosSaude.objects.filter(recruta=recruta).first()
        secoes.append({"titulo": "Saúde (protegido)", "itens": [
            ("Tipo sanguíneo", saude.tipo_sanguineo if saude else ""),
            ("Alergias", saude.alergias if saude else ""),
            ("Observações", saude.observacoes if saude else ""),
        ]})
        registrar("CONSULTAR", modulo="recruits.DadosSaude", registro_id=recruta.pk,
                  registro_repr=str(recruta), justificativa="Seção de saúde incluída em exportação da ficha")
    if "historico" in escolhidas:
        secoes.append({
            "titulo": "Histórico", "cabecalhos": ["Quando", "Tipo", "Evento", "Detalhe"],
            "linhas": [
                [timezone.localtime(e["quando"]).strftime("%d/%m/%Y %H:%M"), e["tipo"], e["titulo"], e["detalhe"]]
                for e in montar_timeline(recruta)
            ],
        })
    if "documentos" in escolhidas:
        entregues = {c.documento: c.entregue for c in ChecklistDocumento.objects.filter(recruta=recruta)}
        secoes.append({
            "titulo": "Documentos entregues", "cabecalhos": ["Documento", "Entregue"],
            "linhas": [[nome, entregues.get(cod, False)] for cod, nome in ChecklistDocumento.DOCUMENTOS],
        })
    return secoes


@exige("ver")
def ficha(request, pk):
    recruta = get_object_or_404(Recruta.objects.select_related("turma", "situacao_atual"), pk=pk)
    formato = _formato(request)
    if formato == "xlsx":
        raise Http404("A ficha individual é exportada em PDF ou DOCX.")
    escolhidas = set(request.GET.getlist("secoes")) or {"dados", "historico"}
    secoes = _secoes_ficha(recruta, escolhidas)
    foto = None
    if recruta.foto:
        try:
            foto = recruta.foto.path
        except (ValueError, NotImplementedError):
            foto = None
    registrar("EXPORTAR", modulo="recruits.Recruta", registro_id=recruta.pk, registro_repr=str(recruta),
              justificativa=f"Ficha individual ({formato}); seções: {', '.join(sorted(escolhidas))}")
    titulo = f"Ficha individual — {recruta.numero:03d} {recruta.nome_guerra}"
    gerar = exporters.ficha_pdf if formato == "pdf" else exporters.ficha_docx
    conteudo = gerar(titulo, secoes, foto_path=foto, usuario=str(request.user), demo=get_param("modo_demo") == "1")
    return exporters.resposta(conteudo, formato, f"ficha-{recruta.numero:03d}-{recruta.nome_guerra}".replace(" ", "_"))


@exige("ver")
def passagem_pdf(request, pk):
    from daily_roster.services import resumo
    from handover.models import PassagemServico

    passagem = get_object_or_404(PassagemServico.objects.select_related("entrega", "recebe", "turma"), pk=pk)
    linhas_pend = [
        [p.recruta.rotulo_curto if p.recruta else "", p.descricao, p.origem_texto, p.situacao_texto]
        for p in passagem.pendencias.select_related("recruta")
    ]
    por_situacao = {}
    for r in Recruta.objects.filter(turma=passagem.turma).select_related("situacao_atual"):
        nome = r.situacao_atual.nome if r.situacao_atual else "No GSD"
        por_situacao[nome] = por_situacao.get(nome, 0) + 1
    secoes = [
        {"titulo": "Passagem", "itens": [
            ("Turma", passagem.turma.nome), ("Entrega", str(passagem.entrega)), ("Recebe", str(passagem.recebe)),
            ("Data e hora", timezone.localtime(passagem.data_hora).strftime("%d/%m/%Y %H:%M")),
            ("Confirmada em", timezone.localtime(passagem.confirmada_em).strftime("%d/%m/%Y %H:%M") if passagem.confirmada_em else "Aguardando confirmação"),
            ("Observações", passagem.observacoes),
        ]},
        {"titulo": "Efetivo no momento da consulta", "itens": sorted(por_situacao.items())},
        {"titulo": "Pendências vinculadas", "cabecalhos": ["Recruta", "Descrição", "Origem", "Situação"], "linhas": linhas_pend},
    ]
    registrar("EXPORTAR", modulo="handover.PassagemServico", registro_id=passagem.pk, registro_repr=str(passagem))
    conteudo = exporters.ficha_pdf(
        "Passagem de serviço", secoes, usuario=str(request.user), demo=get_param("modo_demo") == "1",
    )
    return exporters.resposta(conteudo, "pdf", f"passagem-{passagem.data_hora:%Y%m%d-%H%M}")
