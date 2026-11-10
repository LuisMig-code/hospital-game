# Histórico de desenvolvimento

Registro do que foi implementado em cada etapa, da mais recente para a mais antiga. Ao adicionar algo novo, inclua uma entrada aqui e atualize os outros documentos afetados.

## 2026-11-09 — Melhorias visuais
- Sombras das paredes no piso (degradê no topo e nas laterais dos tiles encostados em parede).
- Sombra sob os pés do personagem.
- Profundidade nas portas: passando atrás de uma porta da parede de cima, ela fica por cima do personagem, semitransparente.
- Névoa com bordas suaves (`lighting.FogLayer`) no lugar dos quadrados tile a tile.
- Luz em volta do personagem que escurece até a borda da visão, com tremulação sutil de lâmpada.
- HUD com painel semitransparente, texto com sombra e barra de estamina arredondada.

## 2026-11-07 — Spawn no canto superior esquerdo e portas
- O personagem nasce no chão mais próximo do canto superior esquerdo.
- **Portas duplas** em todas as entradas das salas (cima, baixo, laterais), começando fechadas; **Espaço** abre/fecha a porta à frente.
- Porta fechada bloqueia passagem e visão; ao abrir, a visão é recalculada.
- Visão: paredes vizinhas de chão visível também aparecem (a parede inteira de uma sala fica visível, não só os primeiros tiles).

## 2026-11-07 — Remoção do círculo de visão
- Círculo branco em volta do personagem removido (o alcance continua 8 tiles, só não é mais desenhado).

## 2026-11-07 — Visão maior, círculo de visão, zoom e documentação
- Raio de visão aumentado de 5 para **8 tiles**.
- **Círculo** semitransparente em volta do personagem mostrando o alcance da visão (some com V).
- Zoom de 0,5x removido; agora só 1x e 2x.
- Documentação criada em `docs/`.

## 2026-11-07 — Tileset do hospital (`2407356`)
- `tileset.py`: recorte automático das 10 peças do `hospital-tiles.png` e remoção do contorno roxo.
- Piso de azulejo contínuo (3×3 placas) com manchas de sangue ocasionais.
- Paredes frontais com 2 tiles de altura, pilares nas pontas, ventilações e faixas variadas; parede baixa onde a parede tem 1 tile de espessura.
- A visão revela a metade de cima das paredes altas.
- Grid desenhado só sobre o piso.

## 2026-11-07 — Base do jogo (`9820838`)
- Dungeon procedural por seed (BSP): salas e corredores; depois ajustada para corredores com 2–3 tiles de largura e salas maiores.
- Grid de 32×32 px; inicialmente verde (chão) e cinza (parede).
- Recorte do sprite sheet do personagem (idle e 4 direções).
- Velocidade 30% maior (195 px/s).
- Movimento **tile a tile** (nunca para entre dois tiles).
- Corrida com Shift (2x) e **estamina**: −25/s correndo, +5/s andando, +10/s parado; cansaço até 20 ao zerar.
- Zoom com `+`/`-`.
- **Névoa de guerra** com linha de visão (paredes bloqueiam) e memória do que já foi explorado.

## Próximos passos sugeridos
- Usar as portas simples (`door_single_*`) — hoje todas as portas têm 2 tiles.
