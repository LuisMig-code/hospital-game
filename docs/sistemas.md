# Sistemas do jogo

## Geração da dungeon (`dungeon.py`)

> Depois das salas, corredores e portas, cada sala recebe um tema e móveis — veja "Salas temáticas e móveis".

Algoritmo **BSP (Binary Space Partitioning)**, determinístico pela seed (`random.Random(seed)`, sem estado global).

1. O mapa (80×60 tiles) menos 1 tile de borda é dividido recursivamente em "folhas". Corta sempre a dimensão maior quando a proporção passa de 1,25; folhas grandes sempre se dividem, as médias com 75% de chance. Tamanho mínimo de folha: `MIN_LEAF = 14`.
2. Em cada folha nasce uma sala retangular aleatória (mínimo `MIN_ROOM = 6`), com pelo menos 1 tile de margem.
3. Ramos irmãos da árvore são ligados por corredores em **L** com largura sorteada em `CORRIDOR_WIDTHS = (2, 3)`. Ligar sempre os irmãos garante que **todo o chão é alcançável**.
4. A borda do mapa é sempre parede.

Seeds em texto viram número com `zlib.crc32` (estável entre execuções, ao contrário de `hash()`); textos numéricos como `"42"` viram o próprio número.

### Spawn
O personagem começa **na frente do elevador de chegada** (`Dungeon.spawn`), que fica na sala mais perto do canto de cima à esquerda — o chão (não porta) com menor `x² + y²` (veja "Elevadores e andares").

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

O desenho da porta fechada depende do tema da sala dona dela (`Door.room`): padrão, com sangue (Emergência), vidro quebrado (Depósito) ou cofre (Necrotério); aberta é sempre a mesma porta dupla aberta.

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

## Salas temáticas e móveis (`themes.py`, `furnish.py`)

### Temas
Depois das portas, `dungeon.generate` chama `furnish` (com um `Random` próprio, derivado da seed). Cada sala sorteia um tema; a sala do spawn (ou a mais perto dele, se o spawn cair num corredor) é sempre a **Recepção**. O tema decide parede, porta, piso e móveis:

| Tema | Parede | Porta fechada | Piso | Móveis (colisão) | Detalhes no chão |
|---|---|---|---|---|---|
| Recepção | branca rachada (0) | padrão | bege ou xadrez | sofás de espera, mesas com computador, cadeiras, poltrona, lixeiras, armário | azulejos soltos, vidro |
| Enfermaria | creme com trilho de cortina (2) | padrão | liso (+ sujeira, gotas, pegadas) | camas, criados-mudos, suportes de soro, cortinas, biombos, cadeira de rodas | bandagens, luvas, panos |
| Emergência | com sangue (1) | com sangue | liso (+ poças, rastros, mão de sangue) | macas, carrinhos de emergência, monitores, soro, pia, cadeira de rodas caída, cama quebrada | seringas, panos, bolsas de soro, vidro |
| Centro cirúrgico | azulejo azul (3) | padrão | azul | mesa de cirurgia + foco + mesa de instrumentos, anestesia, ventilador, monitores, armários de vidro, oxigênio | seringas, luvas, panos |
| Necrotério | concreto enferrujado (4) | cofre | cinza escuro | gavetas de cadáver, mesas de autópsia, maca coberta, lixo hospitalar, estantes | saco de corpo, luvas, panos |
| Depósito | com mofo (5) | vidro quebrado | liso (+ mofo, rachaduras, queimado, poça, concreto) | estantes, armários/lockers, caçambas, caixas, caixotes (sempre fechados), entulho, móveis caídos | azulejos soltos, vidro, forro caído |

Corredores: parede padrão (0), piso liso com detalhes de vez em quando (rachadura, pegadas, poça, papéis, sangue, ralo, vidro). O nome do tema aparece no HUD quando o personagem entra na sala.

