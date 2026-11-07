# Configuração (`settings.py`)

Todas as constantes ajustáveis ficam em `settings.py`.

## Tela, grid e mapa

| Constante | Valor | Descrição |
|---|---|---|
| `TILE` | 32 | Tamanho de um tile em pixels |
| `SCREEN_W`, `SCREEN_H` | 1280, 720 | Tamanho da janela |
| `FPS` | 60 | Frames por segundo |
| `MAP_W`, `MAP_H` | 80, 60 | Tamanho do mapa em tiles |
| `ZOOM_LEVELS` | (1.0, 2.0) | Níveis de zoom disponíveis (`+`/`-`) |
| `ZOOM_DEFAULT` | 0 | Índice do zoom inicial em `ZOOM_LEVELS` |

## Cores e visual

| Constante | Valor | Descrição |
|---|---|---|
| `COLOR_FLOOR` | (60, 170, 80) | Piso quando o tileset não carrega |
| `COLOR_WALL` | (90, 90, 90) | Parede quando o tileset não carrega |
| `COLOR_WALL_TOP` | (35, 40, 42) | Topo/laterais das paredes |
| `COLOR_GRID` | (0, 0, 0, 40) | Linhas do grid (RGBA) |
| `COLOR_BG` | (20, 20, 20) | Fundo fora do mapa |
| `COLOR_TEXT` | branco | Texto do HUD |
| `FLOOR_BLOOD_CHANCE` | 0.08 | Chance de um bloco 3×3 de piso ter sangue |
| `WALL_VENT_CHANCE` | 0.15 | Chance de ventilação numa parede alta |

## Visão

| Constante | Valor | Descrição |
|---|---|---|
| `VISION_RADIUS` | 8 | Raio de visão em tiles |
| `FOG_EXPLORED_ALPHA` | 160 | Escurecimento do já descoberto (0 = nada, 255 = preto) |
| `COLOR_UNEXPLORED` | (0, 0, 0) | Cor do não descoberto |

## Jogador

| Constante | Valor | Descrição |
|---|---|---|
| `PLAYER_SPEED` | 195 (150 × 1,3) | Velocidade andando, em px/s |
| `RUN_MULT` | 2.0 | Multiplicador da velocidade ao correr |
| `PLAYER_SPRITE_HEIGHT` | 48 | Altura do sprite na tela |
| `ANIM_FPS` | 13 | Frames de animação por segundo (dobra correndo) |

## Estamina

| Constante | Valor | Descrição |
|---|---|---|
| `STAMINA_MAX` | 100 | Estamina máxima e inicial |
| `STAMINA_DRAIN` | 25 | Gasto por segundo correndo |
| `STAMINA_REGEN_WALK` | 5 | Recuperação por segundo andando |
| `STAMINA_REGEN_IDLE` | 10 | Recuperação por segundo parado |
| `STAMINA_RECOVER_TO_RUN` | 20 | Ao zerar, só volta a correr com essa estamina |

## Geração da dungeon (em `dungeon.py`)

| Constante | Valor | Descrição |
|---|---|---|
| `MIN_LEAF` | 14 | Tamanho mínimo de uma divisão da BSP (controla o número e o tamanho das salas) |
| `MIN_ROOM` | 6 | Tamanho mínimo de uma sala |
| `CORRIDOR_WIDTHS` | (2, 3) | Larguras possíveis dos corredores |
