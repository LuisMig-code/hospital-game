# Assets

## Personagem — `assets/personagem/Chibi Character Animation Sprite Sheet.png`

- 1536×1024 px, RGBA, fundo com alpha 0. O "brilho" escuro que aparece em alguns visualizadores é só cor RGB debaixo de alpha 0.
- Grade de **8 colunas × 5 linhas**. A altura de cada linha não é inteira (1024 / 5 = 204,8 px), então não dá para cortar com uma divisão fixa.

| Linha | Animação (nome no código) |
|---|---|
| 1 | `idle` (de frente) |
| 2 | `walk_right` |
| 3 | `walk_left` |
| 4 | `walk_up` (de costas) |
| 5 | `walk_down` (de frente) |

O sheet só tem `idle` de frente. Para parado olhando para os lados/costas, `load_animations` cria `idle_right`, `idle_left` e `idle_up` com o 1º quadro da caminhada de cada direção (pose com os pés juntos).

> Atenção: a 2ª linha é o personagem andando para a **direita** e a 3ª para a **esquerda**. Isso foi conferido visualmente.

**Como o recorte funciona** (`sprites.py`):

1. Projeção do canal alpha: conta os pixels opacos por linha e por coluna (via `Mask.overlap_area`, sem numpy) para achar onde começam e terminam as 5 linhas e, em cada linha, as 8 colunas. Vãos pequenos são ignorados.
2. Calcula o retângulo de cada frame dentro da sua célula e usa a **união** desses retângulos em toda a animação. Assim todos os frames de uma animação têm o mesmo tamanho e os pés ficam alinhados, sem o personagem "tremer".
3. Escala todas as animações pelo mesmo fator, de modo que a altura fique em `PLAYER_SPRITE_HEIGHT` (48 px = 1,5 tile).
4. Se a detecção falhar, usa a divisão uniforme como alternativa.

## Personagem atacando — `assets/personagem/atack_spritsheet.png`

- 1536×1024 px, RGBA, **5 linhas × 9 quadros** (passo de ~159 px), com um contorno **magenta** em volta do desenho. O desenho é menor que o do sheet de andar (~148 px × ~191 px de altura).
- Quadros: 0–4 preparação, **5–6 golpe com rastro** (azul/rosa), 7–8 recuperação.

| Linha | Direção | Uso |
|---|---|---|
| 1 | frente | não usada (igual à 5) |
| 2 | direita | `attack_right` |
| 3 | costas | `attack_up` |
| 4 | esquerda | não usada: o rastro do golpe vai para a direita |
| 5 | frente | `attack_down` |

`attack_left` é a linha 2 **espelhada** (rastro para a esquerda).

**Como o recorte funciona** (`sprites.load_attack_animations`):
1. Linhas pela projeção alpha (como no sheet de andar).
2. Colunas: os quadros sem rastro dão os centros e o passo da grade (regressão linear); entre dois centros, a fronteira fica no **vale** da projeção alpha, porque os rastros dos quadros 5–6 encostam no quadro seguinte.
3. Contorno: pixel roxo saturado (verde < 0,3 × min(vermelho, azul)) claro vira transparente, escuro vira traço quase preto. O rastro rosa tem verde alto e não é afetado.
4. **Âncora**: o centro do cabelo (faixa de cima, sem faca nem rastro) fica no centro da imagem e a base da linha embaixo → o personagem não "pula" ao começar a atacar (conferido sobrepondo com o `idle`).
5. Escala para `attack_down` ter a mesma altura do `idle` na tela.

## Personagem levando dano — `assets/personagem/damage.png`

- 1024×1536 px, 8 linhas numa grade de **6 colunas** (1024 / 6 px de passo; as linhas são achadas pela projeção do alpha). As 4 primeiras têm 4 quadros (dano curto: silhueta branca, dor, recuperando) e as 4 últimas 6 (dano com empurrão: silhueta branca, recuando, no ar, caindo, caído, de pé).
- Recortado por `load_damage_animations` em `sprites.py` (`DAMAGE_ROWS`):

| Linha | Animação |
|---|---|
| 0 | `hurt_light_down` |
| 1 | (não usada: outra versão de frente) |
| 2 | `hurt_light_left` (`hurt_light_right` = espelhada) |
| 3 | `hurt_light_up` |
| 4 | `hurt_down` |
| 5 | `hurt_right` (`hurt_left` = espelhada) |
| 6 | (não usada: direção confusa no desenho) |
| 7 | `hurt_up` |