### Onde vão os móveis
Densidade moderada: cada sala ocupa no máximo `FURNITURE_DENSITY` (24%) dos tiles com móveis (em 100 seeds, média de ~11%).
1. **Parede de cima** (a que aparece): móveis do tema lado a lado, com vãos sorteados.
2. **Grupos no meio** das salas grandes (≥ 8×7): 1 (ou 2 nas salas ≥ 110 tiles), ex.: mesa de cirurgia com foco e mesa de instrumentos, fileira de cadeiras, maca com soro. O primeiro móvel do grupo precisa de 1 tile livre em volta.
3. **Laterais**: móveis de 1 tile de largura (criado-mudo, soro, estante, cama de pé...).
4. **Soltos**: 0–2 móveis 1×1 pela sala (cadeira caída, entulho...), com 1 tile livre em volta.
5. **Detalhes no chão** (sem colisão): 1–3 por sala, desenhados no mapa.

Regras de cada móvel (se falhar, tenta outra posição ou outro móvel): pegada inteira no chão da sala; a mais de 2 tiles de qualquer porta e do spawn; não encosta em nenhuma abertura da sala (chão na linha da parede); e **não fecha passagem** — depois de colocar, uma busca em largura confere que os vizinhos livres do móvel continuam ligados entre si pelo chão da sala (com as aberturas). Por isso todo chão sem móvel do mapa continua alcançável a partir do spawn (testado em 100 seeds).

### Colisão
- `Dungeon.blocked` guarda os tiles com móvel; `is_walkable` recusa esses tiles. Como personagem (inclusive a regra de quina na diagonal), zumbis (passo, perseguição, empurrões), spawn de zumbis e de kits usam `is_walkable`, todos respeitam os móveis sem código a mais.
- Móveis **não bloqueiam a visão**: a névoa usa `is_transparent` (chão que não é porta fechada).

## Renderização do mapa (`tileset.py`, `props.py`)

O mapa inteiro é desenhado uma vez por dungeon (`render_map`) a partir das peças novas (veja [assets.md](assets.md)):

- **Piso**: blocos de 3×3 tiles; cada tile usa a fatia `(x % 3, y % 3)` do bloco. Cada bloco 3×3 do grid usa o piso base da sala (`Room.floor`) ou do corredor e, com `FLOOR_DECAL_CHANCE` (22%), um bloco com detalhe do tema (só nos temas de piso liso, porque os blocos de detalhe têm fundo liso).
- **Detalhes no chão** dos props sem colisão: desenhados no mapa logo depois do piso.
- **Parede frontal** (parede com chão logo abaixo), por trechos horizontais contínuos **do mesmo estilo** (o da sala que fica embaixo; corredor = estilo 0):
  - tile de cima também é parede → **parede alta** de 2 tiles, com **pilar** nas pontas do trecho, um **detalhe** de 2 colunas de vez em quando (`WALL_DETAIL_CHANCE`, 18%: parede cheia com rachadura/sangue/mofo, janela, ventilação, placa, armário de remédios, luminária, canos; na parede branca também buraco, entulho, lâmpada vermelha, persiana, extintor e placa) e, no resto, 4 faixas lisas sorteadas;
  - tile de cima é chão → **parede baixa**, 1 tile de altura.
- **Demais paredes** (topo, laterais, miolo): cor sólida `COLOR_WALL_TOP`.
- **Portas**: porta dupla fechada do tema da sala dona da porta (`Door.room`) e a porta dupla aberta para todas (veja "Portas").
- As variações usam um `Random` derivado da seed: a mesma seed gera exatamente a mesma imagem.
- **Móveis** (com colisão) **não** vão no mapa: são desenhados a cada quadro junto com personagem, zumbis e kits, ordenados pela base da pegada (`PropArt.anchor`) — o personagem atrás de uma maca fica com as pernas escondidas por ela; à frente, passa por cima. Só os móveis na área da câmera são desenhados, antes da névoa.
- O grid é desenhado só sobre o piso, para não cortar a arte das paredes.

## Efeitos visuais (`lighting.py`, `tileset.py`, `player.py`, `main.py`)

