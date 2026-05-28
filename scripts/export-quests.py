#!/usr/bin/env python3
"""
Export LQS quest data from server Lua files into a client-side questdata.lua.

Parses quest info tables and step structures to extract static metadata.
The generated file is loaded by the LQS addon instead of requesting data
from the server.

Usage:
    python3 export-quests.py [quest_dir] [output_file]

Defaults:
    quest_dir:   ~/dev/cexi/catseyexi/modules/catseyexi/lua/additive_overrides/quests/
    output_file: ~/dev/cexi/addons/lqs/data/questdata.lua
"""

import os
import re
import sys
import glob

sys.path.insert(0, os.path.dirname(__file__))
try:
    from config import *
except ImportError:
    from importlib.machinery import SourceFileLoader
    SourceFileLoader("config", os.path.join(os.path.dirname(__file__), "config.default.py")).load_module()
    from config import *

DEFAULT_QUEST_DIR = QUEST_DIR
DEFAULT_OUTPUT = QUEST_OUTPUT


def read_db_config():
    """Read SQL credentials from LSB settings/network.lua."""
    config = {'host': '127.0.0.1', 'port': 3306, 'user': 'xi', 'password': '', 'database': 'xidb'}
    if not os.path.isfile(LSB_SETTINGS):
        return config
    with open(LSB_SETTINGS) as f:
        text = f.read()
    for key, lua_key in [('host', 'SQL_HOST'), ('user', 'SQL_LOGIN'),
                          ('password', 'SQL_PASSWORD'), ('database', 'SQL_DATABASE')]:
        m = re.search(rf"{lua_key}\s*=\s*['\"]([^'\"]+)['\"]", text)
        if m:
            config[key] = m.group(1)
    port_m = re.search(r'SQL_PORT\s*=\s*(\d+)', text)
    if port_m:
        config['port'] = int(port_m.group(1))
    return config

# Load xi.item enum for resolving references
_item_enum = {}
def load_item_enum():
    global _item_enum
    if _item_enum:
        return
    if not os.path.isfile(ITEM_ENUM_FILE):
        print(f"Warning: {ITEM_ENUM_FILE} not found, xi.item refs won't resolve", file=sys.stderr)
        return
    with open(ITEM_ENUM_FILE) as f:
        for line in f:
            m = re.match(r'\s+(\w+)\s*=\s*(\d+)', line)
            if m:
                _item_enum[m.group(1)] = int(m.group(2))
    print(f"Loaded {len(_item_enum)} item enum entries", file=sys.stderr)

def resolve_item(ref):
    """Resolve xi.item.NAME to numeric ID."""
    if ref in _item_enum:
        return _item_enum[ref]
    return None


# Item name cache (from database)
_item_names = {}

