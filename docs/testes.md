# Testes

Os testes usam `unittest` (biblioteca padrão) e rodam sem abrir janela. `test_tileset.py` usa `SDL_VIDEODRIVER=dummy`.

```bash
venv\Scripts\python.exe -m unittest discover tests        # todos
venv\Scripts\python.exe -m unittest discover tests -v     # com nome de cada teste
venv\Scripts\python.exe -m unittest tests.test_fov        # um arquivo
```

## O que cada arquivo cobre

### `tests/test_dungeon.py`
- A mesma seed gera o mesmo grid (número e texto); seeds diferentes geram grids diferentes.
- `normalize_seed`: `"123"` vira 123 e textos são estáveis.
- Em 200 seeds (com todas as portas abertas): mais de 3 salas, **todo o chão é alcançável** a partir do spawn (flood fill) e a borda é sempre parede.
- Em 200 seeds: **não existe passagem de 1 tile de largura** (todo tile de chão faz parte de algum bloco 2×2 de chão).
- O spawn é o chão (não porta) mais próximo do canto superior esquerdo.

### `tests/test_doors.py`
- Todas as seeds têm portas, e há portas nos 4 lados no conjunto das seeds.
- Toda porta tem 2 tiles contíguos de chão na linha da parede, parede nas pontas, sala de um lado e corredor do outro.
- Portas começam fechadas e a posição é determinística.
- Fechada não é andável e esconde o corredor atrás; aberta deixa passar e ver.
- `try_toggle`: abre, fecha, recusa fechar com o personagem em cima ou indo para a porta, e não faz nada longe de portas.

### `tests/test_player.py`
- Soltando a tecla no meio de um passo, o personagem termina **exatamente no centro de um tile** e nunca entra em parede.
- A velocidade é 150 × 1,3 px/s.
- Correndo, percorre 2x a distância de andando.
- Estamina: gasta 25/s correndo, zera e deixa o personagem cansado (não corre até recuperar 20), recupera 10/s andando e 20/s parado, e não passa de 100.

- Diagonal: W+A/W+D/S+A/S+D andam na diagonal e terminam no centro do tile, com sprite horizontal; mesma velocidade em px/s; desliza na parede; não corta quina (parede no tile reto ou no diagonal); zumbi no destino bloqueia, nos retos não; teclas opostas se anulam; regra de virar; numa dungeon real nunca entra em parede nem corta quina.
- Virar antes de andar: toque rápido em outra direção só vira; segurando, anda após `TURN_DELAY`; na mesma direção anda na hora; trocando de direção andando, segue sem pausa.
- Ataque: o golpe acerta **uma vez**, no quadro 5, no tile à frente; durante o ataque não anda nem vira; pedido no meio de um passo começa ao chegar no tile; pedidos durante o ataque não empilham.

- Parado: continua virado para a direção em que andava (`idle_<direção>`; de frente, `idle`).
- Golpe de zumbi (`take_hit`): tira 2; empurra 1 tile para o lado oposto (reto e diagonal) e termina no centro do tile; parede atrás ou zumbi atrás → sem empurrão e dano curto; diagonal bloqueada desliza pelo eixo livre; no meio de um passo parte do tile desenhado; cancela o ataque e trava os controles durante o dano; invulnerável durante o dano e por 1 s depois; vida 0 → morto, caído no quadro 4, sem controle.
- Kit médico: pegar trava os controles durante a animação e só funciona parado; H cura 2 no quadro do brilho e gasta 1 kit; não passa de 10; sem kit ou vida cheia não faz nada; pedido no meio de um passo começa ao chegar; golpe antes da cura cancela sem gastar; golpe cancela a animação de pegar; usando o kit não ataca.
- Sprite de dano: 6 quadros com empurrão e 4 sem, nas 4 direções, de pé na altura do personagem.

### `tests/test_combat.py`
- Área do golpe nas 4 direções: impacto 11, 7 tiles com 6 (os 8 vizinhos do impacto menos o personagem), 11 com 4 (o anel de 16 sem a fileira a 3 tiles à frente), nada além de 2 tiles à frente.
- Dano por distância: no impacto morre, colado fica com 4, a 2 fica com 6; 6 + 4 mata.
- Não levam dano: enterrado, fora da visão, morrendo.
- Morrendo: para de bloquear, afunda (quadros de 7 a 0), sai da horda e conta como abatido.
- Piscar e barra de vida ligam no golpe e somem depois; números de dano sobem e somem.
- Zumbi lançado: quem sobrevive voa 1 tile para longe do personagem (reto e diagonal), termina no centro do tile no tempo certo; quem morre não é lançado; parede ou zumbi atrás seguram; no meio de um passo parte do tile desenhado; morrendo durante o voo, para ali.
- Sprite de ataque: 9 quadros por direção, altura igual à do `idle`, `attack_left` é o espelho de `attack_right`, sem contorno magenta.

### `tests/test_controls.py`
- Espaço olhando para uma porta: abre/fecha e não ataca; sem porta por perto: ataca; dentro de uma porta aberta: não fecha nem ataca; com zumbi na porta: não fecha.
- Ordem do Espaço: kit embaixo → pega (some do chão, conta 1, animação de pegar); zumbi colado (de lado ou na diagonal) → ataca e não pega; zumbi longe ou enterrado não impede pegar; sem kit nem porta → ataca; ocupado → nada; zumbi na porta → a porta não fecha e o Espaço ataca. H: "Sem kit médico", "Vida cheia", e cura +2 com o número verde.
- Game over: golpe de zumbi tira vida e acende a moldura vermelha; vida 0 → depois de `GAME_OVER_TIME` recomeça a mesma seed com vida cheia no spawn.