| Efeito | Como funciona | Ajuste em `settings.py` |
|---|---|---|
| **Sombra das paredes no piso** | `bake_wall_shadows` desenha, uma vez, faixas em degradê nos tiles de chão encostados em parede: no topo (parede acima, a sombra da parede alta) e nas laterais. Cantos internos ficam mais escuros pela soma. Usa o grid, então não muda com as portas. | `WALL_SHADOW_TOP`, `WALL_SHADOW_SIDE`, `WALL_SHADOW_ALPHA` |
| **Sombra do personagem** | Elipse escura e suave sob os pés, desenhada antes do sprite. | `PLAYER_SHADOW_ALPHA` |
| **Personagem atrás da porta** | Portas da parede de cima ocupam 2 tiles; a metade de cima fica sobre o corredor. Com o personagem nesse corredor (ao norte da porta), essa metade é redesenhada por cima dele, semitransparente — dá profundidade sem esconder o personagem. | `OCCLUDER_ALPHA` |
| **Névoa suave** | `FogLayer` guarda a névoa numa superfície minúscula (1 pixel por tile; alpha 255 não descoberto, `FOG_EXPLORED_ALPHA` descoberto, 0 visível). A cada quadro, só o pedaço que aparece na tela é ampliado com `smoothscale`: a interpolação cria degradês entre os tiles em vez de quadrados. | `FOG_EXPLORED_ALPHA` |
| **Luz com queda** | Máscara radial (pré-calculada) centrada no personagem: claro perto dele, escurecendo até `LIGHT_EDGE_ALPHA` na borda do raio de visão. Fora do quadrado da máscara, o resto da tela recebe a mesma escuridão da borda (sem emenda). Como essa escuridão soma com a névoa, a névoa dos tiles descobertos é compensada (`explored_fog_alpha`) para o resultado final continuar sendo `FOG_EXPLORED_ALPHA`. | `LIGHT_EDGE_ALPHA` |
| **Tremulação** | A cada 0,08 s a luz sorteia um nível (quase sempre estável; às vezes uma piscada rápida, como lâmpada de hospital). São 4 máscaras pré-calculadas. | `LIGHT_FLICKER` |
| **HUD** | **Tarja preta** no topo (`HUD_BAR_H` px, linha cinza embaixo), fora da área do mundo: vida e estamina (barras arredondadas) e kits à esquerda, a mensagem temporária no meio (fonte menor se não couber), andar/abatidos e seed/tile/zoom à direita. Texto com sombra de 1 px. Controles num painel semitransparente no rodapé. | `HUD_BAR_H`, `COLOR_HUD_BAR`, `HUD_PANEL_ALPHA` |

Custo: o desenho do mundo leva ~3–4 ms por quadro (medido sem janela), bem abaixo dos 16 ms de 60 FPS.

## Zumbis (`zombies.py`)

### Spawn
`spawn_zombies` (chamado por `Horde`) coloca **3 a 5 zumbis por sala** (`ZOMBIES_PER_ROOM`), em tiles de chão distintos dentro do retângulo da sala, sem encostar em portas e a mais de 2 tiles do spawn do personagem. Usa um `Random` derivado da seed: a mesma seed gera os mesmos zumbis nos mesmos lugares. Em 200 seeds, todas as salas ficaram com 3, 4 ou 5.

### Tipos de zumbi
São 4 tipos (`settings.ZOMBIE_KINDS`), cada um com aparência e atributos próprios:

| Tipo | Vida | Vagando | Perseguindo | Dano | Como aparece / morre |
|---|---|---|---|---|---|
| `classic` (o zumbi de 32 px) | 10 | 45 px/s | 70 px/s | 2 | Sai de um buraco no chão; ao morrer afunda de volta |
| `doctor` (médico) | 10 | 45 px/s | 70 px/s | 2 | Começa caído e **levanta** (a animação de morte ao contrário); ao morrer **cai** e o corpo some aos poucos (`corpse_time`, 1,2 s) |
| `nurse` (enfermeira) | 7 | 55 px/s | 85 px/s | 2 | Igual ao médico — frágil e rápida |
| `wheelchair` (cadeirante) | 14 | 30 px/s | 95 px/s em linha reta, ×0,6 na diagonal | 2 | Igual ao médico — lento vagando, mas dispara em linha reta; resistente |

