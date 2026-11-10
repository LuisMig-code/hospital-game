# Configuração (`settings.py`)

Todas as constantes ajustáveis ficam em `settings.py`.

## Tela, grid e mapa

| Constante | Valor | Descrição |
|---|---|---|
| `TILE` | 32 | Tamanho de um tile em pixels |
| `SCREEN_W`, `SCREEN_H` | 1280, 720 | Tamanho da janela |
| `FPS` | 60 | Frames por segundo |
| `MAP_W`, `MAP_H` | 80, 60 | Tamanho do mapa em tiles |
| `ZOOM_MIN` | 1.0 | Zoom mais afastado (e inicial) |
| `ZOOM_MAX` | 2.0 | Zoom mais aproximado |
| `ZOOM_STEP` | 0.1 | Quanto cada clique da roda do mouse muda o zoom |
| `ZOOM_SMOOTHING` | 12 | Velocidade da transição suave (maior = chega mais rápido) |

## Cores e visual

| Constante | Valor | Descrição |
|---|---|---|
| `COLOR_FLOOR` | (60, 170, 80) | Piso quando o tileset não carrega |
| `COLOR_WALL` | (90, 90, 90) | Parede quando o tileset não carrega |
| `COLOR_WALL_TOP` | (35, 40, 42) | Topo/laterais das paredes |
| `COLOR_DOOR_CLOSED` | (120, 80, 40) | Porta fechada quando o tileset não carrega |
| `COLOR_DOOR_OPEN` | (50, 35, 20) | Porta aberta quando o tileset não carrega |
| `COLOR_GRID` | (0, 0, 0, 40) | Linhas do grid (RGBA) |
| `COLOR_BG` | (20, 20, 20) | Fundo fora do mapa |
| `COLOR_TEXT` | branco | Texto do HUD |
| `FLOOR_BLOOD_CHANCE` | 0.08 | Chance de um bloco 3×3 de piso ter sangue |
| `WALL_VENT_CHANCE` | 0.15 | Chance de ventilação numa parede alta |

## Sombras e luz

| Constante | Valor | Descrição |
|---|---|---|
| `WALL_SHADOW_TOP` | 20 | Altura (px) da sombra no piso logo abaixo de uma parede |
| `WALL_SHADOW_SIDE` | 8 | Largura (px) da sombra no piso ao lado de uma parede |
| `WALL_SHADOW_ALPHA` | 150 | Intensidade máxima da sombra das paredes (0–255) |
| `PLAYER_SHADOW_ALPHA` | 130 | Intensidade da sombra sob o personagem |
| `OCCLUDER_ALPHA` | 150 | Opacidade da porta quando o personagem passa atrás dela |
| `LIGHT_EDGE_ALPHA` | 110 | Escurecimento na borda do raio de visão (0 = sem queda de luz) |
| `LIGHT_FLICKER` | True | Tremulação sutil da luz |
| `HUD_PANEL_ALPHA` | 150 | Opacidade do painel atrás do HUD |

## Visão

| Constante | Valor | Descrição |
|---|---|---|
| `VISION_RADIUS` | 8 | Raio de visão em tiles |
| `FOG_EXPLORED_ALPHA` | 160 | Escurecimento final do já descoberto (0 = nada, 255 = preto), já contando a luz |
| `COLOR_UNEXPLORED` | (0, 0, 0) | Cor do não descoberto |

## Jogador

| Constante | Valor | Descrição |
|---|---|---|
| `PLAYER_SPEED` | 195 (150 × 1,3) | Velocidade andando, em px/s |
| `RUN_MULT` | 2.0 | Multiplicador da velocidade ao correr |
| `PLAYER_SPRITE_HEIGHT` | 48 | Altura do sprite na tela |
| `ANIM_FPS` | 13 | Frames de animação por segundo (dobra correndo) |
| `TURN_DELAY` | 0.12 | Parado, ao apertar outra direção: só vira; segurando, anda depois desse tempo (s) |

## Estamina

| Constante | Valor | Descrição |
|---|---|---|
| `STAMINA_MAX` | 100 | Estamina máxima e inicial |
| `STAMINA_DRAIN` | 25 | Gasto por segundo correndo |
| `STAMINA_REGEN_WALK` | 10 | Recuperação por segundo andando |
| `STAMINA_REGEN_IDLE` | 20 | Recuperação por segundo parado |
| `STAMINA_RECOVER_TO_RUN` | 20 | Ao zerar, só volta a correr com essa estamina |

