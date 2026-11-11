# Histórico de desenvolvimento

Registro do que foi implementado em cada etapa, da mais recente para a mais antiga. Ao adicionar algo novo, inclua uma entrada aqui e atualize os outros documentos afetados.

## 2026-11-11 — Pegar kit do lado
- O Espaço também pega um kit médico **colado** no personagem (8 direções, sem quina de parede), não só embaixo dele; o personagem vira para o kit. Preferência: embaixo, à frente, depois os outros lados.

## 2026-11-11 — Vídeo na troca de andar
- Depois que as portas da saída fecham, toca em tela cheia o vídeo do elevador (portas abrindo para a luz, ~7,9 s, com som), com "Andar N" aparecendo no fim; Espaço/Enter pulam.
- Quadros lidos com OpenCV (`opencv-python-headless`, nova dependência); som extraído para `elevator_video.wav` por `tools/extract_video_audio.py`. Sem OpenCV, volta a tela escura de antes.

## 2026-11-11 — Elevadores e andares
- O andar começa com o personagem saindo do **elevador de chegada** (animação das portas abrindo com ele dentro); o spawn é a frente desse elevador.
- O **elevador de saída** fica numa sala sorteada entre as mais longe; pulsa a luz com o personagem perto. **Espaço** na frente dele: portas abrem, ele entra, portas fecham, "Andar N" e o próximo andar começa, **mantendo vida e kits**.
- Game over (e a tecla R) começam uma **run nova**: seed aleatória, andar 1. HUD mostra o andar.
- Sheets do elevador recortados (chegada e saída); o vídeo `.mp4` não é usado.

## 2026-11-11 — Camas maiores
- Camas de pé passam a 2×2 tiles (52 px de largura, ~2,4 tiles de altura no desenho) e camas deitadas/quebrada a 3×2 (88–90 px). Nas laterais da Enfermaria ficam só criados-mudos, suportes de soro e gaveteiros.

## 2026-11-11 — Estantes maiores
- Estantes (cheia, com sangue, vazia) aumentadas como os armários: 2 tiles de largura e ~2 tiles de altura, só na parede de cima. A estante quebrada (no chão do Depósito) também ficou um pouco maior. Nas laterais entram gaveteiros, caixas e caixotes.

## 2026-11-11 — Armários maiores
- Armários altos (de vidro, de metal, enferrujado), lockers e armários baixos aumentados: agora ocupam 2 tiles de largura e os altos ficam com ~2 tiles de altura, mais altos que o personagem. Por isso só vão encostados na parede de cima (nas laterais só entram móveis de 1 tile).

## 2026-11-11 — Salas temáticas, cenário novo e móveis com colisão
- Piso, paredes e portas trocados pelos sheets novos (o `hospital-tiles.png` deixou de ser usado): piso em blocos 3×3 com 32 variações, 6 estilos de parede com pilares, janelas e detalhes, portas duplas por tema.
- 6 temas de sala: **Recepção** (sempre a do spawn), **Enfermaria**, **Emergência**, **Centro cirúrgico**, **Necrotério** e **Depósito**, cada um com parede, porta, piso e móveis próprios; o nome aparece no HUD ao entrar.
- ~95 props recortados dos 3 sheets de cenário: móveis encostados nas paredes, grupos no meio das salas grandes, alguns soltos e detalhes no chão. Densidade moderada (≤ 24% da sala), nunca perto de portas ou do spawn e **nunca fechando passagem**.
- **Colisão**: personagem e zumbis não atravessam móveis; os móveis não bloqueiam a visão. O personagem passa por trás dos móveis (desenho ordenado pela base).

## 2026-11-11 — Kit médico
- 3 sprites novas recortadas: kit girando (com brilho), personagem pegando e guardando o kit, personagem usando o kit.
- Cada sala tem **40%** de chance de ter um kit **flutuando** no chão.
- **Espaço** em cima do kit pega e guarda (sem limite), mas **atacar tem preferência**: com zumbi colado (8 direções) o Espaço ataca — inclusive com porta à frente.
- **H** usa um kit: animação de cura e **+2 de vida** no brilho; golpe antes disso cancela sem gastar. HUD mostra "Kits: N".

## 2026-11-10 — Zumbis enxergam mais longe
- Raio de perseguição dos zumbis aumentado de 3 para **5 tiles** (`ZOMBIE_CHASE_RADIUS`).

## 2026-11-10 — Zumbi lançado pelo golpe
- Zumbi que sobrevive ao golpe do personagem é **lançado 1 tile para o lado oposto** a ele (8 direções, 0,15 s); parede, porta fechada ou outro zumbi atrás seguram. Cancela o passo e o preparo do golpe do zumbi.