- O tipo é sorteado na hora do spawn com os **pesos do tema da sala** (`Theme.zombies`): enfermeiras mais na Enfermaria e na Emergência, médicos no Centro cirúrgico e no Necrotério, cadeirantes na Recepção e na Enfermaria, o clássico no Depósito; os outros tipos também aparecem, menos. O sorteio usa outro `Random` (seed ^ 0x7C1D): as **posições** dos zumbis não dependem dos tipos.
- Os tipos novos ficam parados virados para o último lado em que andaram (`idle_left/right/up`); o clássico só tem a pose de frente.
- O golpe tira o dano do tipo (`Zombie.damage`); a barra de vida é relativa à vida máxima do tipo.

### Estados
| Estado | O que acontece | Bloqueia? |
|---|---|---|
| `underground` | Enterrado e invisível, esperando ser visto. | não |
| `emerging` | Assim que o tile dele entra na visão do personagem (e o personagem não está em cima), toca a animação de **sair do chão** (clássico: 8 quadros, 1 s) ou de **levantar do chão** (tipos novos: 6 quadros, `rise_fps`). | sim |
| `idle` | Pausa entre caminhadas (`ZOMBIE_IDLE_TIME`, hoje **0**: emenda direto na próxima caminhada). Cercado, sem direção livre, espera 0,1–0,3 s e tenta de novo. | sim |
| `chase` | Personagem a até **5 tiles** (Chebyshev, `ZOMBIE_CHASE_RADIUS`): vai atrás dele a 70 px/s (`ZOMBIE_CHASE_SPEED`) e, colado nele, ataca (veja "Vida do personagem"). | sim |
| `walk` | Sorteia uma das **8 direções** livres (retas ou diagonais) e anda 1–4 tiles nela (`ZOMBIE_WANDER_STEPS`), tile a tile, a 45 px/s (`ZOMBIE_SPEED`) — na diagonal, mesma velocidade em px/s. Depois volta a `idle`. | sim |
| `dying` | Vida chegou a 0: toca a animação `death` (`death_fps` do tipo) — o clássico afunda de volta no chão; os tipos novos caem e o corpo fica deitado sumindo (`corpse_time`). Não leva mais dano. | não |
| `dead` | Terminou de afundar (ou o corpo sumiu): sai do jogo e conta em "Abatidos". | — |

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
- Zumbi em `chase` **colado** no personagem (reto ou diagonal sem quina de parede no meio) prepara o golpe por `ZOMBIE_ATTACK_WINDUP` (0,4 s) e bate: **o dano do tipo** (hoje **2** em todos; `ZOMBIE_KINDS`). Depois espera `ZOMBIE_ATTACK_COOLDOWN` (1 s) antes de preparar de novo. Se o personagem sair de perto durante o preparo, o golpe é cancelado.
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
- Depois de `GAME_OVER_TIME` (3 s) começa uma **run nova**: seed aleatória, andar 1, vida cheia, sem kits (veja "Elevadores e andares").

## Kit médico (`items.py`, `player.py`, `main.py`)

### No chão
- Cada sala tem **40%** de chance (`MEDKIT_ROOM_CHANCE`) de ter **1 kit**, num tile de chão da sala sem encostar em porta, a mais de 2 tiles do spawn e fora dos tiles onde nascem zumbis (`spawn_medkits`, determinístico pela seed). Em 150 seeds, ~40% das salas tiveram kit.
- O kit **flutua**: gira (8 quadros, `MEDKIT_ANIM_FPS`), sobe e desce devagar (`MEDKIT_BOB`) com uma sombra no chão que encolhe quando ele sobe. Cada kit começa numa fase diferente.
- Não bloqueia ninguém. É desenhado junto com os personagens (ordem pela altura) e **antes da névoa**: não aparece em tile não descoberto e fica escurecido fora da visão.

