"""Regras de alerta. Cada regra é "idempotente": se a condição vale, garante UMA notificação ativa;
se deixou de valer, resolve a notificação. Por isso pode rodar a qualquer momento (ao salvar um
registro ou pela rotina agendada) sem duplicar nada."""
from django.utils import timezone

from core.params import get_int

from .models import Notificacao

ATIVOS = ("ATIVA", "RECONHECIDA")
P = Notificacao.Prioridade


def sincronizar(turma, regra, origem_id, deve_existir, *, categoria="", prioridade=P.MEDIA,
                mensagem="", recruta=None, destinatario=None):
    ativa = Notificacao.objects.filter(regra=regra, origem_id=origem_id, estado__in=ATIVOS).first()
    if deve_existir:
        if ativa is not None:
            if ativa.mensagem != mensagem or ativa.prioridade != prioridade:
                ativa.mensagem, ativa.prioridade = mensagem, prioridade
                ativa.save()
            return ativa
        if Notificacao.objects.filter(regra=regra, origem_id=origem_id, resolvida_manual=True).exists():
            return None  # alguém já resolveu manualmente: não reabrir sozinho
        return Notificacao.objects.create(
            turma=turma, regra=regra, origem_id=origem_id, categoria=categoria, prioridade=prioridade,
            mensagem=mensagem[:300], recruta=recruta, destinatario=destinatario,
        )
    if ativa is not None:
        ativa.estado = Notificacao.Estado.RESOLVIDA
        ativa.resolvida_em = timezone.now()
        ativa.save()
    return None


def _rotulo(recruta):
    return f"Recruta {recruta.numero:03d} ({recruta.nome_guerra})"


def avaliar_recruta(recruta):
    """Avalia as regras ligadas a um recruta. Turmas arquivadas não geram alertas."""
    turma = recruta.turma
    if turma.status != "FORMACAO" or recruta.deleted_at is not None:
        return
    hoje = timezone.localdate()
    agora = timezone.now()
    nome = _rotulo(recruta)

    # 1) Permanência no GSAU-YS além do limite
    limite_h = get_int("horas_alerta_gsau")
    for ida in recruta.idas.all():
        minutos = int((agora - ida.saida).total_seconds() // 60)
        sincronizar(
            turma, "GSAU_LONGO", ida.pk, ida.aberta and minutos >= limite_h * 60,
            categoria="GSAU-YS", prioridade=P.ALTA, recruta=recruta,
            mensagem=f"{nome} está no GSAU-YS há {minutos // 60}h{minutos % 60:02d}.",
        )

    # 2) Dispensa perto do fim
    aviso_d = get_int("dias_aviso_dispensa")
    for d in recruta.dispensas.all():
        dias = (d.termino - hoje).days
        sincronizar(
            turma, "DISPENSA_FIM", d.pk, 0 <= dias <= aviso_d,
            categoria="Dispensa", prioridade=P.MEDIA, recruta=recruta,
            mensagem=f"Dispensa de {nome} termina " + ("hoje." if dias == 0 else f"em {dias} dia(s) ({d.termino:%d/%m}).")
            if dias >= 0 else "",
        )

    # 3) Junta de Saúde: pedir nova junta com antecedência (se não houver uma posterior)
    antecedencia = get_int("antecedencia_junta_dias")
    for j in recruta.juntas.all():
        dias = (j.termino - hoje).days
        renovada = recruta.juntas.filter(termino__gt=j.termino).exists()
        sincronizar(
            turma, "JUNTA_RENOVAR", j.pk, 0 <= dias <= antecedencia and not renovada,
            categoria="Junta de Saúde", prioridade=P.ALTA, recruta=recruta,
            mensagem=f"Solicitar Nova Junta de Saúde para o Recruta {recruta.numero:03d}",
        )

    # 4) Punição perto do fim
    aviso_p = get_int("dias_aviso_punicao")
    for p in recruta.punicoes.all():
        dias = (p.termino - hoje).days
        sincronizar(
            turma, "PUNICAO_FIM", p.pk, 0 <= dias <= aviso_p,
            categoria="Punição", prioridade=P.MEDIA, recruta=recruta,
            mensagem=f"Punição de {nome} termina " + ("hoje." if dias == 0 else f"em {dias} dia(s) ({p.termino:%d/%m}).")
            if dias >= 0 else "",
        )

    # 5) Total de fatos observados
    limiar = get_int("limiar_fatos")
    total = recruta.fatos.count()
    sincronizar(
        turma, "FATOS_LIMIAR", recruta.pk, total >= limiar,
        categoria="Fatos observados", prioridade=P.MEDIA, recruta=recruta,
        mensagem=f"{nome} acumulou {total} fatos observados (limite configurado: {limiar}).",
    )


def avaliar_tudo():
    """Recalcula situação e alertas de todas as turmas em formação (rotina agendada)."""
    from core.models import Turma
    from recruits.models import Recruta
    from situation.services import recalcular_situacao

    for turma in Turma.objects.filter(status="FORMACAO"):
        for recruta in Recruta.objects.filter(turma=turma).select_related("turma"):
            recalcular_situacao(recruta)
            avaliar_recruta(recruta)
