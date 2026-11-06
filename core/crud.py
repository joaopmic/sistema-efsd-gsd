"""Fábrica de CRUD: gera listagem, criação, edição e exclusão (lógica) para um modelo,
com busca, filtros, paginação, permissões e regras de turma arquivada em um só lugar."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .permissions import exige, pode

FILTRO_PELOTAO = ("pelotao", "recruta__pelotao", "Pelotão", [(1, "1º Pelotão"), (2, "2º Pelotão")])


def _grupos(request):
    from recruits.models import Recruta

    return list(
        Recruta.objects.filter(turma=request.turma).exclude(grupo="")
        .order_by("grupo").values_list("grupo", "grupo").distinct()
    )


FILTRO_GRUPO = ("grupo", "recruta__grupo", "Grupo", _grupos)


def crud_urls(
    *, slug, nome, model, titulo, singular, colunas=(), form_class=None, turma_lookup=None,
    cap_ver="ver", cap_escrita="gerir", busca=(), filtros=(), ordenacao=(), select_related=(),
    incluir=("list", "create", "update", "delete"), detalhe_url=None, acoes_extra=(),
    queryset_fn=None, pre_save=None, pos_save=None, sucesso_fn=None, pode_excluir=None,
    subtitulo_fn=None, form_template="crud/form.html", pk_conv="uuid",
):
    """Devolve a lista de `path()` do CRUD.

    colunas: [(rótulo, caminho_do_atributo)] ou [(rótulo, caminho, "badge")] para mostrar a cor do objeto.
    filtros: [(parametro, lookup|None, rótulo, opcoes|callable(request))]; lookup None = filtro tratado em queryset_fn.
    acoes_extra: [{"label", "url", "post", "cap", "visivel", "classe"}] mostradas em cada linha.
    """
    escrita = bool(turma_lookup)
    tem_turma = "turma" in {f.name for f in model._meta.concrete_fields}

    def _qs_base(request):
        qs = model.objects.all()
        if turma_lookup:
            qs = qs.filter(**{turma_lookup: request.turma})
        if queryset_fn:
            qs = queryset_fn(request, qs)
        if select_related:
            qs = qs.select_related(*select_related)
        if ordenacao:
            qs = qs.order_by(*ordenacao)
        return qs

    def _pode_escrever(request):
        if not pode(request.user, cap_escrita):
            return False
        if turma_lookup:
            return request.turma is not None and request.turma.editavel
        return True

    def _sem_turma(request):
        return turma_lookup and request.turma is None

    def _destino(request, obj, ns):
        if sucesso_fn:
            return sucesso_fn(request, obj)
        proximo = request.POST.get("next") or request.GET.get("next")
        if proximo and url_has_allowed_host_and_scheme(proximo, allowed_hosts={request.get_host()}):
            return proximo
        return reverse(f"{ns}:{nome}_list") if "list" in incluir else "/"

    @exige(cap_ver)
    def lista(request):
        ns = request.resolver_match.namespace
        if _sem_turma(request):
            return render(request, "core/sem_turma.html")
        qs = _qs_base(request)
        q = request.GET.get("q", "").strip()
        if q and busca:
            cond = Q()
            for campo in busca:
                if campo.endswith("numero"):
                    if q.isdigit():
                        cond |= Q(**{campo: int(q)})
                else:
                    cond |= Q(**{campo + "__icontains": q})
            qs = qs.filter(cond)
        filtros_ctx = []
        for param, lookup, rotulo, opcoes in filtros:
            valor = request.GET.get(param, "")
            if valor and lookup:
                qs = qs.filter(**{lookup: valor})
            lista_opcoes = opcoes(request) if callable(opcoes) else opcoes
            filtros_ctx.append({"param": param, "rotulo": rotulo, "opcoes": lista_opcoes, "valor": valor})
        page = Paginator(qs, 25).get_page(request.GET.get("page"))
        itens = list(page.object_list)
        for obj in itens:
            obj.acoes_linha = [
                {
                    "label": a["label"],
                    "url": reverse(a["url"], args=[obj.pk]),
                    "post": a.get("post", True),
                    "classe": a.get("classe", "btn-outline-secondary"),
                }
                for a in acoes_extra
                if pode(request.user, a.get("cap", "registrar"))
                and (request.turma is None or request.turma.editavel or not a.get("post", True))
                and (not a.get("visivel") or a["visivel"](obj))
            ]
        pode_escrever = _pode_escrever(request)
        contexto = {
            "titulo": titulo, "colunas": colunas, "itens": itens, "page": page, "q": q,
            "filtros": filtros_ctx, "busca_ativa": bool(busca),
            "url_criar": reverse(f"{ns}:{nome}_create") if "create" in incluir else None,
            "pode_criar": "create" in incluir and pode_escrever,
            "pode_editar": "update" in incluir and pode_escrever,
            "pode_excluir": "delete" in incluir and pode_escrever,
            "url_editar": f"{ns}:{nome}_update", "url_excluir": f"{ns}:{nome}_delete",
            "detalhe_url": detalhe_url,
            "subtitulo": subtitulo_fn(request) if subtitulo_fn else "",
        }
        return render(request, "crud/list.html", contexto)

    def _formulario(request, instance=None):
        kwargs = {"turma": request.turma, "user": request.user, "instance": instance}
        if instance is None:
            kwargs["initial"] = {k: v for k, v in request.GET.items() if k in form_class.base_fields}
        if request.method == "POST":
            return form_class(request.POST, request.FILES, **kwargs)
        return form_class(**kwargs)

    def _salvar(request, form, ns, criando):
        obj = form.save(commit=False)
        if criando and tem_turma and obj.turma_id is None:
            obj.turma = request.turma
        if pre_save:
            pre_save(obj, request)
        with transaction.atomic():
            obj.save()
            if hasattr(form, "save_m2m"):
                form.save_m2m()
            if hasattr(form, "depois_de_salvar"):
                form.depois_de_salvar(obj)
            if pos_save:
                pos_save(obj, request)
        messages.success(request, f"{singular} {'cadastrado(a)' if criando else 'atualizado(a)'} com sucesso.")
        return redirect(_destino(request, obj, ns))

    @exige(cap_escrita, escrita=escrita)
    def criar(request):
        ns = request.resolver_match.namespace
        if _sem_turma(request):
            return render(request, "core/sem_turma.html")
        form = _formulario(request)
        if request.method == "POST" and form.is_valid():
            return _salvar(request, form, ns, True)
        return render(request, form_template, {
            "form": form, "titulo": f"Novo(a) {singular.lower()}",
            "voltar": reverse(f"{ns}:{nome}_list") if "list" in incluir else "/",
            "next": request.GET.get("next", ""),
        })

    @exige(cap_escrita, escrita=escrita)
    def editar(request, pk):
        ns = request.resolver_match.namespace
        obj = get_object_or_404(_qs_base(request), pk=pk)
        form = _formulario(request, instance=obj)
        if request.method == "POST" and form.is_valid():
            return _salvar(request, form, ns, False)
        return render(request, form_template, {
            "form": form, "titulo": f"Editar {singular.lower()}", "objeto": obj,
            "anexos": obj.anexos if hasattr(obj, "anexos") else [],
            "voltar": reverse(f"{ns}:{nome}_list") if "list" in incluir else "/",
            "next": request.GET.get("next", ""),
        })

    @exige(cap_escrita, escrita=escrita)
    def excluir(request, pk):
        ns = request.resolver_match.namespace
        obj = get_object_or_404(_qs_base(request), pk=pk)
        if pode_excluir:
            ok, motivo = pode_excluir(obj, request)
            if not ok:
                messages.error(request, motivo)
                return redirect(_destino(request, obj, ns))
        if request.method == "POST":
            obj.delete()
            messages.success(request, f"{singular} excluído(a). O registro foi preservado no histórico.")
            return redirect(_destino(request, obj, ns))
        return render(request, "crud/confirm_delete.html", {
            "objeto": obj, "titulo": f"Excluir {singular.lower()}",
            "voltar": reverse(f"{ns}:{nome}_list") if "list" in incluir else "/",
        })

    urls = []
    prefixo = f"{slug}/" if slug else ""
    if "list" in incluir:
        urls.append(path(prefixo, lista, name=f"{nome}_list"))
    if "create" in incluir:
        urls.append(path(f"{prefixo}novo/", criar, name=f"{nome}_create"))
    if "update" in incluir:
        urls.append(path(f"{prefixo}<{pk_conv}:pk>/editar/", editar, name=f"{nome}_update"))
    if "delete" in incluir:
        urls.append(path(f"{prefixo}<{pk_conv}:pk>/excluir/", excluir, name=f"{nome}_delete"))
    return urls