### Espaço: atacar tem preferência
`Game.action` decide, nesta ordem:
1. personagem ocupado (levando dano, atacando, pegando ou usando kit) ou chegando/saindo de elevador → nada;
2. **zumbi colado** (fora do chão e vivo, em qualquer uma das 8 direções, sem quina de parede no meio — `zombies.touching`) → **ataca**, mesmo com kit embaixo ou porta à frente;
3. parado na **frente do elevador de saída** → entra (próximo andar; veja "Elevadores e andares");
4. **parado em cima ou do lado de um kit** (colado em qualquer uma das 8 direções, sem quina de parede no meio) → pega — preferência para o kit embaixo, depois o da frente; se o kit está do lado, o personagem vira para ele antes: o kit sai do chão, entra na conta (**sem limite**) e toca a animação de pegar e guardar (`pickup_<direção>`, 6 quadros a `PICKUP_FPS`, sem andar nem atacar). Mensagem "Kit médico guardado [H] usar";
5. porta à frente / embaixo → abre/fecha;
6. senão → ataca.

### H: usar o kit
- Sem kit: mensagem "Sem kit médico"; vida cheia: "Vida cheia" (nada é gasto).
- Senão toca a animação de uso (`heal_<direção>`, 8 quadros a `HEAL_FPS` ≈ 0,67 s). No quadro do brilho verde (`HEAL_FRAME` = 4) recupera **2 de vida** (`MEDKIT_HEAL`, até 10), gasta o kit e mostra um **+2** verde subindo.
- Pedido no meio de um passo: começa ao chegar no tile. Durante a animação não anda, não vira e não ataca.
- **Golpe de zumbi antes do brilho cancela e não gasta** o kit (o golpe também interrompe a animação de pegar — o kit já está guardado).
- HUD: ícone do kit e **"Kits: N"** na tarja do topo, ao lado das barras.

## Elevadores e andares (`elevators.py`, `main.py`)

### Onde ficam
- `place_elevators` (em `dungeon.generate`, depois das portas e antes dos móveis). Cada elevador ocupa **2 tiles da parede de cima** de uma sala — parede alta (parede em cima também) com chão da sala embaixo — sem porta nem abertura a menos de 2 tiles. Os 2 tiles de chão logo abaixo são a **frente**.
- **Chegada**: na sala mais perto (pelo caminho) do chão do canto de cima à esquerda, na posição mais perto dele. `Dungeon.spawn` é o tile da esquerda da frente desse elevador, então tudo que usa o spawn (Recepção, zumbis e kits longe do spawn) continua igual.
- **Saída**: sorteada entre a **metade das salas mais longe** do spawn (distância pelo caminho), nunca na sala da chegada; se nenhuma delas tiver lugar na parede de cima, tenta as mais perto. Em 100 seeds, a saída ficou numa sala longe em mais de 90%.
- A frente dos dois fica livre: nenhum móvel a até 2 tiles dela; zumbis e kits não nascem a até 2 tiles da frente da saída.

### Fases de um andar (`Game.phase`)
| Fase | O que acontece |
|---|---|
| `arrive` | O elevador de chegada toca a animação das portas abrindo **com o personagem dentro** (8 quadros a `ELEVATOR_FPS`). O personagem real fica escondido e sem controle. No fim ele aparece na frente, olhando para baixo, as portas fecham (`close`) e aparece "Andar N — encontre o elevador". |
| `play` | Jogo normal. A saída fica fechada (`closed`) e passa a **pulsar a luz** (`idle`, em loop) com o personagem a até `ELEVATOR_NEAR` (3) tiles. |
| `exit` | **Espaço** parado num tile da frente da saída: as portas abrem (luz amarela, `open_exit`), o personagem anda sozinho para dentro de costas (`ELEVATOR_WALK_TIME`, desenhado por cima do elevador), some e as portas fecham (`open_exit` ao contrário). Zumbis e controles param. |
| `video` | Toca em tela cheia o **vídeo do elevador** (o elevador por dentro, as portas abrindo para uma luz forte; ~7,9 s, com som). Ele surge do preto e, nos últimos `FLOOR_VIDEO_TEXT_TIME` s, aparece **"Andar N+1"** por cima. **Espaço** ou **Enter** pulam. No fim, o próximo andar começa. |
| `fade` | Só sem o vídeo (OpenCV não instalado ou arquivo faltando): a tela escurece com **"Andar N+1"** (`FLOOR_FADE_TIME`). |

