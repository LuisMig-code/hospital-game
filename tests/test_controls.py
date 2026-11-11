"""Testes do Espaço (porta à frente / ataque) e do game over."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")      # o vídeo do elevador tem som
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402
import settings as S  # noqa: E402
from doors import SIDES  # noqa: E402
from player import Player  # noqa: E402
from items import MedKit  # noqa: E402
from zombies import IDLE, Zombie  # noqa: E402

FACING = {(0, -1): "up", (0, 1): "down", (-1, 0): "left", (1, 0): "right"}


def play(g):
    """Pula a chegada do elevador: o andar já em jogo normal."""
    g.phase, g.player_visible = "play", True
    return g


class SpaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = play(main.Game(42))

    def place_facing_door(self):
        """Personagem dentro da sala, olhando para a primeira porta."""
        g = self.game
        door = g.dungeon.doors[0]
        door.open = False
        (_, _), (ox, oy) = SIDES[door.side]
        x, y = door.tiles[0]
        g.player = Player(g.anims, (x - ox, y - oy))
        g.player.facing = FACING[(ox, oy)]
        return door

    def test_space_in_front_of_door_toggles_it(self):
        g = self.game
        door = self.place_facing_door()
        g.action()
        self.assertTrue(door.open)
        self.assertFalse(g.player.attack_queued)            # não ataca
        g.action()
        self.assertFalse(door.open)
        self.assertFalse(g.player.attack_queued)

    def test_space_without_door_attacks(self):
        g = self.game
        sx, sy = g.dungeon.spawn
        g.player = Player(g.anims, (sx, sy))
        g.player.facing = "down"
        front = (sx, sy + 1)
        self.assertNotIn(front, g.dungeon.door_at)
        self.assertNotIn((sx, sy), g.dungeon.door_at)
        g.action()
        self.assertTrue(g.player.attack_queued)

    def test_space_inside_open_door_does_not_attack(self):
        g = self.game
        door = self.place_facing_door()
        g.action()                                          # abre
        g.player = Player(g.anims, door.tiles[0])           # entra na porta
        g.action()                                          # não fecha (bloqueada) e não ataca
        self.assertTrue(door.open)
        self.assertFalse(g.player.attack_queued)

    def test_door_with_zombie_does_not_close(self):
        g = self.game
        door = self.place_facing_door()
        g.action()                                          # abre
        z = Zombie(door.tiles[0], None)
        z.state = IDLE
        g.horde.zombies.append(z)
        try:
            self.assertEqual(g.toggle_door(), "zumbi")      # zumbi na porta: não fecha
            self.assertTrue(door.open)
            g.action()                                      # e o Espaço, com ele colado, ataca
            self.assertTrue(door.open)
            self.assertTrue(g.player.attack_queued)
        finally:
            g.horde.zombies.remove(z)


class SpaceOrderTests(unittest.TestCase):
    """Espaço: zumbi colado → ataca; kit embaixo → pega; porta → abre/fecha; senão ataca."""

    @classmethod
    def setUpClass(cls):
        cls.game = play(main.Game(42))

    def setUp(self):
        g = self.game
        g.horde.zombies = []
        g.medkits = []
        sx, sy = g.dungeon.spawn
        g.player = Player(g.anims, (sx, sy))
        g.player.facing = "down"

    def zombie(self, tile):
        z = Zombie(tile, None)
        z.state = IDLE
        self.game.horde.zombies.append(z)
        return z

    def test_kit_under_player_is_collected(self):
        g = self.game
        kit = MedKit(g.player.tile)
        g.medkits.append(kit)
        g.action()
        self.assertNotIn(kit, g.medkits)                    # sumiu do chão
        self.assertEqual(g.player.medkits, 1)
        self.assertEqual(g.player.action, "pickup")
        self.assertFalse(g.player.attack_queued)

    def test_kit_beside_player_is_collected_and_player_turns(self):
        g = self.game
        x, y = g.player.tile
        for dx, dy, facing in ((1, 0, "right"), (0, 1, "down"), (1, 1, "right")):
            if not g.dungeon.is_walkable(x + dx, y + dy):
                continue
            g.player = Player(g.anims, (x, y))
            g.player.facing = "up"
            kit = MedKit((x + dx, y + dy))
            g.medkits = [kit]
            g.action()
            self.assertEqual(g.medkits, [], (dx, dy))           # pegou o kit do lado
            self.assertEqual(g.player.medkits, 1)
            self.assertEqual(g.player.facing, facing)           # virou para ele
            self.assertEqual(g.player.action, "pickup")

    def test_kit_two_tiles_away_is_not_collected(self):
        g = self.game
        x, y = g.player.tile
        g.medkits = [MedKit((x + 2, y))]
        g.action()
        self.assertEqual(len(g.medkits), 1)
        self.assertEqual(g.player.medkits, 0)
        self.assertTrue(g.player.attack_queued)                 # sem kit ao alcance: ataca

    def test_kit_under_player_has_priority(self):
        g = self.game
        x, y = g.player.tile
        under, beside = MedKit((x, y)), MedKit((x + 1, y))
        g.medkits = [beside, under]
        g.action()
        self.assertEqual(g.medkits, [beside])

    def test_zombie_touching_attacks_instead_of_collecting(self):
        g = self.game
        x, y = g.player.tile
        kit = MedKit((x, y))
        g.medkits.append(kit)
        self.zombie((x + 1, y))                             # colado (de lado, não à frente)
        g.action()
        self.assertTrue(g.player.attack_queued)
        self.assertIn(kit, g.medkits)
        self.assertEqual(g.player.medkits, 0)

    def test_diagonal_zombie_counts_as_touching(self):
        g = self.game
        x, y = g.player.tile
        g.medkits.append(MedKit((x, y)))
        self.zombie((x + 1, y + 1))
        g.action()
        self.assertTrue(g.player.attack_queued)

    def test_far_or_buried_zombie_does_not_block_pickup(self):
        g = self.game
        x, y = g.player.tile
        g.medkits.append(MedKit((x, y)))
        self.zombie((x + 2, y))                             # a 2 tiles
        buried = Zombie((x + 1, y), None)                   # enterrado
        g.horde.zombies.append(buried)
        g.action()
        self.assertEqual(g.player.medkits, 1)

    def test_no_kit_no_door_attacks(self):
        g = self.game
        g.action()
        self.assertTrue(g.player.attack_queued)

    def test_busy_ignores_space(self):
        g = self.game
        g.medkits.append(MedKit(g.player.tile))
        g.player.start_pickup()                             # já pegando outro
        g.action()
        self.assertEqual(len(g.medkits), 1)
        self.assertFalse(g.player.attack_queued)

    def test_h_messages_and_heal(self):
        g = self.game
        p = g.player
        g.use_medkit()
        self.assertEqual(g.message, "Sem kit médico")
        p.medkits = 1
        g.use_medkit()
        self.assertEqual(g.message, "Vida cheia")
        self.assertFalse(p.heal_queued)
        p.hp = 5
        g.use_medkit()
        self.assertTrue(p.heal_queued)
        texts = len(g.texts)
        for _ in range(60):
            g.step(1 / 60, _NoKeys())
        self.assertEqual((p.hp, p.medkits), (5 + S.MEDKIT_HEAL, 0))
        self.assertEqual(len(g.texts), texts + 1)           # "+2" verde
        self.assertEqual(g.texts[-1].text, f"+{S.MEDKIT_HEAL}")


class GameOverTests(unittest.TestCase):
    def test_zombie_hit_then_game_over_starts_new_run(self):
        g = main.Game(7)
        g.horde.zombies = []
        p = g.player
        x, y = p.tile
        z = Zombie((x + 1, y), None)
        g.zombie_hits([z])
        self.assertEqual(p.hp, S.PLAYER_HP - S.ZOMBIE_DAMAGE)
        self.assertTrue(p.hurt)
        self.assertGreater(g.hit_flash, 0)
        p.hp = S.ZOMBIE_DAMAGE                              # próximo golpe mata
        p.hurt, p.invulnerable, p.target = False, 0.0, None
        g.zombie_hits([z])
        self.assertTrue(p.dead)
        no_keys = _NoKeys()
        for _ in range(round((S.GAME_OVER_TIME - 0.2) * 60)):
            g.step(1 / 60, no_keys)
        self.assertIs(g.player, p)                          # ainda no game over
        g.draw_world(); g.draw_hit_flash(); g.draw_hud(); g.draw_game_over()
        for _ in range(round(0.4 * 60)):
            g.step(1 / 60, no_keys)
        self.assertIsNot(g.player, p)                       # recomeçou
        self.assertNotEqual(g.run_seed, 7)                  # run nova, outra seed
        self.assertEqual(g.floor, 1)
        self.assertEqual(g.player.medkits, 0)
        self.assertEqual(g.player.hp, S.PLAYER_HP)
        self.assertEqual(g.player.tile, g.dungeon.spawn)
        self.assertFalse(g.player.dead)


class ElevatorFlowTests(unittest.TestCase):
    def setUp(self):
        self.g = main.Game(42)

    def run_frames(self, seconds, keys=None):
        for _ in range(round(seconds * 60)):
            self.g.step(1 / 60, keys or _NoKeys())

    def test_arrival_locks_controls_then_closes(self):
        g = self.g
        self.assertEqual(g.phase, "arrive")
        self.assertFalse(g.player_visible)
        self.assertEqual(g.player.tile, g.dungeon.elevator_in.front[0])
        keys = _Keys({main.pygame.K_s: True})
        self.run_frames(0.5, keys)                          # ainda saindo: não anda
        self.assertEqual(g.player.tile, g.dungeon.spawn)
        g.action()
        self.assertFalse(g.player.attack_queued)
        self.run_frames(8 / S.ELEVATOR_FPS)
        self.assertEqual(g.phase, "play")
        self.assertTrue(g.player_visible)
        self.assertEqual(g.el_in.anim, "close")

    def test_space_at_exit_goes_to_next_floor_keeping_hp_and_kits(self):
        g = play(self.g)
        ex = g.dungeon.elevator_out
        g.horde.zombies = []
        g.medkits = []
        g.player = Player(g.anims, ex.front[1])
        g.player.hp, g.player.medkits = 6, 2
        first_seed = g.seed
        g.action()
        self.assertEqual(g.phase, "exit")
        self.assertFalse(g.player.attack_queued)
        g.action()                                          # Espaço durante a saída: nada
        self.run_frames(8 / S.ELEVATOR_FPS + S.ELEVATOR_WALK_TIME + 8 / S.ELEVATOR_FPS + 0.2)
        self.assertEqual(g.phase, "video")                  # vídeo do elevador
        self.assertTrue(g.draw_floor_video())
        self.assertEqual(g.floor, 1)
        self.run_frames(g.video.duration + 0.1)
        self.assertIsNone(g.video)
        self.assertEqual(g.floor, 2)
        self.assertNotEqual(g.seed, first_seed)
        self.assertEqual((g.player.hp, g.player.medkits), (6, 2))
        self.assertEqual(g.phase, "arrive")
        self.assertEqual(g.player.tile, g.dungeon.spawn)

    def to_video(self):
        g = play(self.g)
        g.horde.zombies = []
        g.player = Player(g.anims, g.dungeon.elevator_out.front[0])
        g.action()
        self.run_frames(8 / S.ELEVATOR_FPS + S.ELEVATOR_WALK_TIME + 8 / S.ELEVATOR_FPS + 0.2)
        return g

    def test_video_plays_frames_and_can_be_skipped(self):
        g = self.to_video()
        self.assertEqual(g.phase, "video")
        first = g.video.index
        self.run_frames(1.0)
        self.assertGreater(g.video.index, first + 20)       # ~24 quadros por segundo
        self.assertEqual(g.video.surface.get_size(), (S.SCREEN_W, S.SCREEN_H))
        g.end_floor_video()                                 # Espaço/Enter pulam
        self.assertEqual((g.floor, g.phase), (2, "arrive"))

    def test_without_video_falls_back_to_fade(self):
        import video
        saved, video.cv2 = video.cv2, None
        try:
            g = self.to_video()
            self.assertEqual(g.phase, "fade")
            self.run_frames(S.FLOOR_FADE_TIME + 0.1)
            self.assertEqual(g.floor, 2)
        finally:
            video.cv2 = saved

    def test_zombie_touching_at_exit_attacks(self):
        g = play(self.g)
        ex = g.dungeon.elevator_out
        g.horde.zombies = []
        g.player = Player(g.anims, ex.front[0])
        z = Zombie((ex.front[0][0], ex.front[0][1] + 1), None)
        z.state = IDLE
        g.horde.zombies.append(z)
        g.action()
        self.assertEqual(g.phase, "play")
        self.assertTrue(g.player.attack_queued)

    def test_away_from_exit_does_not_enter(self):
        g = play(self.g)
        g.horde.zombies = []
        g.action()                                          # no spawn, longe da saída
        self.assertEqual(g.phase, "play")

    def test_exit_light_pulses_when_near(self):
        g = play(self.g)
        g.horde.zombies = []
        ex = g.dungeon.elevator_out
        self.run_frames(0.1)
        self.assertEqual(g.el_out.anim, "closed")
        g.player = Player(g.anims, (ex.front[0][0], ex.front[0][1] + 2))
        self.run_frames(0.1)
        self.assertEqual(g.el_out.anim, "idle")

    def test_new_run_key_resets_floor(self):
        g = self.g
        g.floor = 3
        g.new_run(123)
        self.assertEqual((g.floor, g.run_seed, g.seed), (1, 123, 123))


class _Keys(dict):
    def __getitem__(self, k):
        return dict.get(self, k, False)


class _NoKeys:
    def __getitem__(self, k):
        return False


if __name__ == "__main__":
    unittest.main()
