"""Campos criptografados (Fernet) e índice cego para unicidade de valores criptografados."""
import base64
import hashlib
import hmac
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _chave_bruta():
    chave = settings.FIELD_ENCRYPTION_KEY
    return chave if isinstance(chave, bytes) else chave.encode()


@lru_cache(maxsize=4)
def _fernet_para(chave):
    try:
        return Fernet(chave)
    except (ValueError, TypeError):
        derivada = base64.urlsafe_b64encode(hashlib.sha256(chave).digest())
        return Fernet(derivada)


def _fernet():
    return _fernet_para(_chave_bruta())


def indice_cego(valor):
    """HMAC do valor com a chave do sistema. Permite checar unicidade sem guardar o valor em claro
    e sem permitir força bruta a quem não tem a chave."""
    return hmac.new(_chave_bruta(), valor.encode(), hashlib.sha256).hexdigest()


class EncryptedTextField(models.TextField):
    """Texto guardado criptografado no banco. Não suporta filtro por valor."""

    description = "Texto criptografado"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        return _fernet().encrypt(str(value).encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        try:
            return _fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            return "[ilegível: chave de criptografia incorreta]"