- **Vídeo** (`video.py`): o pygame não toca vídeo, então `FloorVideo` lê os quadros do `.mp4` com o OpenCV, um por vez, no ritmo do vídeo (24 fps, ~1,7 ms por quadro), converte BGR → RGB e mostra numa `Surface`. O som (AAC dentro do `.mp4`, que o mixer do pygame não lê) foi extraído uma vez para `elevator_video.wav` (`tools/extract_video_audio.py`) e toca no mixer junto com o vídeo; pular o vídeo para o som.
- **Próximo andar**: dungeon nova com seed derivada da run (`"<seed da run>-<andar>"`), **mantendo vida e kits**.
- **Game over**: a run acaba; depois de `GAME_OVER_TIME` começa uma **run nova com seed aleatória**, andar 1, vida cheia e sem kits. **R** também começa uma run nova.
- Ordem do Espaço: zumbi colado → ataca; **frente da saída → entra no elevador**; kit embaixo ou do lado → pega; porta → abre/fecha; senão ataca. Durante a chegada e a saída o Espaço não faz nada.
- Os elevadores são desenhados junto com personagem, zumbis e móveis, ordenados pela base (a linha logo abaixo da parede), antes da névoa: a saída só aparece depois de descoberta.
- HUD: "Andar N" à direita da tarja do topo (a seed mostrada embaixo é a da run).

## Mapa — tecla M (`map_view.py`, `main.py`)

- **M** abre o mapa do andar (só jogando, com o personagem vivo; não abre na chegada/saída do elevador). **M** ou **ESC** fecham — com o mapa aberto o ESC não sai do jogo. **R** fecha o mapa e começa uma run nova.
- O jogo fica **pausado**: `Game.frame` pula o `step` (zumbis, animações, estamina e tempo param). Espaço, H e os outros comandos são ignorados.
- O quadro (`MAP_BOARD`) aparece centralizado, com `MAP_SCREEN_H` px de altura, sobre o jogo escurecido (`MAP_SHADE`). Ele é montado **uma vez ao abrir** (`MapBoard.render`); a cada quadro só o ponto do personagem é redesenhado, piscando (`MAP_BLINK`).
- Na área quadriculada, só o que já foi **descoberto** (`Vision.explored`) — ~8 px por tile. Cores em `MAP_COLORS`:

| O quê | Cor |
|---|---|
| Chão de sala **limpa** | azul-claro de planta ("cor normal") |
| Chão de sala que **ainda tem inimigos** | vermelho claro |
| Corredor | azul-acinzentado |
| Paredes descobertas | cinza-azulado (contorno das salas) |
| Porta **já aberta alguma vez** (mesmo fechada depois) | verde |
| Porta **nunca aberta** | vermelho carmesim |
| Elevador de chegada / de saída (depois de descoberto) | cinza / amarelo |
| Kit médico visto e ainda no chão | cruz verde |
| Personagem | ponto branco piscando |

- **Sala com inimigos**: algum zumbi vivo **nasceu nela** (`Zombie.home`, que não muda) — enterrado, vagando ou perseguindo o personagem fora dela. Quando o último morre (sai da `Horde`), a sala fica limpa. Sala sem zumbi é limpa.
- **Porta aberta**: `Door.opened` vira `True` na primeira vez que `try_toggle` abre a porta e não volta a `False`.
- Painel do quadro: faixa de cima "MAPA — ANDAR N"; círculo com **salas limpas / salas descobertas**; as 5 linhas com caixinha são a **legenda** (com zumbis, sala limpa, porta aberta, nunca aberta, saída); faixa de baixo "[M] fechar".
