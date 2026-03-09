# Plano de Testes - Jogo Welligton

## Frameworks Recomendados

| Camada | Framework | Justificativa |
|--------|-----------|---------------|
| Backend (Python) | **pytest** | Mais popular, excelente suporte a fixtures e mocks, fácil integração com CI/CD |
| Frontend (JS) | **Vitest** | Rápido, moderno, compatível com Jest, ideal para projetos com Vite |

---

## Backend Tests (pytest)

### Estrutura de Arquivos

```
backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Fixtures compartilhadas
│   ├── test_card_model.py   # Testes do modelo Card
│   ├── test_game_init.py    # Testes de inicialização
│   ├── test_turn_flow.py    # Testes de fluxo de turnos
│   ├── test_abilities.py    # Testes das habilidades 5,6,7,8
│   ├── test_cuts.py         # Testes de sistema de cuts
│   ├── test_wellington.py   # Testes de chamada Wellington
│   └── test_scoring.py     # Testes de pontuação
├── app/
│   └── game_engine.py
└── requirements.txt
```

### Testes por Categoria

#### 1. test_card_model.py - Modelo de Cartas

| ID | Descrição | Caso de Teste |
|----|-----------|---------------|
| CARD-01 | Pontuação do Ás | A = 0 pontos |
| CARD-02 | Pontuação do Rei | K = -1 pontos |
| CARD-03 | Pontuação do Joker | JK = -2 pontos |
| CARD-04 | Pontuação das cartas numéricas | 2-10 = valor facial |
| CARD-05 | Pontuação do Valete | J = 11 pontos |
| CARD-06 | Pontuação da Rainha | Q = 12 pontos |
| CARD-07 | Construção de baralho | 54 cartas (52 + 2 Jokers) |
| CARD-08 | Label da carta | Formato correto (ex: "AH", "10S") |

#### 2. test_game_init.py - Inicialização do Jogo

| ID | Descrição | Caso de Teste |
|----|-----------|---------------|
| INIT-01 | Criação de novo jogo | 4 jogadores criados |
| INIT-02 | Distribuição inicial | Cada jogador recebe 4 cartas |
| INIT-03 | Cartas conhecidas inicial | Jogador conhece 2 cartas (slots 2,3) |
| INIT-04 | Monte de compras | Cartas restantes no draw_pile |
| INIT-05 | Descarte inicial | 1 carta no discard_pile |
| INIT-06 | Turno inicial | Jogador humano começa (index 0) |

#### 3. test_turn_flow.py - Fluxo de Turnos

| ID | Descrição | Caso de Teste |
|----|-----------|---------------|
| TURN-01 | Ação de draw | Carta adicionada ao drawn_card |
| TURN-02 | Ação de discard drawn | drawn_card vai para discard_pile |
| TURN-03 | Ação de replace | Carta substituída no slot correto |
| TURN-04 | Avanço de turno | current_player incrementa circularmente |
| TURN-05 | Descarte vai para pilha | Carta visível no descarte |
| TURN-06 | Turno retorna ao bem-sucedido | next_player index correto |

#### 4. test_abilities.py - Habilidades

| ID | Descrição | Caso de Teste |
|----|-----------|---------------|
| ABIL-5-01 | Habilidade 5 ativa | Ao descartar 5, pending_ability é configurado |
| ABIL-5-02 | Habilidade 5 revela carta | Carta própria fica conhecida |
| ABIL-6-01 | Habilidade 6 ativa | Ao descartar 6 |
| ABIL-6-02 | Habilidade 6 revela carta de outro | Carta de outro jogador fica conhecida |
| ABIL-7-01 | Habilidade 7 ativa | Ao descartar 7 |
| ABIL-7-02 | Habilidade 7 troca cartas | Cartas trocadas entre jogadores |
| ABIL-7-03 | Habilidade 7 preserva conhecimento | Cards known to players preserved |
| ABIL-8-01 | Habilidade 8 ativa | Ao descartar 8 |
| ABIL-8-02 | Habilidade 8 revela e oferece swap |both cards revealed + swap option |
| ABIL-8-03 | Habilidade 8 revela sem swap | Apenas revelação |

#### 5. test_cuts.py - Sistema de Cuts

| ID | Descrição | Caso de Teste |
|----|-----------|---------------|
| CUT-01 | Cut com valor correspondente | Sucesso quando valores batem |
| CUT-02 | Cut com valor diferente | Falha com penalty |
| CUT-03 | Self cut | Jogador corta própria carta |
| CUT-04 | Self cut deixa slot vazio | Slot fica None |
| CUT-05 | Cut em outro jogador | Usa carta de outro |
| CUT-06 | Cut incorreto own card | Penalidade: 2 cartas cegas |
| CUT-07 | Cut incorreto outro | Penalidade: 1 carta cega |
| CUT-08 | Chain de cuts | Múltiplos cuts em sequência |
| CUT-09 | Cut com carta nunca vista | Permite tentativa às cegas |

