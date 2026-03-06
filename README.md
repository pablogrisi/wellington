# Wellington

MVP web do jogo de cartas Wellington (1 humano + 3 bots).

## Regras implementadas
- Baralho completo (52) + 2 coringas.
- 4 jogadores por partida (jogador 0 = humano, 1-3 bots).
- Distribuicao inicial: 4 cartas por jogador.
- O humano comeca conhecendo as 2 cartas de baixo (slots 2 e 3).
- Compra do monte, troca opcional por uma carta da mesa, descarte.
- Pontuacao:
  - A = 0
  - Coringa = -2
  - K = -1
  - 2..10 = valor da carta
  - J = 11
  - Q = 12
- Habilidades ao descartar:
  - 5: ver uma carta sua
  - 6: ver uma carta de outro jogador
  - 7: trocar uma carta sua por uma de outro jogador sem ver
  - 8: ver uma sua e uma de outro jogador e escolher trocar ou nao
- Corte:
  - corte normal (com sua carta)
  - corte usando carta de outro jogador (troca por uma sua)
  - corte errado: compra 2 cartas cegas
- Chamada de Wellington:
  - quem chama fica travado (nao mexe mais nas cartas e nao corta)
  - o jogo termina quando a vez volta para quem chamou

## Estrutura
- `backend/` FastAPI + motor de jogo
- `frontend/` SPA simples em HTML/CSS/JS

## Como rodar
1. Criar ambiente virtual no backend
2. Instalar dependencias
3. Subir API

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abrir no navegador:
- http://127.0.0.1:8000

## Observacoes
- Cada sessao (cookie do navegador) tem seu proprio jogo.
- Ao entrar, o jogador precisa informar nome.
- O backend gera logs de entrada (`event=player_start`) visiveis no Render.
- Persistencia opcional de jogadores no Supabase (gratis) via REST.
- Multiplayer real (4 humanos online) fica para a proxima fase.

## Logs de jogadores (gratis)
Voce pode ver quem entrou no jogo de duas formas:

- Render Logs: no painel do servico web, procure por `event=player_start`.
- Supabase (opcional): persistir entradas em tabela para consulta historica.

### Variaveis de ambiente (opcional para Supabase)
- `SUPABASE_URL` (ex.: `https://xxxx.supabase.co`)
- `SUPABASE_SERVICE_ROLE_KEY`

Se essas variaveis nao forem definidas, o sistema continua funcionando e registra apenas no log do servidor.

### Exemplo de tabela no Supabase
```sql
create table if not exists public.player_sessions (
  id bigint generated always as identity primary key,
  session_id text not null,
  player_name text not null,
  started_at timestamptz not null,
  user_agent text
);
```

## Deploy gratis (Render)
1. Suba este projeto para um repositorio no GitHub.
2. Crie conta em https://render.com e conecte o GitHub.
3. Em Render, clique em `New +` -> `Blueprint` e selecione o repositorio.
4. O arquivo `render.yaml` ja esta pronto; confirme o deploy.
5. Ao final, abra a URL publica gerada pelo Render e compartilhe com seus amigos.

### Importante sobre o plano gratis
- O servico gratuito pode "dormir" apos inatividade; a primeira requisicao pode demorar.
- O armazenamento local nao e persistente em longo prazo no free tier. O `game_state.json` pode ser perdido em restart/redeploy.