- Mesmo tratamento do ataque: contorno magenta removido (`_clean_attack_outline`), quadro do topo do desenho até a base da linha, **centralizado pelo cabelo**, e escala para o último quadro de `hurt_down` (de pé) ter a altura do `idle`.
- O quadro 4 do empurrão (`HURT_FALLEN_FRAME`, caído) é onde o personagem fica no game over.
- `tools/export_frames.py` salva os quadros em `assets/personagem/damage_frames/` (ignorada pelo git).

## Kit médico

### No chão — `assets/items/medkit/Two-Row Green Medkit Sprite Sheet_stay.png`
- 2172×724 px, 2 linhas × 8 quadros do kit girando (linha 0 normal, linha 1 com **brilho verde**). O jogo usa a linha com brilho (mais fácil de ver no escuro); linhas e colunas achadas pela projeção do alpha.
- Escala: o quadro mais largo fica com `MEDKIT_SIZE` (26 px). O quadro 0 da linha 0 vira o **ícone** do HUD (20 px de altura). → `load_medkit_item`.

### Pegando o kit — `assets/personagem/Chibi Medic Kit Animation Sprite Sheet.png`
- 1536×1024 px, grade **4 linhas × 6 quadros** (256 px). Linhas: de frente, direita, esquerda, costas (a mesma ordem do sheet de andar, conferida comparando com `idle_right`/`idle_left`). → `pickup_<direção>`.

### Usando o kit — `assets/personagem/Chibi Medic Healing Animation Sprite Sheet.png`
- 1774×887 px, grade **4 linhas × 8 quadros** (221,75 px; as linhas com brilho se encostam, por isso a grade é fixa). Mesma ordem de direções. Quadros 4–6 com o brilho verde da cura. → `heal_<direção>`.

Os dois sheets do personagem passam por `_load_grid_animation`: o "chão" de cada linha é o pixel opaco mais baixo dela; cada quadro vai do topo do desenho até esse chão, é **centralizado pelo cabelo** e escalado para o último quadro de frente (de pé) ter a altura do `idle`. `tools/export_frames.py` salva tudo em `assets/personagem/medkit_frames/` (ignorada pelo git).

## Piso — `assets/background/Seamless Grungy Hospital Floor Tileset.png`

- 1774×887 px, grade fixa **8×4 blocos** (221,75 px); cada bloco tem 3×3 placas e vira **3×3 tiles** (96×96 px) — `load_floor_blocks`.
- Nomes (`tileset.FLOOR_BLOCKS`), linha a linha: `plain`, `cracked`, `broken`, `footprints`, `puddle`, `papers`, `plain_streak`, `blood_smear` / `beige`, `blue`, `checker`, `dark`, `slime`, `yellow_line`, `grate`, `concrete` / `blood_drops`, `blood_splat`, `blood_hand`, `blood_trail`, `dirt`, `blood_crack`, `blood_dried`, `mold` / `metal_bar`, `drain`, `hatch`, `hole`, `carpet`, `burnt`, `glass_floor`, `blood_bag`.
- Sem uso por enquanto: `hole` (parece intransponível), `yellow_line`, `carpet`, `metal_bar`, `hatch`, `blood_bag`, `plain_streak` (tem o começo do rastro de sangue do bloco vizinho).

## Paredes — `assets/background/Pixel Hospital Wall Tileset.png`

- 1086×1448 px, **fundo magenta** (vira transparente por `Mask.from_threshold`; a franja arroxeada na borda das peças vira traço escuro). Peças achadas pela projeção do alpha: **8 linhas × 6 peças** — `load_wall_pieces`.
- Linhas 0–5 = 6 estilos (0 branca rachada, 1 com sangue, 2 creme com trilho de cortina, 3 azulejo azul, 4 concreto enferrujado, 5 com mofo). Colunas: parede cheia (com detalhe do estilo), parede baixa, com pilar à esquerda, com pilar à direita, com janela, com detalhe (ventilação, placa, armário, luminária, grade, canos).
- Linha 6: cantos (sem uso). Linha 7: buraco, entulho, lâmpada vermelha, persiana, extintor, placa — detalhes extras do estilo 0.
- `Tileset.walls[estilo]`: `plain` (4 faixas 32×64 do miolo das peças com pilar), `left`/`right` (pilares, 64×64; usa a coluna da ponta), `details` (peças de 2 colunas, 64×64, cortando 2,5% de cada lado para o contorno não virar uma risca), `low` (64×32). As peças são recortadas pelo topo da parede medido longe do pilar (a ponta do pilar sobe acima).

