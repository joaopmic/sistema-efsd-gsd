from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _criar_parametros(sender, **kwargs):
    from .models import Parametro
    from .params import PADROES

    for chave, (valor, descricao) in PADROES.items():
        Parametro.objects.get_or_create(chave=chave, defaults={"valor": valor, "descricao": descricao})


class CoreConfig(AppConfig):
    name = "core"
    verbose_name = "Núcleo"

    def ready(self):
        post_migrate.connect(_criar_parametros, sender=self, dispatch_uid="core_criar_parametros")