### `tests/test_fov.py`
- A origem é sempre visível; nada fora do raio é visível.
- Em sala aberta, o círculo inteiro é visível.
- Uma parede esconde o que está atrás, mas ela mesma é visível; salas atrás de paredes ficam escondidas.
- A face de uma parede alta revela o tile de cima; uma porta na parede de cima também.
- Olhando rente a uma parede, a fileira inteira dela no alcance fica visível.
- Andando, `explored` só cresce e `visible` respeita o raio.

### `tests/test_lighting.py`
- `FogLayer`: começa toda preta; visível fica transparente; ao sair da visão fica escurecido (alpha compensado pela luz) e nunca volta a preto.
- `render` cobre a tela inteira, é transparente no centro de um tile visível, opaco no não descoberto e tem valores intermediários na fronteira (borda suave).
- Máscara de luz: centro claro, borda com a escuridão configurada, escurecendo do centro para fora.
- Sem emenda: dentro e fora do quadrado da máscara a escuridão é a mesma, mesmo com o personagem perto do canto da tela.
- Luz da borda + névoa compensada dão exatamente `FOG_EXPLORED_ALPHA` nos tiles descobertos.
- Tremulação: desligada fica sempre no nível 0; ligada varia de nível.

### `tests/test_items.py`
- Em 150 seeds: no máximo 1 kit por sala, em chão, longe do spawn, sem encostar em porta e fora dos tiles dos zumbis; ~40% das salas com kit; mesma seed → mesmos kits.
- Sprites: 6 quadros de pegar e 8 de usar nas 4 direções, de pé na altura do personagem; kit no chão com 8 quadros, 26 px de largura; ícone de 20 px.

### `tests/test_zombies.py`
- Em 60 seeds: cada sala com espaço tem de 3 a 5 zumbis, em tiles distintos de chão dentro da sala, todos enterrados e a mais de 2 tiles do spawn; a mesma seed gera os mesmos zumbis.
- Ficam enterrados enquanto não são vistos; ao entrar na visão, saem do chão e depois começam a andar; zumbis de outras salas continuam enterrados.
- Simulando 60 s com o personagem longe: nunca saem da sala, dois zumbis nunca ocupam o mesmo tile, nenhum entra no tile do personagem, e se movem (mais da metade sai do tile inicial).
- Também andam na diagonal, sempre para um tile vizinho, sem cortar quina, com sprite horizontal e a mesma velocidade em px/s.
- Sem pausa entre caminhadas: andam mais de 90% do tempo; parada mais longa só quando cercados (≤ 0,3 s).
- Zumbi enterrado não bloqueia o personagem; fora do chão, bloqueia. Não acorda com o personagem em cima.
- Perseguição: começa a `ZOMBIE_CHASE_RADIUS` tiles (5) e não a 6; chega colado e bate com preparo e intervalo certos; passa por porta aberta mas não por fechada; contorna parede; não bate através de quina; longe do personagem volta a vagar na sala em que está; personagem morto, zumbi enterrado ou morrendo não perseguem. Numa dungeon real, com o personagem parado perto: batem nele sem ninguém entrar no tile dele ou de outro zumbi.
- Sprite: quantidade de quadros por animação, tamanho 64×64, nenhum pixel magenta/roxo sobrando.

### `tests/test_zoom.py`
- Começa em 1x; limites 1x e 2x.
- A roda muda o alvo em `ZOOM_STEP` por clique, aceita frações (touchpad) e não passa dos limites; dez cliques dão exatamente 2.0.
- A transição é suave: começa a mudar no primeiro quadro, sem pular de uma vez, só cresce, sem passar do alvo e sem saltos grandes; termina exatamente no alvo.
- Evento `MOUSEWHEEL` muda o alvo; o desenho funciona em zooms fracionários.

### `tests/test_tileset.py`
- O recorte encontra as 10 peças na ordem esperada (pisos em cima, portas embaixo, proporções corretas).
- Nenhum pixel do contorno roxo sobra nas peças.
- As peças são escaladas para múltiplos do tile (piso 96×96, paredes altas 64 px, parede baixa 32 px).
- `render_map` é determinístico: a mesma seed gera exatamente a mesma imagem.
- Sombra das paredes: o topo de um tile de chão encostado numa parede fica bem mais escuro que o meio.
- Os sprites de porta têm o tamanho certo para cada lado; abrir todas as portas muda o mapa, e fechar de novo volta exatamente à imagem original.

## Teste manual

```bash
venv\Scripts\python.exe main.py 42
```

Confira: atacar com Espaço nas 4 direções (zumbis piscando, números de dano, barra de vida, zumbi afundando ao morrer, contador de abatidos), zumbis saindo do chão ao entrar numa sala e vagando sem atravessar o personagem, nascer no canto superior esquerdo, Espaço abrindo/fechando portas, movimento alinhado ao grid, corrida e barra de estamina, névoa suave e luz tremulando, sombras, personagem semitransparente atrás de porta, zoom suave pela roda do mouse (1x a 2x), R/G/V.
