--[[
* lqs/utils/config.lua — Addon settings
*
* Uses a standalone file to avoid conflicts with other settings users.
]]--

local config = {};

local defaults = {
    showDailiesInTracker = true,
    showCompass          = true,
    theme                = 'default',
};

local current = {};
local configPath = nil;

config.load = function()
    -- Build path: addons/lqs/config.lua (shared across characters)
    configPath = string.format('%saddons/lqs/config.dat', AshitaCore:GetInstallPath());

    local f = io.open(configPath, 'r');
    if f then
        local content = f:read('*a');
        f:close();
        -- Parse simple key=value format
        for key, value in content:gmatch('([%w_]+)=([^\n]+)') do
            if value == 'true' then
                current[key] = true;
            elseif value == 'false' then
                current[key] = false;
            else
                current[key] = value;
            end
        end
    end

    -- Fill in defaults
    for key, value in pairs(defaults) do
        if current[key] == nil then
            current[key] = value;
        end
    end
end

config.save = function()
    if configPath == nil then return; end
    local f = io.open(configPath, 'w');
    if f then
        for key, value in pairs(current) do
            f:write(string.format('%s=%s\n', key, tostring(value)));
        end
        f:close();
    end
end

config.get = function(key)
    if current[key] ~= nil then return current[key]; end
    return defaults[key];
end

config.set = function(key, value)
    current[key] = value;
    config.save();
end

return config;
