from django.conf import settings
from django.db import models
from django.db.models import Q

from core.models import BaseModel


class Notificacao(BaseModel):
    class Prioridade(models.IntegerChoices):
        ALTA = 1, "Alta (ação imediata)"
        MEDIA = 2, "Média (alerta)"
        BAIXA = 3, "Baixa (informativo)"

    class Estado(models.TextChoices):
        ATIVA = "ATIVA", "Ativa"
        RECONHECIDA = "RECONHECIDA", "Reconhecida"
        RESOLVIDA = "RESOLVIDA", "Resolvida"

    turma = models.ForeignKey("core.Turma", on_delete=models.PROTECT, related_name="notificacoes", editable=False)
    categoria = models.CharField(max_length=40)
    prioridade = models.PositiveSmallIntegerField(choices=Prioridade.choices, default=Prioridade.MEDIA)
    mensagem = models.CharField(max_length=300)
    recruta = models.ForeignKey("recruits.Recruta", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    regra = models.CharField(max_length=40, db_index=True)
    origem_id = models.UUIDField(null=True, blank=True)
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+",
    )
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.ATIVA)
    reconhecida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    reconhecida_em = models.DateTimeField(null=True, blank=True)
    resolvida_em = models.DateTimeField(null=True, blank=True)
    resolvida_manual = models.BooleanField(default=False)

    class Meta:
        ordering = ["prioridade", "-created_at"]
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        constraints = [
            # Uma notificação ativa por regra e registro: evita duplicar alertas
            models.UniqueConstraint(
                fields=["regra", "origem_id"],
                condition=Q(estado__in=["ATIVA", "RECONHECIDA"], deleted_at__isnull=True),
                name="notifications_ativa_unica",
            )
        ]

    def __str__(self):
        return self.mensagem

    def _turma_do_registro(self):
        return self.turma

    @property
    def aberta(self):
        return self.estado != self.Estado.RESOLVIDA
