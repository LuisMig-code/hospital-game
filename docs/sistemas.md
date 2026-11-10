# Sistemas do jogo

## Geração da dungeon (`dungeon.py`)

Algoritmo **BSP (Binary Space Partitioning)**, determinístico pela seed (`random.Random(seed)`, sem estado global).

1. O mapa (80×60 tiles) menos 1 tile de borda é dividido recursivamente em "folhas". Corta sempre a dimensão maior quando a proporção passa de 1,25; folhas grandes sempre se dividem, as médias com 75% de chance. Tamanho mínimo de folha: `MIN_LEAF = 14`.
2. Em cada folha nasce uma sala retangular aleatória (mínimo `MIN_ROOM = 6`), com pelo menos 1 tile de margem.
3. Ramos irmãos da árvore são ligados por corredores em **L** com largura sorteada em `CORRIDOR_WIDTHS = (2, 3)`. Ligar sempre os irmãos garante que **todo o chão é alcançável**.
4. A borda do mapa é sempre parede.

Seeds em texto viram número com `zlib.crc32` (estável entre execuções, ao contrário de `hash()`); textos numéricos como `"42"` viram o próprio número.

### Spawn

O personagem nasce no **canto superior esquerdo**: `Dungeon.spawn` é o tile de chão (que não seja porta) mais próximo de `(0, 0)` — menor `x² + y²`, com desempate por `y` e depois `x`. Como o canto em si é sempre parede, ele nasce no chão mais próximo dali.

## Portas (`doors.py`)

### Onde ficam
`place_doors` roda no fim de `generate` (mesmo `rng`, então é determinístico). Para cada sala e cada lado (cima, baixo, esquerda, direita), percorre a linha de parede logo fora da sala procurando **aberturas** — chão na linha da parede com corredor do lado de fora. Vira porta a abertura que:
- tem 2 ou 3 tiles contínuos (corredores têm 2–3 de largura);
- tem parede nas duas pontas, e o corredor entra perpendicular à parede.

Aberturas de 3 tiles são estreitadas para 2 (uma ponta, sorteada, vira parede): todas as portas são **duplas** (2 tiles). Depois disso, `_fill_nubs` transforma em parede qualquer chão que tenha ficado com 1 tile de largura (por exemplo, um corredor curtinho entre duas portas estreitadas).

Resultado típico: ~17 portas por dungeon, nos 4 lados.

### Comportamento
- `Door`: `tiles` (2 tiles), `side` (lado da sala), `open` (começa `False`).
- Os tiles de porta continuam `FLOOR` no grid. `Dungeon.is_walkable` devolve `False` para **porta fechada** — então a porta fechada bloqueia o movimento e a visão automaticamente. `Dungeon.is_floor` ignora as portas (usado na geração e no desenho).
- **Espaço** → `try_toggle(dungeon, player)`: usa a porta no tile à frente do personagem (direção em que ele está virado) ou no próprio tile. Abre/fecha os 2 tiles juntos. Não fecha se o personagem estiver em cima da porta ou indo para ela (mostra "Saia da porta para fechá-la").

### Desenho
| Lado | Sprite | Área |
|---|---|---|
| cima | porta dupla de frente, 2×2 tiles | tiles da porta + tile de cima (igual à parede alta, com pilares dos lados) |
| baixo | porta dupla achatada, 2×1 tiles | tiles da porta |
| esquerda / direita | porta dupla girada 90° (base virada para dentro da sala), 1×2 tiles | tiles da porta |

`render_map` guarda em `door.base` o pedaço do mapa por baixo de cada porta. `draw_door` restaura esse pedaço e desenha o sprite do estado atual, atualizando só aquela área do mapa pré-renderizado.

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
- **Paredes vizinhas de chão visível** também ficam visíveis (inclusive portas fechadas). Sem isso, olhando rente a uma parede, a linha de visão "raspa" nela e só os primeiros tiles daquela parede aparecem.
- **Paredes altas**: ocupam 2 tiles (veja o tileset). Se a face frontal de uma parede está visível, o tile de cima também é revelado. O mesmo vale para portas na parede de cima da sala.
- **Portas**: fechada bloqueia a visão (não é andável); ao abrir/fechar, a visão é recalculada na hora (`Vision.update(origin, force=True)`).
- `Vision` guarda `visible` (visto agora) e `explored` (visto alguma vez). Só recalcula quando muda o tile em que o personagem está desenhado, por isso a visão avança no meio do passo.
- Cada tile fica num de três estados:
  - **não descoberto**: preto;
  - **descoberto, fora da visão**: escurecido (`FOG_EXPLORED_ALPHA`);
  - **dentro da visão**: cores normais.
- A névoa é desenhada com bordas suaves (veja "Efeitos visuais" abaixo).

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

