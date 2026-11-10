# Hospital Game — documentação

Jogo top-down feito em **Python + Pygame (pygame-ce)**. Cada partida gera, a partir de uma **seed**, uma dungeon de hospital com salas, corredores e portas. O personagem nasce no canto superior esquerdo, anda tile a tile, pode correr gastando estamina, abre e fecha portas e só enxerga o que está perto dele (névoa de guerra). Cada sala tem de 3 a 5 zumbis enterrados que saem do chão quando o personagem os vê e ficam vagando pela sala.

## Índice

| Documento | Conteúdo |
|---|---|
| [arquitetura.md](arquitetura.md) | Módulos, loop do jogo e ordem de desenho |
| [sistemas.md](sistemas.md) | Geração da dungeon, portas, zumbis, combate, movimento, estamina, visão, câmera/zoom, renderização do mapa e efeitos visuais |
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
| WASD / setas | Andar (um tile por vez; segurando, anda contínuo). Parado, apertar outra direção primeiro só vira; segurando, anda em seguida |
| Shift (segurar) | Correr — 2x mais rápido, gasta estamina |
| Clique esquerdo / J | Atacar com a faca na direção em que o personagem está virado (dano em área) |
| Espaço | Abrir/fechar a porta à frente do personagem |
| Roda do mouse | Zoom contínuo e suave entre 1x e 2x (para cima aproxima) |
| R | Gerar nova dungeon (seed aleatória) |
| G | Mostrar/esconder o grid |
| V | Ligar/desligar a névoa de guerra e a iluminação (mostra o mapa inteiro) |
| ESC | Sair |

## Estrutura de pastas

```
main.py              loop do jogo, câmera, zoom, névoa, HUD
settings.py          todas as constantes ajustáveis
dungeon.py           geração procedural (BSP) a partir da seed; spawn
doors.py             posicionamento das portas e abrir/fechar
player.py            movimento em grid, corrida, estamina, animação
zombies.py           zumbis: spawn por sala, surgir do chão, vagar, colisão, vida/morte
combat.py            combate: área de dano do golpe, acertos, números de dano
fov.py               campo de visão (linha de visão) e memória do explorado
lighting.py          névoa com bordas suaves e luz em volta do personagem
sprites.py           recorte dos sprite sheets (personagem andando/atacando e zumbi)
tileset.py           recorte do tileset do hospital e desenho do mapa
tools/export_frames.py   exporta os recortes em PNG para conferência
tests/               testes unitários (unittest)
assets/personagem/   sprite sheet do personagem
assets/background/   tileset do hospital (pisos, paredes, portas)
assets/monster/      sprite sheet do zumbi
docs/                esta documentação
```
