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
- **Espaço** (o mesmo botão do ataque; a porta tem prioridade) → `try_toggle(dungeon, player)`: usa a porta no tile à frente do personagem (direção em que ele está virado) ou no próprio tile. Abre/fecha os 2 tiles juntos. Não fecha se o personagem estiver em cima da porta ou indo para ela (mostra "Saia da porta para fechá-la").

### Desenho
| Lado | Sprite | Área |
|---|---|---|
| cima | porta dupla de frente, 2×2 tiles | tiles da porta + tile de cima (igual à parede alta, com pilares dos lados) |
| baixo | porta dupla achatada, 2×1 tiles | tiles da porta |
| esquerda / direita | porta dupla girada 90° (base virada para dentro da sala), 1×2 tiles | tiles da porta |

`render_map` guarda em `door.base` o pedaço do mapa por baixo de cada porta. `draw_door` restaura esse pedaço e desenha o sprite do estado atual, atualizando só aquela área do mapa pré-renderizado.

## Movimento (`player.py`)

- O personagem anda **um tile por vez** e nunca para entre dois tiles.
- As teclas viram um vetor `(dx, dy)` (`_read_move`): **duas teclas juntas andam na diagonal** (W+A, W+D, S+A, S+D); teclas opostas (A+D, W+S) se anulam.
- Parado:
  - Se é **outra direção**, primeiro só **vira** para ela. Segurando a tecla, começa a andar depois de `TURN_DELAY` (0,12 s); um toque rápido só vira. Na diagonal, se ele já olha para um dos dois lados (ex.: olhando para cima e aperta W+A), anda na hora.
  - Se já está virado para lá, anda na hora.
  - Andando sem parar (ao chegar num tile com a tecla apertada), trocar de direção — inclusive reta ↔ diagonal — é imediato, sem pausa.
- Escolha do passo (`_choose_step`), na ordem: a **diagonal**, só o eixo horizontal, só o vertical. Assim, com W+A encostado numa parede à esquerda ele **desliza** para cima.
  - A diagonal **não corta quina**: o tile diagonal e os dois tiles retos que ela atravessa têm que ser andáveis (parede ou porta fechada bloqueiam). Por isso não dá para entrar numa porta na diagonal nem passar espremido entre duas paredes.
  - O tile de destino não pode estar ocupado por zumbi; zumbi num dos tiles retos não impede a diagonal.
- Sprite: só existem 4 direções; na diagonal usa o sprite **horizontal** (`walk_left`/`walk_right`). `facing` continua sendo uma das 4 direções — o ataque e o Espaço nas portas usam `facing`.
- Em movimento, avança `velocidade × dt` em linha reta até o centro do alvo (distância euclidiana: a diagonal tem √2 tiles e leva ~1,41× o tempo de um passo reto — mesma velocidade em px/s, sem andar mais rápido na diagonal). Ao chegar, encaixa exatamente no tile e, se a tecla continua pressionada, já começa o próximo passo no mesmo frame, usando o tempo que sobrou. Por isso segurar a tecla dá um movimento contínuo e suave.
- Colisão: "o tile de destino é chão?" (`dungeon.is_walkable`), mais a regra da quina na diagonal.
- Velocidade: `PLAYER_SPEED` = 195 px/s (≈ 6 tiles/s); correndo, × `RUN_MULT` (2).
- Animação: `walk_<direção>` em movimento; a animação roda 2x mais rápido na corrida.
- Parado, continua **olhando para onde estava indo**: de frente usa a animação `idle`; para a direita, esquerda e costas usa a pose parada `idle_<direção>` (o 1º quadro da caminhada, com os pés juntos).

## Estamina (`player.py`)

