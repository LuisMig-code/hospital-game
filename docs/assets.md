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

> Atenção: a 2ª linha é o personagem andando para a **direita** e a 3ª para a **esquerda**. Isso foi conferido visualmente.

**Como o recorte funciona** (`sprites.py`):

1. Projeção do canal alpha: conta os pixels opacos por linha e por coluna (via `Mask.overlap_area`, sem numpy) para achar onde começam e terminam as 5 linhas e, em cada linha, as 8 colunas. Vãos pequenos são ignorados.
2. Calcula o retângulo de cada frame dentro da sua célula e usa a **união** desses retângulos em toda a animação. Assim todos os frames de uma animação têm o mesmo tamanho e os pés ficam alinhados, sem o personagem "tremer".
3. Escala todas as animações pelo mesmo fator, de modo que a altura fique em `PLAYER_SPRITE_HEIGHT` (48 px = 1,5 tile).
4. Se a detecção falhar, usa a divisão uniforme como alternativa.

## Tileset do hospital — `assets/background/hospital-tiles.png`

- 530×471 px, RGBA, fundo transparente. **Não é uma grade uniforme**: são 10 peças soltas de tamanhos diferentes, cada uma com um contorno roxo.

| Linha | Peças (esquerda → direita) |
|---|---|
| 1 | `floor` (azulejo 3×3), `floor_blood` (azulejo com sangue) |
| 2 | `wall_vent` (parede com ventilação), `wall_low` (parede baixa), `wall_pillar_left`, `wall_pillar_right` |
| 3 | `door_double_closed`, `door_double_open`, `door_single_left`, `door_single_right` |

Em uso: as **portas duplas** (fechada e aberta), em 4 versões — de frente (parede de cima), achatada (parede de baixo) e giradas 90° (laterais). As portas simples (`door_single_*`) ainda **não são usadas**: todas as portas do mapa têm 2 tiles.

**Como o recorte funciona** (`tileset.py`):

1. `find_pieces`: encontra os **componentes conectados** do alpha (`Mask.connected_components`) e descarta ruídos com menos de 400 px. Agrupa as peças em linhas pelo centro Y e ordena por X, chegando aos nomes da tabela. Se não encontrar exatamente 2 + 4 + 4 peças, gera um erro claro.
2. `clean_outline`: deixa transparentes os pixels **roxos** do contorno (vermelho e azul bem acima do verde) e recorta a peça para o que sobrou. Cortar uma margem fixa não bastava, porque o contorno também passa no degrau entre a parede e o pilar.
3. `Tileset` escala as peças para o grid:
   - piso: 96×96 px (3×3 tiles);
   - paredes altas: 64 px de altura, recortadas pelo **topo da parede** (e não pela ponta do pilar) para os topos ficarem alinhados, com a largura arredondada para um múltiplo de 32;
   - parede lisa: 4 faixas de 1 coluna tiradas do miolo das paredes com pilar;
   - parede baixa: 32 px de altura;
   - portas duplas: 64×64 (cima), 64×32 (baixo), 32×64 girada ±90° (laterais), fechada e aberta (`Tileset.door[lado][aberta]`).

> Bug contornado: no pygame-ce 2.5.8 (Windows), `mask.from_surface` numa subsurface de 1 px de largura causa um *access violation*. Por isso `_crop_to_wall` lê os pixels da coluna diretamente.

## Conferindo os recortes

```bash
venv\Scripts\python.exe tools\export_frames.py
```

Gera:
- `assets/personagem/frames/<animação>_<i>.png` e `preview.png` (todos os frames com borda vermelha);
- `assets/background/pieces/<peça>.png` e `preview.png`.

As duas pastas estão no `.gitignore`, porque o jogo faz os recortes sozinho ao abrir.

## Adicionando assets novos

- **Novo sprite sheet com o mesmo layout**: troque `CHARACTER_SHEET` em `settings.py`. Se a ordem das linhas mudar, ajuste `ROW_NAMES` em `sprites.py`.
- **Novo tileset**: se o número de peças por linha mudar, ajuste `PIECE_ROWS` em `tileset.py`. O teste `test_finds_all_pieces_in_order` avisa se a detecção não bater.
