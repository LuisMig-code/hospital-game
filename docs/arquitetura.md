# Arquitetura

## Módulos

| Módulo | Responsabilidade | Principais nomes |
|---|---|---|
| `main.py` | Janela, loop principal, input, câmera, zoom, névoa e HUD | `Game`, `build_map_surface`, `build_grid_surface`, `build_vision_circle` |
| `settings.py` | Constantes (tela, cores, velocidades, estamina, visão, zoom) | — |
| `dungeon.py` | Gera o grid da dungeon a partir da seed | `generate`, `Dungeon`, `Room`, `WALL`, `FLOOR`, `normalize_seed` |
| `player.py` | Movimento tile a tile, corrida, estamina, animação | `Player`, `tile_center` |
| `fov.py` | Campo de visão e tiles já explorados | `compute_fov`, `Vision`, `in_radius` |
| `sprites.py` | Recorta o sprite sheet do personagem em animações | `load_animations`, `slice_sheet` |
| `tileset.py` | Recorta o tileset do hospital e desenha o mapa | `load_pieces`, `Tileset`, `render_map` |

Dependências entre módulos (setas = "usa"):

```
main ──► dungeon, player, fov, sprites, tileset, settings
player ─► settings
fov ────► (só recebe o objeto Dungeon)
tileset ► dungeon (FLOOR), settings
sprites ► settings
```

`dungeon.py` e `fov.py` não dependem de pygame, então podem ser testados sem janela.

## Ciclo de vida

1. `Game.__init__` abre a janela, carrega as animações (`load_animations`) e o tileset (`Tileset()`). Se o tileset falhar ao carregar, o jogo cai para as cores sólidas verde/cinza.
2. `Game.new_level(seed)` (no início e ao apertar **R**):
   - gera a dungeon (`generate`);
   - pré-renderiza o mapa inteiro numa `Surface` (`build_map_surface` → `render_map`) e o grid (`build_grid_surface`) — os tiles não mudam, então isso é feito uma vez só;
   - cria o `Player` no centro da primeira sala;
   - cria a `Vision` e a superfície da névoa (`fog_surf`, toda preta).
3. A cada frame (`Game.run`):
   - eventos de teclado (R, G, V, +/-, ESC);
   - `player.update(dt, teclas, dungeon)`;
   - `update_vision()` — recalcula a visão se o personagem mudou de tile e "descobre" os tiles novos na névoa;
   - `draw_world()` e `draw_hud()`.

## Ordem de desenho (`draw_world`)

O mundo é desenhado numa superfície do tamanho da área visível (`view_size()` = tela ÷ zoom) e depois escalado para a tela:

1. mapa pré-renderizado (piso + paredes);
2. grid (só sobre o piso), se ligado;
3. névoa (`fog_surf`): preto no não descoberto, escurecido no já descoberto;
4. tiles dentro da visão redesenhados por cima da névoa (cores normais);
5. círculo de visão em volta do personagem;
6. personagem.

O HUD (seed, tile, zoom, estamina) é desenhado direto na tela, depois da escala, para não mudar de tamanho com o zoom.

## Coordenadas

- **Tile**: `(tx, ty)` inteiros no grid; `dungeon.grid[ty][tx]`.
- **Pixels do mundo**: `tx * TILE`. O personagem guarda `(x, y)` = centro do tile em pixels (interpolado durante o passo).
- **Câmera**: canto superior esquerdo da área visível, em pixels do mundo; centrada no personagem e limitada às bordas do mapa.