## Portas — `assets/background/Industrial Teal Door Tile Sprite Sheet.png`

- 1774×887 px, fundo preto, cada porta com **contorno magenta**; grade 8×4. Recorte: retângulo do contorno magenta em cada célula, encolhido 5 px de cada lado — `load_door_pieces`.
- Em uso, só a linha 0 (portas duplas): fechada padrão (col. 0), com sangue (1, Emergência), vidro quebrado (6, Depósito), cofre (7, Necrotério) e a **aberta** (3, todas). Sem uso: quebrada, acorrentada, com tábuas (linha 0) e as portas simples/elevador/necrotério das linhas 1–3.
- `Tileset.door[variante][lado][aberta]`: 64×64 (cima), 64×32 (baixo), 32×64 girada ±90° (laterais).

## Props das salas — `assets/cenario/*.png`

Três sheets com fundo transparente (e uma névoa de alpha baixo em volta das peças):

| Sheet (`PROP_SHEETS`) | Arquivo | Grade |
|---|---|---|
| `equip` | `Detailed Hospital Equipment Sprite Sheet.png` | 6×6: camas, macas, cadeiras de rodas, criado-mudo/soro/cortina, monitores/carrinhos/oxigênio/ventilador, mesa de cirurgia/foco/instrumentos |
| `furn` | `Hospital Furniture Sprite Sheet on Transparent Background.png` | 9/8/10/9/11 por linha: camas, macas, soro, cortinas / cadeiras, sofás, poltrona / armários, carrinhos, criados-mudos, pia / monitores, anestesia, mesas com computador, estantes / biombos, lixeiras, oxigênio, foco, maca de exame, luminária |
| `weath` | `Weathered Medical Facility Prop Sprite Sheet.png` | 7/8/8/8/8/8: gavetas de cadáver, mesas de autópsia, saco de corpo, maca coberta / móveis caídos, entulho, caixas / lixo hospitalar, luvas, seringas, bandagens / caixotes (o aberto, `crate_open`, não é usado nos temas: fica para o loot), lockers, armários, caçambas / luminárias / escadas e passagens bloqueadas |

- Recorte (`props.slice_sheet`): linhas pela projeção do alpha ≥ 250, colunas pela projeção do alpha ≥ 220 com vãos de 3 px (separa peças bem próximas, como as duas macas). A névoa (alpha < 70) é apagada e a peça recortada no desenho.
- `themes.PROPS` dá a cada prop usado: sheet, (linha, coluna), largura na tela, pegada em tiles e se tem colisão. Ex.: cama de pé 2×2 (52 px, ~2,4 tiles de altura), cama deitada 3×2 (88 px), armário alto 2×1 (50 px de largura, ~2 tiles de altura), locker 2×1 (46 px), estante 2×1 (50 px, ~2 tiles de altura), sofá 3×1 (92 px), mesa de cirurgia 2×1 (70 px), gaveteiro de necrotério 3×1 (90 px), cadeira 1×1 (24 px). O desenho fica com o meio da base no meio da base da pegada e cresce para cima (vista 3/4).
- Sem uso: foco de teto, luminárias de parede e tubos (são de parede/teto), escadas e passagens bloqueadas.

> Bug contornado: no pygame-ce 2.5.8 (Windows), `mask.from_surface` numa subsurface de 1 px de largura causa um *access violation*. Por isso `_crop_to_wall` lê os pixels da coluna diretamente.

> O tileset antigo (`assets/background/hospital-tiles.png`) continua no repositório, mas não é mais usado.

## Elevador — `assets/cenario/*Elevator*.png`

Dois sheets de 1402×1122 px, fundo transparente, 4 linhas; os quadros encostam uns nos outros, então as colunas usam a **grade fixa de 175,25 px** (1402 / 8) e as linhas a projeção do alpha. Cada quadro é recortado no desenho e escalado para `ELEVATOR_WIDTH` (68 px, ~2 tiles; ~85 px de altura) — `sprites.load_elevator_animations`.

