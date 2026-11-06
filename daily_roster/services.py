from django.db import transaction
from django.utils import timezone

from situation.services import condicoes, principal_codigo, tipos_por_codigo

from .models import AjusteEfetivo, EfetivoDiario


@transaction.atomic
def gerar_efetivo(turma, data):
    """Monta o efetivo do dia a partir dos registros existentes.

    - dia passado: só cria o que falta (o que já foi montado não é reescrito);
    - hoje: atualiza as linhas não ajustadas conforme a situação atual;
    - dia futuro: não gera.
    """
    from recruits.models import Recruta

    hoje = timezone.localdate()
    if data > hoje:
        raise ValueError("Não é possível gerar o efetivo de uma data futura.")
    tipos = tipos_por_codigo()
    criados = atualizados = 0
    for recruta in Recruta.objects.filter(turma=turma).order_by("numero"):
        cod = principal_codigo(condicoes(recruta, data, agora=(data == hoje)), tipos)
        linha = EfetivoDiario.objects.filter(data=data, recruta=recruta).first()
        if linha is None:
            EfetivoDiario.objects.create(turma=turma, data=data, recruta=recruta, tipo_situacao=tipos[cod])
            criados += 1
        elif data == hoje and not linha.ajustado and linha.tipo_situacao_id != tipos[cod].id:
            linha.tipo_situacao = tipos[cod]
            linha.save()
            atualizados += 1
    return criados, atualizados


@transaction.atomic
def ajustar_efetivo(linha, tipo_novo, justificativa, usuario):
    """Ajuste manual da situação de um dia. Sem justificativa, abre uma pendência."""
    from handover.models import Pendencia

    justificativa = (justificativa or "").strip()
    AjusteEfetivo.objects.create(
        efetivo=linha, tipo_anterior=linha.tipo_situacao, tipo_novo=tipo_novo,
        justificativa=justificativa, usuario=usuario,
    )
    linha.tipo_situacao = tipo_novo
    linha.ajustado = True
    linha.save()
    if not justificativa:
        Pendencia.objects.create(
            turma=linha.turma, recruta=linha.recruta, origem="ajuste_efetivo",
            descricao=f"Ajuste de efetivo de {linha.data:%d/%m/%Y} sem justificativa: informar o motivo.",
        )
    return linha


def resumo(linhas):
    """Totais do dia: efetivo, presentes e contagem por situação."""
    por_tipo = {}
    presentes = 0
    for linha in linhas:
        por_tipo.setdefault(linha.tipo_situacao, 0)
        por_tipo[linha.tipo_situacao] += 1
        if linha.presente:
            presentes += 1
    total = len(linhas)
    return {
        "total": total, "presentes": presentes, "ausentes": total - presentes,
        "por_tipo": sorted(por_tipo.items(), key=lambda kv: kv[0].prioridade),
    }
