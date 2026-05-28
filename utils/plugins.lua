--[[
* lqs/utils/plugins.lua — Plugin manager
*
* Auto-discovers and loads .lua files from the plugins/ directory.
* Each plugin adds a tab to the LQS panel with its own content.
*
* Plugin format:
*
*   return {
*       name  = 'Incursion',          -- tab label (required)
*       order = 10,                    -- tab sort order (lower = left)
*       init  = function(items, ui) end,  -- called with shared utils
*       render = function(state, ui, items) end,  -- renders tab content
*       onUnload = function() end,     -- cleanup
*   }
*
* The `state` table contains all addon state including quest list,
* timers, instance cache, etc. Plugins can read from it freely.
*
* Plugins receive `items` (utils/items.lua) and `ui` (utils/ui.lua)
* for rendering icons, tooltips, and themed UI elements.
]]--

local plugins = {};

local loaded = {};  -- array of { plugin, file }

------------------------------------------------------------
-- Discovery: scan plugins/ directory
------------------------------------------------------------
local function discoverPlugins()
    local dir = string.format('%saddons\\lqs\\plugins\\', AshitaCore:GetInstallPath());
    local handle = io.popen('dir /b "' .. dir .. '*.lua" 2>nul');
    if handle == nil then return {}; end

    local files = {};
    for line in handle:lines() do
        if line:match('%.lua$') then
            files[#files + 1] = line;
        end
    end
    handle:close();
    return files;
end

------------------------------------------------------------
-- Load all plugins
------------------------------------------------------------
plugins.load = function()
    local files = discoverPlugins();
    local names = {};
    for _, filename in ipairs(files) do
        local name = filename:gsub('%.lua$', '');
        local ok, result = pcall(function()
            return require('plugins/' .. name);
        end);

        if ok and type(result) == 'table' and result.name then
            loaded[#loaded + 1] = { plugin = result, file = filename };
            names[#names + 1] = result.name;
        elseif ok then
            print(string.format('[lqs] Plugin %s: invalid (must return table with .name)', filename));
        else
            print(string.format('[lqs] Plugin %s failed to load: %s', filename, tostring(result)));
        end
    end

    -- Sort by order (lower = left in tab bar)
    table.sort(loaded, function(a, b)
        return (a.plugin.order or 100) < (b.plugin.order or 100);
    end);

    -- Silent load
end

------------------------------------------------------------
-- Initialize all plugins with shared utilities
------------------------------------------------------------
plugins.init = function(items, ui)
    for _, entry in ipairs(loaded) do
        if entry.plugin.init then
            local ok, err = pcall(entry.plugin.init, items, ui);
            if not ok then
                print(string.format('[lqs] Plugin %s init error: %s', entry.plugin.name, tostring(err)));
            end
        end
    end
end

------------------------------------------------------------
-- Unload all plugins
------------------------------------------------------------
plugins.unload = function()
    for _, entry in ipairs(loaded) do
        if entry.plugin.onUnload then
            pcall(entry.plugin.onUnload);
        end
    end
    loaded = {};
end

------------------------------------------------------------
-- Get all loaded plugins (for tab rendering)
------------------------------------------------------------
plugins.getAll = function()
    return loaded;
end

return plugins;
