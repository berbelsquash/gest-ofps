# Plataforma de Gestão — Federação Paulista de Squash

> Documento de especificação da plataforma. Fonte: briefing do usuário
> (`plataforma-fpj-prompt-claude-code.pdf`, jul/2026). As seções marcadas
> **[EM ABERTO]** ainda precisam de definição — são pendências, não requisitos.

## 1. Contexto e objetivo

Plataforma interna de gestão da Federação Paulista (Squash), cobrindo três frentes:

1. **Financeiro** — receitas, despesas, resultado por evento e por instituição, e previsões.
2. **Bases de dados** — atletas, participações em eventos e filiações (integradas entre si).
3. **Dashboards e Insights** — indicadores de gestão e automações acionáveis.

Um quarto módulo, **Tarefas**, estava previsto e foi detalhado depois (ver seção 8 e o estado atual no `CLAUDE.md`).

**Princípio central da arquitetura:** todos os módulos se apoiam em uma **camada única de identidade de pessoa** (seção 4.4). É ela que permite cruzar filiação, participação e pagamento da mesma pessoa, mesmo quando o nome vem grafado de formas diferentes em cada fonte.

## 2. Visão geral da estrutura

```
MÓDULO FINANCEIRO
├── Aba 1 — Base Financeira (upload e classificação de extratos)
├── Aba 2 — Visão Eventos
├── Aba 3 — Visão Institucional
└── Aba 4 — Previsto x Realizado

MÓDULO BASES
├── Base de Atletas
├── Base de Participações (Resultados)
├── Base de Filiações (integração Vindi)
├── Base de Eventos (cadastro)
└── Camada de Conciliação de Identidade

MÓDULO DASHBOARDS
├── Arbitragem
├── Participações
├── Filiações
└── Recortes (Interior / Feminino) — filtros sobre os anteriores

MÓDULO INSIGHTS E AUTOMAÇÕES
└── Listas acionáveis + integração de e-mail

MÓDULO TAREFAS  [detalhado depois — ver CLAUDE.md]
```

**UX:** o usuário sinalizou preocupação com excesso de abas num mesmo nível. Navegação em **dois níveis** — módulo na barra principal, abas internas dentro de cada módulo — em vez de todas lado a lado.

## 3. Módulo Financeiro

### 3.1 Aba 1 — Base Financeira (upload e classificação)
Ponto de entrada de todo dado financeiro real. O usuário sobe o extrato bancário do mês e o sistema classifica cada lançamento.

- Upload do extrato do mês (arquivo bancário).
- **Arquivamento permanente**: todo extrato enviado fica armazenado e consultável. Nada é descartado após o processamento.
- Cada lançamento recebe: **Categoria** (nível 1), **Subcategoria** (nível 2), **Evento associado** (nível 3, quando aplicável).
- Listagem: ordenação do mais recente para o mais antigo; **coluna de evento editável inline** (sem modal).
- **Filtros obrigatórios**: por categoria, subcategoria, período e por **status de conciliação** (crítico: "mostrar apenas lançamentos de inscrição não vinculados a nenhum evento").

### 3.2 Categorias de receita (5 fontes)
1. **Inscrições em eventos** — pagamentos de atletas por evento.
2. **Filiações — pessoa física** — plataforma Vindi.
3. **Filiações — clubes e academias**.
4. **Vendas em geral** — valores distintos dos de inscrição.
5. **Patrocínios**.

Regra de desambiguação: valores de inscrição diferem dos de venda, o que permite separar automaticamente as categorias 1 e 4.

### 3.3 Categorias de despesa
Três níveis: **Categoria → Subcategoria → Evento**. Ex.: Categoria=Evento, Subcategoria=Arbitragem, Evento="Etapa X — Interior". Subcategorias já identificadas: arbitragem, transmissão, cobertura do evento, promotores.

**[EM ABERTO]** A árvore completa de categorias/subcategorias de despesa não foi definida. Construir como **configurável pelo usuário, não hardcoded**. Requisito: somar gasto por subcategoria tanto por evento quanto no consolidado.

