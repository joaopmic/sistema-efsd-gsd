from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from audit.services import registrar
from core.permissions import exige, pode
from situation.models import TipoSituacao

from .forms import DadosSaudeForm
from .models import ChecklistDocumento, DadosSaude, Recruta
from .services import montar_timeline, totais


@exige("ver")
def lista(request):
    if request.turma is None:
        return render(request, "core/sem_turma.html")
    qs = Recruta.objects.filter(turma=request.turma).select_related("situacao_atual")
    q = request.GET.get("q", "").strip()
    pelotao = request.GET.get("pelotao", "")
    grupo = request.GET.get("grupo", "")
    situacao = request.GET.get("situacao", "")
    presentes = request.GET.get("presentes", "")
    if q:
        cond = Q(nome_completo__icontains=q) | Q(nome_guerra__icontains=q) | Q(saram__icontains=q)
        if q.isdigit():
            cond |= Q(numero=int(q))
        qs = qs.filter(cond)
    if pelotao:
        qs = qs.filter(pelotao=pelotao)
    if grupo:
        qs = qs.filter(grupo=grupo)
    if situacao:
        qs = qs.filter(situacao_atual__codigo=situacao)
    if presentes == "1":
        qs = qs.filter(Q(situacao_atual__conta_como_presente=True) | Q(situacao_atual__isnull=True))
    page = Paginator(qs.order_by("numero"), 100).get_page(request.GET.get("page"))
    grupos = (
        Recruta.objects.filter(turma=request.turma).exclude(grupo="")
        .order_by("grupo").values_list("grupo", flat=True).distinct()
    )
    return render(request, "recruits/list.html", {
        "page": page, "q": q, "pelotao": pelotao, "grupo": grupo, "situacao": situacao, "presentes": presentes,
        "situacoes": TipoSituacao.objects.all(), "grupos": list(grupos),
        "pode_criar": pode(request.user, "gerir") and request.turma.editavel,
    })


@exige("ver")
def ficha(request, pk):
    recruta = get_object_or_404(Recruta.objects.select_related("turma", "situacao_atual"), pk=pk)
    aba = request.GET.get("aba", "dados")
    contexto = {
        "r": recruta, "aba": aba, "totais": totais(recruta),
        "editavel": recruta.turma.editavel and pode(request.user, "gerir"),
    }
    if aba == "historico":
        contexto["timeline"] = montar_timeline(recruta)
    elif aba == "saude":
        contexto["saude"] = DadosSaude.objects.filter(recruta=recruta).first()
        registrar(
            "CONSULTAR", modulo="recruits.DadosSaude", registro_id=recruta.pk,
            registro_repr=str(recruta), justificativa="Consulta à seção de saúde da ficha",
        )
    elif aba == "documentos":
        entregues = {c.documento: c.entregue for c in ChecklistDocumento.objects.filter(recruta=recruta)}
        contexto["documentos"] = [
            {"codigo": cod, "nome": nome, "entregue": entregues.get(cod, False)}
            for cod, nome in ChecklistDocumento.DOCUMENTOS
        ]
    return render(request, "recruits/ficha.html", contexto)


@exige("ver")
def foto(request, pk):
    recruta = get_object_or_404(Recruta, pk=pk)
    if not recruta.foto:
        raise Http404("Recruta sem foto.")
    try:
        arquivo = recruta.foto.open("rb")
    except FileNotFoundError:
        raise Http404("Foto não encontrada no armazenamento.")
    resposta = FileResponse(arquivo)
    resposta["Cache-Control"] = "private, max-age=300"
    resposta["X-Content-Type-Options"] = "nosniff"
    return resposta


@exige("gerir", escrita=True)
def saude_editar(request, pk):
    recruta = get_object_or_404(Recruta, pk=pk, turma=request.turma)
    saude = DadosSaude.objects.filter(recruta=recruta).first() or DadosSaude(recruta=recruta)
    form = DadosSaudeForm(request.POST or None, instance=saude, turma=request.turma, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Dados de saúde atualizados.")
        return redirect(f"{recruta.get_absolute_url()}?aba=saude")
    return render(request, "crud/form.html", {
        "form": form, "titulo": f"Dados de saúde — {recruta}", "voltar": f"{recruta.get_absolute_url()}?aba=saude",
    })


@exige("gerir", escrita=True)
@require_POST
def checklist_salvar(request, pk):
    recruta = get_object_or_404(Recruta, pk=pk, turma=request.turma)
    marcados = set(request.POST.getlist("entregue"))
    for codigo, _nome in ChecklistDocumento.DOCUMENTOS:
        item, _ = ChecklistDocumento.objects.get_or_create(recruta=recruta, documento=codigo)
        entregue = codigo in marcados
        if item.entregue != entregue:
            item.entregue = entregue
            item.save()
    messages.success(request, "Checklist de documentos atualizado.")
    return redirect(f"{recruta.get_absolute_url()}?aba=documentos")
