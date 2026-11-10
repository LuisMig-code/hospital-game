# Arquitetura

## Módulos

| Módulo | Responsabilidade | Principais nomes |
|---|---|---|
| `main.py` | Janela, loop principal, input, câmera, zoom, névoa e HUD | `Game`, `build_map_surface`, `build_grid_surface` |
| `settings.py` | Constantes (tela, cores, velocidades, estamina, visão, zoom) | — |
| `dungeon.py` | Gera o grid da dungeon a partir da seed; spawn | `generate`, `Dungeon`, `Room`, `WALL`, `FLOOR`, `normalize_seed` |
| `doors.py` | Onde ficam as portas e abrir/fechar | `Door`, `place_doors`, `try_toggle` |
| `player.py` | Movimento tile a tile, corrida, estamina, animação | `Player`, `tile_center` |
| `zombies.py` | Zumbis: spawn por sala, estados (enterrado, surgindo, parado, andando), colisão | `Zombie`, `Horde`, `spawn_zombies` |
| `fov.py` | Campo de visão e tiles já explorados | `compute_fov`, `Vision`, `in_radius` |
| `lighting.py` | Névoa suave (1 pixel por tile, ampliada) e luz com queda/tremulação | `FogLayer`, `Light`, `build_light_mask` |
| `sprites.py` | Recorta os sprite sheets do personagem e do zumbi | `load_animations`, `slice_sheet`, `load_zombie_animations` |
| `tileset.py` | Recorta o tileset do hospital e desenha o mapa e as portas | `load_pieces`, `Tileset`, `render_map`, `draw_door` |

Dependências entre módulos (setas = "usa"):

```
main ──► dungeon, doors, player, fov, sprites, tileset, settings
dungeon ► doors (place_doors, no fim de generate)
doors ──► dungeon (WALL)
player ─► settings
zombies ► player (tile_center, sombra), sprites (ZOMBIE_ROWS), settings
fov ────► (só recebe o objeto Dungeon)
lighting ► settings
tileset ► dungeon (FLOOR), settings
sprites ► settings
```

`dungeon.py`, `doors.py` e `fov.py` não dependem de pygame, então podem ser testados sem janela.

## Ciclo de vida

1. `Game.__init__` abre a janela, carrega as animações (`load_animations`) e o tileset (`Tileset()`). Se o tileset falhar ao carregar, o jogo cai para as cores sólidas verde/cinza.
2. `Game.new_level(seed)` (no início e ao apertar **R**):
   - gera a dungeon (`generate`), já com as portas (fechadas);
   - pré-renderiza o mapa inteiro numa `Surface` (`build_map_surface` → `render_map`) e o grid (`build_grid_surface`) — o mapa só muda na área de uma porta quando ela abre/fecha;
   - cria o `Player` no spawn (chão mais próximo do canto superior esquerdo);
   - cria a `Horde` (3–5 zumbis enterrados por sala, longe do spawn);
   - cria a `Vision` e a névoa (`FogLayer`, toda preta).
3. A cada frame (`Game.run`):
   - eventos de teclado (R, G, V, +/-, Espaço, ESC);
   - Espaço → `toggle_door()`: `try_toggle` muda o estado da porta, `draw_door` redesenha só aquela área do `map_surf` e a visão é recalculada (`update_vision(force=True)`);
   - `horde.update(dt, player, vision.visible)` — acorda os zumbis vistos e move os ativos;
   - `player.update(dt, teclas, dungeon, blocked=horde.blocked_tiles())` — zumbis ativos bloqueiam;
   - `update_vision()` — recalcula a visão se o personagem mudou de tile e atualiza a névoa (`FogLayer.update`);
   - `light.update(dt)` — tremulação da luz;
   - `draw_world()` e `draw_hud()`.

## Ordem de desenho (`draw_world`)

O mundo é desenhado numa superfície do tamanho da área visível (`view_size()` = tela ÷ zoom) e depois escalado para a tela:

1. mapa pré-renderizado (piso + sombras das paredes + paredes + portas no estado atual);
2. grid (só sobre o piso), se ligado;
3. personagem e zumbis visíveis (`draw_actors`), cada um com sua sombra, **ordenados pela altura dos pés** — quem está mais embaixo na tela fica na frente; com a névoa ligada, só aparecem zumbis em tiles visíveis;
4. sobreposição: a metade de cima de uma porta da parede de cima, semitransparente, se o personagem está atrás dela (`draw_door_overlap`);
5. luz em volta do personagem (`Light.draw`) e névoa suave (`FogLayer.render`) — as duas só com a névoa ligada (V).

O HUD (seed, tile, zoom, estamina, mensagens temporárias) é desenhado direto na tela, sobre um painel semitransparente e com sombra no texto,, depois da escala, para não mudar de tamanho com o zoom.

## Coordenadas

- **Tile**: `(tx, ty)` inteiros no grid; `dungeon.grid[ty][tx]`.
- **Pixels do mundo**: `tx * TILE`. O personagem guarda `(x, y)` = centro do tile em pixels (interpolado durante o passo).
- **Câmera**: canto superior esquerdo da área visível, em pixels do mundo; centrada no personagem e limitada às bordas do mapa.
