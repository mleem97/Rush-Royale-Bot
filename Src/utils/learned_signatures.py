"""
Auto-generierte Screen-Signaturen.
Generiert aus Screenshots - KEINE Icons noetig!
"""
from Src.utils.template_free_detector import GameScreen, ColorCheckpoint, ScreenSignature

# Mapping von gelernten Namen zu GameScreen
# pve = Dungeon/PvE Screens, pvp = Battle Screens, home = Home
SCREEN_MAPPING = {
    "home": GameScreen.HOME,
    "pve": GameScreen.DUNGEON_SELECT,
    "pvp": GameScreen.BATTLE_ACTIVE,
    "battle": GameScreen.BATTLE_ACTIVE,
    "dungeon": GameScreen.DUNGEON_SELECT,
    "victory": GameScreen.BATTLE_VICTORY,
    "defeat": GameScreen.BATTLE_DEFEAT,
    "store": GameScreen.STORE,
    "shop": GameScreen.STORE,
    "loading": GameScreen.LOADING,
    "popup": GameScreen.POPUP_DIALOG,
    "quest": GameScreen.HOME,
    "events": GameScreen.HOME,
    "expedition": GameScreen.HOME,
    "heroes": GameScreen.HOME,
}

LEARNED_SIGNATURES = [
    # home (aus 4 Screenshots)
    ScreenSignature(
        screen_type=SCREEN_MAPPING.get("home", GameScreen.UNKNOWN),
        checkpoints=[
            ColorCheckpoint(800, 50, [(6, 27, 52)], 20, "auto"),
            ColorCheckpoint(100, 300, [(9, 36, 65)], 20, "auto"),
            ColorCheckpoint(450, 300, [(9, 29, 50)], 20, "auto"),
            ColorCheckpoint(100, 600, [(12, 61, 115)], 20, "auto"),
            ColorCheckpoint(100, 1000, [(87, 186, 195)], 20, "auto"),
            ColorCheckpoint(450, 1000, [(177, 181, 210)], 20, "auto"),
            ColorCheckpoint(800, 1000, [(214, 168, 58)], 27, "auto"),
            ColorCheckpoint(140, 1259, [(255, 179, 0)], 20, "auto"),
            ColorCheckpoint(450, 1259, [(12, 77, 141)], 20, "auto"),
            ColorCheckpoint(450, 1450, [(150, 215, 239)], 20, "auto"),
            ColorCheckpoint(800, 1450, [(255, 197, 0)], 20, "auto"),
        ],
        min_matches=5,
    ),
    # Other (aus 5 Screenshots)
    ScreenSignature(
        screen_type=SCREEN_MAPPING.get("Other", GameScreen.UNKNOWN),
        checkpoints=[
            ColorCheckpoint(800, 50, [(26, 17, 35)], 55, "auto"),
            ColorCheckpoint(100, 1450, [(4, 45, 75)], 58, "auto"),
        ],
        min_matches=1,
    ),
    # dungeon (aus 5 Screenshots)
    ScreenSignature(
        screen_type=SCREEN_MAPPING.get("dungeon", GameScreen.UNKNOWN),
        checkpoints=[
            ColorCheckpoint(800, 50, [(56, 65, 113)], 50, "auto"),
            ColorCheckpoint(100, 300, [(80, 81, 70)], 51, "auto"),
        ],
        min_matches=1,
    ),
    # pvp (aus 2 Screenshots)
    ScreenSignature(
        screen_type=SCREEN_MAPPING.get("pvp", GameScreen.UNKNOWN),
        checkpoints=[
            ColorCheckpoint(100, 50, [(16, 47, 84)], 20, "auto"),
            ColorCheckpoint(450, 50, [(15, 55, 98)], 20, "auto"),
            ColorCheckpoint(800, 50, [(12, 44, 82)], 20, "auto"),
            ColorCheckpoint(100, 300, [(15, 56, 103)], 20, "auto"),
            ColorCheckpoint(450, 300, [(41, 41, 72)], 20, "auto"),
            ColorCheckpoint(800, 300, [(15, 56, 103)], 20, "auto"),
            ColorCheckpoint(100, 600, [(16, 58, 107)], 20, "auto"),
            ColorCheckpoint(450, 600, [(19, 104, 179)], 20, "auto"),
            ColorCheckpoint(800, 600, [(16, 58, 107)], 20, "auto"),
            ColorCheckpoint(100, 1000, [(16, 58, 107)], 20, "auto"),
            ColorCheckpoint(450, 1000, [(19, 96, 170)], 20, "auto"),
            ColorCheckpoint(800, 1000, [(16, 58, 107)], 20, "auto"),
            ColorCheckpoint(140, 1259, [(223, 239, 243)], 20, "auto"),
            ColorCheckpoint(450, 1259, [(223, 239, 243)], 20, "auto"),
            ColorCheckpoint(750, 1259, [(223, 239, 243)], 20, "auto"),
            ColorCheckpoint(100, 1450, [(14, 51, 93)], 20, "auto"),
            ColorCheckpoint(450, 1450, [(171, 156, 166)], 20, "auto"),
            ColorCheckpoint(800, 1450, [(14, 51, 94)], 20, "auto"),
        ],
        min_matches=9,
    ),
    # quest (aus 5 Screenshots)
    ScreenSignature(
        screen_type=SCREEN_MAPPING.get("quest", GameScreen.UNKNOWN),
        checkpoints=[
            ColorCheckpoint(100, 50, [(27, 74, 164)], 32, "auto"),
            ColorCheckpoint(800, 50, [(27, 74, 164)], 32, "auto"),
            ColorCheckpoint(100, 1450, [(0, 105, 181)], 20, "auto"),
        ],
        min_matches=1,
    ),
    # store (aus 4 Screenshots)
    ScreenSignature(
        screen_type=SCREEN_MAPPING.get("store", GameScreen.UNKNOWN),
        checkpoints=[
            ColorCheckpoint(100, 50, [(34, 34, 65)], 20, "auto"),
            ColorCheckpoint(450, 50, [(23, 23, 57)], 20, "auto"),
            ColorCheckpoint(800, 50, [(6, 28, 54)], 20, "auto"),
            ColorCheckpoint(750, 1259, [(58, 50, 80)], 54, "auto"),
            ColorCheckpoint(100, 1450, [(166, 86, 16)], 20, "auto"),
            ColorCheckpoint(450, 1450, [(0, 106, 186)], 20, "auto"),
            ColorCheckpoint(800, 1450, [(255, 197, 0)], 20, "auto"),
        ],
        min_matches=3,
    ),
    # auto_1 (aus 4 Screenshots)
    ScreenSignature(
        screen_type=SCREEN_MAPPING.get("auto_1", GameScreen.UNKNOWN),
        checkpoints=[
            ColorCheckpoint(100, 50, [(34, 34, 65)], 20, "auto"),
            ColorCheckpoint(450, 50, [(23, 23, 57)], 20, "auto"),
            ColorCheckpoint(800, 50, [(6, 27, 51)], 20, "auto"),
            ColorCheckpoint(100, 600, [(13, 54, 100)], 20, "auto"),
            ColorCheckpoint(450, 600, [(15, 90, 159)], 33, "auto"),
            ColorCheckpoint(800, 600, [(14, 59, 109)], 20, "auto"),
            ColorCheckpoint(100, 1000, [(24, 52, 90)], 44, "auto"),
            ColorCheckpoint(450, 1000, [(13, 96, 171)], 20, "auto"),
            ColorCheckpoint(800, 1000, [(11, 58, 110)], 20, "auto"),
            ColorCheckpoint(140, 1259, [(35, 48, 106)], 46, "auto"),
            ColorCheckpoint(450, 1259, [(37, 60, 119)], 32, "auto"),
            ColorCheckpoint(100, 1450, [(255, 197, 0)], 20, "auto"),
            ColorCheckpoint(450, 1450, [(0, 106, 186)], 20, "auto"),
            ColorCheckpoint(800, 1450, [(255, 197, 0)], 20, "auto"),
        ],
        min_matches=7,
    ),
    # auto_2 (aus 2 Screenshots)
    ScreenSignature(
        screen_type=SCREEN_MAPPING.get("auto_2", GameScreen.UNKNOWN),
        checkpoints=[
            ColorCheckpoint(100, 50, [(34, 34, 65)], 20, "auto"),
            ColorCheckpoint(450, 50, [(23, 23, 57)], 20, "auto"),
            ColorCheckpoint(800, 50, [(6, 27, 52)], 20, "auto"),
            ColorCheckpoint(100, 300, [(54, 32, 56)], 20, "auto"),
            ColorCheckpoint(450, 300, [(170, 94, 44)], 20, "auto"),
            ColorCheckpoint(800, 300, [(203, 112, 92)], 20, "auto"),
            ColorCheckpoint(100, 600, [(15, 50, 89)], 20, "auto"),
            ColorCheckpoint(450, 600, [(16, 73, 126)], 20, "auto"),
            ColorCheckpoint(800, 600, [(15, 50, 89)], 20, "auto"),
            ColorCheckpoint(100, 1000, [(12, 63, 117)], 20, "auto"),
            ColorCheckpoint(450, 1000, [(255, 255, 255)], 20, "auto"),
            ColorCheckpoint(800, 1000, [(12, 62, 116)], 20, "auto"),
            ColorCheckpoint(140, 1259, [(11, 35, 65)], 20, "auto"),
            ColorCheckpoint(450, 1259, [(15, 60, 111)], 20, "auto"),
            ColorCheckpoint(750, 1259, [(11, 35, 65)], 20, "auto"),
            ColorCheckpoint(100, 1450, [(255, 197, 0)], 20, "auto"),
            ColorCheckpoint(450, 1450, [(0, 106, 186)], 20, "auto"),
            ColorCheckpoint(800, 1450, [(255, 197, 0)], 20, "auto"),
        ],
        min_matches=9,
    ),
    # auto_4 (aus 2 Screenshots)
    ScreenSignature(
        screen_type=SCREEN_MAPPING.get("auto_4", GameScreen.UNKNOWN),
        checkpoints=[
            ColorCheckpoint(100, 50, [(24, 82, 210)], 20, "auto"),
            ColorCheckpoint(450, 50, [(35, 20, 47)], 20, "auto"),
            ColorCheckpoint(800, 50, [(27, 12, 39)], 20, "auto"),
            ColorCheckpoint(100, 300, [(23, 73, 192)], 20, "auto"),
            ColorCheckpoint(450, 300, [(40, 147, 229)], 20, "auto"),
            ColorCheckpoint(800, 300, [(86, 106, 68)], 20, "auto"),
            ColorCheckpoint(100, 600, [(84, 84, 116)], 20, "auto"),
            ColorCheckpoint(450, 600, [(122, 112, 140)], 20, "auto"),
            ColorCheckpoint(800, 600, [(102, 85, 51)], 20, "auto"),
            ColorCheckpoint(100, 1000, [(255, 255, 255)], 20, "auto"),
            ColorCheckpoint(450, 1000, [(246, 233, 6)], 20, "auto"),
            ColorCheckpoint(800, 1000, [(246, 233, 6)], 20, "auto"),
            ColorCheckpoint(140, 1259, [(90, 56, 43)], 20, "auto"),
            ColorCheckpoint(450, 1259, [(255, 255, 255)], 20, "auto"),
            ColorCheckpoint(750, 1259, [(158, 171, 182)], 20, "auto"),
            ColorCheckpoint(100, 1450, [(138, 82, 65)], 20, "auto"),
            ColorCheckpoint(450, 1450, [(4, 4, 40)], 20, "auto"),
            ColorCheckpoint(800, 1450, [(138, 82, 65)], 20, "auto"),
        ],
        min_matches=9,
    ),
]