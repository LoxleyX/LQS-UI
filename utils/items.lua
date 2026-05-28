--[[
* lqs/utils/items.lua — Item icon loading, name resolution, and tooltips
*
* Provides item rendering utilities extracted from the Trove pattern.
]]--

local ffi   = require('ffi');
local d3d   = require('d3d8');
local imgui = require('imgui');

local C       = ffi.C;
local d3d8dev = d3d.get_device();

local items = {};

------------------------------------------------------------
-- Texture cache
------------------------------------------------------------
local textureCache   = {};  -- itemId -> texture object (or false)
local textureHandles = {};  -- itemId -> number for imgui.Image
local textureLRU     = {};
local CACHE_MAX      = 128;

------------------------------------------------------------
-- Item resource lookup
------------------------------------------------------------
items.getRes = function(itemId)
    if itemId == nil or itemId == 0 then return nil; end
    return AshitaCore:GetResourceManager():GetItemById(itemId);
end

items.getName = function(itemId)
    local res = items.getRes(itemId);
    if res and res.Name and res.Name[1] then
        return res.Name[1];
    end
    return string.format('Item %d', itemId);
end

------------------------------------------------------------
-- Icon loading
------------------------------------------------------------
items.loadTexture = function(itemId)
    if textureCache[itemId] ~= nil then return textureCache[itemId]; end
    if itemId == nil or itemId == 0 then textureCache[itemId] = false; return false; end

    local res = items.getRes(itemId);
    if res == nil or res.ImageSize == 0 then textureCache[itemId] = false; return false; end

    -- Evict oldest if cache is full
    if #textureLRU >= CACHE_MAX then
        local evict = table.remove(textureLRU, 1);
        textureCache[evict]   = nil;
        textureHandles[evict] = nil;
    end

    local ptr = ffi.new('IDirect3DTexture8*[1]');
    if (C.D3DXCreateTextureFromFileInMemoryEx(
        d3d8dev, res.Bitmap, res.ImageSize,
        0xFFFFFFFF, 0xFFFFFFFF, 1, 0,
        C.D3DFMT_A8R8G8B8, C.D3DPOOL_MANAGED,
        C.D3DX_DEFAULT, C.D3DX_DEFAULT,
        0xFF000000, nil, nil, ptr) ~= C.S_OK) then
        textureCache[itemId] = false; return false;
    end

    local tex = d3d.gc_safe_release(ffi.cast('IDirect3DTexture8*', ptr[0]));
    textureCache[itemId] = tex;
    textureHandles[itemId] = tonumber(ffi.cast('uint32_t', tex));
    textureLRU[#textureLRU + 1] = itemId;
    return tex;
end

------------------------------------------------------------
-- Render icon (returns true if rendered, false if no icon)
------------------------------------------------------------
items.renderIcon = function(itemId, size)
    items.loadTexture(itemId);
    local handle = textureHandles[itemId];
    if handle ~= nil then
        imgui.Image(handle, { size, size });
        return true;
    end
    return false;
end

------------------------------------------------------------
-- Element glyph rendering
------------------------------------------------------------
local ELEMENT_COLORS = {
    [0x1F] = { 1.00, 0.45, 0.25, 1.00 },  -- Fire
    [0x20] = { 0.55, 0.85, 1.00, 1.00 },  -- Ice
    [0x21] = { 0.55, 1.00, 0.55, 1.00 },  -- Wind
    [0x22] = { 0.90, 0.75, 0.45, 1.00 },  -- Earth
    [0x23] = { 1.00, 0.90, 0.30, 1.00 },  -- Thunder
    [0x24] = { 0.45, 0.60, 1.00, 1.00 },  -- Water
    [0x25] = { 1.00, 1.00, 0.85, 1.00 },  -- Light
    [0x26] = { 0.75, 0.45, 1.00, 1.00 },  -- Dark
};

local DOT_RADIUS = 4;
local DOT_WIDTH  = 12;

-- Render a description string with element icons as colored dots
items.renderDescription = function(desc, color)
    if desc == nil or #desc == 0 then return; end
    color = color or { 0.82, 0.82, 0.87, 1.00 };

    local i, n = 1, #desc;
    local rendered = false;

    while i <= n do
        local b = desc:byte(i);
        if b == 0x0A then
            -- Newline
            if not rendered then imgui.Text(''); end
            rendered = false;
            i = i + 1;
        elseif b == 0xEF and i < n and ELEMENT_COLORS[desc:byte(i + 1)] then
            -- Element glyph → colored dot
            if rendered then imgui.SameLine(0, 0); end
            local ec = ELEMENT_COLORS[desc:byte(i + 1)];
            local dl = imgui.GetWindowDrawList();
            local sx, sy = imgui.GetCursorScreenPos();
            local lineH = imgui.GetTextLineHeight();
            dl:AddCircleFilled(
                { sx + DOT_WIDTH / 2, sy + lineH / 2 },
                DOT_RADIUS,
                imgui.GetColorU32(ec));
            imgui.Dummy({ DOT_WIDTH, lineH });
            rendered = true;
            i = i + 2;
        else
            -- Regular text segment
            local start = i;
            while i <= n do
                local bb = desc:byte(i);
                if bb == 0x0A or (bb == 0xEF and i < n and ELEMENT_COLORS[desc:byte(i + 1)]) then break; end
                i = i + 1;
            end
            local text = desc:sub(start, i - 1):gsub('%%', '%%%%');
            if rendered then imgui.SameLine(0, 0); end
            imgui.TextColored(color, text);
            rendered = true;
        end
    end
end

------------------------------------------------------------
-- Equipment helpers
------------------------------------------------------------
local FLAG_RARE = 0x8000;
local FLAG_EX   = 0x4000;

local JOB_ABBR = {
    'WAR','MNK','WHM','BLM','RDM','THF','PLD','DRK','BST','BRD',
    'RNG','SAM','NIN','DRG','SMN','BLU','COR','PUP','DNC','SCH',
    'GEO','RUN',
};

items.getJobList = function(jobs)
    if jobs == nil or jobs == 0 then return nil; end
    if bit.band(jobs, 0x7FFFFE) == 0x7FFFFE then return 'All Jobs'; end
    local list = {};
    for i = 1, 22 do
        if bit.band(jobs, bit.lshift(1, i)) ~= 0 then
            table.insert(list, JOB_ABBR[i]);
        end
    end
    return table.concat(list, '/');
end

------------------------------------------------------------
-- Render tooltip for an item
------------------------------------------------------------

items.renderTooltip = function(itemId, qtyOrAugs, augs)
    local res = items.getRes(itemId);
    if res == nil then return; end

    -- Handle overloaded args: (id, qty) or (id, augsTable) or (id, qty, augsTable)
    local qty = nil;
    if type(qtyOrAugs) == 'number' then
        qty = qtyOrAugs;
    elseif type(qtyOrAugs) == 'table' then
        augs = qtyOrAugs;
    end

    local name = (res.Name and res.Name[1]) or '???';

    imgui.BeginTooltip();
    imgui.PushTextWrapPos(300);

    -- Icon + name header
    if items.renderIcon(itemId, 32) then
        imgui.SameLine();
    end
    imgui.TextColored({ 0.80, 0.60, 1.00, 1.00 }, name);

    -- Quantity
    if qty and qty > 1 then
        imgui.SameLine();
        imgui.TextColored({ 0.50, 0.50, 0.55, 1.00 }, string.format(' x%d', qty));
    end

    imgui.Separator();

    -- Flags
    local flags = res.Flags or 0;
    if bit.band(flags, FLAG_RARE) ~= 0 then
        imgui.TextColored({ 1.00, 0.85, 0.30, 1.00 }, 'Rare');
        imgui.SameLine();
    end
    if bit.band(flags, FLAG_EX) ~= 0 then
        imgui.TextColored({ 0.40, 0.90, 0.40, 1.00 }, 'Ex');
    end

    -- Description (with element dots)
    if res.Description and res.Description[1] and res.Description[1] ~= '' then
        imgui.Spacing();
        items.renderDescription(res.Description[1]);
    end

    -- Augments
    if augs and #augs > 0 then
        imgui.Spacing();
        for _, aug in ipairs(augs) do
            imgui.TextColored({ 1.0, 0.55, 0.75, 1.0 }, aug);
        end
    end

    -- Level + Jobs
    local isEquip = (res.Level and res.Level > 0) or (res.Jobs and res.Jobs > 0);
    if isEquip then
        imgui.Spacing();
        local infoStr = '';
        if res.Level and res.Level > 0 then
            infoStr = string.format('Lv.%d  ', res.Level);
        end
        local jobStr = items.getJobList(res.Jobs);
        if jobStr then
            infoStr = infoStr .. jobStr;
        end
        imgui.TextColored({ 0.55, 0.75, 0.55, 1.00 }, infoStr);
    end

    imgui.PopTextWrapPos();
    imgui.EndTooltip();
end

------------------------------------------------------------
-- Cleanup
------------------------------------------------------------
items.clear = function()
    textureCache   = {};
    textureHandles = {};
    textureLRU     = {};
end

return items;
