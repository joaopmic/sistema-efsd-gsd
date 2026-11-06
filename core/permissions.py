"""Controle de acesso por capacidade.

Capacidades:
  ver        consultar tudo da turma (inclui CPF, tipo sanguíneo e alergias, por decisão do projeto)
  registrar  lançar idas/retornos ao GSAU-YS, fatos observados e confirmar notificações
  gerir      dispensas, juntas, punições, ajustes de efetivo, passagem de serviço, Livro de Alterações
  admin      usuários, turmas, parâmetros, tipos configuráveis, arquivamento

A matriz abaixo é a única fonte da regra; para mudar o que cada graduação pode fazer, edite aqui.
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

TODAS = {"ver", "registrar", "gerir", "admin"}

POR_GRADUACAO = {
    "TEN": {"ver", "registrar", "gerir"},
    "SGT": {"ver", "registrar", "gerir"},
    "CB": {"ver", "registrar"},
    "SD": {"ver"},
}


def capacidades(user):
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return set()
    if getattr(user, "administrador", False) or user.is_superuser:
        return set(TODAS)
    return set(POR_GRADUACAO.get(getattr(user, "graduacao", ""), {"ver"}))


def pode(user, capacidade):
    return capacidade in capacidades(user)


def exige(capacidade, escrita=False):
    """Decorator para views. escrita=True bloqueia alterações quando a turma ativa está arquivada."""

    def decorador(view):
        @wraps(view)
        def envoltorio(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not pode(request.user, capacidade):
                raise PermissionDenied
            if escrita:
                turma = getattr(request, "turma", None)
                if turma is not None and not turma.editavel:
                    messages.error(request, "Turma arquivada: o registro é somente leitura.")
                    return redirect("core:dashboard")
            return view(request, *args, **kwargs)

        return envoltorio

    return decorador
