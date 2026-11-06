from django.apps import AppConfig
from django.db import connections
from django.db.models.signals import post_delete, post_migrate, pre_save, post_save

SQL_SQLITE = [
    """CREATE TRIGGER IF NOT EXISTS audit_logauditoria_sem_update
       BEFORE UPDATE ON audit_logauditoria
       BEGIN SELECT RAISE(ABORT, 'Livro de Alterações é somente inclusão'); END;""",
    """CREATE TRIGGER IF NOT EXISTS audit_logauditoria_sem_delete
       BEFORE DELETE ON audit_logauditoria
       BEGIN SELECT RAISE(ABORT, 'Livro de Alterações é somente inclusão'); END;""",
]

SQL_POSTGRES = [
    """CREATE OR REPLACE FUNCTION audit_bloquear_alteracao() RETURNS trigger AS $$
       BEGIN RAISE EXCEPTION 'Livro de Alterações é somente inclusão'; END;
       $$ LANGUAGE plpgsql;""",
    "DROP TRIGGER IF EXISTS audit_logauditoria_imutavel ON audit_logauditoria;",
    """CREATE TRIGGER audit_logauditoria_imutavel BEFORE UPDATE OR DELETE ON audit_logauditoria
       FOR EACH ROW EXECUTE FUNCTION audit_bloquear_alteracao();""",
    "DROP TRIGGER IF EXISTS audit_logauditoria_sem_truncate ON audit_logauditoria;",
    """CREATE TRIGGER audit_logauditoria_sem_truncate BEFORE TRUNCATE ON audit_logauditoria
       FOR EACH STATEMENT EXECUTE FUNCTION audit_bloquear_alteracao();""",
]


def instalar_gatilhos(sender, using="default", **kwargs):
    """Cria, de forma idempotente, os gatilhos que impedem UPDATE/DELETE no Livro de Alterações,
    mesmo para quem acessa o banco por fora da aplicação."""
    conexao = connections[using]
    if conexao.vendor == "sqlite":
        comandos = SQL_SQLITE
    elif conexao.vendor == "postgresql":
        comandos = SQL_POSTGRES
    else:
        return
    with conexao.cursor() as cursor:
        for sql in comandos:
            cursor.execute(sql)


class AuditConfig(AppConfig):
    name = "audit"
    verbose_name = "Livro de Alterações"

    def ready(self):
        from django.apps import apps

        from accounts.models import User
        from core.models import BaseModel

        from . import signals

        for modelo in apps.get_models():
            if modelo is User or issubclass(modelo, BaseModel):
                uid = modelo._meta.label_lower
                pre_save.connect(signals.antes_de_salvar, sender=modelo, dispatch_uid=f"audit_pre_{uid}")
                post_save.connect(signals.depois_de_salvar, sender=modelo, dispatch_uid=f"audit_post_{uid}")
                post_delete.connect(signals.depois_de_apagar, sender=modelo, dispatch_uid=f"audit_del_{uid}")
        post_migrate.connect(instalar_gatilhos, sender=self, dispatch_uid="audit_gatilhos")
