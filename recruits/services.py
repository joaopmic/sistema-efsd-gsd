from datetime import datetime, time

from django.db.models import Count, Q
from django.utils import timezone


def totais(recruta):
    """Totais da ficha, calculados no banco (nada de contagem manual)."""
    from health.models import Dispensa
    from observations.models import FatoObservado

    fatos = recruta.fatos.aggregate(
        total=Count("id"),
        positivos=Count("id", filter=Q(tipo="POS")),
        negativos=Count("id", filter=Q(tipo="NEG")),
    )
    dias_dispensado = sum(d.dias for d in Dispensa.objects.filter(recruta=recruta))
    return {
        "idas": recruta.idas.count(),
        "dias_dispensado": dias_dispensado,
        "dispensas": recruta.dispensas.count(),
        "juntas": recruta.juntas.count(),
        "punicoes": recruta.punicoes.count(),
        "fatos_total": fatos["total"],
        "fatos_positivos": fatos["positivos"],
        "fatos_negativos": fatos["negativos"],
    }


def montar_timeline(recruta):
    """Linha do tempo única com tudo que aconteceu com o recruta (mais recente primeiro)."""
    eventos = []

    def inicio_do_dia(d):
        return timezone.make_aware(datetime.combine(d, time.min))

    for d in recruta.dispensas.all():
        eventos.append({
            "quando": inicio_do_dia(d.inicio), "tipo": "Dispensa", "cor": "warning",
            "titulo": f"{d.get_tipo_display()} ({d.inicio:%d/%m} a {d.termino:%d/%m/%Y})",
            "detalhe": f"CID: {d.cid}" if d.cid else "", "anexos": list(d.anexos),
        })
    for j in recruta.juntas.all():
        eventos.append({
            "quando": inicio_do_dia(j.inicio), "tipo": "Junta de Saúde", "cor": "warning",
            "titulo": f"Junta de Saúde ({j.inicio:%d/%m} a {j.termino:%d/%m/%Y})",
            "detalhe": f"CID: {j.cid}" if j.cid else "", "anexos": list(j.anexos),
        })
    for ida in recruta.idas.select_related("acompanhante"):
        retorno = (
            f"retorno em {timezone.localtime(ida.retornou_em):%d/%m %H:%M} ({ida.tempo_fora_texto} fora)"
            if ida.retornou_em else "ainda no GSAU-YS"
        )
        acomp = f"; acompanhante: {ida.acompanhante.rotulo_curto}" if ida.acompanhante_id else ""
        eventos.append({
            "quando": ida.saida, "tipo": "GSAU-YS", "cor": "danger",
            "titulo": f"Ida ao GSAU-YS: {ida.motivo}", "detalhe": retorno + acomp, "anexos": [],
        })
    for f in recruta.fatos.select_related("observador"):
        eventos.append({
            "quando": f.data, "tipo": "Fato observado", "cor": "success" if f.tipo == "POS" else "secondary",
            "titulo": f"Fato {f.get_tipo_display().lower()}: {f.ocorrencia}",
            "detalhe": f.medida_tomada or "", "anexos": list(f.anexos),
        })
    for p in recruta.punicoes.select_related("tipo"):
        eventos.append({
            "quando": inicio_do_dia(p.inicio), "tipo": "Punição", "cor": "dark",
            "titulo": f"{p.tipo.nome} ({p.inicio:%d/%m} a {p.termino:%d/%m/%Y})",
            "detalhe": p.fundamento, "anexos": list(p.anexos),
        })
    for h in recruta.historico_situacao.select_related("tipo"):
        fim = f" até {timezone.localtime(h.fim):%d/%m %H:%M}" if h.fim else " (atual)"
        eventos.append({
            "quando": h.inicio, "tipo": "Situação", "cor": "primary",
            "titulo": f"Situação: {h.tipo.nome}{fim}", "detalhe": h.motivo, "anexos": [],
        })
    eventos.sort(key=lambda e: e["quando"], reverse=True)
    return eventos