| Situação | Efeito por segundo |
|---|---|
| Correndo (Shift + andando) | −25 (`STAMINA_DRAIN`) |
| Andando normal | +10 (`STAMINA_REGEN_WALK`) |
| Parado | +20 (`STAMINA_REGEN_IDLE`) |

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
- Zoom pela **roda do mouse**, contínuo entre `ZOOM_MIN` (1x) e `ZOOM_MAX` (2x). Cada clique da roda muda o **alvo** em `ZOOM_STEP` (0,1); em touchpads usa `precise_y` (frações de clique), então o scroll também é contínuo. O alvo é arredondado (dez cliques dão 2.0 exato, não 1.9999999).
- **Transição suave**: a cada quadro o zoom anda uma fração da distância até o alvo (`1 - e^(-ZOOM_SMOOTHING·dt)`), independente do FPS — chega a ~95% em 0,25 s e encaixa no alvo quando a diferença fica mínima.
- O mundo é desenhado numa superfície de tamanho tela ÷ zoom e escalado para a tela: em 1x sem escala, em exatamente 2x com `scale` (pixels nítidos) e nos zooms fracionários (1,3x, 1,7x...) com `smoothscale`, para não serrilhar (custa ~1–2 ms). A câmera continua centrada no personagem.

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
| `idle` | Pausa entre caminhadas (`ZOMBIE_IDLE_TIME`, hoje **0**: emenda direto na próxima caminhada). Cercado, sem direção livre, espera 0,1–0,3 s e tenta de novo. | sim |
| `chase` | Personagem a até **5 tiles** (Chebyshev, `ZOMBIE_CHASE_RADIUS`): vai atrás dele a 70 px/s (`ZOMBIE_CHASE_SPEED`) e, colado nele, ataca (veja "Vida do personagem"). | sim |
| `walk` | Sorteia uma das **8 direções** livres (retas ou diagonais) e anda 1–4 tiles nela (`ZOMBIE_WANDER_STEPS`), tile a tile, a 45 px/s (`ZOMBIE_SPEED`) — na diagonal, mesma velocidade em px/s. Depois volta a `idle`. | sim |
| `dying` | Vida chegou a 0: toca a animação de surgir **ao contrário** (afunda de volta no chão, `ZOMBIE_DEATH_FPS`). Não leva mais dano. | não |
| `dead` | Terminou de afundar: sai do jogo e conta em "Abatidos". | — |

- Vagando, o zumbi só anda para tiles **dentro da própria sala**, que sejam chão e estejam livres (sem o personagem nem outro zumbi — vale o tile atual e o de destino). Se não houver direção livre, espera um pouco e tenta de novo.
- Na diagonal, como o personagem, **não corta quina**: os dois tiles retos atravessados também têm que ser chão da sala. Usa o sprite horizontal (`walk_left`/`walk_right`).
- O personagem não entra em tile de zumbi fora do chão (`Player.update(..., blocked=...)`); zumbi enterrado não bloqueia.
- Têm **10 de vida** (`ZOMBIE_HP`) e levam dano do personagem (veja "Combate").

### Perseguição
- Vale para zumbis fora do chão e vivos (`idle`/`walk`/`chase`); o personagem morto não é perseguido. A troca entre vagar e perseguir só acontece com o zumbi parado no centro de um tile (nunca no meio de um passo).
- A cada tile, `chase_step` faz uma **busca em largura** curta (8 direções, sem cortar quina, sem paredes, portas fechadas, outros zumbis nem o personagem; até 11 tiles do personagem) e dá o primeiro passo do caminho mais curto até um tile **colado** nele. Sem caminho, espera virado para ele.
- Perseguindo pode **sair da sala** por portas abertas e corredores; porta fechada segura o zumbi.
- Com o personagem a mais de 5 tiles, volta a vagar **onde está**: na sala em que estiver (passa a ser a sala dele) ou, num corredor, pelo corredor (qualquer chão menos as portas) até entrar numa sala.
- O Espaço não fecha uma porta com zumbi dentro ("Tem um zumbi na porta!").

### Desenho
- Sprite 32×32 escalada 2× (64 px, `ZOMBIE_SIZE`) por vizinho mais próximo: pixel art nítida, mais ou menos da altura do personagem.
- Mesma sombra elíptica do personagem (menos durante o buraco no chão, nos primeiros quadros do surgimento).
- Ordenados por profundidade junto com o personagem; com a névoa ligada, só aparecem quando o tile em que estão desenhados está visível.
- Golpe: o sheet do zumbi não tem animação de ataque, então ele **recua um pouco** enquanto prepara e **avança** `ZOMBIE_LUNGE` px na direção do personagem ao bater.
- Ao levar dano: **piscam** claro/avermelhado (`HIT_FLASH_TIME`) e mostram uma **barra de vida** acima da cabeça por `HP_BAR_TIME` s (verde → laranja → vermelho).

## Combate (`combat.py`, `player.py`)

### Ataque do personagem
- **Espaço**: ataca com a faca na direção em que o personagem está virado (`Player.request_attack`). É o mesmo botão das portas: se há uma porta à frente (ou o personagem está numa), o Espaço abre/fecha a porta em vez de atacar (`Game.action`).
- Animação de 9 quadros a `ATTACK_FPS` (≈ 0,4 s). Durante o ataque ele não anda nem vira. Pedido no meio de um passo: o ataque começa assim que ele chega no tile. Pedidos durante um ataque são ignorados (não empilham). Parado atacando recupera estamina como parado.
- No quadro `ATTACK_HIT_FRAME` (5, quando aparece o rastro do golpe), `Player.update` devolve o **tile de impacto** (o tile à frente) — uma única vez por ataque.

