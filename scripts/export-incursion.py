#!/usr/bin/env python3
"""
Export Allied Incursion data from server Lua files into the LQS plugin.

Usage:
    python3 export-incursion.py

Generates: plugins/incursion.lua
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
INC_DIR = INCURSION_DIR
OUTPUT = INCURSION_OUTPUT

TIER_SECTIONS = {
    "t1":  {"section": "Allied Incursion - Beastmen Strongholds", "difficulty": 1, "order": 1},
    "alt": {"section": "Allied Incursion - Cave Expeditions",     "difficulty": 2, "order": 2},
    "t2":  {"section": "Allied Incursion - Stronghold Assault",   "difficulty": 3, "order": 3},
}

ZONE_NAMES = {
    "Fort_Ghelsba": "Fort Ghelsba",
    "Giddeus": "Giddeus",
    "Palborough_Mines": "Palborough Mines",
    "Dangruf_Wadi": "Dangruf Wadi",
    "Maze_of_Shakhrami": "Maze of Shakhrami",
    "Ordelles_Caves": "Ordelle's Caves",
    "Davoi": "Davoi",
    "Castle_Oztroja": "Castle Oztroja",
    "Beadeaux": "Beadeaux",
}

RATE_NAMES = {
    'GUARANTEED': 'Guaranteed', 'VERY_COMMON': 'Very Common',
    'COMMON': 'Common', 'UNCOMMON': 'Uncommon',
    'RARE': 'Rare', 'VERY_RARE': 'Very Rare',
}

# Item enum
_item_enum = {}

def load_item_enum():
    global _item_enum
    if _item_enum:
        return
    for path in [ITEM_ENUM_FILE, CEXI_ENUM_FILE]:
        if not os.path.isfile(path):
            continue
        with open(path) as f:
            for line in f:
                m = re.match(r'.*?(\w+)\s*=\s*(\d+)', line)
                if m and m.group(1) not in ('item', 'xi'):
                    _item_enum[m.group(1)] = int(m.group(2))

def resolve_item(ref):
    return _item_enum.get(ref)


def parse_loot_entries(text):
    """Parse { rate, itemId } pairs."""
    items = []
    seen = set()
    for m in re.finditer(r'cexi\.rate\.(\w+),\s*(\d{3,5})', text):
        rate = RATE_NAMES.get(m.group(1), m.group(1))
        item_id = int(m.group(2))
        if item_id >= 1000 and item_id not in seen:
            items.append({"id": item_id, "rate": rate})
            seen.add(item_id)
    # xi.item refs
    for m in re.finditer(r'cexi\.rate\.(\w+),\s*xi\.item\.(\w+)', text):
        rate = RATE_NAMES.get(m.group(1), m.group(1))
        resolved = resolve_item(m.group(2))
        if resolved and resolved not in seen:
            items.append({"id": resolved, "rate": rate})
            seen.add(resolved)
    return items


def parse_zone_file(filepath):
    """Parse a single incursion zone file."""
    with open(filepath) as f:
        text = f.read()

    area_m = re.search(r'area\s*=\s*"(\w+)"', text)
    area = area_m.group(1) if area_m else os.path.basename(filepath).replace(".lua", "")
    zone_name = ZONE_NAMES.get(area, area.replace("_", " "))

    exp_m = re.search(r'exp\s*=\s*(\d+)', text)
    gil_m = re.search(r'gil\s*=\s*(\d+)', text)

    # Currency and extra items
    currency = re.search(r'currency\s*=\s*xi\.item\.(\w+)', text)
    extra = re.search(r'extra\s*=\s*xi\.item\.(\w+)', text)
    currency_id = resolve_item(currency.group(1)) if currency else None
    extra_id = resolve_item(extra.group(1)) if extra else None

    # Parse phases
    phases = []
    phase_pattern = re.compile(r'\[(\d+)\]\s*=\s*\{(.*?)\n\s{8}\}', re.DOTALL)

    for pm in phase_pattern.finditer(text):
        phase_num = int(pm.group(1))
        body = pm.group(2)

        cap_m = re.search(r'cap\s*=\s*(\d+)', body)
        cap = int(cap_m.group(1)) if cap_m else 0

        # Mobs
        mob_section = body[:body.find('boss')] if 'boss' in body else body
        mob_names = re.findall(r'"(\w+)"', mob_section)
        mob_names = [m.replace("_", " ") for m in mob_names]
        mobs = [[name, 3] for name in mob_names]  # Default qty

        # Boss
        boss_name_m = re.search(r'boss\s*=\s*\{.*?name\s*=\s*"([^"]+)"', body, re.DOTALL)
        boss_lv_m = re.search(r'boss\s*=\s*\{.*?lv\s*=\s*(\d+)', body, re.DOTALL)

        # Boss loot
        boss_loot = []
        loot_match = re.search(r'boss\s*=\s*\{.*?loot\s*=\s*\{(.*?)\}', body, re.DOTALL)
        if loot_match:
            boss_loot = parse_loot_entries(loot_match.group(1))

        # Bonus
        bonus = None
        bonus_match = re.search(r'bonus\s*=\s*\{(.*?)\n\s{12}\}', body, re.DOTALL)
        if bonus_match:
            bb = bonus_match.group(1)
            bonus_mobs_m = re.search(r'mobs\s*=\s*\{\s*"(\w+)",\s*(\d+)', bb)
            bonus_boss_m = re.search(r'boss\s*=\s*\{.*?name\s*=\s*"([^"]+)"', bb, re.DOTALL)
            bonus_lv_m = re.search(r'boss\s*=\s*\{.*?lv\s*=\s*(\d+)', bb, re.DOTALL)

            bonus = {}
            if bonus_mobs_m:
                bonus["mobs"] = [[bonus_mobs_m.group(1).replace("_", " "), int(bonus_mobs_m.group(2))]]
            if bonus_boss_m:
                bonus["boss"] = {
                    "name": bonus_boss_m.group(1),
                    "lv": int(bonus_lv_m.group(1)) if bonus_lv_m else 0,
                }

        phase = {
            "cap": cap,
            "mobs": mobs,
            "boss": {
                "name": boss_name_m.group(1) if boss_name_m else "Unknown",
                "lv": int(boss_lv_m.group(1)) if boss_lv_m else 0,
                "loot": boss_loot,
            },
        }
        if bonus:
            phase["bonus"] = bonus
        phases.append(phase)

    # Mark last phase as final
    if phases:
        phases[-1]["boss"]["final"] = True

    # Case (chest) loot
    case_loot = []
    case_match = re.search(r'case\s*=\s*\{(.*?)\n\s{4}\}', text, re.DOTALL)
    if case_match:
        case_loot = parse_loot_entries(case_match.group(1))

    return {
        "name": zone_name,
        "exp": int(exp_m.group(1)) if exp_m else 0,
        "gil": int(gil_m.group(1)) if gil_m else 0,
        "currency_id": currency_id,
        "extra_id": extra_id,
        "phases": phases,
        "case_loot": case_loot,
    }


def lua_str(s):
    return s.replace("\\", "\\\\").replace("'", "\\'")


def generate_plugin(sections):
    lines = [
        "--[[",
        "* lqs/plugins/incursion.lua \xe2\x80\x94 Incursion content browser",
        "*",
        "* Auto-generated by scripts/export-incursion.py",
        "* Do not edit manually \xe2\x80\x94 re-run the script to update.",
        "]]--",
        "",
        "local imgui = require('imgui');",
        "local diff  = require('utils/difficulty');",
        "",
        "local ui    = nil;",
        "local items = nil;",
        "",
        "local RATE_COLORS = {",
        "    ['Guaranteed']  = { 1.00, 1.00, 1.00, 1.0 },",
        "    ['Very Common'] = { 0.55, 0.90, 0.55, 1.0 },",
        "    ['Common']      = { 0.55, 0.85, 1.00, 1.0 },",
        "    ['Uncommon']    = { 1.00, 0.92, 0.60, 1.0 },",
        "    ['Rare']        = { 1.00, 0.65, 0.40, 1.0 },",
        "    ['Very Rare']   = { 1.00, 0.45, 0.45, 1.0 },",
        "};",
        "",
        "local content = {",
    ]

    for tier_key in sorted(sections.keys(), key=lambda k: TIER_SECTIONS[k]["order"]):
        info = TIER_SECTIONS[tier_key]
        zones = sections[tier_key]

        lines.append(f"    {{")
        lines.append(f"        section    = '{lua_str(info['section'])}',")
        lines.append(f"        difficulty = {info['difficulty']},")
        lines.append(f"        instances  = {{")

        for z in zones:
            lines.append(f"            {{")
            lines.append(f"                name       = '{lua_str(z['name'])}',")
            lines.append(f"                difficulty = {info['difficulty']},")
            lines.append(f"                exp        = {z['exp']},")
            lines.append(f"                gil        = {z['gil']},")
            if z['currency_id']:
                lines.append(f"                currency   = {z['currency_id']},")
            if z['extra_id']:
                lines.append(f"                extra      = {z['extra_id']},")

            # Phases
            lines.append(f"                phases = {{")
            for pi, phase in enumerate(z['phases']):
                is_final = phase['boss'].get('final', False)
                lines.append(f"                    {{")
                lines.append(f"                        cap  = {phase['cap']},")

                # Mobs
                if phase['mobs']:
                    mob_strs = ", ".join(f"{{ '{lua_str(m[0])}', {m[1]} }}" for m in phase['mobs'])
                    lines.append(f"                        mobs = {{ {mob_strs} }},")
                else:
                    lines.append(f"                        mobs = {{}},")

                # Boss
                b = phase['boss']
                lines.append(f"                        boss = {{ name = '{lua_str(b['name'])}', lv = {b['lv']},")
                if b['loot']:
                    loot_strs = ", ".join(f"{{ id = {l['id']}, rate = '{l['rate']}' }}" for l in b['loot'])
                    lines.append(f"                            loot = {{ {loot_strs} }},")
                else:
                    lines.append(f"                            loot = {{}},")
                if is_final:
                    lines.append(f"                            final = true,")
                lines.append(f"                        }},")

                # Bonus
                if 'bonus' in phase:
                    bn = phase['bonus']
                    lines.append(f"                        bonus = {{")
                    if 'mobs' in bn:
                        bm_strs = ", ".join(f"{{ '{lua_str(m[0])}', {m[1]} }}" for m in bn['mobs'])
                        lines.append(f"                            mobs = {{ {bm_strs} }},")
                    if 'boss' in bn:
                        lines.append(f"                            boss = {{ name = '{lua_str(bn['boss']['name'])}', lv = {bn['boss']['lv']} }},")
                    lines.append(f"                        }},")

                lines.append(f"                    }},")
            lines.append(f"                }},")

            # Case loot
            if z['case_loot']:
                lines.append(f"                case_loot = {{")
                RATE_ORDER = {'Very Rare': 0, 'Rare': 1, 'Uncommon': 2, 'Common': 3, 'Very Common': 4, 'Guaranteed': 5}
                sorted_case = sorted(z['case_loot'], key=lambda x: RATE_ORDER.get(x['rate'], 99))
                for cl in sorted_case:
                    lines.append(f"                    {{ id = {cl['id']}, rate = '{cl['rate']}' }},")
                lines.append(f"                }},")

            lines.append(f"            }},")

        lines.append(f"        }},")
        lines.append(f"    }},")

    lines.append("};")
    lines.append("")
    lines.append(RENDER_CODE)
    return "\n".join(lines)


RENDER_CODE = r"""
local selectedInstance = nil;
local selectedPhase   = nil;

