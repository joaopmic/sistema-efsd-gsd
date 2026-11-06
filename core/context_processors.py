from django.conf import settings
from django.urls import reverse

from .permissions import capacidades

NAVEGACAO = [
    ("Dashboard", "core:dashboard", "ver"),
    ("Recrutas", "recruits:recruta_list", "ver"),
    ("Efetivo diário", "daily_roster:efetivo", "ver"),
    ("Dispensas", "health:dispensa_list", "ver"),
    ("Juntas de Saúde", "health:junta_list", "ver"),
    ("GSAU-YS", "hospital:ida_list", "ver"),
    ("Fatos observados", "observations:fato_list", "ver"),
    ("Punições", "discipline:punicao_list", "ver"),
    ("Passagem de serviço", "handover:passagem_list", "ver"),
    ("Pendências", "handover:pendencia_list", "ver"),
    ("Notificações", "notifications:notificacao_list", "ver"),
    ("Relatórios", "reports:index", "ver"),
    ("Livro de Alterações", "audit:log_list", "gerir"),
    ("Administração", "core:admin_index", "admin"),
]


def global_ctx(request):
    ctx = {"BOOTSTRAP_CDN": settings.BOOTSTRAP_CDN}
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return ctx

    from .models import Turma
    from .params import get_param

    caps = capacidades(user)
    itens = []
    for rotulo, nome, cap in NAVEGACAO:
        if cap in caps:
            itens.append({"rotulo": rotulo, "url": reverse(nome), "ativo": False, "inicial": rotulo[0]})
    # Marca como ativo o item cujo endereço é o prefixo mais longo do caminho atual.
    candidatos = [i for i in itens if request.path.startswith(i["url"]) and (i["url"] != "/" or request.path == "/")]
    if candidatos:
        max(candidatos, key=lambda i: len(i["url"]))["ativo"] = True

    turma = getattr(request, "turma", None)
    pendentes = 0
    if turma is not None:
        from django.db.models import Q

        from notifications.models import Notificacao

        pendentes = Notificacao.objects.filter(
            Q(destinatario__isnull=True) | Q(destinatario=user),
            turma=turma, estado__in=("ATIVA", "RECONHECIDA"),
        ).count()

    ctx.update({
        "caps": caps,
        "nav_itens": itens,
        "turma_ativa": turma,
        "turmas_disponiveis": list(Turma.objects.all()),
        "notificacoes_pendentes": pendentes,
        "modo_demo": get_param("modo_demo") == "1",
    })
    return ctx