### Dano em área
O golpe é centrado no impacto, pela distância de Chebyshev (contando diagonais) até ele (`ATTACK_DAMAGE = (11, 6, 4)`), mas **para a frente só alcança 2 tiles** a partir do personagem (`ATTACK_REACH`):

```
4 6 6 6 4
4 6 11 6 4      (⊙ = personagem olhando para cima)
4 6 ⊙ 6 4
4 4 4 4 4
```

- Impacto: **11** (mata na hora: zumbi tem 10). Colado no impacto: **6**. A 2 tiles do impacto: **4**, nos lados e atrás (a fileira a 3 tiles à frente do personagem ficou de fora). O personagem não se acerta.
- 6 + 4 também mata; quem leva só 6 fica com 4 de vida.
- Só leva dano o zumbi **vivo e fora do chão** que está num tile **visível** pelo personagem (parede bloqueia o golpe, igual à visão). Vale o tile em que o zumbi está desenhado (no meio de um passo, o mais próximo).

### Zumbi lançado pelo golpe
- Zumbi que **sobrevive** ao golpe (parado, andando ou perseguindo) é **lançado 1 tile para o lado oposto ao personagem** (`Zombie.knock_back`, chamado por `apply_attack`), em 8 direções: zumbi na diagonal do personagem voa na diagonal. O voo dura `ZOMBIE_KNOCKBACK_TIME` (0,15 s, desacelerando).
- Diagonal bloqueada: tenta os eixos. Parede, porta fechada, quina, outro zumbi ou o personagem no caminho: não é lançado (fica no tile em que estava desenhado).
- O golpe cancela o passo e o preparo do golpe do zumbi; durante o voo ele não anda nem ataca, e depois volta a vagar/perseguir dali. Se cair fora da sala, a sala dele passa a ser onde caiu.
- Quem morre com o golpe não é lançado: afunda onde está (inclusive se morrer no meio do voo).

### Feedback
- **Números de dano** (`FloatingText`) sobem e somem em `DAMAGE_TEXT_TIME` s: vermelho para 11, laranja para 6, claro para 4, com contorno escuro.
- Contador **Abatidos** no HUD.

## Vida do personagem (`player.py`, `zombies.py`, `main.py`)

### Golpe do zumbi
- Zumbi em `chase` **colado** no personagem (reto ou diagonal sem quina de parede no meio) prepara o golpe por `ZOMBIE_ATTACK_WINDUP` (0,4 s) e bate: **2 de dano** (`ZOMBIE_DAMAGE`). Depois espera `ZOMBIE_ATTACK_COOLDOWN` (1 s) antes de preparar de novo. Se o personagem sair de perto durante o preparo, o golpe é cancelado.
- `Horde.update` devolve os zumbis que bateram no quadro; `Game.zombie_hits` aplica no personagem (`Player.take_hit`).

### Dano e empurrão
- Vida inicial **10** (`PLAYER_HP`): cinco golpes de zumbi.
- `take_hit` cancela o passo e o ataque, vira o personagem **para o zumbi** e o **empurra 1 tile para o lado oposto** (8 direções: zumbi na diagonal empurra na diagonal), em `KNOCKBACK_TIME` (0,15 s, desacelerando). Se estava no meio de um passo, parte do tile em que está desenhado.
- Empurrão bloqueado (parede, porta fechada, zumbi, quina): tenta os eixos da diagonal; se nada estiver livre, não é empurrado.
- Animação: com empurrão, `hurt_<direção>` (6 quadros: silhueta branca, recuando, no ar, caindo, caído, de pé); sem empurrão, `hurt_light_<direção>` (4 quadros). `HURT_FPS` = 12 (0,5 s / 0,33 s). Durante a animação ele **não anda, não vira e não ataca**.
- Depois fica `PLAYER_INVULN_TIME` (1 s) **invulnerável, piscando** (já pode agir). Durante o dano também não leva outro golpe — vários zumbis em volta não tiram 6 de uma vez.
- Feedback: número `-2` vermelho subindo, **moldura vermelha** nas bordas da tela (`HIT_SCREEN_FLASH`) e a barra **Vida** no HUD (marcas a cada 2 de vida).

### Game over
- Vida 0: o personagem cai (animação de empurrão parada no quadro "caído"), os controles e os zumbis param de agir sobre ele, a tela escurece e aparece **GAME OVER**.
- Depois de `GAME_OVER_TIME` (3 s) a **mesma dungeon** (mesma seed) recomeça do zero: vida cheia, zumbis enterrados de novo, névoa zerada.