### 3.4 Associação automática a eventos
O usuário cadastra os eventos (com datas). Cascata de associação de um lançamento:
1. **Match por data** — cai na janela de um único evento → associa.
2. **Match por valor** — se há eventos simultâneos, desempata pelo valor da inscrição (eventos diferentes costumam ter valores diferentes).
3. **Deixa em aberto** — se não dá pra distinguir, o campo fica vazio (**não chutar**); aparece no filtro de "não conciliados" para tratamento manual na própria linha.

### 3.5 Aba 2 — Visão Eventos
Filtro por evento específico ou consolidado. Indicadores por evento: total arrecadado, total de gastos, lucro (absoluto), **margem % (indicador-chave)**, total pago ao promotor, total retido pela federação, e detalhamento de despesa por subcategoria (valor absoluto + % do custo).

### 3.6 Aba 3 — Visão Institucional
Visão da federação como um todo: receitas x despesas mensais (comparativo lado a lado), **drill-down por mês** (clicar atualiza a tela), totais consolidados, quebra por categoria, classificação **recorrente x esporádica**, e **dependência de receita (indicador-chave)** — % do caixa por fonte (filiação x eventos x patrocínio) com evolução no tempo.

### 3.7 Aba 4 — Previsto x Realizado
Aba separada por design: mistura real com estimativa e não deve contaminar as telas de número realizado. Previsão em três camadas:
- **Camada 1 — Recorrente contratado (automático):** filiações da Vindi (projeção automática) + despesas fixas cadastradas uma vez (folha, assinaturas, contratos), que se repetem sozinhas mês a mês.
- **Camada 2 — Eventos planejados (input manual):** por evento futuro, receita e custo estimados (sugestão: pré-preencher com a média histórica de eventos similares).
- **Camada 3 — Ajuste manual:** linha livre.

Previsão do mês = C1 + C2 + C3. Comparativo previsto x realizado por mês, categoria e evento, com desvio absoluto e %.

## 4. Módulo Bases

### 4.1 Base de Atletas
Cadastro mestre. Campos: nome, telefone, e-mail, sexo, data de nascimento, clube, treinador. **[EM ABERTO]** lista não fechada; prever categoria, cidade/região e faixa etária (derivável da data de nascimento).

### 4.2 Base de Participações (Resultados)
Todas as participações dos atletas em eventos oficiais. Vinculada a Atletas (nomes batem) e a Eventos. Permite, por evento: listar quem participou; por atleta: contar quantas vezes participou.

### 4.3 Base de Filiações — Integração Vindi
Plataforma **Vindi** (V-I-N-D-I), via API. Dados: status (ativo/cancelado/inadimplente), tipo de plano, data de filiação, data de cancelamento.
- **Uso 1 — Previsão automática de receita** (calculada, não estimada): filiação anual → projeta renovação 12 meses à frente na data exata; mensal → replica mês a mês. Elimina input manual de previsão de filiações.
- **Uso 2 — Métricas de retenção**: com datas de filiação/cancelamento, calcular churn, LTV e permanência com histórico completo.
- **Separação previsto/realizado**: a Vindi dá o **previsto**; o extrato dá o **realizado** (categoria "Filiações"). A aba Previsto x Realizado cruza as duas.

### 4.4 Camada de Conciliação de Identidade  **[CRÍTICO]**
Componente central. Sem ele nenhum cruzamento funciona. Problema: nomes divergem entre fontes (Atletas↔Participações batem; Vindi e Pix do extrato têm grafias variadas).

Solução — camada única de resolução de identidade que:
1. Faz **match automático por similaridade de nome** (fuzzy matching).
2. Sinaliza casos duvidosos para revisão manual.
3. **Persiste o vínculo confirmado** (não refazer a cada importação).
4. É **reutilizada por todas as fontes** — filiações, participações e favorecidos de Pix.

Destrava: cruzar participação com filiação ("quantos atletas estavam filiados na data do torneio"), identificar árbitros pelo favorecido do Pix (5.1), e qualquer recorte por sexo/categoria/região sobre a base unificada.

### 4.5 Base de Eventos
Cadastro dos eventos. Alimenta a associação automática do financeiro e o vínculo das participações. Campos mínimos: nome, data/janela, **valor da inscrição** (desambiguação, 3.4), **região** (recorte "Interior"), aba de atletas participantes.

