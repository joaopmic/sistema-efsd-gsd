from django.conf import settings
from django.db import models
from django.db.models import Q

from core.models import BaseModel


class EfetivoDiario(BaseModel):
    """Situação de cada recruta em um dia. Montado dos registros existentes; só muda por ajuste justificado."""

    turma = models.ForeignKey("core.Turma", on_delete=models.PROTECT, related_name="efetivos", editable=False)
    data = models.DateField()
    recruta = models.ForeignKey("recruits.Recruta", on_delete=models.PROTECT, related_name="efetivos")
    tipo_situacao = models.ForeignKey("situation.TipoSituacao", on_delete=models.PROTECT, related_name="+")
    ajustado = models.BooleanField(default=False)

    class Meta:
        ordering = ["-data", "recruta__numero"]
        verbose_name = "Efetivo diário"
        verbose_name_plural = "Efetivos diários"
        constraints = [
            models.UniqueConstraint(
                fields=["data", "recruta"], condition=Q(deleted_at__isnull=True), name="daily_roster_um_por_dia"
            )
        ]

    def __str__(self):
        return f"{self.data:%d/%m/%Y} — {self.recruta.rotulo_curto}: {self.tipo_situacao.nome}"

    def _turma_do_registro(self):
        return self.turma

    @property
    def presente(self):
        return self.tipo_situacao.conta_como_presente


class AjusteEfetivo(BaseModel):
    efetivo = models.ForeignKey(EfetivoDiario, on_delete=models.PROTECT, related_name="ajustes")
    tipo_anterior = models.ForeignKey("situation.TipoSituacao", on_delete=models.PROTECT, related_name="+")
    tipo_novo = models.ForeignKey("situation.TipoSituacao", on_delete=models.PROTECT, related_name="+")
    justificativa = models.TextField(blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Ajuste de {self.efetivo}"

    def _turma_do_registro(self):
        return self.efetivo.turma
