# Gestão FPS

Sistema interno de gestão da **Federação Paulista de Squash (FPS)**.

Centraliza as operações da federação em um só lugar:

- 👥 **Associados** — cadastro das pessoas associadas
- 📄 **Assinaturas e pagamentos** — planos, assinaturas e controle de mensalidades/pagamentos (com estrutura pronta para cobrança online no futuro)
- 📊 **Financeiro** — lançamentos de receitas e despesas (extrato)
- ✅ **Tarefas** — distribuição e acompanhamento de tarefas por pessoa
- 🔐 **Acesso restrito** — somente a equipe da FPS acessa

## Tecnologias

- **Python 3.11+**
- **Django 5.2** (framework web)
- **SQLite** (banco de dados — arquivo único, fácil de fazer backup)

## Como rodar localmente (Windows / PowerShell)

1. **Criar o ambiente virtual** (apenas na primeira vez):
   ```powershell
   py -m venv .venv
   ```

2. **Instalar as dependências**:
   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. **Criar o arquivo `.env`** a partir do exemplo (em produção, gere uma nova `SECRET_KEY`):
   ```powershell
   Copy-Item .env.example .env
   ```

4. **Aplicar as migrações do banco**:
   ```powershell
   .\.venv\Scripts\python.exe manage.py migrate
   ```

5. **Criar um usuário administrador**:
   ```powershell
   .\.venv\Scripts\python.exe manage.py createsuperuser
   ```

6. **Rodar o servidor**:
   ```powershell
   .\.venv\Scripts\python.exe manage.py runserver
   ```

7. Abrir no navegador: **http://127.0.0.1:8000**

## Acesso

- **Painel** (indicadores): <http://127.0.0.1:8000/>
- **Administração** (cadastros): <http://127.0.0.1:8000/admin/>

## Estrutura do projeto

```
Gestão FPS/
├── gestao_fps/        # configurações do projeto (settings, urls)
├── contas/            # usuários do sistema (equipe da FPS) + painel
├── associados/        # cadastro de associados
├── assinaturas/       # planos, assinaturas e pagamentos
├── financeiro/        # lançamentos financeiros (extrato)
├── tarefas/           # tarefas por pessoa
├── templates/         # páginas HTML
├── static/            # CSS e arquivos estáticos
├── manage.py          # utilitário de linha de comando do Django
├── requirements.txt   # dependências do projeto
├── .env.example       # modelo de configuração
└── .env               # configuração local (NÃO versionado)
```

## Observações importantes

- O banco `db.sqlite3` e o arquivo `.env` **não** são enviados ao GitHub (ver `.gitignore`), pois contêm dados locais e segredos.
- Para publicar o sistema na internet (gerar um link de acesso para a equipe), será necessário hospedá-lo em um serviço — etapa futura.

## Repositório

<https://github.com/berbelsquash/gest-ofps>
