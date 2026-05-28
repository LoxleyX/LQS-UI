#!/usr/bin/env python3
"""
Export Dragonslaying data from server Lua files into the plugin data table.

Usage:
    python3 export-dragonslaying.py

Reads from:
    ~/dev/cexi/catseyexi/modules/catseyexi/lua/base/dragonslaying/
    ~/dev/cexi/catseyexi/modules/catseyexi/lua/base/augments/dragonslaying/
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
try:
    from config import *
except ImportError:
    from importlib.machinery import SourceFileLoader
    SourceFileLoader("config", os.path.join(os.path.dirname(__file__), "config.default.py")).load_module()
    from config import *

BASE = LUA_BASE
OUTPUT = DRAGON_OUTPUT
LORE_FILE = DRAGON_LORE_FILE

# Item enum for resolving xi.item references
_item_enum = {}

def load_item_enum():
    global _item_enum
    if _item_enum:
        return
    enum_files = [
        ITEM_ENUM_FILE,
        os.path.join(BASE, "enum/xi/item.lua"),
    ]
    for path in enum_files:
        if not os.path.isfile(path):
            continue
        with open(path) as f:
            for line in f:
                m = re.match(r'.*?(\w+)\s*=\s*(\d+)', line)
                if m and m.group(1) not in ('item', 'xi'):
                    _item_enum[m.group(1)] = int(m.group(2))
    print(f"Loaded {len(_item_enum)} item enum entries", file=sys.stderr)

def resolve_item(ref):
    return _item_enum.get(ref)

TIER_INFO = {
    "t1": {"section": "Tier 1 - Drakes", "difficulty": 3, "order": 1},        # Advanced
    "t2": {"section": "Tier 2 - Wyrms", "difficulty": 4, "order": 2},         # Expert
    "t3": {"section": "Tier 3 - Elder Wyrms", "difficulty": 5, "order": 3},   # Master
    "t4": {"section": "Tier 4 - Zilant", "difficulty": 6, "order": 4},        # Legendary
}

ZONE_NAMES = {
    "CRAWLERS_NEST": "Crawler's Nest",
    "IFRITS_CAULDRON": "Ifrit's Cauldron",
    "XARCABARD": "Xarcabard",
    "THE_ELDIEME_NECROPOLIS": "The Eldieme Necropolis",
    "PASHHOW_MARSHLANDS": "Pashhow Marshlands",
    "JUGNER_FOREST": "Jugner Forest",
    "MERIPHATAUD_MOUNTAINS": "Meriphataud Mountains",
    "BIBIKI_BAY": "Bibiki Bay",
    "WESTERN_ALTEPA_DESERT": "Western Altepa Desert",
    "BATALLIA_DOWNS": "Batallia Downs",
    "THE_SHRINE_OF_RUAVITAU": "The Shrine of Ru'Avitau",
    "PURGONORGO_ISLE": "Purgonorgo Isle",
}


RATE_NAMES = {
    'GUARANTEED': 'Guaranteed',
    'VERY_COMMON': 'Very Common',
    'COMMON': 'Common',
    'UNCOMMON': 'Uncommon',
    'RARE': 'Rare',
    'VERY_RARE': 'Very Rare',
    'SUPER_RARE': 'Super Rare',
    'ULTRA_RARE': 'Ultra Rare',
}


def parse_loot_entries(text):
    """Parse { rate, itemId } pairs from a loot table body."""
    items = {}  # itemId -> rate_name (keep best rate per item)
    for m in re.finditer(r'cexi\.rate\.(\w+),\s*(\d{3,5})', text):
        rate = RATE_NAMES.get(m.group(1), m.group(1))
        item_id = int(m.group(2))
        if item_id >= 1000 and item_id not in items:
            items[item_id] = rate
    # Also catch numeric rate entries: { 500, itemId }
    for m in re.finditer(r'\{\s*(\d{2,4}),\s*(\d{4,5})', text):
        rate_num = int(m.group(1))
        item_id = int(m.group(2))
        if item_id >= 1000 and item_id not in items:
            # Convert numeric rate to name
            if rate_num >= 240:
                items[item_id] = 'Very Common'
            elif rate_num >= 150:
                items[item_id] = 'Common'
            elif rate_num >= 100:
                items[item_id] = 'Uncommon'
            elif rate_num >= 50:
                items[item_id] = 'Rare'
            else:
                items[item_id] = 'Very Rare'
    return items


def parse_shared_pools():
    """Parse wyrmMats, wyrmTrash, upgradeMats from the dragonslayer quest file."""
    pools = {}
    quest_file = os.path.join(BASE, "additive_overrides/quests/battle/lqs_the_dragonslayer.lua")
    if not os.path.isfile(quest_file):
        return pools

    with open(quest_file) as f:
        text = f.read()

    for pool_name in ('wyrmMats', 'wyrmTrash', 'upgradeMats'):
        m = re.search(rf'local\s+{pool_name}\s*=\s*\{{(.*?)\n\}}', text, re.DOTALL)
        if m:
            pools[pool_name] = parse_loot_entries(m.group(1))

    return pools


# Shared loot pools (loaded once)
_shared_pools = {}


def parse_dragon_file(filepath):
    with open(filepath) as f:
        text = f.read()

    # Skip hidden/disabled dragons
    if re.search(r'hidden\s*=\s*true', text):
        return None

    name_m = re.search(r'name\s*=\s*"([^"]+)"', text)
    lv_m = re.search(r'lv\s*=\s*(\d+)', text)
    zone_m = re.search(r'zone\s*=\s*xi\.zone\.(\w+)', text)

    # Extract loot with drop rates
    loot_items = {}  # itemId -> rate_name

    # Find the MAIN loot table (the last one at indent level 4)
    loot_matches = list(re.finditer(r'^    loot\s*=\s*\{', text, re.MULTILINE))
    if loot_matches:
        start = loot_matches[-1].end()
        depth = 1
        i = start
        while i < len(text) and depth > 0:
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
            i += 1
        loot_body = text[start:i]

        # Parse rated entries
        loot_items.update(parse_loot_entries(loot_body))

        # Resolve string-referenced shared pools
        for pool_ref in re.findall(r'"(\w+)"', loot_body):
            if pool_ref in _shared_pools:
                for item_id, rate in _shared_pools[pool_ref].items():
                    if item_id not in loot_items:
                        loot_items[item_id] = rate

    return {
        "name": name_m.group(1) if name_m else os.path.basename(filepath).replace(".lua", "").replace("_", " ").title(),
        "lv": int(lv_m.group(1)) if lv_m else 0,
        "zone": ZONE_NAMES.get(zone_m.group(1), zone_m.group(1).replace("_", " ").title()) if zone_m else "Unknown",
        "loot": loot_items,  # { itemId: rate_name }
        "key": os.path.basename(filepath).replace(".lua", ""),
    }


def load_augment_names():
    """Load augment name enum for resolving augment IDs."""
    aug_path = os.path.join(BASE, "enum/cexi/augment_name.lua")
    names = {}
    if not os.path.isfile(aug_path):
        return names
    with open(aug_path) as f:
        for line in f:
            m = re.match(r'\s*\[(\d+)\]\s*=\s*"([^"]+)"', line)
            if m:
                names[int(m.group(1))] = m.group(2)
    return names


def format_augment(aug_id, value, aug_names):
    """Format a single augment pair into a display string."""
    name = aug_names.get(aug_id, f"Aug{aug_id}")
    m = re.search(r'([+-])(\d+)', name)
    if m:
        base = int(m.group(2))
        sign = m.group(1)
        total = base + value
        return re.sub(r'[+-]\d+', f'{sign}{total}', name, count=1)
    return name


def parse_augment_files():
    """Extract dragon → equipment item mappings with final tier augments."""
    load_item_enum()
    equipment = {}  # dragon_key -> [ { name, id, augments } ]
    aug_names = load_augment_names()

    for filename in sorted(os.listdir(AUGMENT_DIR)):
        if not filename.startswith("t") or not filename.endswith(".lua"):
            continue

        filepath = os.path.join(AUGMENT_DIR, filename)
        with open(filepath) as f:
            text = f.read()

        for dm in re.finditer(r'ds\.(\w+)\s*=\s*\{(.*?)\n\}', text, re.DOTALL):
            dragon_key = dm.group(1)
            if dragon_key not in equipment:
                equipment[dragon_key] = []

            for im in re.finditer(
                r'name\s*=\s*"([^"]+)".*?item\s*=\s*(xi\.item\.\w+|\d+).*?tier\s*=\s*\{(.*?)\n\s{8}\}',
                dm.group(2), re.DOTALL
            ):
                item_name = im.group(1)
                item_ref = im.group(2)
                if item_ref.startswith('xi.item.'):
                    item_id = resolve_item(item_ref.replace('xi.item.', ''))
                    if item_id is None:
                        print(f"  Warning: unresolved {item_ref} for {item_name}", file=sys.stderr)
                        continue
                else:
                    item_id = int(item_ref)
                tiers = im.group(3)

                # Get the LAST tier's augments (final upgrade)
                aug_entries = re.findall(r'augs\s*=\s*\{([^}]+)\}', tiers)
                aug_strs = []
                if aug_entries:
                    last = aug_entries[-1]
                    nums = [int(x.strip()) for x in last.split(',')]
                    for i in range(0, len(nums), 2):
                        if i + 1 < len(nums):
                            aug_strs.append(format_augment(nums[i], nums[i + 1], aug_names))

                equipment[dragon_key].append({
                    "name": item_name,
                    "id": item_id,
                    "augments": aug_strs,
                })

    return equipment


def parse_lore():
    """Extract dragon lore descriptions from the lore chapters."""
    lore = {}
    if not os.path.isfile(LORE_FILE):
        return lore

    with open(LORE_FILE) as f:
        text = f.read()

    # Find loreChapters table
    lore_section = re.search(r'loreChapters\s*=\s*\{(.*?)\n\}', text, re.DOTALL)
    if not lore_section:
        return lore

    body = lore_section.group(1)

    # Parse each chapter: { "Name", { "line1", "line2", ... } }
    for cm in re.finditer(r'\{\s*"([^"]+)",\s*\{(.*?)\},\s*\}', body, re.DOTALL):
        chapter_name = cm.group(1).strip()
        lines_raw = cm.group(2)

        # Extract string lines, skip the title line (starts with ~)
        lines = []
        for lm in re.findall(r'"([^"]+)"', lines_raw):
            lm = lm.strip()
            if lm.startswith('~'):
                continue
            lines.append(lm)

        if lines:
            # Join into a paragraph, collapse leading spaces (continuation lines)
            desc = ' '.join(lines)
            # Normalize whitespace
            desc = re.sub(r'\s+', ' ', desc).strip()

            # Map chapter name to dragon key
            key = chapter_name.lower().replace(' ', '_').replace("'", '').replace(',', '')
            # Also try direct name match
            lore[chapter_name.lower()] = desc
            lore[key] = desc

    return lore


def lua_str(s):
    return s.replace("\\", "\\\\").replace("'", "\\'")


def generate_plugin(tiers, equipment, lore={}):
    lines = [
        "--[[",
        "* lqs/plugins/dragonslaying.lua — Dragonslaying content browser",
        "*",
        "* Auto-generated by scripts/export-dragonslaying.py",
        "* Do not edit manually — re-run the script to update.",
        "]]--",
        "",
        "local imgui = require('imgui');",
        "",
        "local ui    = nil;",
        "local items = nil;",
        "",
        "local content = {",
    ]

    for tier_key in sorted(tiers.keys(), key=lambda k: TIER_INFO[k]["order"]):
        info = TIER_INFO[tier_key]
        dragons = tiers[tier_key]

        lines.append(f"    {{")
        lines.append(f"        section = '{lua_str(info['section'])}',")
        lines.append(f"        dragons = {{")

        for d in dragons:
            equip = equipment.get(d["key"], [])
            equip_ids = [e["id"] for e in equip]

            # Find lore for this dragon
            desc = ""
            dragon_name_lower = d["name"].lower()
            for lore_key, lore_text in lore.items():
                if dragon_name_lower in lore_key or lore_key in dragon_name_lower:
                    desc = lore_text
                    break

            lines.append(f"            {{")
            lines.append(f"                name       = '{lua_str(d['name'])}',")
            lines.append(f"                zone       = '{lua_str(d['zone'])}',")
            lines.append(f"                lv         = {d['lv']},")
            lines.append(f"                difficulty = {info['difficulty']},")
            if desc:
                lines.append(f"                description = '{lua_str(desc)}',")

            if d["loot"]:
                # Sort by rarity (rarest first)
                RATE_ORDER = {
                    'Ultra Rare': 0, 'Super Rare': 1, 'Very Rare': 2,
                    'Rare': 3, 'Uncommon': 4, 'Common': 5,
                    'Very Common': 6, 'Guaranteed': 7,
                }
                sorted_loot = sorted(d["loot"].items(), key=lambda x: RATE_ORDER.get(x[1], 99))
                lines.append(f"                loot       = {{")
                for item_id, rate in sorted_loot:
                    lines.append(f"                    {{ id = {item_id}, rate = '{rate}' }},")
                lines.append(f"                }},")
            else:
                lines.append(f"                loot       = {{}},")

            if equip:
                lines.append(f"                equipment  = {{")
                for e in equip:
                    aug_str = ""
                    if e["augments"]:
                        escaped = ", ".join(f"'{lua_str(a)}'" for a in e["augments"])
                        aug_str = f", augs = {{ {escaped} }}"
                    lines.append(f"                    {{ id = {e['id']}{aug_str} }},")
                lines.append(f"                }},")
            else:
                lines.append(f"                equipment  = {{}},")

            lines.append(f"            }},")

        lines.append(f"        }},")
        lines.append(f"    }},")

    lines.append("};")
    lines.append("")

    # Append the rest of the plugin (rendering code)
    lines.append(RENDER_CODE)

    return "\n".join(lines)


RENDER_CODE = r"""
local diff = require('utils/difficulty');