#### 6. test_wellington.py - Sistema Wellington

| ID | Descrição | Caso de Teste |
|----|-----------|---------------|
| WELL-01 | Chamada normal | wellington_caller configurado |
| WELL-02 | Cartas travam após chamada | locked = True |
| WELL-03 | Fim de rodada | game_over = True ao retornar |
| WELL-04 | Auto Wellington | Joga automaticamente se sem cartas |
| WELL-05 | Immediate Wellington | Corte instantâneo dispara |
| WELL-06 | Tiebreak - não chamador ganha | Não chamador vence em caso de empate |
| WELL-07 | Empate sem chamadores | Resulta em draw |

#### 7. test_scoring.py - Sistema de Pontuação

| ID | Descrição | Caso de Teste |
|----|-----------|---------------|
| SCORE-01 | Cálculo de pontuação | Soma correta dos valores |
| SCORE-02 | Menor pontuação vence | Comparação correta |
| SCORE-03 | K reduz pontuação | Valor negativo aplicado |
| SCORE-04 | Joker reduz 2 | Valor -2 aplicado |
| SCORE-05 | Pontuação com empty slots | Slots vazios não contam |

---

## Frontend Tests (Vitest)

### Estrutura de Arquivos

```
frontend/
├── src/
│   ├── __tests__/
│   │   ├── card-render.test.js
│   │   ├── game-state.test.js
│   │   ├── event-handlers.test.js
│   │   └── ui-components.test.js
│   ├── script.js
│   └── ...
├── index.html
├── package.json
└── vite.config.js
```

### Testes por Categoria

#### 1. card-render.test.js - Renderização de Cartas

| ID | Descrição | Caso de Teste |
|----|-----------|---------------|
| UI-CARD-01 | Carta vermelha ♥♦ renderiza em vermelho |
| UI-CARD-02 | Carta preta ♠♣ renderiza em preto |
| UI-CARD-03 | Carta oculta mostra verso |
| UI-CARD-04 | Carta vazia mostra slot vazio |
| UI-CARD-05 | Joker tem estilo único |

#### 2. game-state.test.js - Estado do Jogo

| ID | Descrição | Caso de Teste |
|----|-----------|---------------|
| UI-STATE-01 | Estado inicial correto |
| UI-STATE-02 | Atualização após draw |
| UI-STATE-03 | Atualização após discard |
| UI-STATE-04 | Indicação de vez do jogador |
| UI-STATE-05 | Exibição de wellington chamado |

#### 3. event-handlers.test.js - Manipuladores de Eventos

| ID | Descrição | Caso de Teste |
|----|-----------|---------------|
| UI-EVENT-01 | Click em draw pile dispara ação |
| UI-EVENT-02 | Click em carta seleciona |
| UI-EVENT-03 | Cut window abre após descarte |
| UI-EVENT-04 | Botões de ação habilitados corretamente |
| UI-EVENT-05 | Ability instructions exibidas |

#### 4. ui-components.test.js - Componentes de UI

| ID | Descrição | Caso de Teste |
|----|-----------|---------------|
| UI-COMP-01 | Layout de 4 jogadores |
| UI-COMP-02 | Grid 2x2 de cartas |
| UI-COMP-03 | Área de monte e descarte |
| UI-COMP-04 | Painel de controles |
| UI-COMP-05 | Event log atualiza |
| UI-COMP-06 | Contagem regressiva de cut window |

---

##安装 e Configuração

### Backend

```bash
cd backend
pip install pytest pytest-mock
```

### Frontend

```bash
cd frontend
npm install -D vitest jsdom @testing-library/dom
```

---

## Prioridades de Implementação

### Fase 1 - Backend Core (Alta Prioridade)
1. test_card_model.py
2. test_game_init.py
3. test_turn_flow.py

### Fase 2 - Backend Game Logic (Média Prioridade)
4. test_abilities.py
5. test_cuts.py
6. test_wellington.py

### Fase 3 - Backend Scoring (Baixa Prioridade)
7. test_scoring.py

### Fase 4 - Frontend (se tempo permitir)
- Testes de UI básicos

---

## Métricas de Cobertura Alvo

| Componente | Cobertura Mínima |
|------------|------------------|
| game_engine.py | 80% |
| script.js | 60% |