- **Portas**: desenhadas por cima, depois das paredes (veja "Portas" acima). Para decidir o desenho das paredes, um tile de porta conta como sólido — por isso a parede ao lado de uma porta de cima termina em **pilar**.

## Efeitos visuais (`lighting.py`, `tileset.py`, `player.py`, `main.py`)

| Efeito | Como funciona | Ajuste em `settings.py` |
|---|---|---|
| **Sombra das paredes no piso** | `bake_wall_shadows` desenha, uma vez, faixas em degradê nos tiles de chão encostados em parede: no topo (parede acima, a sombra da parede alta) e nas laterais. Cantos internos ficam mais escuros pela soma. Usa o grid, então não muda com as portas. | `WALL_SHADOW_TOP`, `WALL_SHADOW_SIDE`, `WALL_SHADOW_ALPHA` |
| **Sombra do personagem** | Elipse escura e suave sob os pés, desenhada antes do sprite. | `PLAYER_SHADOW_ALPHA` |
| **Personagem atrás da porta** | Portas da parede de cima ocupam 2 tiles; a metade de cima fica sobre o corredor. Com o personagem nesse corredor (ao norte da porta), essa metade é redesenhada por cima dele, semitransparente — dá profundidade sem esconder o personagem. | `OCCLUDER_ALPHA` |
| **Névoa suave** | `FogLayer` guarda a névoa numa superfície minúscula (1 pixel por tile; alpha 255 não descoberto, `FOG_EXPLORED_ALPHA` descoberto, 0 visível). A cada quadro, só o pedaço que aparece na tela é ampliado com `smoothscale`: a interpolação cria degradês entre os tiles em vez de quadrados. | `FOG_EXPLORED_ALPHA` |
| **Luz com queda** | Máscara radial (pré-calculada) centrada no personagem: claro perto dele, escurecendo até `LIGHT_EDGE_ALPHA` na borda do raio de visão. Fora do quadrado da máscara, o resto da tela recebe a mesma escuridão da borda (sem emenda). Como essa escuridão soma com a névoa, a névoa dos tiles descobertos é compensada (`explored_fog_alpha`) para o resultado final continuar sendo `FOG_EXPLORED_ALPHA`. | `LIGHT_EDGE_ALPHA` |
| **Tremulação** | A cada 0,08 s a luz sorteia um nível (quase sempre estável; às vezes uma piscada rápida, como lâmpada de hospital). São 4 máscaras pré-calculadas. | `LIGHT_FLICKER` |
| **HUD** | Painel escuro semitransparente com cantos arredondados, texto com sombra de 1 px e barra de estamina arredondada. | `HUD_PANEL_ALPHA` |

Custo: o desenho do mundo leva ~3–4 ms por quadro (medido sem janela), bem abaixo dos 16 ms de 60 FPS.

## Zumbis (`zombies.py`)

### Spawn
`spawn_zombies` (chamado por `Horde`) coloca **3 a 5 zumbis por sala** (`ZOMBIES_PER_ROOM`), em tiles de chão distintos dentro do retângulo da sala, sem encostar em portas e a mais de 2 tiles do spawn do personagem. Usa um `Random` derivado da seed: a mesma seed gera os mesmos zumbis nos mesmos lugares. Em 200 seeds, todas as salas ficaram com 3, 4 ou 5.

### Estados
| Estado | O que acontece | Bloqueia? |
|---|---|---|
| `underground` | Enterrado e invisível, esperando ser visto. | não |
| `emerging` | Assim que o tile dele entra na visão do personagem (e o personagem não está em cima), toca a animação de **sair do chão** (8 quadros, 1 s). | sim |
| `idle` | Parado por 1–4 s (`ZOMBIE_IDLE_TIME`). | sim |
| `walk` | Sorteia uma direção livre e anda 1–4 tiles (`ZOMBIE_WANDER_STEPS`), tile a tile, a 45 px/s (`ZOMBIE_SPEED`). Depois volta a `idle`. | sim |

- O zumbi só anda para tiles **dentro da própria sala**, que sejam chão e estejam livres (sem o personagem nem outro zumbi — vale o tile atual e o de destino). Se não houver direção livre, espera um pouco e tenta de novo.
- O personagem não entra em tile de zumbi fora do chão (`Player.update(..., blocked=...)`); zumbi enterrado não bloqueia.
- Ainda não há dano nem perseguição: eles só vagam.

### Desenho
- Sprite 32×32 escalada 2× (64 px, `ZOMBIE_SIZE`) por vizinho mais próximo: pixel art nítida, mais ou menos da altura do personagem.
- Mesma sombra elíptica do personagem (menos durante o buraco no chão, nos primeiros quadros do surgimento).
- Ordenados por profundidade junto com o personagem; com a névoa ligada, só aparecem quando o tile em que estão desenhados está visível.
