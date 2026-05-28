# Export script configuration
# Copy this file to config.py and edit paths for your environment.

import os

# Server source directory
SERVER_BASE = os.path.expanduser("~/dev/cexi/catseyexi")
LUA_BASE = os.path.join(SERVER_BASE, "modules/catseyexi/lua")

# Item enum files
ITEM_ENUM_FILE = os.path.join(SERVER_BASE, "scripts/enum/item.lua")
CEXI_ENUM_FILE = os.path.join(LUA_BASE, "enum/xi/item.lua")

# LSB network settings (for DB credentials)
LSB_SETTINGS = os.path.join(SERVER_BASE, "settings/network.lua")

# Quest files
QUEST_DIR = os.path.join(LUA_BASE, "additive_overrides/quests")

# Dragonslaying
DRAGON_DIR = os.path.join(LUA_BASE, "base/dragonslaying")
AUGMENT_DIR = os.path.join(LUA_BASE, "base/augments/dragonslaying")
DRAGON_LORE_FILE = os.path.join(LUA_BASE, "additive_overrides/quests/battle/lqs_the_dragonslayer.lua")

# Incursion
INCURSION_DIR = os.path.join(LUA_BASE, "base/crystal_warrior/allied_incursion")

# Output paths
OUTPUT_DIR = os.path.expanduser("~/dev/cexi/addons/lqs")
QUEST_OUTPUT = os.path.join(OUTPUT_DIR, "data/questdata.lua")
DRAGON_OUTPUT = os.path.join(OUTPUT_DIR, "plugins/dragonslaying.lua")
INCURSION_OUTPUT = os.path.join(OUTPUT_DIR, "plugins/incursion.lua")