## 5. Módulo Dashboards

### 5.1 Arbitragem
Fonte: base financeira (Evento → Arbitragem). Árbitros pagos por Pix, sempre na mesma chave (pessoa física) → o **nome do favorecido identifica o árbitro** (aplicar a camada 4.4 para variações de grafia). Métricas: quantos árbitros por evento, quanto cada um recebeu (mês/ano), total com arbitragem por evento e consolidado.

### 5.2 Participações
Total por torneio, consolidado, média por atleta, distribuição (quantos atletas em quantas etapas/ano), participações por categoria, e **retenção de atleta (indicador-chave)** — quantos dos que competiram voltaram no ano seguinte.

### 5.3 Filiações
**LTV (indicador-chave)**, churn, tempo médio de permanência por plano, novos filiados/mês, cancelamentos/mês, inadimplência, curva de sobrevivência.

### 5.4 Recortes: Interior e Feminino
Não são dashboards separados — são **filtros/lentes** sobre o mesmo cruzamento (filiação + participação + financeiro). Aplicar o recorte mostra todos os indicadores filtrados. Implicação: construir sobre uma **camada de dados unificada e filtrável**, não consultas isoladas por tela.

### 5.5 Indicadores-chave de gestão (topo do painel principal)
Devem aparecer no topo do painel, não escondidos:
- **Margem por evento (%)** — que tipo de evento vale repetir (não o lucro absoluto).
- **Dependência de receita** — fatia do caixa por fonte e se cresce/encolhe.
- **Retenção de atleta** — quantos voltaram no ano seguinte.
- **Taxa de conversão participante → filiado** — quantos não filiados que competiram filiaram.
- **CAC x LTV** — custo de aquisição vs. retorno de um filiado.

## 6. Módulo Insights e Automações
Transformar cruzamentos em **listas acionáveis**.

### 6.1 Insight principal — participantes não filiados
Por evento: lista de quem participou, destaque dos **não filiados na data do evento**, quantidade e %. Ações: (1) exportar os não filiados; (2) **integrar com e-mail** — disparar campanha de conversão com oferta de filiação.

### 6.2 Análise de perfil
Quantos eventos cada não filiado disputou; quem participa recorrente e não filia (**público prioritário**); perfil demográfico (sexo, faixa etária, região, clube). **[EM ABERTO]** outros insights depois; construir extensível.

## 7. Requisitos técnicos transversais
- Fuzzy matching de nomes com **persistência do vínculo confirmado** (4.4).
- Integração com **API da Vindi** (assinaturas ativas/canceladas/inadimplentes, com datas e plano).
- Parser de extrato bancário com **identificação de favorecido de Pix**.
- Motor de classificação por regras (categoria/subcategoria/evento) com **fallback "não classificado"** (não chutar).
- **Edição inline** na listagem financeira.
- **Arquivamento permanente** de todos os extratos importados.
- Estrutura de categorias **configurável pelo usuário, não hardcoded**.
- Integração com serviço de e-mail (campanhas do módulo de insights).
- Exportação de listas em formato tabular.

## 8. Pendências (não especificadas — precisam de definição, não inferir)
- **8.1 Módulo de Tarefas** — no doc original estava em aberto; foi **detalhado e construído depois** (ver `CLAUDE.md` → estado atual).
- **8.2 Indicadores por área** — quais áreas e quais indicadores por área.
- **8.3 Pontuais:** árvore completa de despesa (3.3); lista final de campos de atleta (4.1); perfis de acesso/permissões; reorganização da navegação (seção 2).

## 9. Ordem sugerida de construção
1. Base de Eventos e Base de Atletas (fundação, sem dependências).
2. Camada de Conciliação de Identidade (tudo depende dela).
3. Integração Vindi → Base de Filiações.
4. Base de Participações.
5. Aba 1 do Financeiro (upload, classificação, associação a eventos).
6. Abas 2 e 3 (Visão Eventos e Institucional).
7. Dashboards (Arbitragem, Participações, Filiações).
8. Aba 4 (Previsto x Realizado) — depende de Vindi + base financeira consolidada.
9. Módulo de Insights.
10. Módulo de Tarefas — após especificação (**já construído**).
