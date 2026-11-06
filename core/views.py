from django.contrib import messages
from django.db.models import Count
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Anexo, Turma
from .permissions import exige
from .services import arquivar_turma


@exige("ver")
def dashboard(request):
    turma = request.turma
    if turma is None:
        return render(request, "core/sem_turma.html")
    if not turma.editavel:
        return render(request, "core/dashboard_arquivada.html", {"turma": turma})

    from handover.models import Pendencia
    from notifications.models import Notificacao
    from recruits.models import Recruta

    recrutas = Recruta.objects.filter(turma=turma)
    por_codigo = {
        (cod or ""): n
        for cod, n in recrutas.values_list("situacao_atual__codigo").annotate(n=Count("id"))
    }
    total = recrutas.count()
    presentes = recrutas.filter(situacao_atual__conta_como_presente=True).count()
    sem_situacao = por_codigo.get("", 0)  # recrutas ainda sem situação calculada contam como no GSD
    lista = "recruits:recruta_list"
    alertas = Notificacao.objects.filter(turma=turma, estado__in=("ATIVA", "RECONHECIDA")).count()
    pendencias = Pendencia.objects.filter(turma=turma, resolvida=False).count()
    dias = (turma.data_formatura - timezone.localdate()).days

    def sit(codigo):
        return por_codigo.get(codigo, 0) + (sem_situacao if codigo == "NO_GSD" else 0)

    cartoes = [
        {"titulo": "Efetivo total", "valor": total, "cor": "azul", "url": lista, "param": ""},
        {"titulo": "Presentes no GSD", "valor": presentes + sem_situacao, "cor": "verde", "url": lista, "param": "?presentes=1"},
        {"titulo": "No GSAU-YS", "valor": sit("NO_GSAU"), "cor": "vermelho", "url": lista, "param": "?situacao=NO_GSAU"},
        {"titulo": "Dispensa total de expediente", "valor": sit("DISP_TOTAL"), "cor": "amarelo", "url": lista, "param": "?situacao=DISP_TOTAL"},
        {"titulo": "Dispensa de atividade física", "valor": sit("DISP_FISICA"), "cor": "amarelo", "url": lista, "param": "?situacao=DISP_FISICA"},
        {"titulo": "Em Junta de Saúde", "valor": sit("JUNTA"), "cor": "amarelo", "url": lista, "param": "?situacao=JUNTA"},
        {"titulo": "Em cumprimento de punição", "valor": sit("PUNICAO"), "cor": "amarelo", "url": lista, "param": "?situacao=PUNICAO"},
        {"titulo": "Fora do GSD (administrativo)", "valor": sit("ADMIN"), "cor": "cinza", "url": lista, "param": "?situacao=ADMIN"},
        {"titulo": "Em atividade externa", "valor": sit("EXTERNA"), "cor": "cinza", "url": lista, "param": "?situacao=EXTERNA"},
        {"titulo": "Alertas ativos", "valor": alertas, "cor": "vermelho" if alertas else "verde", "url": "notifications:notificacao_list", "param": ""},
        {"titulo": "Pendências abertas", "valor": pendencias, "cor": "amarelo" if pendencias else "verde", "url": "handover:pendencia_list", "param": ""},
        {"titulo": "Dias para a formatura", "valor": max(dias, 0), "cor": "azul", "url": "daily_roster:efetivo", "param": ""},
    ]
    alertas_lista = (
        Notificacao.objects.filter(turma=turma, estado__in=("ATIVA", "RECONHECIDA"))
        .select_related("recruta").order_by("prioridade", "-created_at")[:10]
    )
    return render(request, "core/dashboard.html", {
        "turma": turma, "cartoes": cartoes, "alertas": alertas_lista,
    })


@exige("ver")
@require_POST
def selecionar_turma(request):
    turma = Turma.objects.filter(pk=request.POST.get("turma")).first() if request.POST.get("turma") else None
    if turma is not None:
        request.session["turma_id"] = str(turma.pk)
    return redirect("core:dashboard")


@exige("admin")
def admin_index(request):
    return render(request, "core/admin_index.html")


@exige("admin")
@require_POST
def turma_arquivar(request, pk):
    turma = get_object_or_404(Turma, pk=pk)
    if not turma.editavel:
        messages.info(request, "Esta turma já está arquivada.")
    else:
        arquivar_turma(turma)
        messages.success(
            request,
            f"Turma {turma.nome} arquivada. Fichas, relatórios e exportações continuam disponíveis para consulta.",
        )
    return redirect("core:turma_list")


@exige("ver")
def anexo_download(request, pk):
    """Entrega um anexo somente a usuário autenticado e registra a consulta."""
    from audit.services import registrar

    anexo = get_object_or_404(Anexo, pk=pk)
    try:
        arquivo = anexo.arquivo.open("rb")
    except FileNotFoundError:
        raise Http404("Arquivo não encontrado no armazenamento.")
    registrar(
        "CONSULTAR", modulo="core.Anexo", registro_id=anexo.pk,
        registro_repr=anexo.nome_original, justificativa="Abertura de anexo",
    )
    resposta = FileResponse(arquivo, content_type=anexo.tipo_mime)
    resposta["Content-Disposition"] = f'inline; filename="{anexo.nome_original}"'
    resposta["X-Content-Type-Options"] = "nosniff"
    resposta["Cache-Control"] = "private, no-store"
    return resposta


def erro_403(request, exception=None):
    return render(request, "403.html", status=403)


def erro_404(request, exception=None):
    return render(request, "404.html", status=404)


def erro_500(request):
    return render(request, "500.html", status=500)
