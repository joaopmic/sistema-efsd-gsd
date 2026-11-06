"""Registro automático de criação, alteração e exclusão de todos os modelos do sistema."""
from core.fields import EncryptedTextField, indice_cego

from .services import registrar

IGNORADOS = {"created_at", "created_by", "updated_at", "updated_by"}


def _snapshot(instancia):
    """Valores dos campos em formato JSON. Campos criptografados nunca são gravados em claro:
    ficam como marcador com HMAC (permite saber que mudou sem revelar o valor)."""
    excluir = set(getattr(instancia, "audit_excluir", ()))
    dados = {}
    for campo in instancia._meta.concrete_fields:
        if campo.name in IGNORADOS or campo.name in excluir:
            continue
        valor = campo.value_from_object(instancia)
        if isinstance(campo, EncryptedTextField):
            dados[campo.name] = f"[protegido:{indice_cego(str(valor))[:10]}]" if valor else ""
        elif valor is None or isinstance(valor, (bool, int, float, str)):
            dados[campo.name] = valor
        elif hasattr(valor, "name") and hasattr(valor, "storage"):  # arquivos
            dados[campo.name] = valor.name or ""
        elif hasattr(valor, "isoformat"):
            dados[campo.name] = valor.isoformat()
        else:
            dados[campo.name] = str(valor)
    return dados


def antes_de_salvar(sender, instance, raw=False, **kwargs):
    instance._audit_antes = None
    if raw or instance._state.adding or instance.pk is None:
        return
    try:
        antigo = sender._base_manager.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    instance._audit_antes = _snapshot(antigo)


def depois_de_salvar(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    atual = _snapshot(instance)
    antes = getattr(instance, "_audit_antes", None)
    if created:
        operacao, antes = "CRIAR", None
    else:
        if antes == atual:
            return
        excluiu = bool(atual.get("deleted_at")) and not (antes or {}).get("deleted_at")
        operacao = "EXCLUIR" if excluiu else "ALTERAR"
    registrar(
        operacao, modulo=sender._meta.label, registro_id=instance.pk,
        registro_repr=str(instance), anterior=antes, atual=atual,
    )


def depois_de_apagar(sender, instance, **kwargs):
    registrar(
        "EXCLUIR", modulo=sender._meta.label, registro_id=instance.pk,
        registro_repr=str(instance), anterior=_snapshot(instance), atual=None,
        justificativa="Exclusão física",
    )
