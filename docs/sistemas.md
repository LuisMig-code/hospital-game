# Sistemas do jogo

## Geração da dungeon (`dungeon.py`)

Algoritmo **BSP (Binary Space Partitioning)**, determinístico pela seed (`random.Random(seed)`, sem estado global).

1. O mapa (80×60 tiles) menos 1 tile de borda é dividido recursivamente em "folhas". Corta sempre a dimensão maior quando a proporção passa de 1,25; folhas grandes sempre se dividem, as médias com 75% de chance. Tamanho mínimo de folha: `MIN_LEAF = 14`.
2. Em cada folha nasce uma sala retangular aleatória (mínimo `MIN_ROOM = 6`), com pelo menos 1 tile de margem.
3. Ramos irmãos da árvore são ligados por corredores em **L** com largura sorteada em `CORRIDOR_WIDTHS = (2, 3)`. Ligar sempre os irmãos garante que **todo o chão é alcançável**.
4. A borda do mapa é sempre parede.

Seeds em texto viram número com `zlib.crc32` (estável entre execuções, ao contrário de `hash()`); textos numéricos como `"42"` viram o próprio número.

O personagem começa no centro da primeira sala (`Dungeon.spawn`).

## Movimento (`player.py`)

- O personagem anda **um tile por vez** e nunca para entre dois tiles.
- Parado, lê uma direção (sem diagonal; a horizontal tem prioridade). Vira para ela e, se o tile vizinho é chão, define esse tile como alvo.
- Em movimento, avança `velocidade × dt` até o centro do alvo. Ao chegar, encaixa exatamente no tile e, se a tecla continua pressionada, já começa o próximo passo no mesmo frame, usando o tempo que sobrou. Por isso segurar a tecla dá um movimento contínuo e suave.
- Colisão: só "o tile de destino é chão?" (`dungeon.is_walkable`).
- Velocidade: `PLAYER_SPEED` = 195 px/s (≈ 6 tiles/s); correndo, × `RUN_MULT` (2).
- Animação: `walk_<direção>` em movimento, `idle` parado; a animação roda 2x mais rápido na corrida.

## Estamina (`player.py`)

| Situação | Efeito por segundo |
|---|---|
| Correndo (Shift + andando) | −25 (`STAMINA_DRAIN`) |
| Andando normal | +5 (`STAMINA_REGEN_WALK`) |
| Parado | +10 (`STAMINA_REGEN_IDLE`) |

- Começa e vai no máximo até 100.
- **Cansaço**: ao chegar a 0, o personagem fica "cansado" e não corre até a estamina voltar a 20 (`STAMINA_RECOVER_TO_RUN`). Isso evita que ele fique alternando entre correr e andar com a estamina perto de zero.
- HUD: barra amarela (vermelha abaixo de 25%) com o valor e o aviso "CORRENDO".

## Visão / névoa de guerra (`fov.py` + `main.py`)

- Raio de **8 tiles** (`VISION_RADIUS`). Um tile está no raio se `dx² + dy² <= r² + r`, o que deixa o círculo mais redondo no grid.
- **Linha de visão**: para cada tile no raio, traça uma linha de Bresenham a partir do personagem. O tile só é visível se todos os tiles no caminho forem chão. A parede em si aparece, mas o que está atrás dela não.
- **Paredes altas**: ocupam 2 tiles (veja o tileset). Se a face frontal de uma parede está visível, o tile de cima também é revelado.
- `Vision` guarda `visible` (visto agora) e `explored` (visto alguma vez). Só recalcula quando muda o tile em que o personagem está desenhado, por isso a visão avança no meio do passo.
- Cada tile fica num de três estados:
  - **não descoberto**: preto;
  - **descoberto, fora da visão**: escurecido (`FOG_EXPLORED_ALPHA`);
  - **dentro da visão**: cores normais.
- A névoa é uma superfície do tamanho do mapa, atualizada só nos tiles recém-descobertos (incremental).
- Um **círculo** semitransparente mostra o alcance da visão; ele some com a névoa ao apertar V.

## Câmera e zoom (`main.py`)

- Câmera centrada no personagem, limitada às bordas do mapa.
- Zoom com `+`/`-` entre os níveis de `ZOOM_LEVELS` (hoje 1x e 2x). O mundo é desenhado numa superfície de tamanho tela ÷ zoom e escalado: aproximando usa `scale` (pixels nítidos), afastando usaria `smoothscale`.
- A tecla `+` também responde ao `=` (com ou sem Shift) e ao teclado numérico.

## Renderização do mapa (`tileset.py`)

O mapa inteiro é desenhado uma vez por dungeon (`render_map`) a partir das peças do tileset (veja [assets.md](assets.md)):

- **Piso**: o azulejo tem 3×3 placas, e cada placa vira 1 tile; cada tile usa a fatia `(x % 3, y % 3)`. Cada bloco 3×3 tem 8% de chance de ser a versão **com sangue**.
- **Parede frontal** (parede com chão logo abaixo), processada por trechos horizontais contínuos:
  - tile de cima também é parede → **parede alta** de 2 tiles (desenhada no tile da frente e no de cima), com **pilar** nas pontas do trecho, **ventilação** (2 colunas, 15% de chance) e, no resto, faixas lisas sorteadas entre 4 variações para a rachadura não se repetir;
  - tile de cima é chão (parede de 1 tile de espessura) → **parede baixa**, com 1 tile de altura.
- **Demais paredes** (topo, laterais, miolo): cor sólida `COLOR_WALL_TOP`.
- As variações (sangue, ventilação, faixas) usam um `Random` derivado da seed, então são as mesmas a cada vez.
- O grid é desenhado só sobre o piso, para não cortar a arte das paredes.

As **portas** já são recortadas, mas ainda não são usadas no mapa, porque a dungeon não marca as entradas das salas.