## Geração da dungeon (em `dungeon.py`)

| Constante | Valor | Descrição |
|---|---|---|
| `MIN_LEAF` | 14 | Tamanho mínimo de uma divisão da BSP (controla o número e o tamanho das salas) |
| `MIN_ROOM` | 6 | Tamanho mínimo de uma sala |
| `CORRIDOR_WIDTHS` | (2, 3) | Larguras possíveis dos corredores |

## Zumbis

| Constante | Valor | Descrição |
|---|---|---|
| `ZOMBIE_SIZE` | 64 | Tamanho do sprite na tela (quadro de 32 px escalado 2×) |
| `ZOMBIES_PER_ROOM` | (3, 5) | Mínimo e máximo de zumbis por sala |
| `ZOMBIE_SPEED` | 45 | Velocidade andando, em px/s |
| `ZOMBIE_IDLE_TIME` | (0.0, 0.0) | Tempo parado entre caminhadas, em segundos (0 = emendam uma caminhada na outra) |
| `ZOMBIE_WANDER_STEPS` | (1, 4) | Tiles andados em cada caminhada |
| `ZOMBIE_ANIM_FPS` | 6 | Quadros por segundo parado/andando |
| `ZOMBIE_EMERGE_FPS` | 8 | Quadros por segundo saindo do chão (8 quadros = 1 s) |

## Combate

| Constante | Valor | Descrição |
|---|---|---|
| `ATTACK_FPS` | 22 | Quadros por segundo do ataque (9 quadros ≈ 0,4 s) |
| `ATTACK_HIT_FRAME` | 5 | Quadro em que o golpe acerta |
| `ATTACK_DAMAGE` | (11, 6, 4) | Dano no impacto, colado no impacto e a 2 tiles do impacto |
| `ATTACK_REACH` | 2 | Alcance do golpe para a frente, a partir do personagem (tiles) |
| `ZOMBIE_HP` | 10 | Vida de cada zumbi |
| `ZOMBIE_DEATH_FPS` | 14 | Velocidade do zumbi afundando no chão ao morrer |
| `HIT_FLASH_TIME` | 0.12 | Segundos piscando ao levar dano |
| `HP_BAR_TIME` | 2.0 | Segundos mostrando a barra de vida depois de um golpe |
| `DAMAGE_TEXT_TIME` | 0.7 | Segundos do número de dano flutuando |

## Vida do personagem e ataque dos zumbis

| Constante | Valor | Descrição |
|---|---|---|
| `PLAYER_HP` | 10 | Vida do personagem |
| `ZOMBIE_DAMAGE` | 2 | Dano de cada golpe de zumbi |
| `ZOMBIE_CHASE_RADIUS` | 5 | Distância (tiles, Chebyshev) em que o zumbi persegue |
| `ZOMBIE_CHASE_SPEED` | 70 | Velocidade perseguindo, em px/s |
| `ZOMBIE_CHASE_SEARCH` | 6 | Quanto além do raio a busca do caminho pode ir |
| `ZOMBIE_ATTACK_WINDUP` | 0.4 | Segundos preparando o golpe |
| `ZOMBIE_ATTACK_COOLDOWN` | 1.0 | Segundos entre um golpe e o próximo preparo |
| `ZOMBIE_LUNGE` | 7 | Pixels que o zumbi avança ao bater (só visual) |
| `KNOCKBACK_TIME` | 0.15 | Duração do empurrão de 1 tile (personagem) |
| `ZOMBIE_KNOCKBACK_TIME` | 0.15 | Duração do zumbi sendo lançado 1 tile pelo golpe do personagem |
| `HURT_FPS` | 12 | Quadros por segundo da animação de dano |
| `PLAYER_INVULN_TIME` | 1.0 | Segundos invulnerável (piscando) depois do dano |
| `HIT_SCREEN_FLASH` | 0.35 | Segundos da moldura vermelha ao levar golpe |
| `GAME_OVER_TIME` | 3.0 | Segundos de GAME OVER antes de recomeçar a mesma dungeon |