| Sheet | Linha | Conteúdo | Animação |
|---|---|---|---|
| `Haunted Elevator Sprite Sheet_chegada.png` | 0 | portas abrindo, luz azul (8) | sem uso |
| | 1 | portas fechando (8) | `close` (depois da chegada) |
| | 2 | portas abrindo **com o personagem dentro** (8) | `arrive` |
| | 3 | peças soltas (batente, folhas, interiores) | sem uso |
| `Pixel Art Elevator Sprite Sheet_elevator out.png` | 0 | fechado, luz pulsando (6) | `idle` (saída com o personagem perto) |
| | 1 | portas abrindo, luz amarela (8) | `open_exit` (e ao contrário para fechar) |
| | 2 | variações fechadas/quebradas (6) | `closed` = col. 1 (fechado aceso) |
| | 3 | luz amarela no chão (5) | sem uso |

### Vídeo — `assets/cenario/Elevator_doors_opening_with_glow_50d001eb.mp4`
- 1280×720 (o tamanho da tela), 24 fps, 190 quadros (~7,9 s), H.264 + som AAC estéreo 48 kHz. Tocado na troca de andar (`video.py`, com OpenCV).
- O som está também em `assets/cenario/elevator_video.wav` (16 bits, estéreo, 48 kHz), gerado por `tools/extract_video_audio.py` (usa o pacote `av`). Se trocar o vídeo, rode a ferramenta de novo.

## Conferindo os recortes

```bash
venv\Scripts\python.exe tools\export_frames.py
```

Gera:
- `assets/personagem/frames/<animação>_<i>.png` e `preview.png` (todos os frames com borda vermelha);
- `assets/background/pieces/`: blocos de piso (`floor_<nome>.png`), peças de parede (`wall_<linha>_<coluna>.png`) e portas (`door_<coluna>.png`);
- `assets/cenario/pieces/`: cada prop do catálogo (`<nome>.png`) e um `preview_<sheet>.png` com todas as peças numeradas (linha,coluna) — use para achar os índices de `themes.PROPS`;
- quadros de zumbi, ataque, dano, kit médico e elevador (`assets/cenario/elevator_frames/`) nas pastas de cada um.

Essas pastas estão no `.gitignore`, porque o jogo faz os recortes sozinho ao abrir.

## Adicionando assets novos

- `tools/export_frames.py` também salva os quadros de ataque em `assets/personagem/attack_frames/` (ignorada no git).
- **Novo sprite sheet com o mesmo layout**: troque `CHARACTER_SHEET` em `settings.py`. Se a ordem das linhas mudar, ajuste `ROW_NAMES` em `sprites.py`.
- **Novo prop**: rode `tools/export_frames.py`, ache o (linha, coluna) no `preview_<sheet>.png` e adicione em `themes.PROPS` (largura na tela, pegada, colisão); depois coloque o nome nas listas do tema (`top`, `side`, `center`, `loose` ou `scatter`). `tests/test_furnish.py` confere o recorte e as regras.
- **Novo tema**: adicione um `Theme` em `themes.THEMES` (estilo de parede 0–5, porta, pisos e props).

## Zumbi — `assets/monster/zombie_spritesheet_32x32.png`

- 256×192 px, grade uniforme de **8×6 quadros de 32×32**, fundo **magenta opaco** (255, 0, 255).

| Linha | Animação | Quadros |
|---|---|---|
| 1 | `idle` (de frente) | 2 |
| 2 | `walk_right` | 4 |
| 3 | `walk_left` | 4 |
| 4 | `walk_up` (de costas) | 4 |
| 5 | `walk_down` (cabeça baixa, queixo aparecendo sob o cabelo) | 4 |
| 6 | `emerge` — sai do chão: buraco, mãos, cabeça, corpo, em pé | 8 |

**Como o recorte funciona** (`sprites.load_zombie_animations`):
1. Fundo magenta vira transparente. Os pixels de transição na borda do desenho (roxos: vermelho e azul parecidos e bem acima do verde) também: os claros viram transparentes e os escuros viram contorno quase preto. O sangue (vermelho, pouco azul) não é afetado.
2. Cada quadro é recortado da grade (`ZOMBIE_ROWS` diz quantos quadros cada linha tem; as colunas vazias são ignoradas).
3. Escala 2× por vizinho mais próximo (`ZOMBIE_SIZE = 64`).

`tools/export_frames.py` também salva os quadros do zumbi em `assets/monster/frames/` (ignorada no git) com um `preview.png` ampliado sobre fundo escuro.
