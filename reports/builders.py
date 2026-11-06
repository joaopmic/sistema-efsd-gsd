"""Montagem dos dados de cada relatório de listagem: devolve (título, subtítulo, cabeçalhos, linhas)."""
from datetime import date

from django.utils import timezone

from audit.services import registrar


def _data(valor, padrao):
    try:
        return date.fromisoformat(valor) if valor else padrao
    except ValueError:
        return padrao


def _fmt_dt(dt):
    return timezone.localtime(dt).strftime("%d/%m/%Y %H:%M") if dt else ""


def _fmt_d(d):
    return d.strftime("%d/%m/%Y") if d else ""


def efetivo(request):
    from daily_roster.models import EfetivoDiario

    data = _data(request.GET.get("data"), timezone.localdate())
    linhas = EfetivoDiario.objects.filter(turma=request.turma, data=data).select_related(
        "recruta", "tipo_situacao").order_by("recruta__pelotao", "recruta__numero")
    total = linhas.count()
    presentes = sum(1 for l in linhas if l.presente)
    sub = f"Turma {request.turma.nome} · {data:%d/%m/%Y} · efetivo {total}, presentes {presentes}, ausentes {total - presentes}"
    return (
        f"Efetivo diário — {data:%d/%m/%Y}", sub,
        ["Nº", "Nome de guerra", "Nome", "Pelotão", "Grupo", "Situação", "Presente", "Ajustado"],
        [[f"{l.recruta.numero:03d}", l.recruta.nome_guerra, l.recruta.nome_completo, l.recruta.get_pelotao_display(),
          l.recruta.grupo, l.tipo_situacao.nome, l.presente, l.ajustado] for l in linhas],
    )


def recrutas(request):
    from recruits.models import Recruta

    qs = Recruta.objects.filter(turma=request.turma).select_related("situacao_atual").order_by("numero")
    return (
        "Relação de recrutas", f"Turma {request.turma.nome}",
        ["Nº", "Nome de guerra", "Nome completo", "Pelotão", "Grupo", "SARAM", "Situação atual", "Motivo"],
        [[f"{r.numero:03d}", r.nome_guerra, r.nome_completo, r.get_pelotao_display(), r.grupo, r.saram,
          r.situacao_atual.nome if r.situacao_atual else "No GSD", r.situacao_motivo] for r in qs],
    )


def gsau(request):
    from hospital.models import IdaGSAU

    qs = IdaGSAU.objects.filter(recruta__turma=request.turma, aberta=True).select_related("recruta", "acompanhante").order_by("saida")
    return (
        "Recrutas no GSAU-YS", f"Turma {request.turma.nome} · posição em {_fmt_dt(timezone.now())}",
        ["Nº", "Nome de guerra", "Saída", "Motivo", "Acompanhante", "Tempo fora"],
        [[f"{i.recruta.numero:03d}", i.recruta.nome_guerra, _fmt_dt(i.saida), i.motivo,
          i.acompanhante.rotulo_curto if i.acompanhante else "", i.tempo_fora_texto] for i in qs],
    )


def dispensas(request):
    from health.models import Dispensa

    hoje = timezone.localdate()
    qs = Dispensa.objects.filter(recruta__turma=request.turma, inicio__lte=hoje, termino__gte=hoje).select_related("recruta").order_by("recruta__numero")
    return (
        "Dispensas vigentes", f"Turma {request.turma.nome} · em {_fmt_d(hoje)}",
        ["Nº", "Nome de guerra", "Tipo", "CID", "Início", "Término", "Dias restantes"],
        [[f"{d.recruta.numero:03d}", d.recruta.nome_guerra, d.get_tipo_display(), d.cid, _fmt_d(d.inicio),
          _fmt_d(d.termino), (d.termino - hoje).days] for d in qs],
    )


def juntas(request):
    from health.models import JuntaSaude

    hoje = timezone.localdate()
    qs = JuntaSaude.objects.filter(recruta__turma=request.turma, inicio__lte=hoje, termino__gte=hoje).select_related("recruta").order_by("termino")
    return (
        "Juntas de Saúde vigentes", f"Turma {request.turma.nome} · em {_fmt_d(hoje)}",
        ["Nº", "Nome de guerra", "CID", "Início", "Término", "Dias restantes"],
        [[f"{j.recruta.numero:03d}", j.recruta.nome_guerra, j.cid, _fmt_d(j.inicio), _fmt_d(j.termino),
          (j.termino - hoje).days] for j in qs],
    )


def fatos(request):
    from observations.models import FatoObservado

    hoje = timezone.localdate()
    de = _data(request.GET.get("de"), date(hoje.year, 1, 1))
    ate = _data(request.GET.get("ate"), hoje)
    qs = FatoObservado.objects.filter(
        recruta__turma=request.turma, data__date__gte=de, data__date__lte=ate,
    ).select_related("recruta", "observador").order_by("-data")
    return (
        "Fatos observados", f"Turma {request.turma.nome} · de {_fmt_d(de)} a {_fmt_d(ate)}",
        ["Nº", "Nome de guerra", "Data", "Tipo", "Ocorrência", "Medida tomada", "Observador"],
        [[f"{f.recruta.numero:03d}", f.recruta.nome_guerra, _fmt_dt(f.data), f.get_tipo_display(), f.ocorrencia,
          f.medida_tomada, str(f.observador) if f.observador else ""] for f in qs],
    )


def punicoes(request):
    from discipline.models import Punicao

    qs = Punicao.objects.filter(recruta__turma=request.turma).select_related("recruta", "tipo").order_by("-inicio")
    return (
        "Punições", f"Turma {request.turma.nome}",
        ["Nº", "Nome de guerra", "Tipo", "Fundamento", "Início", "Término", "Situação"],
        [[f"{p.recruta.numero:03d}", p.recruta.nome_guerra, p.tipo.nome, p.fundamento, _fmt_d(p.inicio),
          _fmt_d(p.termino), p.situacao_texto] for p in qs],
    )


# chave -> (título do relatório, descrição, parâmetros extras, função)
RELATORIOS = {
    "efetivo": ("Efetivo diário", "Situação de cada recruta em uma data, com totais.", "data", efetivo),
    "recrutas": ("Relação de recrutas", "Todos os recrutas da turma e a situação atual.", "", recrutas),
    "gsau": ("Recrutas no GSAU-YS", "Quem está no GSAU-YS agora e há quanto tempo.", "", gsau),
    "dispensas": ("Dispensas vigentes", "Dispensas em vigor hoje, com dias restantes.", "", dispensas),
    "juntas": ("Juntas de Saúde vigentes", "Juntas em vigor hoje e quando terminam.", "", juntas),
    "fatos": ("Fatos observados", "Fatos positivos e negativos em um período.", "periodo", fatos),
    "punicoes": ("Punições", "Todas as punições da turma.", "", punicoes),
}


def registrar_exportacao(chave, formato):
    registrar("EXPORTAR", modulo=f"reports.{chave}", registro_repr=f"Relatório {chave} ({formato})")
