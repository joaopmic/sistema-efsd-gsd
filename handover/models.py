from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel


class PassagemServico(BaseModel):
    turma = models.ForeignKey("core.Turma", on_delete=models.PROTECT, related_name="passagens", editable=False)
    entrega = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", editable=False,
        verbose_name="Quem entrega",
    )
    recebe = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", verbose_name="Quem recebe",
    )
    data_hora = models.DateTimeField("Data e hora", default=timezone.now)
    observacoes = models.TextField("Observações", blank=True)
    confirmada_em = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-data_hora"]
        verbose_name = "Passagem de serviço"
        verbose_name_plural = "Passagens de serviço"

    def __str__(self):
        return f"Passagem de {self.entrega} para {self.recebe} em {timezone.localtime(self.data_hora):%d/%m/%Y %H:%M}"

    def _turma_do_registro(self):
        return self.turma

    @property
    def situacao_texto(self):
        return "Confirmada" if self.confirmada_em else "Aguardando confirmação"


class Pendencia(BaseModel):
    turma = models.ForeignKey("core.Turma", on_delete=models.PROTECT, related_name="pendencias", editable=False)
    recruta = models.ForeignKey(
        "recruits.Recruta", null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="Recruta",
    )
    descricao = models.CharField("Descrição", max_length=500)
    origem = models.CharField(max_length=40, default="manual", editable=False)
    resolvida = models.BooleanField(default=False, editable=False)
    resolvida_em = models.DateTimeField(null=True, blank=True, editable=False)
    passagem = models.ForeignKey(
        PassagemServico, null=True, blank=True, editable=False, on_delete=models.SET_NULL, related_name="pendencias",
    )

    class Meta:
        ordering = ["resolvida", "-created_at"]
        verbose_name_plural = "Pendências"

    def __str__(self):
        return self.descricao

    def _turma_do_registro(self):
        return self.turma

    @property
    def origem_texto(self):
        return {
            "manual": "Lançada à mão",
            "retorno_sem_ida": "Retorno sem ida",
            "ajuste_efetivo": "Ajuste de efetivo",
        }.get(self.origem, self.origem)

    @property
    def situacao_texto(self):
        return "Resolvida" if self.resolvida else "Aberta"
