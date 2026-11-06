import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone

from core.models import Turma
from discipline.models import Punicao, TipoPunicao
from health.models import Dispensa
from hospital.models import IdaGSAU
from observations.models import FatoObservado
from recruits.models import Recruta


class Command(BaseCommand):
    help = "Cria uma turma FICTÍCIA com dados de demonstração (apenas com DJANGO_DEBUG=1 ou --forcar)."

    def add_arguments(self, parser):
        parser.add_argument("--forcar", action="store_true")
        parser.add_argument("--qtd", type=int, default=20)

    def handle(self, *args, **o):
        if not settings.DEBUG and not o["forcar"]:
            raise CommandError("Recusado fora do modo de desenvolvimento (use --forcar se tiver certeza).")
        rnd = random.Random(1)
        hoje = timezone.localdate()
        turma, _ = Turma.objects.get_or_create(
            nome="Turma DEMO", defaults={"data_praca": hoje - timedelta(days=60), "data_formatura": hoje + timedelta(days=120)}
        )
        tp, _ = TipoPunicao.objects.get_or_create(nome="Repreensão (demo)")
        for n in range(1, o["qtd"] + 1):
            r, novo = Recruta.objects.get_or_create(
                turma=turma, numero=n,
                defaults={"nome_completo": f"Recruta Fictício {n}", "nome_guerra": f"Demo{n}", "pelotao": 1 if n % 2 else 2, "grupo": str(1 + n % 4)},
            )
            if not novo:
                continue
            x = rnd.random()
            if x < 0.15:
                IdaGSAU.objects.create(recruta=r, saida=timezone.now() - timedelta(hours=rnd.randint(1, 9)), motivo="Consulta (demo)")
            elif x < 0.30:
                Dispensa.objects.create(recruta=r, tipo=Dispensa.Tipo.values[0], inicio=hoje - timedelta(days=1), termino=hoje + timedelta(days=rnd.randint(1, 5)), observacoes="Demo")
            elif x < 0.38:
                Punicao.objects.create(recruta=r, tipo=tp, inicio=hoje, termino=hoje + timedelta(days=2))
            if rnd.random() < 0.3:
                FatoObservado.objects.create(recruta=r, tipo="POS", ocorrencia="Fato de demonstração")
        self.stdout.write(self.style.SUCCESS("Dados de demonstração criados."))
