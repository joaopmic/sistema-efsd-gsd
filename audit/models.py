import uuid

from django.conf import settings
from django.db import models


class SomenteInclusaoQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise RuntimeError("O Livro de Alterações é somente inclusão.")

    def delete(self):
        raise RuntimeError("O Livro de Alterações é somente inclusão.")

    def bulk_update(self, *args, **kwargs):
        raise RuntimeError("O Livro de Alterações é somente inclusão.")


class LogAuditoria(models.Model):
    """Livro de Alterações. Só aceita INSERT: a aplicação bloqueia UPDATE/DELETE e,
    além disso, gatilhos no banco (criados após `migrate`) recusam essas operações."""

    class Operacao(models.TextChoices):
        CRIAR = "CRIAR", "Criação"
        ALTERAR = "ALTERAR", "Alteração"
        EXCLUIR = "EXCLUIR", "Exclusão"
        CONSULTAR = "CONSULTAR", "Consulta a dado protegido"
        EXPORTAR = "EXPORTAR", "Exportação"
        ARQUIVAR = "ARQUIVAR", "Arquivamento de turma"
        LOGIN = "LOGIN", "Entrada no sistema"
        LOGIN_FALHA = "LOGIN_FALHA", "Falha de login"
        LOGOUT = "LOGOUT", "Saída do sistema"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    datahora = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+")
    user_nome = models.CharField(max_length=200, blank=True)
    operacao = models.CharField(max_length=12, choices=Operacao.choices, db_index=True)
    modulo = models.CharField(max_length=80, blank=True, db_index=True)
    registro_id = models.CharField(max_length=64, blank=True)
    registro_repr = models.CharField(max_length=200, blank=True)
    valor_anterior = models.JSONField(null=True, blank=True)
    valor_atual = models.JSONField(null=True, blank=True)
    justificativa = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    objects = SomenteInclusaoQuerySet.as_manager()

    class Meta:
        ordering = ["-datahora"]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise RuntimeError("O Livro de Alterações é somente inclusão.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("O Livro de Alterações é somente inclusão.")

    def __str__(self):
        return f"{self.datahora:%d/%m/%Y %H:%M} {self.operacao} {self.modulo}"
