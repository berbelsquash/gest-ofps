# Gestão FPS — Plataforma de gestão da Federação Paulista de Squash

Ferramenta interna da **FPS**. Usuário principal: **Vinicius Berbel** (diretor operacional). Acesso restrito à equipe.

A **especificação completa da plataforma** (visão-alvo, os 5 módulos em detalhe, indicadores e ordem de construção) está em **[docs/especificacao-plataforma.md](docs/especificacao-plataforma.md)** — consulte ao planejar qualquer módulo. Este arquivo é o resumo operacional.

## Como trabalhar aqui (regras firmes)
- **Idioma:** tudo em pt-BR — código, UI, mensagens, commits.
- **Segredos e dados NUNCA no git:** `.env` (chave da Vindi), `db.sqlite3`, `backups/`, planilhas/comprovantes `.xlsx`. São gitignored e há um guard de commit. Confira antes de commitar.
- **Git:** NUNCA commitar nem pushar sem o usuário pedir explicitamente. Branch main, repo `berbelsquash/gest-ofps` (origin), **separado** do site público da FPS.
- **Credenciais:** NUNCA aceitar login/senha de plataformas. Integrações (Vindi, e-mail) usam **API key no `.env`** — o usuário coloca; você não manuseia nem digita senhas.
- **Backups:** ao mexer em dados importantes, gerar `backups/db_backup_AAAA-MM-DD_HHMM.sqlite3` (API de backup do SQLite; fora do git).
- **Design:** limpo, referência é o site público da FPS — Poppins, hero com degradê, cartões/chips com sombra suave, menu lateral em **dropdown**, dados centralizados nas tabelas. Editar via **modal** (janela sobre a tela), nunca mandar pro admin.
- **Verificação:** validar com o **test client do Django** (`force_login` superuser, `HTTP_HOST='localhost'`), não pedir teste manual. Mudança de `.py` exige reiniciar o servidor (`--noreload`); template/CSS recarrega sozinho (CSS tem cache-buster `?v=N` no `base.html`).
- **Acentos em scripts:** rodar seeds/checagens via `manage.py shell -c "exec(open(path, encoding='utf-8').read())"` (evita erro de BOM/encoding no Windows).

## Stack
Django 5.2 + SQLite · custom user `contas.Usuario` · pt-BR / America/Sao_Paulo · `.venv/Scripts/python.exe` · rodar `manage.py runserver` (o preview do harness cai quando ocioso).

## Arquitetura-alvo — 5 módulos, navegação em 2 níveis
**Princípio central: camada única de identidade de pessoa** (fuzzy matching de nomes + vínculo persistido) cruza filiação + participação + pagamento da mesma pessoa entre fontes (Atletas, Vindi, Pix do extrato). Sem ela nenhum cruzamento funciona.

Outros princípios: classificar com **fallback "não classificado"** (nunca chutar) · categorias **configuráveis**, não hardcoded · **separar previsto x realizado** (não misturar estimativa com número real) · dashboards sobre **uma camada de dados unificada e filtrável**.

1. **Financeiro** — Base Financeira (upload+classificação), Visão Eventos, Visão Institucional, Previsto x Realizado.
2. **Bases** — Atletas, Participações, Filiações (Vindi), Eventos + **Conciliação de Identidade**.
3. **Dashboards** — Arbitragem, Participações, Filiações, Recortes (Interior/Feminino).
4. **Insights e Automações** — listas acionáveis (ex.: participantes não filiados) + e-mail.
5. **Tarefas** — tarefas por pessoa/evento/projeto.

**5 indicadores-chave** no topo do painel: Margem por evento (%) · Dependência de receita · Retenção de atleta · Conversão participante→filiado · CAC x LTV.

## Estado atual (o que já existe)
- **Financeiro** — construído (app `financeiro`): abas Início, Detalhado, Eventos (importar inscrições do Google Forms + conciliação manual esperado×extrato), Previsão (itens recorrentes + Vindi), Relatórios. Modelos: `LancamentoBancario`, `LancamentoFinanceiro`, `ItemPrevisao`, `Inscricao`. Casamento de comprovantes por nome já existe (embrião da conciliação de identidade).
- **Filiações / Vindi** — integração via API construída (grupo de menu "Filiações"; app `assinaturas`).
- **Tarefas e projetos** — construído (app `tarefas`): 43 eventos com checklist + comunicações semanais + avisos de inscrição, recorrentes, reuniões, agenda, projetos com business plan. `gerar.py` gera checklist+comunicações de um evento. **Obs.:** a spec trata Tarefas como "em aberto", mas ele já foi detalhado e construído.
- **Ainda NÃO construído:** módulo **Bases** (Atletas, Participações, Conciliação de Identidade), **Dashboards**, **Insights/Automações**, e a reorganização do Financeiro para as 4 abas exatas da spec.

## Próximos passos (a spec sugere fundação primeiro)
Como Financeiro, Tarefas e Vindi já existem, os próximos naturais são **Bases + Conciliação de Identidade** (fundação de tudo) → **Dashboards** → **Insights/Automações**, aproximando o Financeiro atual das 4 abas da spec ao longo do caminho. Sempre alinhar o escopo antes de construir módulo grande.
