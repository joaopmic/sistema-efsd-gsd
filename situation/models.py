from django.db import models
from django.db.models import Q

from core.models import BaseModel


class TipoSituacao(BaseModel):
    """Tipos de situação do recruta. Os tipos de sistema (campo `sistema`) são usados pelas regras
    e não podem ser excluídos; o administrador ajusta nome, cor, prioridade e se conta como presente."""

    codigo = models.CharField("Código", max_length=20)
    nome = models.CharField("Nome", max_length=60)
    cor = models.CharField("Cor (hex)", max_length=7, default="#6c757d")
    conta_como_presente = models.BooleanField("Conta como presente no GSD", default=False)
    prioridade = models.PositiveSmallIntegerField(
        "Prioridade (1 = mais prioritária)", help_text="Quando o recruta tem mais de uma condição, vale a de menor número."
    )
    sistema = models.BooleanField(default=False, editable=False)

    class Meta:
        ordering = ["prioridade"]
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"], condition=Q(deleted_at__isnull=True), name="situation_tipo_codigo_unico"
            )
        ]

    def __str__(self):
        return self.nome


class HistoricoSituacao(BaseModel):
    """Cada mudança da situação principal do recruta: quando começou, quando acabou e por quê."""

    recruta = models.ForeignKey("recruits.Recruta", on_delete=models.PROTECT, related_name="historico_situacao")
    tipo = models.ForeignKey(TipoSituacao, on_delete=models.PROTECT, related_name="+")
    motivo = models.CharField(max_length=500, blank=True)
    inicio = models.DateTimeField()
    fim = models.DateTimeField(null=True, blank=True)
    origem_tipo = models.CharField(max_length=40, blank=True)
    origem_id = models.UUIDField(null=True, blank=True)

    class Meta:
        ordering = ["-inicio"]
        indexes = [models.Index(fields=["recruta", "fim"])]

    def __str__(self):
        return f"{self.recruta.rotulo_curto}: {self.tipo.nome}"

    def _turma_do_registro(self):
        return self.recruta.turma


class CondicaoManual(BaseModel):
    """Situação lançada à mão (fora do GSD por motivo administrativo ou em atividade externa)."""

    recruta = models.ForeignKey("recruits.Recruta", on_delete=models.PROTECT, related_name="condicoes_manuais")
    tipo = models.ForeignKey(
        TipoSituacao, on_delete=models.PROTECT, related_name="+",
        limit_choices_to={"codigo__in": ["ADMIN", "EXTERNA"]},
    )
    motivo = models.CharField("Motivo", max_length=300)
    inicio = models.DateField("Início")
    termino = models.DateField("Término", null=True, blank=True, help_text="Deixe em branco até encerrar manualmente.")

    class Meta:
        ordering = ["-inicio"]

    def __str__(self):
        return f"{self.tipo.nome} — {self.recruta.rotulo_curto}"

    def _turma_do_registro(self):
        return self.recruta.turma
