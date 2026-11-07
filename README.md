# Mojow Shaman Extended Targets & Healing

A WoW Forever addon for shaman click healing, extended target lists, and party/raid member tracking, by Mojow.

This release preserves the original narrow, vertical windows from **0.9.44-test**, including the incoming-heal texture fix. It predates the later landscape window, scale slider, and 25-person raid grid.

**[Download the install-ready ZIP](https://github.com/Mojowjoejoe/Mojow-Shaman-Extended-Targets/releases/latest/download/MojowAssist-v0.9.44-classic-layout.zip)** ? [All releases](https://github.com/Mojowjoejoe/Mojow-Shaman-Extended-Targets/releases)

## Install

1. Download the ZIP linked above. GitHub's automatic source archives are for developers.
2. Extract the **MojowAssist** folder into your WoW Forever installation's `Interface/AddOns/` directory.
3. Confirm the result is `Interface/AddOns/MojowAssist/MojowAssist.toc`, without an extra nested folder.
4. Enable Mojow Assist in the character-selection AddOns menu, then log in on your shaman. Use `/reload` if already logged in.
5. Type `/mja` for Settings, or right-click the minimap icon for window controls and unit filters.

For an existing MojowAssist installation, back up its addon folder and saved settings before replacing the addon folder. This package uses the same addon name and saved-variable name as other MojowAssist versions; install one version at a time. It does not include or erase your saved settings.

## Included

- Vertical Extended Targets window for focus target, NPCs, enemy players, and nearby friendly players.
- Separate Group Members window using party/raid units, even when nameplates are off. Long lists scroll outside combat; this version does not display all 25 raid members at once.
- Configurable shaman primary and secondary healing clicks, with range/status information and readable dispel cues.
- Incoming-heal display when the client provides prediction data: a green segment and a numeric estimate when readable, capped at missing health. Live prediction behavior remains experimental.
- Class-colored player names, health bars, raid markers, and optional native nameplate styling with class/level badges.
- Owner-side pet bars. Stable party/raid pet references support click healing; other discovered pets may be display-only.
- Compact raid-marker bar, totem controls, shield selection, and Ghost Wolf button.

This is a standalone addon. DogHouse, HealBot, and external software are not required. Questie icons are used only when Questie exposes the relevant data.

## Healing clicks

| Input on a friendly row | Action |
| --- | --- |
| Left click | Primary heal, normally Healing Wave when learned |
| Right click | Secondary/light heal, normally Lesser Healing Wave when learned |
| Shift + right click | Unit menu where a supported unit reference is available |

Use `/mja heals` to choose learned spells. Saved selections can override defaults. Each heal requires your click; there is no automatic healing. Group-row primary healing can also change your target. Nearby ungrouped healing may use a name-based targeting macro, which changes your target and can be ambiguous when names match. Check the tooltip and target before casting.

## Useful commands

| Command | Purpose |
| --- | --- |
| `/mja` | Settings |
| `/mja heals` | Choose healing clicks |
| `/mja attacks` | Choose hostile-row click spells |
| `/mja enemies` / `/mja enemies hide` | Show/hide Extended Targets |
| `/mja groupwindow` / `/mja groupwindow hide` | Show/hide Group Members |
| `/mja enemies reset` | Reset Extended Targets position |
| `/mja groupwindow reset` | Reset Group Members position |
| `/mja marks` / `/mja marks hide` | Show/hide the raid-marker bar |
| `/mja visibility` | Nameplate and tracking controls |
| `/mja plates on` | Apply the optional nameplate preset and badges |
| `/mja plates restore` | Restore recorded prior nameplate settings |
| `/mja totems` | Totem controls |
| `/mja debug` | Build and diagnostic information |

## Compatibility and limits

Built for **WoW Forever, Interface 16001**. Other WoW editions are not verified. Client patches can change addon behavior.

Nearby strangers and NPCs generally require observable nameplate, target, or focus unit references. Normal floating names alone do not provide a full nearby-unit list. Group roster entries are independent of nameplates. In combat, clickable row membership stays fixed; new entries and scrolling wait until combat ends. Unknown/restricted data is not treated as confirmed health, range, or dispel information.

Only learned abilities are available, and normal range, line-of-sight, mana, cooldown, and raid-marker permissions still apply. Find Minerals defaults on when learned and can be disabled in Nameplates / tracking. Nameplate styling is optional and changes native game settings when explicitly applied.

**Validation:** 393 Lua fixture checks pass, including the healing texture regression. These checks do not emulate WoW's secure execution or prove live casting, rendering, or compatibility after a patch. Report issues with `/mja debug` output and reproduction steps; omit private account information.

## Development

Runtime files are in `MojowAssist/`; their bytes match the archived pre-landscape 0.9.44 build. Packaging and documentation are separate from runtime code.

With Python and the `lupa` package installed:

```text
python MojowAssist/tests/run_checks.py
python tools/package.py
```

The package script writes the install-ready ZIP and SHA-256 checksum to `dist/`. Tests, local settings, and development notes are excluded from the ZIP.
