from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.models import BaseModel


class IdaGSAU(BaseModel):
    """Saída do recruta para o GSAU-YS. Fica `aberta` até o retorno ser registrado."""

    recruta = models.ForeignKey("recruits.Recruta", on_delete=models.PROTECT, related_name="idas")
    saida = models.DateTimeField("Saída (data e hora)", default=timezone.now)
    motivo = models.CharField("Motivo", max_length=200)
    acompanhante = models.ForeignKey(
        "recruits.Recruta", null=True, blank=True, on_delete=models.PROTECT,
        related_name="+", verbose_name="Acompanhante (recruta)",
    )
    observacoes = models.TextField("Observações", blank=True)
    aberta = models.BooleanField(default=True, editable=False)
    retornou_em = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-saida"]
        verbose_name = "Ida ao GSAU-YS"
        verbose_name_plural = "Idas ao GSAU-YS"
        constraints = [
            # No máximo uma ida aberta por recruta (garantido no banco)
            models.UniqueConstraint(
                fields=["recruta"], condition=Q(aberta=True, deleted_at__isnull=True),
                name="hospital_uma_ida_aberta_por_recruta",
            )
        ]

    def __str__(self):
        return f"Ida de {self.recruta.rotulo_curto} em {timezone.localtime(self.saida):%d/%m/%Y %H:%M}"

    def _turma_do_registro(self):
        return self.recruta.turma

    @property
    def tempo_fora(self):
        fim = self.retornou_em or timezone.now()
        return fim - self.saida

    @property
    def tempo_fora_texto(self):
        total = int(self.tempo_fora.total_seconds() // 60)
        return f"{total // 60}h{total % 60:02d}"

    @property
    def situacao_texto(self):
        return "No GSAU-YS" if self.aberta else "Retornou"


class RetornoGSAU(BaseModel):
    """Retorno do GSAU-YS. Fecha a ida aberta do recruta (relação um para um)."""

    recruta = models.ForeignKey("recruits.Recruta", on_delete=models.PROTECT, related_name="retornos")
    ida = models.OneToOneField(IdaGSAU, null=True, blank=True, editable=False, on_delete=models.PROTECT, related_name="retorno")
    retorno = models.DateTimeField("Retorno (data e hora)", default=timezone.now)
    recebeu_dispensa = models.BooleanField("Recebeu dispensa", default=False)
    justificativa = models.TextField(
        "Justificativa (obrigatória se não houver ida aberta)", blank=True,
    )

    class Meta:
        ordering = ["-retorno"]
        verbose_name = "Retorno do GSAU-YS"
        verbose_name_plural = "Retornos do GSAU-YS"

    def __str__(self):
        return f"Retorno de {self.recruta.rotulo_curto} em {timezone.localtime(self.retorno):%d/%m/%Y %H:%M}"

    def _turma_do_registro(self):
        return self.recruta.turma

    def delete(self, using=None, keep_parents=False):
        """Excluir um retorno reabre a ida, se o recruta não tiver outra ida aberta."""
        ida = self.ida
        resultado = super().delete(using=using, keep_parents=keep_parents)
        if ida is not None and not ida.aberta:
            if not IdaGSAU.objects.filter(recruta=ida.recruta, aberta=True).exists():
                ida.aberta = True
                ida.retornou_em = None
                ida.save()
        return resultado
