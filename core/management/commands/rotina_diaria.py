from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Turma
from daily_roster.services import gerar_efetivo
from notifications.rules import avaliar_tudo


class Command(BaseCommand):
    help = "Rotina diária: recalcula situações e alertas e monta o efetivo do dia (agendar no cron, ex.: 06:00)."

    def handle(self, *args, **opts):
        avaliar_tudo()
        hoje = timezone.localdate()
        for turma in Turma.objects.filter(status="FORMACAO"):
            criados, atualizados = gerar_efetivo(turma, hoje)
            self.stdout.write(f"{turma.nome}: {criados} linhas criadas, {atualizados} atualizadas.")
        self.stdout.write(self.style.SUCCESS("Rotina concluída."))
