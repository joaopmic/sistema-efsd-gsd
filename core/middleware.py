import threading

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect

from .exceptions import TurmaArquivadaError

_estado = threading.local()


def get_request_atual():
    return getattr(_estado, "request", None)


def get_current_user():
    """Usuário da requisição em andamento (ou None fora de uma requisição)."""
    req = get_request_atual()
    user = getattr(req, "user", None) if req is not None else None
    if user is not None and getattr(user, "is_authenticated", False):
        return user
    return None


class UsuarioAtualMiddleware:
    """Guarda a requisição em uma variável de thread para preencher created_by/updated_by
    e para o Livro de Alterações."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _estado.request = request
        try:
            return self.get_response(request)
        finally:
            _estado.request = None


class TurmaAtivaMiddleware:
    """Define request.turma a partir da sessão. Sem escolha, usa a turma em formação mais recente."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.turma = None
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            from .models import Turma

            turma = None
            tid = request.session.get("turma_id")
            if tid:
                try:
                    turma = Turma.objects.filter(pk=tid).first()
                except (ValueError, ValidationError):
                    turma = None
            if turma is None:
                turma = (
                    Turma.objects.filter(status="FORMACAO").order_by("-data_praca").first()
                    or Turma.objects.order_by("-data_praca").first()
                )
                if turma is not None:
                    request.session["turma_id"] = str(turma.pk)
            request.turma = turma
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, TurmaArquivadaError):
            messages.error(request, str(exception))
            return redirect("core:dashboard")
        return None
