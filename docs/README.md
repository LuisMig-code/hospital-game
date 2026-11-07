# Hospital Game — documentação

Jogo top-down feito em **Python + Pygame (pygame-ce)**. Cada partida gera, a partir de uma **seed**, uma dungeon de hospital com salas e corredores. O personagem anda tile a tile, pode correr gastando estamina e só enxerga o que está perto dele (névoa de guerra).

## Índice

| Documento | Conteúdo |
|---|---|
| [arquitetura.md](arquitetura.md) | Módulos, loop do jogo e ordem de desenho |
| [sistemas.md](sistemas.md) | Geração da dungeon, movimento, estamina, visão, câmera/zoom e renderização do mapa |
| [assets.md](assets.md) | Sprite sheet do personagem, tileset do hospital e como os recortes funcionam |
| [configuracao.md](configuracao.md) | Todas as constantes de `settings.py` |
| [testes.md](testes.md) | Como rodar os testes e o que cada um cobre |
| [historico.md](historico.md) | O que foi implementado em cada etapa |

## Como rodar

Requisitos: Python 3.14 (testado) e `pygame-ce` (tem wheels para Python 3.14; o `pygame` clássico pode não ter).

```bash
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe main.py            # seed aleatória
venv\Scripts\python.exe main.py 42         # seed específica
venv\Scripts\python.exe main.py hospital   # seed em texto também funciona
```

A mesma seed sempre gera a mesma dungeon (layout e variações visuais).

## Controles

| Tecla | Ação |
|---|---|
| WASD / setas | Andar (um tile por vez; segurando, anda contínuo) |
| Shift (segurar) | Correr — 2x mais rápido, gasta estamina |
| `+` / `-` | Zoom 1x ↔ 2x |
| R | Gerar nova dungeon (seed aleatória) |
| G | Mostrar/esconder o grid |
| V | Ligar/desligar a névoa de guerra (mostra o mapa inteiro) |
| ESC | Sair |

## Estrutura de pastas

```
main.py              loop do jogo, câmera, zoom, névoa, HUD
settings.py          todas as constantes ajustáveis
dungeon.py           geração procedural (BSP) a partir da seed
player.py            movimento em grid, corrida, estamina, animação
fov.py               campo de visão (linha de visão) e memória do explorado
sprites.py           recorte do sprite sheet do personagem
tileset.py           recorte do tileset do hospital e desenho do mapa
tools/export_frames.py   exporta os recortes em PNG para conferência
tests/               testes unitários (unittest)
assets/personagem/   sprite sheet do personagem
assets/background/   tileset do hospital (pisos, paredes, portas)
docs/                esta documentação
```
