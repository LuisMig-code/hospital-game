"""Salas temáticas: catálogo de props (móveis e detalhes) e o que cada tema usa.

Só dados — sem pygame. `furnish.py` usa as pegadas para posicionar e a
colisão; `props.py` usa sheet/linha/coluna/largura para recortar e desenhar.

Índices (linha, coluna) dos sheets de props: linhas pela projeção do alpha
e colunas separadas por vãos de 3 px (veja `props.slice_sheet`); conferidos
no preview numerado de `tools/export_frames.py`.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Prop:
    sheet: str          # "equip", "furn" ou "weath" (settings.PROP_SHEETS)
    row: int
    col: int
    width: int          # largura do desenho na tela (px)
    fw: int = 1         # pegada em tiles (largura, altura)
    fh: int = 1
    solid: bool = True  # bloqueia o movimento (False: detalhe no chão, sem colisão)


P = Prop
PROPS = {
    # --- camas e macas
    "bed_v": P("furn", 0, 0, 40, 1, 2),
    "bed_v_dirty": P("furn", 0, 1, 40, 1, 2),
    "bed_v_blood": P("furn", 0, 2, 40, 1, 2),
    "bed_h": P("equip", 0, 0, 66, 2, 1),
    "bed_h_blood": P("equip", 0, 2, 66, 2, 1),
    "bed_broken": P("equip", 0, 5, 68, 2, 1),
    "stretcher": P("equip", 1, 0, 64, 2, 1),
    "stretcher_body": P("equip", 1, 1, 64, 2, 1),
    "stretcher_blood": P("equip", 1, 2, 64, 2, 1),
    "stretcher_straps": P("equip", 1, 5, 64, 2, 1),
    "stretcher_fallen": P("equip", 1, 4, 62, 2, 1),
    "gurney_covered": P("weath", 0, 6, 60, 2, 1),
    # --- cadeiras de rodas
    "wheelchair": P("equip", 2, 1, 32),
    "wheelchair_back": P("equip", 2, 3, 30),
    "wheelchair_fallen": P("equip", 2, 4, 38),
    "wheelchair_rusty": P("equip", 2, 5, 34),
    # --- enfermaria
    "nightstand": P("equip", 3, 0, 26),
    "nightstand_open": P("equip", 3, 1, 28),
    "iv_stand": P("equip", 3, 2, 22),
    "iv_blood": P("equip", 3, 3, 22),
    "curtain": P("furn", 0, 7, 50, 2, 1),
    "curtain_blood": P("furn", 0, 8, 50, 2, 1),
    "screen": P("furn", 4, 0, 56, 2, 1),
    "screen_blood": P("furn", 4, 1, 56, 2, 1),
    # --- equipamentos
    "monitor": P("equip", 4, 0, 28),
    "monitor_on": P("equip", 4, 1, 28),
    "crash_cart": P("equip", 4, 2, 32),
    "crash_cart_messy": P("equip", 4, 3, 36),
    "oxygen": P("furn", 4, 5, 16),
    "oxygen_blood": P("furn", 4, 6, 16),
    "ventilator": P("equip", 4, 5, 32),
    "anesthesia": P("furn", 3, 2, 30),
    "monitor_cart": P("furn", 3, 0, 30),
    "monitor_broken": P("furn", 3, 1, 30),
    "op_table": P("equip", 5, 0, 70, 2, 1),
    "op_table_blood": P("equip", 5, 1, 70, 2, 1),
    "instrument_table": P("equip", 5, 4, 54, 2, 1),
    "tray_fallen": P("equip", 5, 5, 54, 2, 1),
    "surgical_lamp": P("furn", 4, 7, 32),
    "exam_chair": P("furn", 4, 8, 50, 2, 1),
    "exam_chair_blood": P("furn", 4, 9, 50, 2, 1),
    "sink": P("furn", 2, 8, 34),
    "cart": P("furn", 2, 4, 32),
    "cart_blood": P("furn", 2, 5, 32),
    # --- recepção / escritório
    "office_chair": P("furn", 1, 0, 24),
    "office_chair_torn": P("furn", 1, 1, 24),
    "chair": P("furn", 1, 2, 24),
    "chair_torn": P("furn", 1, 3, 24),
    "sofa": P("furn", 1, 4, 92, 3, 1),
    "sofa_blood": P("furn", 1, 5, 92, 3, 1),
    "armchair": P("furn", 1, 7, 30),
    "desk": P("furn", 3, 3, 62, 2, 1),
    "desk_blood": P("furn", 3, 4, 62, 2, 1),
    "desk_green": P("furn", 3, 5, 62, 2, 1),
    "trash": P("furn", 4, 2, 18),
    "trash_blood": P("furn", 4, 3, 18),
    "floor_lamp": P("furn", 4, 10, 22),
    # --- armários e estantes
    # armários altos: 2 tiles de largura na pegada, ~2 tiles de altura no desenho
    "cabinet_glass": P("furn", 2, 0, 50, 2, 1),
    "cabinet_glass_broken": P("furn", 2, 1, 50, 2, 1),
    "cabinet_metal": P("furn", 2, 2, 50, 2, 1),
    "cabinet_rusty": P("furn", 2, 3, 50, 2, 1),
    "drawers": P("furn", 2, 6, 26),
    "drawers_rusty": P("furn", 2, 7, 26),
    # estantes altas: 2 tiles de largura na pegada, ~2 tiles de altura no desenho
    "shelf": P("furn", 3, 6, 50, 2, 1),
    "shelf_blood": P("furn", 3, 7, 50, 2, 1),
    "shelf_empty": P("furn", 3, 8, 50, 2, 1),
    "locker": P("weath", 3, 2, 46, 2, 1),
    "locker_open": P("weath", 3, 3, 46, 2, 1),
    "cabinet_low": P("weath", 3, 4, 52, 2, 1),
    "cabinet_low_open": P("weath", 3, 5, 54, 2, 1),
    # --- necrotério
    "morgue_drawers": P("weath", 0, 0, 90, 3, 1),
    "morgue_drawers_open": P("weath", 0, 1, 66, 2, 1),
    "morgue_drawers_body": P("weath", 0, 2, 66, 2, 1),
    "autopsy_table": P("weath", 0, 3, 60, 2, 1),
    "autopsy_table_blood": P("weath", 0, 4, 60, 2, 1),
    "biohazard": P("furn", 4, 4, 24),
    "biohazard_bin": P("weath", 2, 0, 28),
    "biohazard_bin_open": P("weath", 2, 1, 28),
    # --- depósito / abandonado
    "boxes": P("weath", 1, 6, 36),
    "crate": P("weath", 3, 0, 36),
    "crate_open": P("weath", 3, 1, 36),
    "dumpster": P("weath", 3, 6, 36),
    "dumpster_open": P("weath", 3, 7, 36),
    "shelf_broken": P("weath", 1, 7, 62, 2, 1),
    "rubble": P("weath", 1, 5, 36),
    "chair_fallen": P("weath", 1, 0, 30),
    "table_fallen": P("weath", 1, 1, 34),
    "monitor_smashed": P("weath", 2, 7, 30),
    # --- detalhes no chão (sem colisão)
    "body_bag": P("weath", 0, 5, 48, 2, 1, solid=False),
    "tiles_loose": P("weath", 1, 2, 30, solid=False),
    "glass": P("weath", 1, 3, 30, solid=False),
    "ceiling_debris": P("weath", 1, 4, 34, solid=False),
    "bloody_cloth": P("weath", 2, 2, 26, solid=False),
    "gloves": P("weath", 2, 3, 26, solid=False),
    "iv_bags": P("weath", 2, 4, 28, solid=False),
    "syringes": P("weath", 2, 5, 26, solid=False),
    "bandages": P("weath", 2, 6, 28, solid=False),
}
del P


@dataclass(frozen=True)
class Theme:
    name: str                     # nome mostrado no HUD
    wall: int                     # estilo de parede (linha do sheet de paredes)
    door: str                     # porta dupla fechada (tileset.DOOR_CLOSED)
    floors: tuple                 # piso base (tileset.FLOOR_BLOCKS): um deles por sala
    decals: tuple                 # blocos de piso com detalhe, sorteados às vezes (só com
                                  # base no piso liso: os blocos de detalhe têm fundo liso)
    top: tuple                    # props encostados na parede de cima
    side: tuple                   # props encostados nas laterais (1 tile de largura)
    center: tuple = ()            # grupos no meio das salas grandes: ((nome, dx, dy), ...)
    scatter: tuple = ()           # detalhes no chão (sem colisão)
    loose: tuple = ()             # props soltos pela sala (1x1, com colisão)
    weight: int = 1               # chance relativa de sortear o tema


THEMES = {
    "recepcao": Theme(
        "Recepção", wall=0, door="closed",
        floors=("beige", "checker"), decals=(),
        top=("sofa", "sofa", "sofa_blood", "desk", "desk_green", "cabinet_metal", "trash", "armchair",
             "floor_lamp"),
        side=("chair", "chair_torn", "trash", "armchair", "drawers"),
        center=((("desk", 0, 0), ("office_chair", 0, 1)),
                (("desk_green", 0, 0), ("office_chair_torn", 1, 1)),
                (("chair", 0, 0), ("chair", 1, 0), ("chair_torn", 2, 0))),
        scatter=("tiles_loose", "glass"),
        loose=("chair_torn", "office_chair_torn", "trash_blood"),
    ),
    "enfermaria": Theme(
        "Enfermaria", wall=2, door="closed",
        floors=("plain",), decals=("dirt", "blood_drops", "cracked", "footprints"),
        top=("bed_v", "bed_v_dirty", "bed_v_blood", "bed_v", "nightstand", "iv_stand", "iv_blood",
             "curtain", "cabinet_glass"),
        side=("bed_v", "bed_v_dirty", "nightstand", "nightstand_open", "iv_stand", "drawers"),
        center=((("screen", 0, 0),),
                (("bed_h", 0, 0), ("iv_stand", 2, 0)),
                (("curtain_blood", 0, 0),)),
        scatter=("bandages", "gloves", "bloody_cloth"),
        loose=("wheelchair", "wheelchair_back", "iv_stand"),
    ),
    "emergencia": Theme(
        "Emergência", wall=1, door="blood",
        floors=("plain",), decals=("blood_splat", "blood_hand", "blood_trail", "blood_smear", "blood_drops",
                                   "blood_crack"),
        top=("stretcher", "stretcher_blood", "stretcher_straps", "crash_cart", "crash_cart_messy",
             "monitor", "monitor_on", "iv_blood", "sink", "cart_blood"),
        side=("monitor", "crash_cart", "iv_blood", "cart", "cart_blood", "oxygen_blood"),
        center=((("stretcher_blood", 0, 0), ("iv_blood", 2, 0)),
                (("stretcher_fallen", 0, 0),),
                (("bed_broken", 0, 0),)),
        scatter=("syringes", "bloody_cloth", "iv_bags", "glass"),
        loose=("wheelchair_fallen", "monitor_broken", "chair_fallen"),
    ),
    "cirurgia": Theme(
        "Centro cirúrgico", wall=3, door="closed",
        floors=("blue",), decals=(),
        top=("anesthesia", "ventilator", "monitor_cart", "cabinet_glass", "sink", "oxygen", "crash_cart",
             "cabinet_glass_broken"),
        side=("oxygen", "monitor_cart", "cart", "anesthesia", "drawers"),
        center=((("op_table", 0, 0), ("surgical_lamp", 2, 0), ("instrument_table", 0, 1)),
                (("op_table_blood", 0, 0), ("surgical_lamp", -1, 0)),
                (("exam_chair", 0, 0), ("cart", 2, 0))),
        scatter=("syringes", "gloves", "bloody_cloth"),
        loose=("tray_fallen", "oxygen_blood"),
    ),
    "necroterio": Theme(
        "Necrotério", wall=4, door="vault",
        floors=("dark",), decals=(),
        top=("morgue_drawers", "morgue_drawers", "morgue_drawers_open", "morgue_drawers_body", "biohazard",
             "shelf_empty", "sink"),
        side=("biohazard", "biohazard_bin", "biohazard_bin_open", "drawers_rusty"),
        center=((("autopsy_table", 0, 0),),
                (("autopsy_table_blood", 0, 0), ("cart", 2, 0)),
                (("gurney_covered", 0, 0),),
                (("stretcher_body", 0, 0),)),
        scatter=("body_bag", "gloves", "bloody_cloth"),
        loose=("biohazard_bin",),
    ),
    "deposito": Theme(
        "Depósito", wall=5, door="shattered",
        floors=("plain",), decals=("mold", "cracked", "broken", "burnt", "puddle", "slime", "concrete"),
        top=("shelf", "shelf_blood", "shelf_empty", "locker", "locker_open", "cabinet_rusty", "dumpster",
             "cabinet_low", "cabinet_low_open"),
        side=("boxes", "crate", "crate_open", "dumpster_open", "drawers_rusty"),
        center=((("boxes", 0, 0), ("crate", 1, 0)),
                (("shelf_broken", 0, 0),),
                (("crate_open", 0, 0), ("boxes", 0, 1))),
        scatter=("tiles_loose", "glass", "ceiling_debris"),
        loose=("rubble", "boxes", "chair_fallen", "table_fallen", "monitor_smashed", "wheelchair_rusty"),
    ),
}

SPAWN_THEME = "recepcao"

# Corredores: parede padrão, piso liso com sujeira/sangue de vez em quando
CORRIDOR = Theme(
    "Corredor", wall=0, door="closed",
    floors=("plain",),
    decals=("cracked", "broken", "footprints", "puddle", "papers", "blood_smear", "dirt", "blood_drops",
            "drain", "glass_floor"),
    top=(), side=(),
)