local selected = nil;

local function renderBreadcrumb()
    imgui.PushStyleColor(ImGuiCol_Button, { 0, 0, 0, 0 });
    imgui.PushStyleColor(ImGuiCol_ButtonHovered, { 0.3, 0.2, 0.4, 0.3 });
    imgui.PushStyleColor(ImGuiCol_ButtonActive, { 0.3, 0.2, 0.4, 0.5 });
    if imgui.SmallButton('Dragonslaying##bc') then
        selected = nil;
    end
    imgui.PopStyleColor(3);
    imgui.SameLine(0, 4);
    ui.dim('>');
    imgui.SameLine(0, 4);
    imgui.TextColored(ui.color('white'), selected.name);
    imgui.Separator();
    imgui.Spacing();
end

local function renderEquipItem(entry, idx)
    if items == nil or entry == nil or entry.id == nil then return; end
    local itemId = entry.id;
    local hasAugs = entry.augs and #entry.augs > 0;

    local res = items.getRes(itemId);
    local itemName = items.getName(itemId);
    local desc = '';
    if res and res.Description and res.Description[1] and res.Description[1] ~= '' then
        desc = res.Description[1];
    end

    local jobStr = '';
    local lvlStr = '';
    if res then
        local jobs = items.getJobList(res.Jobs);
        if jobs then jobStr = jobs; end
        if res.Level and res.Level > 0 then lvlStr = string.format('Lv.%d ', res.Level); end
    end
    local hasInfo = (jobStr ~= '' or lvlStr ~= '');

    -- Record start position
    local startY = imgui.GetCursorPosY();

    -- Icon + name
    imgui.SetCursorPosX(14);
    if items.renderIcon(itemId, 24) then
        imgui.SameLine(0, 6);
    else
        imgui.SameLine(38);
    end
    imgui.TextColored(ui.color('white'), itemName);

    -- Hover for tooltip (on the name — shows augments)
    if imgui.IsItemHovered() then items.renderTooltip(itemId, entry.augs); end

    imgui.Indent(14);

    -- Description with element dots
    if desc ~= '' then
        imgui.PushTextWrapPos(0);
        items.renderDescription(desc);
        imgui.PopTextWrapPos();
    end

    -- Jobs + Level
    if hasInfo then
        imgui.TextColored({ 0.55, 0.75, 0.55, 1.0 }, lvlStr .. jobStr);
    end

    imgui.Unindent(14);

    -- Draw background + accent bar retroactively
    local endY = imgui.GetCursorPosY();
    local dl = imgui.GetWindowDrawList();
    local wx, wy = imgui.GetWindowPos();
    local ww = imgui.GetWindowWidth();
    local scrollY = imgui.GetScrollY();
    local topY = wy + startY - scrollY;
    local botY = wy + endY - scrollY;

    local base = ui.color('childBg');
    local bgColor = (idx % 2 == 0)
        and imgui.GetColorU32({ base[1] + 0.06, base[2] + 0.05, base[3] + 0.08, 0.45 })
        or  imgui.GetColorU32({ base[1] + 0.02, base[2] + 0.02, base[3] + 0.03, 0.25 });
    dl:AddRectFilled({ wx, topY }, { wx + ww, botY }, bgColor);
    dl:AddRectFilled({ wx, topY }, { wx + 3, botY }, imgui.GetColorU32(ui.color('accent')));

    -- Invisible selectable over the whole row for tooltip
    imgui.SetCursorPosY(startY);
    imgui.Selectable(string.format('##eqhover_%d_%d', itemId, idx), false,
        ImGuiSelectableFlags_AllowItemOverlap, { 0, endY - startY });
    if imgui.IsItemHovered() then items.renderTooltip(itemId, entry.augs); end

    imgui.Separator();
    imgui.Spacing();
