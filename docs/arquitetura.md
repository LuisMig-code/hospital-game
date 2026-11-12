# Arquitetura

## Módulos

| Módulo | Responsabilidade | Principais nomes |
|---|---|---|
| `main.py` | Janela, loop principal, input, câmera, zoom, névoa e HUD | `Game`, `build_map_surface`, `build_grid_surface` |
| `settings.py` | Constantes (tela, cores, velocidades, estamina, visão, zoom) | — |
| `dungeon.py` | Geração BSP por seed: salas, corredores, portas e móveis (via `furnish`); andável (`is_walkable`, com móveis) e transparente (`is_transparent`, sem) | `generate`, `Dungeon`, `Room`, `normalize_seed` |
| `doors.py` | Onde ficam as portas e abrir/fechar | `Door`, `place_doors`, `try_toggle` |
| `player.py` | Movimento tile a tile, corrida, estamina, ataque, vida (golpe, empurrão, invulnerabilidade, morte), animação | `Player`, `tile_center` |
| `zombies.py` | Zumbis: tipos (`ZOMBIE_KINDS`), spawn por sala com o tipo pelo tema, estados (enterrado, surgindo, parado, andando, perseguindo, morrendo), caminho até o personagem, golpe, colisão, vida | `Zombie`, `Horde`, `spawn_zombies`, `chase_step` |
| `combat.py` | Área de dano do golpe, aplicação nos zumbis, números de dano | `damage_map`, `apply_attack`, `FloatingText`, `texts_for` |
| `fov.py` | Campo de visão e tiles já explorados | `compute_fov`, `Vision`, `in_radius` |
| `lighting.py` | Névoa suave (1 pixel por tile, ampliada) e luz com queda/tremulação | `FogLayer`, `Light`, `build_light_mask` |
| `themes.py` | Dados das salas temáticas: catálogo de props (pegada, colisão, recorte) e os 6 temas + corredor | `PROPS`, `THEMES`, `CORRIDOR` |
| `furnish.py` | Escolhe o tema de cada sala e posiciona os móveis sem fechar passagens (sem pygame) | `furnish`, `PlacedProp`, `spawn_room` |
| `props.py` | Recorte e desenho dos props (móveis a cada quadro, detalhes no mapa) | `PropArt`, `load_prop_images`, `slice_sheet` |
| `elevators.py` | Elevadores de chegada e saída: posição (sem pygame) e estado da animação | `place_elevators`, `Elevator`, `ElevatorActor` |
| `video.py` | Vídeo da troca de andar: quadros do `.mp4` pelo OpenCV e som pelo mixer | `FloorVideo` |
| `map_view.py` | Mapa do andar (M): situação das salas, desenho do descoberto sobre o quadro, legenda e resumo | `MapBoard`, `room_status`, `discovered_rooms` |
| `items.py` | Kit médico no chão: spawn por sala (40%), flutuar e desenho | `MedKit`, `spawn_medkits` |
| `sprites.py` | Recorta os sprite sheets do personagem (andando, atacando, levando dano, pegando e usando o kit), do kit médico e do zumbi | `load_animations`, `load_attack_animations`, `load_damage_animations`, `load_kit_animations`, `load_medkit_item`, `load_zombie_animations`, `load_zombie_kind_animations` |
| `tileset.py` | Piso, paredes e portas novos (recorte) e montagem do mapa por tema | `Tileset`, `render_map`, `theme_at`, `load_floor_blocks`, `load_wall_pieces`, `load_door_pieces` |

Dependências entre módulos (setas = "usa"):

```
main ──► dungeon, doors, player, fov, sprites, tileset, settings
dungeon ► doors (place_doors, no fim de generate)
doors ──► dungeon (WALL)
player ─► settings
zombies ► player (tile_center, sombra), sprites (ZOMBIE_ROWS), settings
combat ─► settings (recebe a Horde e os zumbis)
fov ────► (só recebe o objeto Dungeon)
lighting ► settings
tileset ► dungeon (FLOOR), settings
sprites ► settings
```

`dungeon.py`, `doors.py`, `fov.py`, `themes.py`, `furnish.py` e `elevators.py` não dependem de pygame, então podem ser testados sem janela.

## Ciclo de vida

