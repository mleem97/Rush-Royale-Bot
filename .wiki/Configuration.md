# Configuration

The bot is configured via `config.ini` in the project root.

## Configuration File Structure

```ini
[bot]
floor = 4
mana_level = 1,3,5
units = chemist, harlequin, bombardier, dryad, demon_hunter
dps_unit = demon_hunter
pve = True
require_shaman = False
unit_update = False
```

## Settings Reference

### `floor` (integer)
The dungeon floor to play in PvE mode.

| Value | Description |
|-------|-------------|
| 1-14 | Dungeon floor number |

**Example**: `floor = 7`

### `mana_level` (comma-separated integers)
Which mana upgrade buttons to click during combat.

| Value | Card Position |
|-------|---------------|
| 1 | First card (leftmost) |
| 2 | Second card |
| 3 | Third card |
| 4 | Fourth card |
| 5 | Fifth card (rightmost) |

**Example**: `mana_level = 1,3,5` (upgrade cards 1, 3, and 5)

### `units` (comma-separated strings)
The five units in your deck. Names must match files in `cv-images/all_units/`.

**Available Units**:
- Common: `bombardier`, `frost`, `pyro`, `thunder`, `cold_elemental`, etc.
- Rare: `mime`, `portal_keeper`, `shaman`, `witch`, etc.
- Legendary: `demon_hunter`, `dryad`, `harlequin`, `knight_statue`, etc.

**Example**: `units = chemist, harlequin, bombardier, dryad, demon_hunter`

### `dps_unit` (string)
The main damage-dealing unit to prioritize for merging.

**Example**: `dps_unit = demon_hunter`

### `pve` (boolean)
Whether to play PvE (dungeon) or PvP mode.

| Value | Mode |
|-------|------|
| True | PvE Dungeon |
| False | PvP Arena |

### `require_shaman` (boolean)
Wait for opponent to place Shaman before starting combat (PvP strategy).

### `unit_update` (boolean)
Enable missing unit capture mode instead of normal gameplay.

When enabled, the bot enters an interactive mode to capture screenshots of units you don't have templates for.

## GUI Configuration

Most settings can also be adjusted via the GUI:

- **PvE Checkbox**: Toggle PvE/PvP mode
- **Unit Update Checkbox**: Enable unit capture mode
- **Mana Level Targets**: Checkboxes for cards 1-5
- **Dungeon Floor**: Text entry for floor number

Settings are saved to `config.ini` when you click "Start Bot".

## Valid Unit Names

Unit names must match files in `cv-images/all_units/` (without `.png`):

```
banshee          demon_hunter     knight_statue    scrapper
blade_dancer     earth_elemental  kobold          sea_dog
bombardier       engineer         meteor          sentry
catapult         executioner      mime            shaman
clock            frost            portal_keeper   spirit_master
clown            gargoyle         portal_mage     summoner
cold_elemental   genie            pyro            thunder
corsair          gunslinger       reaper          time_keeper
crystal          ivy              twilight_ranger twins1/twins2
                                                  vampire/witch
```

## Example Configurations

### Speed Farm Deck
```ini
[bot]
floor = 5
mana_level = 1,3
units = harlequin, dryad, chemist, bombardier, demon_hunter
dps_unit = demon_hunter
pve = True
```

### High Floor Push
```ini
[bot]
floor = 10
mana_level = 1,2,3,4,5
units = harlequin, dryad, shaman, knight_statue, demon_hunter
dps_unit = demon_hunter
pve = True
```
