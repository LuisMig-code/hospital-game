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
- Em 200 seeds: mais de 3 salas, **todo o chão é alcançável** a partir do spawn (flood fill) e a borda é sempre parede.
- Em 200 seeds: **não existe passagem de 1 tile de largura** (todo tile de chão faz parte de algum bloco 2×2 de chão).

### `tests/test_player.py`
- Soltando a tecla no meio de um passo, o personagem termina **exatamente no centro de um tile** e nunca entra em parede.
- A velocidade é 150 × 1,3 px/s.
- Correndo, percorre 2x a distância de andando.
- Estamina: gasta 25/s correndo, zera e deixa o personagem cansado (não corre até recuperar 20), recupera 5/s andando e 10/s parado, e não passa de 100.

### `tests/test_fov.py`
- A origem é sempre visível; nada fora do raio é visível.
- Em sala aberta, o círculo inteiro é visível.
- Uma parede esconde o que está atrás, mas ela mesma é visível; salas atrás de paredes ficam escondidas.
- A face de uma parede alta revela o tile de cima.
- Andando, `explored` só cresce e `visible` respeita o raio.

### `tests/test_tileset.py`
- O recorte encontra as 10 peças na ordem esperada (pisos em cima, portas embaixo, proporções corretas).
- Nenhum pixel do contorno roxo sobra nas peças.
- As peças são escaladas para múltiplos do tile (piso 96×96, paredes altas 64 px, parede baixa 32 px).
- `render_map` é determinístico: a mesma seed gera exatamente a mesma imagem.

## Teste manual

```bash
venv\Scripts\python.exe main.py 42
```

Confira: movimento alinhado ao grid, corrida e barra de estamina, névoa de guerra, zoom 1x/2x, R/G/V.
