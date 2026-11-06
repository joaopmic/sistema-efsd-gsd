from django.apps import AppConfig
from django.db.models.signals import post_save


def _avaliar(sender, instance, raw=False, **kwargs):
    if raw:
        return
    from .rules import avaliar_recruta

    recruta = getattr(instance, "recruta", None)
    if recruta is not None:
        avaliar_recruta(recruta)


class NotificationsConfig(AppConfig):
    name = "notifications"
    verbose_name = "Notificações"

    def ready(self):
        from django.apps import apps

        for rotulo in ("health.Dispensa", "health.JuntaSaude", "hospital.IdaGSAU",
                       "discipline.Punicao", "observations.FatoObservado"):
            post_save.connect(_avaliar, sender=apps.get_model(rotulo), dispatch_uid=f"notif_{rotulo}")
