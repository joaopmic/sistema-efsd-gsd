# EFSD / GSD-YS — Controle administrativo de recrutas

Sistema Django (monólito modular) conforme o documento "Etapa 1 — Análise e arquitetura".

## Desenvolvimento (SQLite)
    pip install -r requirements.txt
    set DJANGO_DEBUG=1
    python manage.py makemigrations accounts core audit recruits situation health hospital observations discipline daily_roster handover notifications
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py seed_demo      # opcional, dados FICTÍCIOS
    python manage.py runserver
    python manage.py test

Na primeira entrada crie a Turma em Administração > Turmas.

## Produção
Copie `.env.example` para `.env`, preencha (SECRET_KEY e FIELD_ENCRYPTION_KEY obrigatórias) e rode `docker compose up -d`.
Agende `python manage.py rotina_diaria` (cron, 1x/dia) e `deploy/backup.sh`.
Coloque HTTPS na frente (proxy/Cloudflare/Caddy). Guarde a FIELD_ENCRYPTION_KEY fora do servidor: sem ela CPF e dados de saúde não são recuperáveis.
Recomenda-se um usuário de banco da aplicação sem permissão de UPDATE/DELETE/TRUNCATE em `audit_logauditoria` (além dos gatilhos já instalados).

## Avisos
- O código foi escrito sem poder ser executado no ambiente de geração: rode `makemigrations`, os testes e revise antes de usar com dados reais.
- Bootstrap vem de CDN (BOOTSTRAP_CDN=0 usa cópia local em static/vendor/bootstrap).
- Premissas a validar: matriz de permissões, dispensa de atividade física conta como presente, prioridade das situações.