end

local function renderDetail()
    local d = selected;

    imgui.BeginChild('##ds_detail', { 0, -4 }, false);

    ui.colored(d.name, 'header');
    imgui.Spacing();
    ui.kv('Zone:', d.zone, 'dimmed', 'blue');
    ui.kv('Level:', tostring(d.lv), 'dimmed', 'yellow');
    diff.renderKV(d.difficulty, ui);
    imgui.Spacing();

    -- Description
    if d.description and d.description ~= '' then
        imgui.PushTextWrapPos(0);
        imgui.TextColored(ui.color('desc'), d.description);
        imgui.PopTextWrapPos();
        imgui.Spacing();
    end

    -- Unique equipment
    if d.equipment and #d.equipment > 0 then
        ui.sectionHeader('Unique Equipment', #d.equipment);
        imgui.Spacing();
        for ei, entry in ipairs(d.equipment) do
            renderEquipItem(entry, ei);
        end
        imgui.Spacing();
    end

    -- General loot (exclude equipment IDs)
    if d.loot and #d.loot > 0 then
        -- Build set of equipment IDs to exclude
        local equipIds = {};
        if d.equipment then
            for _, entry in ipairs(d.equipment) do
                equipIds[entry.id] = true;
            end
        end

        local filteredLoot = {};
        for _, lootEntry in ipairs(d.loot) do
            if not equipIds[lootEntry.id] then
                table.insert(filteredLoot, lootEntry);
            end
        end

        if #filteredLoot > 0 then
            ui.sectionHeader('Loot', #filteredLoot);
            imgui.Spacing();

            local RATE_COLORS = {
                ['Guaranteed']  = { 1.00, 1.00, 1.00, 1.0 },
                ['Very Common'] = { 0.55, 0.90, 0.55, 1.0 },
                ['Common']      = { 0.55, 0.85, 1.00, 1.0 },
                ['Uncommon']    = { 1.00, 0.92, 0.60, 1.0 },
                ['Rare']        = { 1.00, 0.65, 0.40, 1.0 },
                ['Very Rare']   = { 1.00, 0.45, 0.45, 1.0 },
                ['Super Rare']  = { 0.75, 0.45, 1.00, 1.0 },
                ['Ultra Rare']  = { 0.75, 0.45, 1.00, 1.0 },
            };

            local lootBase = ui.color('childBg');
            for li, lootEntry in ipairs(filteredLoot) do
                local itemId = lootEntry.id;
                local rate = lootEntry.rate or '';
                local lootId = string.format('##dsloot_g_%d_%d', itemId, li);
                local lootBg = { lootBase[1] + 0.02, lootBase[2] + 0.02, lootBase[3] + 0.04, 0.70 };
                imgui.PushStyleColor(ImGuiCol_ChildBg, lootBg);
                imgui.BeginChild(lootId, { -1, 32 }, false);

                imgui.SetCursorPos({ 6, 4 });
                if not items.renderIcon(itemId, 24) then imgui.Dummy({ 24, 24 }); end
                imgui.SameLine(0, 6);
                imgui.SetCursorPosY(8);
                imgui.TextColored(ui.color('white'), items.getName(itemId));

                -- Rate badge on right
                if rate ~= '' then
                    local dl = imgui.GetWindowDrawList();
                    local wx, wy = imgui.GetWindowPos();
                    local ww = imgui.GetWindowWidth();
                    local rateColor = RATE_COLORS[rate] or ui.color('dimmed');
                    local rateW = imgui.CalcTextSize(rate);
                    local bgAlpha = imgui.GetColorU32({ rateColor[1] * 0.3, rateColor[2] * 0.3, rateColor[3] * 0.3, 0.5 });
                    dl:AddRectFilled(
                        { wx + ww - rateW - 16, wy + 7 },
                        { wx + ww - 4, wy + 23 },
                        bgAlpha, 3.0);
                    dl:AddText(
                        { wx + ww - rateW - 10, wy + 9 },
                        imgui.GetColorU32(rateColor), rate);
                end

                imgui.SetCursorPos({ 0, 0 });
                imgui.Selectable(string.format('##dlsel_g_%d_%d', itemId, li), false,
                    ImGuiSelectableFlags_SpanAllColumns, { 0, 32 });
                if imgui.IsItemHovered() then items.renderTooltip(itemId); end
                imgui.EndChild();
                imgui.PopStyleColor(1);
            end
            imgui.Spacing();
        end
    end

    imgui.EndChild();
end

local function renderList()
    imgui.BeginChild('##ds_scroll', { 0, -4 }, false);

    for _, group in ipairs(content) do
        ui.sectionHeader(group.section, #group.dragons);
        imgui.Spacing();

        for idx, dragon in ipairs(group.dragons) do
            local rowId = string.format('##ds_%s_%d', dragon.name, idx);
            local base = ui.color('childBg');
            local isAlt = (idx % 2 == 0);
            local bgColor = isAlt
                and { base[1], base[2], base[3], 0.35 }
                or  { base[1], base[2], base[3], 0.20 };

            imgui.PushStyleColor(ImGuiCol_ChildBg, bgColor);
            imgui.BeginChild(rowId, { -1, 42 }, false);

            imgui.SetCursorPosY(0);
            local clicked = imgui.Selectable(
                string.format('##dsel_%s_%d', dragon.name, idx),
                false, ImGuiSelectableFlags_SpanAllColumns, { 0, 42 });

            local dl = imgui.GetWindowDrawList();
            local wx, wy = imgui.GetWindowPos();
            local ww = imgui.GetWindowWidth();

            dl:AddText({ wx + 8, wy + 4 },
                imgui.GetColorU32(ui.color('white')), dragon.name);

            local subText = string.format('Lv.%d  %s', dragon.lv, dragon.zone);
            dl:AddText({ wx + 8, wy + 22 },
                imgui.GetColorU32(ui.color('dimmed')), subText);

            local dLabel, dColor = diff.get(dragon.difficulty);
            local stW = imgui.CalcTextSize(dLabel);
            dl:AddText({ wx + ww - stW - 8, wy + 4 },
                imgui.GetColorU32(dColor), dLabel);

            -- Equipment preview icons on right side
            if dragon.equipment and #dragon.equipment > 0 and items then
                local iconX = wx + ww - 8;
                for ei = #dragon.equipment, 1, -1 do
                    iconX = iconX - 22;
                end
                imgui.SetCursorPos({ iconX - wx + 1, 22 });
                for ei, entry in ipairs(dragon.equipment) do
                    if ei > 1 then imgui.SameLine(0, 2); end
                    if items.renderIcon(entry.id, 18) then
                        if imgui.IsItemHovered() then items.renderTooltip(entry.id); end
                    end
                end
            end

            imgui.EndChild();
            imgui.PopStyleColor(1);

            if clicked then selected = dragon; end
        end

        imgui.Spacing();
    end

    imgui.EndChild();
end

return {
    name   = 'Dragonslaying',
    order  = 20,
    render = function(state, uiLib, itemsLib)
        ui    = uiLib or ui;
        items = itemsLib or items;
        if selected then renderBreadcrumb(); renderDetail(); else renderList(); end
    end,
    init = function(itemsLib, uiLib)
        items = itemsLib;
        ui    = uiLib;
    end,
};
"""


def main():
    # Load shared loot pools
    global _shared_pools
    _shared_pools = parse_shared_pools()
    print(f"Loaded {len(_shared_pools)} shared loot pools ({sum(len(v) for v in _shared_pools.values())} items)", file=sys.stderr)

    # Parse dragon files
    tiers = {}
    for tier_dir in sorted(os.listdir(DRAGON_DIR)):
        tier_path = os.path.join(DRAGON_DIR, tier_dir)
        if not os.path.isdir(tier_path) or tier_dir not in TIER_INFO:
            continue

        dragons = []
        for lua_file in sorted(os.listdir(tier_path)):
            if not lua_file.endswith(".lua"):
                continue
            d = parse_dragon_file(os.path.join(tier_path, lua_file))
            if d is not None:
                dragons.append(d)

        if dragons:
            tiers[tier_dir] = dragons

    # Parse equipment
    equipment = parse_augment_files()

    # Parse lore
    lore = parse_lore()
    print(f"Found {len(lore)} lore entries", file=sys.stderr)

    # Generate plugin
    content = generate_plugin(tiers, equipment, lore)

    with open(OUTPUT, 'w') as f:
        f.write(content)

    total_dragons = sum(len(d) for d in tiers.values())
    total_equip = sum(len(e) for e in equipment.values())
    print(f"Exported {total_dragons} dragons, {total_equip} equipment items to {OUTPUT}", file=sys.stderr)
    for tier, dragons in sorted(tiers.items()):
        equip_count = sum(len(equipment.get(d["key"], [])) for d in dragons)
        print(f"  {tier}: {len(dragons)} dragons, {equip_count} equipment", file=sys.stderr)


if __name__ == "__main__":
    main()
