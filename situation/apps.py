from django.apps import AppConfig
from django.db.models.signals import post_migrate, post_save


def _criar_tipos(sender, **kwargs):
    from .services import garantir_tipos

    garantir_tipos()


def _recalcular(sender, instance, raw=False, **kwargs):
    if raw:
        return
    from recruits.models import Recruta

    from .services import recalcular_situacao

    recruta = instance.recruta if hasattr(instance, "recruta") else None
    if isinstance(recruta, Recruta) and recruta.deleted_at is None:
        recalcular_situacao(recruta)


class SituationConfig(AppConfig):
    name = "situation"
    verbose_name = "Situação do recruta"

    def ready(self):
        from django.apps import apps

        post_migrate.connect(_criar_tipos, sender=self, dispatch_uid="situation_criar_tipos")
        for rotulo in ("health.Dispensa", "health.JuntaSaude", "hospital.IdaGSAU",
                       "discipline.Punicao", "situation.CondicaoManual"):
            modelo = apps.get_model(rotulo)
            post_save.connect(_recalcular, sender=modelo, dispatch_uid=f"situation_recalc_{rotulo}")
