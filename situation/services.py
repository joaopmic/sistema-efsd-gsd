"""Cálculo da situação do recruta.

O recruta pode ter várias condições vigentes ao mesmo tempo (ida ao GSAU-YS aberta, dispensa, junta,
punição, situação manual). O sistema guarda todas e adota como situação principal a de maior
prioridade (menor número). Sem nenhuma condição, a situação é "No GSD".
"""
from django.apps import apps
from django.db import transaction
from django.utils import timezone

PADROES = [
    # codigo, nome, cor, conta_como_presente, prioridade
    ("NO_GSAU", "No GSAU-YS", "#dc3545", False, 1),
    ("JUNTA", "Em Junta de Saúde", "#d39e00", False, 2),
    ("DISP_TOTAL", "Dispensa total de expediente", "#e0a800", False, 3),
    ("PUNICAO", "Em cumprimento de punição", "#fd7e14", True, 4),
    ("ADMIN", "Fora do GSD (administrativo)", "#6c757d", False, 5),
    ("EXTERNA", "Em atividade externa", "#0d6efd", False, 6),
    ("DISP_FISICA", "Dispensa de atividade física", "#ffc107", True, 7),
    ("NO_GSD", "No GSD", "#198754", True, 8),
]


def garantir_tipos():
    from .models import TipoSituacao

    for codigo, nome, cor, presente, prioridade in PADROES:
        TipoSituacao.objects.get_or_create(
            codigo=codigo,
            defaults={"nome": nome, "cor": cor, "conta_como_presente": presente,
                      "prioridade": prioridade, "sistema": True},
        )


def tipos_por_codigo():
    from .models import TipoSituacao

    tipos = {t.codigo: t for t in TipoSituacao.objects.all()}
    if any(c not in tipos for c, *_ in PADROES):
        garantir_tipos()
        tipos = {t.codigo: t for t in TipoSituacao.objects.all()}
    return tipos


def condicoes(recruta, data=None, agora=True):
    """Condições vigentes do recruta na `data`.

    agora=True trata a ida ao GSAU-YS pelo estado atual (aberta = ainda lá); agora=False usa as datas
    (para reconstruir um dia passado)."""
    Dispensa = apps.get_model("health", "Dispensa")
    Junta = apps.get_model("health", "JuntaSaude")
    Ida = apps.get_model("hospital", "IdaGSAU")
    Punicao = apps.get_model("discipline", "Punicao")
    Manual = apps.get_model("situation", "CondicaoManual")

    data = data or timezone.localdate()
    lista = []

    for ida in Ida.objects.filter(recruta=recruta):
        saida = timezone.localtime(ida.saida).date()
        if agora:
            vigente = ida.aberta
        else:
            retorno = timezone.localtime(ida.retornou_em).date() if ida.retornou_em else None
            vigente = saida <= data and (retorno is None or retorno >= data)
        if vigente:
            lista.append({
                "codigo": "NO_GSAU", "motivo": ida.motivo,
                "origem_tipo": "IdaGSAU", "origem_id": ida.pk,
            })

    for d in Dispensa.objects.filter(recruta=recruta, inicio__lte=data, termino__gte=data):
        codigo = "DISP_TOTAL" if d.tipo == "TOTAL" else "DISP_FISICA"
        lista.append({
            "codigo": codigo, "motivo": f"{d.get_tipo_display()} até {d.termino:%d/%m/%Y}",
            "origem_tipo": "Dispensa", "origem_id": d.pk,
        })

    for j in Junta.objects.filter(recruta=recruta, inicio__lte=data, termino__gte=data):
        lista.append({
            "codigo": "JUNTA", "motivo": f"Junta de Saúde até {j.termino:%d/%m/%Y}",
            "origem_tipo": "JuntaSaude", "origem_id": j.pk,
        })

    for p in Punicao.objects.filter(recruta=recruta, inicio__lte=data, termino__gte=data):
        lista.append({
            "codigo": "PUNICAO", "motivo": f"{p.tipo.nome} até {p.termino:%d/%m/%Y}",
            "origem_tipo": "Punicao", "origem_id": p.pk,
        })

    for m in Manual.objects.filter(recruta=recruta, inicio__lte=data).select_related("tipo"):
        if m.termino is None or m.termino >= data:
            lista.append({
                "codigo": m.tipo.codigo, "motivo": m.motivo,
                "origem_tipo": "CondicaoManual", "origem_id": m.pk,
            })
    return lista


def principal_codigo(lista_condicoes, tipos):
    """Código da condição de maior prioridade; NO_GSD quando não há nenhuma."""
    codigos = {c["codigo"] for c in lista_condicoes if c["codigo"] in tipos} | {"NO_GSD"}
    return min(codigos, key=lambda c: tipos[c].prioridade)


@transaction.atomic
def recalcular_situacao(recruta, agora=None):
    """Recalcula a situação principal, atualiza o resumo no recruta e mantém o histórico de mudanças."""
    from recruits.models import Recruta

    from .models import HistoricoSituacao

    agora = agora or timezone.now()
    tipos = tipos_por_codigo()
    lista = condicoes(recruta, timezone.localtime(agora).date(), agora=True)
    cod = principal_codigo(lista, tipos)
    principal = tipos[cod]
    origem = next((c for c in lista if c["codigo"] == cod), None)
    motivo = " | ".join(f"{tipos[c['codigo']].nome}: {c['motivo']}" for c in lista if c["codigo"] in tipos)[:500]

    aberto = HistoricoSituacao.objects.filter(recruta=recruta, fim__isnull=True).order_by("-inicio").first()
    if aberto is None or aberto.tipo_id != principal.id:
        if aberto is not None:
            aberto.fim = agora
            aberto.save()
        HistoricoSituacao.objects.create(
            recruta=recruta, tipo=principal, motivo=motivo, inicio=agora,
            origem_tipo=origem["origem_tipo"] if origem else "",
            origem_id=origem["origem_id"] if origem else None,
        )
    elif aberto.motivo != motivo:
        aberto.motivo = motivo
        aberto.save()

    # update() evita ruído no Livro de Alterações: o histórico acima já registra a mudança
    Recruta.all_objects.filter(pk=recruta.pk).update(situacao_atual=principal, situacao_motivo=motivo)
    recruta.situacao_atual = principal
    recruta.situacao_motivo = motivo
    return principal