def load_item_names():
    """Load item names from the database."""
    global _item_names
    if _item_names:
        return
    import subprocess
    db = read_db_config()
    try:
        result = subprocess.run(
            ['mysql', '-u', db['user'], f"-p{db['password']}", db['database'],
             '-h', db['host'], '-N', '-e',
             'SELECT itemid, name FROM item_basic'],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) == 2:
                item_id = int(parts[0])
                name = parts[1].replace('_', ' ').title()
                # Clean up common prefixes
                for prefix in ('Handful Of ', 'Piece Of ', 'Chunk Of ', 'Pinch Of ',
                               'Sack Of ', 'Bag Of ', 'Bolt Of ', 'Sheet Of ',
                               'Square Of ', 'Serving Of '):
                    if name.startswith(prefix):
                        name = name[len(prefix):]
                        break
                _item_names[item_id] = name
        print(f"Loaded {len(_item_names)} item names from database", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Could not load item names: {e}", file=sys.stderr)


def get_item_name(item_id):
    """Get display name for an item ID."""
    if item_id in _item_names:
        return _item_names[item_id]
    return f"Item {item_id}"


REGION_NAMES = {
    'bastok': "Bastok",
    'sandoria': "San d'Oria",
    'windurst': "Windurst",
    'jeuno': "Jeuno",
    'aht_urhgan': "Aht Urhgan",
    'other_areas': "Other Areas",
    'outlands': "Outlands",
    'battle': "Battle",
    'questpack/bastok': "Bastok",
    'questpack/sandoria': "San d'Oria",
    'questpack/windurst': "Windurst",
    'questpack/aht_urhgan': "Aht Urhgan",
    'questpack/other_areas': "Other Areas",
}

REGION_TINTS = {
    "Bastok": { 0.12, 0.14, 0.22 },
    "San d'Oria": { 0.20, 0.12, 0.12 },
    "Windurst": { 0.12, 0.18, 0.12 },
    "Jeuno": { 0.20, 0.18, 0.10 },
    "Aht Urhgan": { 0.18, 0.15, 0.10 },
    "Other Areas": { 0.14, 0.14, 0.16 },
    "Battle": { 0.18, 0.10, 0.10 },
    "Outlands": { 0.14, 0.16, 0.14 },
}


def parse_quest_file(filepath):
    """Extract quest metadata from an LQS quest file."""
    with open(filepath) as f:
        text = f.read()

    # Only process files that use LQS.add
    if 'LQS.add' not in text:
        return None

    # Extract info fields
    name = re.search(r'name\s*=\s*"([^"]+)"', text)
    if not name:
        return None

    author = re.search(r'author\s*=\s*"([^"]+)"', text)
    quest_var = re.search(r'var\s*=\s*"([^"]+)"', text)
    category = re.search(r'category\s*=\s*"([^"]+)"', text)
    subcategory = re.search(r'subcategory\s*=\s*"([^"]+)"', text)
    hidden = re.search(r'hidden\s*=\s*true', text)

    if hidden:
        return None

    # Parse required items from info table
    required_items = []
    # Format 1: required = { { itemId, qty } }
    for m in re.finditer(r'required\s*=\s*\{\s*\{\s*(\d+)\s*,\s*(\d+)\s*\}', text):
        required_items.append({"id": int(m.group(1)), "qty": int(m.group(2))})
    # Format 2: required = { item = { { itemId, qty } } }
    if not required_items:
        for m in re.finditer(r'required\s*=\s*\{[^}]*item\s*=\s*\{\s*\{\s*(\d+)\s*,\s*(\d+)\s*\}', text, re.DOTALL):
            required_items.append({"id": int(m.group(1)), "qty": int(m.group(2))})
    # Format 3: required = itemId (single numeric)
    if not required_items:
        m = re.search(r'^\s+required\s*=\s*(\d{3,5})\s*,', text, re.MULTILINE)
        if m:
            required_items.append({"id": int(m.group(1)), "qty": 1})
    # Format 4: required = xi.item.X
    if not required_items:
        m = re.search(r'^\s+required\s*=\s*xi\.item\.(\w+)', text, re.MULTILINE)
        if m:
            resolved = resolve_item(m.group(1))
            if resolved:
                required_items.append({"id": resolved, "qty": 1})

    # Count steps — only look at steps[N] assignments, not other tables
    step_count = 1
    steps_indices = re.findall(r'steps\s*\[(\d+)\]', text)
    if steps_indices:
        step_count = max(int(x) for x in steps_indices)
    else:
        # Fallback: count LQS handler calls (rough estimate, capped)
        handler_count = text.count('LQS.dialog(') + text.count('LQS.trade(') + text.count('LQS.defeat(')
        if handler_count > 0:
            step_count = min(handler_count, 20)

    # Build entity map: variable_name -> { display_name, zone, pos }
    # First, collect all local variable → string mappings
    local_vars = {}
    for m in re.finditer(r'local\s+(\w+)\s*=\s*"([^"]+)"', text):
        local_vars[m.group(1)] = m.group(2)

    # Parse entities block: zone → entities with names and positions
    entity_data = {}  # display_name -> { zone, pos }
    entities_section = re.search(r'entities\s*=\s*\{(.*?)\n\s{4}\},', text, re.DOTALL)
    if entities_section:
        for zm in re.finditer(r'\["(\w+)"\]\s*=\s*\{(.*?)\n\s{8}\},', entities_section.group(1), re.DOTALL):
            zone_name = zm.group(1).replace("_", " ")
            zone_body = zm.group(2)
            for em in re.finditer(r'name\s*=\s*(\w+|"[^"]+").*?pos\s*=\s*\{\s*([^}]+)\}', zone_body, re.DOTALL):
                raw_name = em.group(1)
                if raw_name.startswith('"'):
                    var_name = raw_name.strip('"')
                    display_name = var_name
                else:
                    var_name = raw_name
                    display_name = local_vars.get(var_name, var_name.replace("_", " "))
                pos_str = em.group(2).split('--')[0].strip().rstrip(',')
                pos_parts = [p.strip() for p in pos_str.split(',')]
                pos = None
                if len(pos_parts) >= 3:
                    try:
                        pos = [float(pos_parts[0]), float(pos_parts[1]), float(pos_parts[2])]
                    except ValueError:
                        pass
                # Detect entity type from block between previous { and this match
                entity_block_start = zone_body.rfind('{', 0, em.start())
                entity_block = zone_body[entity_block_start:em.end()] if entity_block_start >= 0 else ''
                is_mob = 'objType.MOB' in entity_block
                is_npc = 'LQS.look(' in entity_block
                is_object = not is_mob and not is_npc
                entity_data[display_name] = {"zone": zone_name, "pos": pos, "mob": is_mob, "object": is_object}
                entity_data[var_name] = {"zone": zone_name, "pos": pos, "mob": is_mob, "object": is_object}

    # Parse steps: one per top-level block in steps = { {}, {}, {} }
    steps = []
    steps_section = re.search(r'steps\s*=\s*\{(.*)', text, re.DOTALL)
    if steps_section:
        step_body = steps_section.group(1)
        # Split on top-level step blocks (indent 8)
        step_entries = re.split(r'\n\s{8}\{', step_body)
        for block in step_entries:
            if not block.strip():
                continue

            # Find all entity-handler pairs in this step
            entity_handlers = re.findall(r'\[(\w+)\]\s*=\s*LQS\.(\w+)\(', block)
            # Also check for combined onTrigger/onTrade blocks
            entity_combined = re.findall(r'\[(\w+)\]\s*=\s*\{', block)

            if not entity_handlers and not entity_combined:
                continue

            # Pick the best entity: prioritize defeat > trade > menu > dialog
            PRIORITY = {'defeat': 0, 'trade': 1, 'menu': 2, 'shop': 3, 'dialog': 4}
            best_var = None
            best_action = 'Speak to'
            best_priority = 99

            # Get previous step's entity to prefer new interactions
            prev_entity = steps[-1]["entity"] if steps else None

            for var, handler in entity_handlers:
                if handler == 'nothingElse':
                    continue  # skip placeholder handlers
                p = PRIORITY.get(handler, 5)
                # Prefer entities different from the previous step
                if var != prev_entity or best_var is None:
                    if p <= best_priority:
                        best_priority = p
                        best_var = var
                        if handler == 'defeat':
                            best_action = 'Defeat'
                        elif handler == 'trade':
                            best_action = 'Trade to'
                        else:
                            best_action = 'Speak to'

            # Check for onTrade inside combined blocks
            has_trade = 'LQS.trade(' in block
            if has_trade and best_priority > 1:
                # Find which entity has the onTrade
                for var in entity_combined:
                    # Check if this entity's block contains onTrade
                    var_block = re.search(rf'\[{var}\]\s*=\s*\{{(.*?)\n\s{{12}}\}}', block, re.DOTALL)
                    if var_block and 'onTrade' in var_block.group(1):
                        best_var = var
                        best_action = 'Trade to'
                        break

            if best_var is None:
                best_var = entity_combined[0] if entity_combined else None
            if best_var is None:
                continue

            var_name = best_var
            display_name = local_vars.get(var_name, var_name.replace("_", " "))
            action = best_action

            ed = entity_data.get(var_name) or entity_data.get(display_name) or {}
            zone = ed.get("zone", "")
            pos = ed.get("pos")
            is_mob = ed.get("mob", action == 'Defeat')
            is_object = ed.get("object", False)

            # Override action for objects
            if is_object and action == 'Speak to':
                action = 'Interact with'

            step = {
                "action": action,
                "entity": display_name,
                "mob": is_mob,
                "zone": zone,
            }
            if has_trade and required_items:
                step["trade"] = required_items
            if pos:
                step["pos"] = pos
            steps.append(step)

    # Fallback if no steps parsed
    if not steps:
        for display_name, ed in entity_data.items():
            if display_name in local_vars.values():
                hint = f"Interact with {display_name} in {ed['zone']}"
                step = {"hint": hint, "zone": ed["zone"]}
                if ed.get("pos"):
                    step["pos"] = ed["pos"]
                steps.append(step)

    # Extract reward data — check both info.reward and step-level rewards
    reward = {}
    # Gil (from anywhere in the file — info.reward or step rewards)
    gil_matches = re.findall(r'gil\s*=\s*(\d+)', text)
    if gil_matches:
        # Take the largest gil value (usually the main reward)
        reward['gil'] = max(int(x) for x in gil_matches)

    # Item IDs — scan all reward blocks in the file (info + step-level)
    item_list = []
    for reward_block in re.finditer(r'reward\s*=\s*\{(.*?)\}', text, re.DOTALL):
        block = reward_block.group(1)
        # Numeric item IDs
        for item_id in re.findall(r'item\s*=\s*(\d+)', block):
            val = int(item_id)
            if val not in item_list:
                item_list.append(val)
        # xi.item.SOMETHING references
        for item_ref in re.findall(r'item\s*=\s*xi\.item\.(\w+)', block):
            resolved = resolve_item(item_ref)
            if resolved and resolved not in item_list:
                item_list.append(resolved)
        # Item tables: { { id, qty }, ... }
        for item_id in re.findall(r'item\s*=\s*\{[^}]*?(\d{3,5})', block):
            val = int(item_id)
            if val > 100 and val not in item_list:
                item_list.append(val)
    if item_list:
        reward['items'] = item_list

    # Feature
    feature_match = re.search(r'feature\s*=\s*"([^"]+)"', text)
    feature_table = re.findall(r'feature\s*=\s*\{([^}]+)\}', text)
    if feature_table:
        features = re.findall(r'"([^"]+)"', feature_table[0])
        if features:
            reward['feature'] = features
    elif feature_match:
        reward['feature'] = [feature_match.group(1)]

    quest = {
        'name': name.group(1),
        'author': author.group(1) if author else 'Unknown',
        'var': quest_var.group(1) if quest_var else '',
        'total': max(1, len(steps) - 1) if steps else max(1, step_count - 1),  # finish = steps - 1
        'category': category.group(1) if category else 'quest',
    }

    if subcategory:
        quest['subcategory'] = subcategory.group(1)
    if steps:
        quest['steps'] = steps
    if reward:
        quest['reward'] = reward
    if required_items:
        quest['required'] = required_items

    return quest


def lua_string(s):
    """Escape a string for Lua."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def generate_lua(quests):
    """Generate the questdata.lua file content."""
    lines = [
        "--[[",
        "* lqs/data/questdata.lua — Auto-generated quest metadata",
        "*",
        "* Generated by: scripts/export-quests.py",
        "* Do not edit manually — re-run the script to update.",
        "]]--",
        "",
        "return {",
    ]

    for key, q in sorted(quests.items()):
        lines.append(f"    ['{lua_string(key)}'] = {{")
        lines.append(f"        name     = '{lua_string(q['name'])}',")
        lines.append(f"        author   = '{lua_string(q['author'])}',")
        lines.append(f"        var      = '{lua_string(q['var'])}',")
        lines.append(f"        total    = {q['total']},")
        lines.append(f"        category = '{q['category']}',")
        if 'region' in q:
            lines.append(f"        region   = '{lua_string(q['region'])}',")

        if 'subcategory' in q:
            lines.append(f"        subcategory = '{lua_string(q['subcategory'])}',")

        if 'steps' in q:
            lines.append("        steps = {")
            for s in q['steps']:
                parts = [f"action = '{s.get('action', 'Speak to')}'"]
                parts.append(f"entity = '{lua_string(s['entity'])}'")
                if s.get('mob'):
                    parts.append("mob = true")
                if s.get('zone'):
                    parts.append(f"zone = '{lua_string(s['zone'])}'")
                if s.get('pos'):
                    parts.append(f"pos = {{ {s['pos'][0]}, {s['pos'][1]}, {s['pos'][2]} }}")
                if s.get('trade'):
                    trade_strs = ", ".join(f"{{ id = {t['id']}, qty = {t['qty']} }}" for t in s['trade'])
                    parts.append(f"trade = {{ {trade_strs} }}")
                lines.append(f"            {{ {', '.join(parts)} }},")
            lines.append("        },")

        if 'required' in q:
            req_strs = ", ".join(f"{{ id = {r['id']}, qty = {r['qty']} }}" for r in q['required'])
            lines.append(f"        required = {{ {req_strs} }},")

        if 'reward' in q:
            r = q['reward']
            lines.append("        reward = {")
            if 'gil' in r:
                lines.append(f"            gil = {r['gil']},")
            if 'items' in r:
                lines.append(f"            items = {{ {', '.join(str(x) for x in r['items'])} }},")
            if 'item_refs' in r:
                lines.append(f"            -- item_refs: {', '.join(r['item_refs'])} (resolve manually)")
            if 'feature' in r:
                if len(r['feature']) == 1:
                    lines.append(f"            feature = '{lua_string(r['feature'][0])}',")
                else:
                    feat_str = ', '.join(f"'{lua_string(f)}'" for f in r['feature'])
                    lines.append(f"            feature = {{ {feat_str} }},")
            lines.append("        },")

        lines.append("    },")

    lines.append("};")
    return "\n".join(lines)


def main():
    quest_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUEST_DIR
    output_file = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT

    if not os.path.isdir(quest_dir):
        print(f"Error: {quest_dir} not found")
        sys.exit(1)

    load_item_enum()
    load_item_names()

    # Find all Lua files recursively
    lua_files = glob.glob(os.path.join(quest_dir, "**/*.lua"), recursive=True)

    quests = {}
    for filepath in sorted(lua_files):
        quest = parse_quest_file(filepath)
        if quest:
            # Derive region from file path
            rel = os.path.relpath(filepath, quest_dir)
            parts = rel.replace("\\", "/").split("/")
            # Try two-level (questpack/bastok) then one-level (battle)
            region_key = "/".join(parts[:2]) if len(parts) > 2 else parts[0]
            if region_key not in REGION_NAMES:
                region_key = parts[0]
            quest['region'] = REGION_NAMES.get(region_key, parts[0].replace("_", " ").title())

            key = quest['name'].lower()
            quests[key] = quest

    # Generate output
    lua_content = generate_lua(quests)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, 'w') as f:
        f.write(lua_content)

    print(f"Exported {len(quests)} quests to {output_file}", file=sys.stderr)

    # Print summary
    categories = {}
    for q in quests.values():
        cat = q['category']
        categories[cat] = categories.get(cat, 0) + 1
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}", file=sys.stderr)


if __name__ == "__main__":
    main()
