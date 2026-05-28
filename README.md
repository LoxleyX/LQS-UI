# LQS UI

Quest browser, content guide, and objective tracker addon for [LQS](https://github.com/LoxleyX/LQS) on [Ashita v4](https://ashitaxi.com/).

## Features

- **Quest Browser** — Browse all custom quests grouped by region with step-by-step objectives, required items, and rewards
- **Quest Tracker** — Floating HUD showing your tracked quest objective with a compass arrow pointing to your destination
- **Toast Notifications** — Quest Accepted / Quest Completed messages with fade effects
- **Plugin System** — Content-specific tabs with custom UI, auto-discovered from `plugins/`
- **Theme Support** — 5 themes (Default, Crystal, Ember, Forest, Midnight) switchable from Settings

### Included Plugins

- **Dailies** — Live tracking for Goblin Dailies and Storming Sea objectives via chat interception
- **Incursion** — Allied and Imperial incursion guide with phase details, boss info, and loot tables with drop rates
- **Dragonslaying** — Dragon fight guide with unique equipment, augment previews, and lore descriptions

## Installation

1. Copy the `lqs` folder into your Ashita `addons/` directory
2. In-game: `/addon load lqs`
3. Press **Ctrl+K** to toggle the quest panel

## Usage

| Input | Action |
|-------|--------|
| **Ctrl+K** | Toggle quest panel |
| `/lqs` | Toggle quest panel |
| `/lqs pos` | Copy current position to chat |

### Quest Tracking

1. Open the quest panel and click a quest
2. Click **Track** to pin it to the HUD tracker
3. A compass arrow appears when the objective is in your current zone
4. The tracker updates automatically as you progress

### Plugins

Plugins are Lua files in the `plugins/` directory. Each plugin adds a tab to the quest panel. See existing plugins for the format:

```lua
return {
    name   = 'My Plugin',
    order  = 10,
    render = function(state, ui, items)
        -- imgui rendering here
    end,
    init = function(items, ui)
        -- called once with shared utilities
    end,
};
```

## Export Scripts

Quest data and plugin content is generated from server Lua files. Run these after updating server content:

```bash
# Regenerate all data
bash scripts/export-all.sh

# Or individually
python3 scripts/export-quests.py
python3 scripts/export-incursion.py
python3 scripts/export-dragonslaying.py
```

Requires Python 3 and MySQL access to the game database for item name resolution.

## Server Requirements

Requires `lqs_ui.cpp` C++ module registered on the server (packet `0x1A5`). The server only sends quest step values — all metadata is client-side.

## License

Copyright (c) 2026 Loxley

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
