from datetime import date

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.permissions import exige, pode
from situation.models import TipoSituacao

from .forms import AjusteForm
from .models import EfetivoDiario
from .services import ajustar_efetivo, gerar_efetivo, resumo


def _data_da_requisicao(valor):
    try:
        return date.fromisoformat(valor) if valor else timezone.localdate()
    except ValueError:
        return timezone.localdate()


@exige("ver")
def efetivo(request):
    if request.turma is None:
        return render(request, "core/sem_turma.html")
    data = _data_da_requisicao(request.GET.get("data"))
    linhas = list(
        EfetivoDiario.objects.filter(turma=request.turma, data=data)
        .select_related("recruta", "tipo_situacao").order_by("recruta__pelotao", "recruta__numero")
    )
    pelotoes = {}
    for linha in linhas:
        pelotoes.setdefault(linha.recruta.get_pelotao_display(), []).append(linha)
    return render(request, "daily_roster/efetivo.html", {
        "data": data, "pelotoes": pelotoes, "resumo": resumo(linhas), "tem_linhas": bool(linhas),
        "pode_gerar": pode(request.user, "gerir") and request.turma.editavel and data <= timezone.localdate(),
        "pode_ajustar": pode(request.user, "gerir") and request.turma.editavel,
        "hoje": timezone.localdate(),
    })


@exige("gerir", escrita=True)
@require_POST
def gerar(request):
    data = _data_da_requisicao(request.POST.get("data"))
    try:
        criados, atualizados = gerar_efetivo(request.turma, data)
        messages.success(request, f"Efetivo de {data:%d/%m/%Y}: {criados} linha(s) criada(s), {atualizados} atualizada(s).")
    except ValueError as erro:
        messages.error(request, str(erro))
    return redirect(f"{reverse('daily_roster:efetivo')}?data={data.isoformat()}")


@exige("gerir", escrita=True)
def ajustar(request, pk):
    linha = get_object_or_404(
        EfetivoDiario.objects.select_related("recruta", "tipo_situacao"), pk=pk, turma=request.turma
    )
    form = AjusteForm(request.POST or None, tipos=TipoSituacao.objects.all(), atual=linha.tipo_situacao)
    if request.method == "POST" and form.is_valid():
        ajustar_efetivo(linha, form.cleaned_data["tipo"], form.cleaned_data["justificativa"], request.user)
        messages.success(request, "Ajuste registrado no Livro de Alterações.")
        return redirect(f"{reverse('daily_roster:efetivo')}?data={linha.data.isoformat()}")
    return render(request, "crud/form.html", {
        "form": form, "titulo": f"Ajustar efetivo de {linha.data:%d/%m/%Y} — {linha.recruta}",
        "voltar": f"{reverse('daily_roster:efetivo')}?data={linha.data.isoformat()}",
        "aviso": "Sem justificativa o ajuste é aceito, mas abre uma pendência para ser regularizada.",
    })