## 2026-11-10 — Vida, zumbis atacando e game over
- Personagem com **10 de vida** (barra Vida no HUD).
- Zumbis a até **3 tiles** perseguem o personagem (busca de caminho curta, 8 direções, podem sair da sala por portas abertas; porta fechada segura) e, colados nele, preparam e dão um golpe de **2 de dano** (intervalo de 1 s). Longe, voltam a vagar onde estão.
- Ao levar golpe: animação de dano de `damage.png` (agora recortado), **empurrão de 1 tile** para o lado oposto ao zumbi (sem empurrão contra parede/zumbi: dano curto), sem controle durante o dano e **1 s invulnerável piscando**; número `-2` e moldura vermelha na tela.
- Vida 0: o personagem cai, **GAME OVER** e a mesma dungeon recomeça depois de 3 s.
- Espaço não fecha porta com zumbi dentro.

## 2026-11-10 — Zumbis na diagonal
- Zumbis passam a sortear entre 8 direções (retas e diagonais) ao vagar, com a mesma regra de não cortar quina e a mesma velocidade em px/s; na diagonal usam o sprite horizontal.

## 2026-11-10 — Movimento na diagonal
- Duas teclas juntas (W+A, W+D, S+A, S+D) andam na diagonal, tile a tile, na mesma velocidade em px/s.
- A diagonal não corta quina; bloqueada, o personagem desliza pelo eixo livre (ex.: W+A rente a uma parede à esquerda → sobe).
- Na diagonal usa o sprite horizontal; ataque e portas continuam nas 4 direções.

## 2026-11-10 — Zumbis sem pausa
- `ZOMBIE_IDLE_TIME` zerado: os zumbis emendam uma caminhada na outra. Cercados, tentam de novo a cada 0,1–0,3 s.

## 2026-11-10 — Ataque no Espaço e zumbis mais ativos
- O ataque passou para o **Espaço**, o mesmo botão das portas: com uma porta à frente (ou embaixo do personagem) o Espaço abre/fecha; senão, ataca. Clique esquerdo e J não atacam mais.
- Zumbis ficam parados no máximo **1 s** (antes 1–4 s) antes de voltar a andar.

## 2026-11-10 — Virar antes de andar e alcance do golpe
- Parado, apertar outra direção primeiro só **vira** o personagem; segurando a tecla ele anda depois de 0,12 s (`TURN_DELAY`). Na mesma direção, ou já andando, segue sem pausa.
- Golpe: alcance para a frente reduzido de 3 para **2 tiles** a partir do personagem (`ATTACK_REACH`); lados e trás iguais.

## 2026-11-10 — Parado olhando para onde andava
- Ao parar, o personagem continua virado para a direção em que andava (antes sempre voltava a olhar de frente). Poses paradas `idle_right/left/up` vêm do 1º quadro de cada caminhada.

## 2026-11-10 — Ataque e combate
- Sprite de ataque com faca recortada (`atack_spritsheet.png`): 9 quadros por direção, contorno magenta removido, alinhada com o personagem parado; esquerda = direita espelhada.
- **Clique esquerdo / J** ataca na direção em que o personagem está virado; durante o ataque ele não anda.
- Dano em área centrado no tile à frente: **11** no impacto, **6** colado nele, **4** a 2 tiles. Só acerta quem o personagem vê.
- Zumbis com **10 de vida**: piscam e mostram barra de vida ao levar dano; ao morrer afundam no chão (surgir ao contrário) e contam em "Abatidos".
- Números de dano flutuando; controles num painel no rodapé.
- `damage.png` adicionado ao projeto, ainda sem uso (zumbis ainda não atacam).

## 2026-11-09 — Zoom pela roda do mouse
- Teclas `+`/`-` substituídas pela **roda do mouse**: zoom contínuo de 1x a 2x (0,1 por clique, frações em touchpad), com transição suave.
- Zooms fracionários escalados com `smoothscale`; 1x e 2x continuam nítidos.

## 2026-11-09 — Recuperação de estamina 2x mais rápida
- Andando: de +5/s para **+10/s**; parado: de +10/s para **+20/s** (o gasto correndo continua −25/s).

## 2026-11-09 — Zumbis
- Sprite do zumbi recortada (`assets/monster/zombie_spritesheet_32x32.png`): parado, andando nas 4 direções e saindo do chão; fundo magenta e franja roxa removidos; escala 2×.
- 3 a 5 zumbis enterrados por sala; saem do chão quando o personagem os vê pela primeira vez.
- Depois vagam pela própria sala: andam 1–4 tiles numa direção aleatória e ficam 1–4 s parados.
- Zumbis bloqueiam o personagem (e uns aos outros); ainda sem dano.
- Personagem e zumbis desenhados ordenados por profundidade, com sombra.

## 2026-11-09 — Correção: corte reto na iluminação
- A escuridão da luz só cobria um quadrado em volta do personagem (~10 tiles para cada lado); além dele as áreas exploradas ficavam mais claras, criando um corte reto por volta dos 12 tiles. Agora a tela inteira recebe a escuridão da borda e a névoa das áreas exploradas é compensada para manter o mesmo brilho.

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
- Zumbis perseguirem e atacarem o personagem (vida do personagem, usando a sprite `damage.png`).
