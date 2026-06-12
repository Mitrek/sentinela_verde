# Memória de Trabalho - 2026-06-12

## Estado Geral

Projeto: Sentinela Verde, aplicação FastAPI + Leaflet para monitoramento de focos de incêndio em Minas Gerais.

Branch atual: `main`.

Último commit enviado antes das mudanças pendentes:

```text
f2d10d8 Refine map visuals and state boundary
```

Depois desse commit, há mudanças locais ainda não commitadas relacionadas ao alarme de incêndio em UCs e ao indicador de satélites ativos.

## Trabalho Já Commitado e Enviado Hoje

- Filtros operacionais por COB, batalhão, companhia, pelotão e posto avançado.
- Textos da interface em português e nomes em caixa natural.
- Marcadores de focos convertidos para círculos cartográficos profissionais.
- Escala atual dos marcadores:
  - baixa: círculo laranja menor;
  - moderada: círculo laranja forte com halo;
  - alta: círculo vermelho maior com halo.
- Popup dos focos ficou mais claro:
  - Data da detecção;
  - Horário da detecção em horário de Brasília;
  - Potência Radiativa do Fogo (FRP);
  - Satélite/sensor;
  - Confiança;
  - Coordenadas.
- Paleta dos polígonos passou a seguir o toggle `Escuro` / `Satélite`, removendo cores legadas fixas de laranja e verde no carregamento dos filtros.
- Contorno permanente do estado de Minas Gerais:
  - endpoint `/api/geojson/mg`;
  - borda branca;
  - sem preenchimento;
  - sempre ativo independentemente dos filtros.
- Removida geração automática de `static/map.html` no startup/fetch, reduzindo reloads desnecessários com `uvicorn --reload`.

## Mudanças Pendentes Não Commitadas

Arquivos modificados/novos observados no último `git status`:

```text
 M conservation_units.py
 M main.py
 M static/css/style.css
 M static/js/app.js
 M templates/index.html
 M tests/test_conservation_units.py
?? INPE/
?? tests/test_alerts_api.py
```

`INPE/` está não rastreado. Conferir conteúdo antes de qualquer commit; pode ser dado baixado/local e talvez não deva entrar no Git.

## Alarme de Incêndio em UC

Implementação atual é funcional, não apenas visual.

### Backend

- Novo endpoint:

```text
GET /api/alerts/uc-fires?unit=<unit_id>&after=<YYYY-MM-DDTHHMM>
```

- Implementado em `main.py`.
- Usa o filtro operacional atual (`unit`) quando informado.
- Retorna lista vazia se `after` for inválido.
- Usa helper em `conservation_units.py` para:
  - testar espacialmente focos dentro de UCs com Shapely;
  - ignorar focos com `acq_date + acq_time` menor ou igual ao cursor `after`;
  - agrupar alertas por `uc_id + satellite + acq_date + acq_time`.

### Regra de Novo Alerta

Ao ativar o alarme no frontend:

- calcula o maior timestamp de aquisição já presente em `currentFires`;
- usa esse valor como baseline (`after`);
- não alerta focos que já estavam na tela;
- alerta apenas nova passagem de satélite posterior ao momento em que o alarme foi armado.

Se a mesma UC aparecer de novo em outra passagem posterior, pode alertar novamente.

### Frontend

Implementado em `static/js/app.js`.

- Botão na topbar:

```text
Ativar alarme de incêndio em UC
```

- Estados do botão:
  - desligado: `Ativar alarme de incêndio em UC`;
  - ligado: `Alarme UC ligado`;
  - disparado: `Alarme disparado`.
- Possui indicador visual tipo toggle.
- Ao ativar:
  - cria/libera `AudioContext`;
  - salva baseline temporal;
  - inicia polling a cada 60 segundos.
- Também verifica alertas após `applyFilters()`, então uma atualização manual pode disparar sem aguardar o próximo polling.
- Ao receber alerta:
  - toca beep em loop via Web Audio API;
  - abre modal institucional;
  - exibe UC, data/hora em Brasília, satélite, quantidade de focos e maior FRP.
- Ao clicar em `Reconhecer alerta`:
  - para o som;
  - fecha modal;
  - desliga o toggle;
  - limpa o timer de polling.
- Se o usuário mudar filtro com o alarme ligado:
  - o alarme é desligado;
  - o estado local é limpo;
  - aparece toast informando o desligamento.

### Limitações Conhecidas

- Reconhecimento é só em memória na aba.
- Não persiste em banco.
- Não sincroniza entre abas ou computadores.
- Ao recarregar a página, o estado do alarme é perdido.

Essas limitações foram decisões conscientes para a primeira versão.

## UI Recente

- Topbar recebeu indicador:

```text
Satélites ativos: NASA FIRMS (MODIS/VIIRS)
```

- Esse indicador é estático por enquanto.
- Pode virar dinâmico no futuro se o backend passar a expor sensores efetivamente presentes nos dados carregados.

## Validações Executadas

Antes das últimas mudanças de texto/topbar, os testes passaram:

```text
26 passed
```

Também foi executado:

```text
node --check static\js\app.js
```

Depois da alteração textual final do botão e do indicador de satélites ativos, recomenda-se rodar novamente:

```powershell
.\.venv\Scripts\python.exe -m pytest
node --check static\js\app.js
```

## Próximos Passos Recomendados

1. Conferir se `INPE/` deve ser ignorado, versionado ou removido.
2. Rodar testes finais.
3. Testar manualmente no navegador:
   - ligar alarme;
   - confirmar que não dispara para focos já carregados;
   - simular/forçar alerta posterior em UC;
   - confirmar som em loop;
   - reconhecer alerta;
   - confirmar desligamento automático.
4. Fazer commit das mudanças pendentes se estiver tudo aprovado.