1. `Game.__init__` abre a janela, carrega as animações (`load_animations`) e o tileset (`Tileset()`). Se o tileset falhar ao carregar, o jogo cai para as cores sólidas verde/cinza.
2. `Game.new_run(seed)` (no início, ao apertar **R** e depois do game over) zera o andar e chama `Game.new_level(seed)`; `Game.next_floor()` (saindo pelo elevador) chama `new_level` com a seed do próximo andar mantendo vida e kits. `new_level`:
   - gera a dungeon (`generate`), já com as portas (fechadas), os elevadores, os temas das salas e os móveis;
   - pré-renderiza o mapa inteiro numa `Surface` (`build_map_surface` → `render_map`) e o grid (`build_grid_surface`) — o mapa só muda na área de uma porta quando ela abre/fecha;
   - cria o `Player` no spawn (chão mais próximo do canto superior esquerdo);
   - cria a `Horde` (3–5 zumbis enterrados por sala, longe do spawn) e os kits médicos (`spawn_medkits`);
   - cria a `Vision` e a névoa (`FogLayer`, toda preta).
3. A cada frame (`Game.run`):
   - eventos de teclado (R, G, V, H, M, Espaço, ESC) e da roda do mouse (→ `change_zoom`), tratados em `Game.handle_event` (devolve False para sair); com o mapa aberto, só M/ESC (fechar), R e fechar a janela valem;
   - `Game.frame(dt, teclas)` roda a lógica (`step`, pulada com o mapa aberto — jogo pausado) e desenha;
   - Espaço → `action()`: primeiro `toggle_door()` (`try_toggle` muda o estado da porta, `draw_door` redesenha só aquela área do `map_surf` e a visão é recalculada com `update_vision(force=True)`); se não há porta à frente nem embaixo do personagem → `player.request_attack()` (antes disso: zumbi colado → ataca; parado em cima de kit → pega); H → `use_medkit()`;
   - a lógica do quadro fica em `Game.step(dt, teclas)` (os testes a usam sem janela):
   - `horde.update(dt, player, vision.visible)` — acorda os zumbis vistos, move os ativos (vagando ou perseguindo) e devolve os que bateram no personagem → `zombie_hits` → `player.take_hit` (vida, empurrão, `-2`, moldura vermelha);
   - personagem morto: conta `GAME_OVER_TIME` e chama `new_level` com a mesma seed;
   - `player.update(dt, teclas, dungeon, blocked=horde.blocked_tiles())` — zumbis vivos bloqueiam; no quadro do golpe devolve o tile de impacto → `apply_attack(horde, impacto, tile do personagem, vision.visible)` → números de dano (`texts_for`);
   - `update_vision()` — recalcula a visão se o personagem mudou de tile e atualiza a névoa (`FogLayer.update`);
   - `light.update(dt)` — tremulação da luz;
   - `update_zoom(dt)` — o zoom anda suavemente até o alvo pedido pela roda;
   - `draw_world()`, `draw_hit_flash()`, `draw_hud()`, `draw_game_over()`, `draw_floor_fade()` e, por cima de tudo, `draw_map()` (mapa aberto).

## Ordem de desenho (`draw_world`)

O mundo é desenhado numa superfície do tamanho da área visível (`view_size()` = área do mundo — a tela abaixo da tarja do HUD, `world_rect` — ÷ zoom) e depois escalado para a tela:

1. mapa pré-renderizado (piso + sombras das paredes + paredes + portas no estado atual);
2. grid (só sobre o piso), se ligado;
3. personagem, zumbis visíveis, kits e móveis na tela (`draw_actors`, inclusive os que estão morrendo), cada um com sua sombra (zumbis com piscar de dano e barra de vida), **ordenados pela altura dos pés** — quem está mais embaixo na tela fica na frente; com a névoa ligada, só aparecem zumbis em tiles visíveis;
4. sobreposição: a metade de cima de uma porta da parede de cima, semitransparente, se o personagem está atrás dela (`draw_door_overlap`);
5. luz em volta do personagem (`Light.draw`) e névoa suave (`FogLayer.render`) — as duas só com a névoa ligada (V);
6. números de dano flutuando (por cima da névoa, para ler bem).

O mundo escalado vai para `world_screen` (subsurface da tela abaixo da tarja). O HUD (vida, estamina, kits, mensagens temporárias, andar, abatidos, seed, tile, zoom) é desenhado direto na tela, numa **tarja preta no topo** que não cobre o mapa, com sombra no texto; os controles ficam num painel semitransparente no rodapé. Não muda de tamanho com o zoom.

## Coordenadas

- **Tile**: `(tx, ty)` inteiros no grid; `dungeon.grid[ty][tx]`.
- **Pixels do mundo**: `tx * TILE`. O personagem guarda `(x, y)` = centro do tile em pixels (interpolado durante o passo).
- **Câmera**: canto superior esquerdo da área visível, em pixels do mundo; centrada no personagem e limitada às bordas do mapa.