------------------------------------------------------------
-- Breadcrumb
------------------------------------------------------------
local function renderBreadcrumb()
    local parts = { 'Incursion' };
    if selectedInstance then table.insert(parts, selectedInstance.name); end
    if selectedPhase then table.insert(parts, string.format('Phase %d', selectedPhase)); end

    imgui.PushStyleColor(ImGuiCol_Button, { 0, 0, 0, 0 });
    imgui.PushStyleColor(ImGuiCol_ButtonHovered, { 0.3, 0.2, 0.4, 0.3 });
    imgui.PushStyleColor(ImGuiCol_ButtonActive, { 0.3, 0.2, 0.4, 0.5 });

    for i, part in ipairs(parts) do
        local isLast = (i == #parts);
        if not isLast then
            if imgui.SmallButton(part .. '##bc_' .. i) then
                if i == 1 then selectedInstance = nil; selectedPhase = nil;
                elseif i == 2 then selectedPhase = nil; end
            end
            imgui.SameLine(0, 4); ui.dim('>'); imgui.SameLine(0, 4);
        else
            imgui.TextColored(ui.color('white'), part);
        end
    end

    imgui.PopStyleColor(3);
    imgui.Separator();
    imgui.Spacing();
end

------------------------------------------------------------
-- Loot row with rate badge
------------------------------------------------------------
local function renderLootRow(lootEntry, idx)
    if items == nil or lootEntry == nil or lootEntry.id == nil or lootEntry.id == 0 then return; end
    local itemId = lootEntry.id;
    local rate = lootEntry.rate or '';

    local base = ui.color('childBg');
    local rowId = string.format('##incloot_%d_%d', itemId, idx);
    local lootBg = { base[1] + 0.02, base[2] + 0.02, base[3] + 0.04, 0.70 };

    imgui.PushStyleColor(ImGuiCol_ChildBg, lootBg);
    imgui.BeginChild(rowId, { -1, 32 }, false);

    imgui.SetCursorPos({ 6, 4 });
    if not items.renderIcon(itemId, 24) then imgui.Dummy({ 24, 24 }); end
    imgui.SameLine(0, 6);
    imgui.SetCursorPosY(8);
    imgui.TextColored(ui.color('white'), items.getName(itemId));

    if rate ~= '' then
        local dl = imgui.GetWindowDrawList();
        local wx, wy = imgui.GetWindowPos();
        local ww = imgui.GetWindowWidth();
        local rateColor = RATE_COLORS[rate] or ui.color('dimmed');
        local rateW = imgui.CalcTextSize(rate);
        local bgAlpha = imgui.GetColorU32({ rateColor[1] * 0.3, rateColor[2] * 0.3, rateColor[3] * 0.3, 0.5 });
        dl:AddRectFilled({ wx + ww - rateW - 16, wy + 7 }, { wx + ww - 4, wy + 23 }, bgAlpha, 3.0);
        dl:AddText({ wx + ww - rateW - 10, wy + 9 }, imgui.GetColorU32(rateColor), rate);
    end

    imgui.SetCursorPos({ 0, 0 });
    imgui.Selectable(string.format('##inclsel_%d_%d', itemId, idx), false,
        ImGuiSelectableFlags_SpanAllColumns, { 0, 32 });
    if imgui.IsItemHovered() then items.renderTooltip(itemId); end

    imgui.EndChild();
    imgui.PopStyleColor(1);
end

------------------------------------------------------------
-- Phase detail (Level 3)
------------------------------------------------------------
local function renderPhaseDetail()
    local phase = selectedInstance.phases[selectedPhase];
    if phase == nil then selectedPhase = nil; return; end

    imgui.BeginChild('##inc_phase_detail', { 0, -4 }, false);

    ui.colored(phase.boss.name, 'header');
    if phase.boss.final then
        imgui.SameLine(0, 8);
        imgui.TextColored(ui.color('accent'), '[BOSS]');
    end
    imgui.Spacing();

    ui.kv('Level:', tostring(phase.boss.lv), 'dimmed', 'yellow');
    ui.kv('Level Cap:', tostring(phase.cap), 'dimmed', 'yellow');

    -- Mobs
    local hasMobs = phase.mobs and #phase.mobs > 0;
    if hasMobs then
        imgui.Spacing();
        local names = {};
        local total = 0;
        for _, mob in ipairs(phase.mobs) do
            table.insert(names, mob[1]);
            total = total + mob[2];
        end
        ui.kv('Defeat:', string.format('%s (%d)', table.concat(names, ', '), total), 'dimmed', 'white');
    end

    -- Boss loot
    if phase.boss.loot and #phase.boss.loot > 0 then
        imgui.Spacing();
        ui.sectionHeader('Boss Loot', #phase.boss.loot);
        imgui.Spacing();
        for li, lootEntry in ipairs(phase.boss.loot) do
            renderLootRow(lootEntry, li);
        end
    end

    -- Bonus
    if phase.bonus then
        imgui.Spacing();
        ui.sectionHeader('Bonus Objective');
        imgui.Spacing();
        if phase.bonus.mobs and #phase.bonus.mobs > 0 then
            local bnames = {};
            local btotal = 0;
            for _, mob in ipairs(phase.bonus.mobs) do
                table.insert(bnames, mob[1]); btotal = btotal + mob[2];
            end
            ui.kv('Defeat:', string.format('%s (%d)', table.concat(bnames, ', '), btotal), 'dimmed', 'green');
        end
        if phase.bonus.boss then
            imgui.Spacing();
            ui.kv('Bonus Boss:', string.format('%s (Lv.%d)', phase.bonus.boss.name, phase.bonus.boss.lv), 'dimmed', 'accent');
        end
    end

    imgui.EndChild();
end

------------------------------------------------------------
-- Instance detail / phase list (Level 2)
------------------------------------------------------------
local function renderInstanceDetail()
    local inst = selectedInstance;

    imgui.BeginChild('##inc_inst_detail', { 0, -4 }, false);

    diff.renderKV(inst.difficulty, ui);
    ui.kv('Rewards:', string.format('%d EXP, %d Gil', inst.exp, inst.gil), 'dimmed', 'yellow');

    -- Currency + extra items
    if inst.currency and items then
        imgui.Spacing();
        ui.dim('Currency:');
        imgui.SameLine(0, 4);
        if items.renderIcon(inst.currency, 16) then imgui.SameLine(0, 4); end
        imgui.TextColored(ui.color('white'), items.getName(inst.currency));
    end

    imgui.Spacing();
    ui.sectionHeader('Phases', #inst.phases);
    imgui.Spacing();

    local base = ui.color('childBg');

    for pi, phase in ipairs(inst.phases) do
        local isFinal = phase.boss and phase.boss.final;
        local hasMobs = phase.mobs and #phase.mobs > 0;
        local hasBonus = phase.bonus ~= nil;
        local hasLoot = phase.boss.loot and #phase.boss.loot > 0;
        local rowHeight = hasMobs and 38 or 24;

        local rowId = string.format('##inc_phase_%d', pi);
        local isAlt = (pi % 2 == 0);
        local bgColor = isAlt
            and { base[1] + 0.02, base[2] + 0.02, base[3] + 0.04, 0.50 }
            or  { base[1], base[2], base[3], 0.30 };

        imgui.PushStyleColor(ImGuiCol_ChildBg, bgColor);
        imgui.BeginChild(rowId, { -1, rowHeight }, false);

        imgui.SetCursorPosY(0);
        local clicked = imgui.Selectable(
            string.format('##incpsel_%d', pi),
            false, ImGuiSelectableFlags_SpanAllColumns, { 0, rowHeight });

        local dl = imgui.GetWindowDrawList();
        local wx, wy = imgui.GetWindowPos();
        local ww = imgui.GetWindowWidth();

        local barColor = isFinal and ui.color('accent') or ui.color('dimmed');
        dl:AddRectFilled({ wx, wy }, { wx + 3, wy + rowHeight }, imgui.GetColorU32(barColor));

        local nameColor = isFinal and ui.color('accent') or ui.color('white');
        local title = string.format('Phase %d  -  %s (Lv.%d)  Cap:%d', pi, phase.boss.name, phase.boss.lv, phase.cap);
        dl:AddText({ wx + 10, wy + 3 }, imgui.GetColorU32(nameColor), title);

        -- Tags
        local rightX = wx + ww - 8;
        if hasBonus then
            local tag = 'BONUS';
            local tagW = imgui.CalcTextSize(tag);
            rightX = rightX - tagW - 12;
            dl:AddRectFilled({ rightX, wy + 2 }, { rightX + tagW + 8, wy + 16 },
                imgui.GetColorU32({ 0.20, 0.40, 0.20, 0.80 }), 3.0);
            dl:AddText({ rightX + 4, wy + 3 }, imgui.GetColorU32({ 0.40, 0.90, 0.40, 1.0 }), tag);
            rightX = rightX - 4;
        end
        if isFinal then
            local tag = 'BOSS';
            local tagW = imgui.CalcTextSize(tag);
            rightX = rightX - tagW - 12;
            dl:AddRectFilled({ rightX, wy + 2 }, { rightX + tagW + 8, wy + 16 },
                imgui.GetColorU32({ 0.50, 0.25, 0.60, 0.80 }), 3.0);
            dl:AddText({ rightX + 4, wy + 3 }, imgui.GetColorU32(ui.color('white')), tag);
        end

        -- Mobs
        if hasMobs then
            local names = {};
            local total = 0;
            for _, mob in ipairs(phase.mobs) do table.insert(names, mob[1]); total = total + mob[2]; end
            dl:AddText({ wx + 24, wy + 20 }, imgui.GetColorU32(ui.color('dimmed')),
                string.format('%s (%d)', table.concat(names, ', '), total));
        end

        imgui.EndChild();
        imgui.PopStyleColor(1);

        -- Loot icons below phase row
        if hasLoot then
            imgui.Indent(24);
            for li, lootEntry in ipairs(phase.boss.loot) do
                if lootEntry.id and lootEntry.id > 0 then
                    if li > 1 then imgui.SameLine(0, 4); end
                    if items and items.renderIcon(lootEntry.id, 20) then
                        if imgui.IsItemHovered() then items.renderTooltip(lootEntry.id); end
                    end
                end
            end
            imgui.Unindent(24);
        end

        if clicked then selectedPhase = pi; end
    end

    -- Case (chest) loot
    if inst.case_loot and #inst.case_loot > 0 then
        imgui.Spacing();
        ui.sectionHeader('Loot', #inst.case_loot);
        imgui.Spacing();
        for li, lootEntry in ipairs(inst.case_loot) do
            renderLootRow(lootEntry, 100 + li);
        end
    end

    imgui.EndChild();
end

------------------------------------------------------------
-- Instance list (Level 1)
------------------------------------------------------------
local function renderList()
    imgui.BeginChild('##inc_scroll', { 0, -4 }, false);

    for _, group in ipairs(content) do
        ui.sectionHeader(group.section, #group.instances);
        imgui.Spacing();

        for idx, inst in ipairs(group.instances) do
            local rowId = string.format('##inc_%s_%d', inst.name, idx);
            local base = ui.color('childBg');
            local isAlt = (idx % 2 == 0);
            local bgColor = isAlt
                and { base[1], base[2], base[3], 0.35 }
                or  { base[1], base[2], base[3], 0.20 };

            imgui.PushStyleColor(ImGuiCol_ChildBg, bgColor);
            imgui.BeginChild(rowId, { -1, 42 }, false);

            imgui.SetCursorPosY(0);
            local clicked = imgui.Selectable(
                string.format('##isel_%s_%d', inst.name, idx),
                false, ImGuiSelectableFlags_SpanAllColumns, { 0, 42 });

            local dl = imgui.GetWindowDrawList();
            local wx, wy = imgui.GetWindowPos();
            local ww = imgui.GetWindowWidth();

            dl:AddText({ wx + 8, wy + 4 }, imgui.GetColorU32(ui.color('white')), inst.name);

            local finalBoss = inst.phases[#inst.phases].boss.name;
            local subText = string.format('%s  (%d phases)', finalBoss, #inst.phases);
            dl:AddText({ wx + 8, wy + 22 }, imgui.GetColorU32(ui.color('dimmed')), subText);

            local dLabel, dColor = diff.get(inst.difficulty);
            local stW = imgui.CalcTextSize(dLabel);
            dl:AddText({ wx + ww - stW - 8, wy + 12 }, imgui.GetColorU32(dColor), dLabel);

            imgui.EndChild();
            imgui.PopStyleColor(1);

            if clicked then
                selectedInstance = inst;
                selectedPhase = nil;
            end
        end

        imgui.Spacing();
    end

    imgui.EndChild();
end

------------------------------------------------------------
-- Plugin definition
------------------------------------------------------------
return {
    name   = 'Incursion',
    order  = 10,
    render = function(state, uiLib, itemsLib)
        ui    = uiLib or ui;
        items = itemsLib or items;

        if selectedInstance then renderBreadcrumb(); end
        if selectedPhase then renderPhaseDetail();
        elseif selectedInstance then renderInstanceDetail();
        else renderList(); end
    end,
    init = function(itemsLib, uiLib)
        items = itemsLib;
        ui    = uiLib;
    end,
};
"""


def main():
    load_item_enum()
    print(f"Loaded {len(_item_enum)} item enum entries", file=sys.stderr)

    sections = {}
    for tier_dir in sorted(os.listdir(INC_DIR)):
        tier_path = os.path.join(INC_DIR, tier_dir)
        if not os.path.isdir(tier_path) or tier_dir not in TIER_SECTIONS:
            continue

        zones = []
        for lua_file in sorted(os.listdir(tier_path)):
            if not lua_file.endswith(".lua"):
                continue
            z = parse_zone_file(os.path.join(tier_path, lua_file))
            zones.append(z)

        if zones:
            sections[tier_dir] = zones

    content = generate_plugin(sections)

    with open(OUTPUT, 'w') as f:
        f.write(content)

    total_zones = sum(len(z) for z in sections.values())
    total_phases = sum(sum(len(z['phases']) for z in zones) for zones in sections.values())
    print(f"Exported {total_zones} zones, {total_phases} phases to {OUTPUT}", file=sys.stderr)
    for tier, zones in sorted(sections.items()):
        phase_count = sum(len(z['phases']) for z in zones)
        print(f"  {tier}: {len(zones)} zones, {phase_count} phases", file=sys.stderr)


if __name__ == "__main__":
    main()
