--[[
* lqs — Quest browser, tracker, and content guide for CatsEyeXI
*
* Usage:
*     /lqs         - Toggle quest panel (also Ctrl+K)
*     /lqs pos     - Copy current position to chat
]]--

addon.name    = 'lqs';
addon.author  = 'Loxley';
addon.version = '1.0.0';
addon.desc    = 'Quest browser and tracker for LQS';

require('common');
local imgui  = require('imgui');

local lqs_ui      = require('utils/ui');
local lqs_items   = require('utils/items');
local lqs_plugins = require('utils/plugins');
local lqs_config  = require('utils/config');
local questPanel  = require('panels/quests');
local toast       = require('panels/toast');
local tracker     = require('panels/tracker');
local questdata   = require('data/questdata');

local KEYBIND = '^k';

------------------------------------------------------------
-- Theme
------------------------------------------------------------
lqs_config.load();
lqs_ui.applyTheme(lqs_config.get('theme'));

------------------------------------------------------------
-- Packet protocol (0x1A5)
------------------------------------------------------------
local PACKET_ID = 0x1A5;

local C2S = {
    HANDSHAKE      = 1,
    UNLOAD         = 5,
    GET_QUEST_LIST = 6,
};

local S2C = {
    HANDSHAKE_ACK  = 0,
    QUEST_ENTRY    = 8,
    QUEST_LIST_END = 9,
};

------------------------------------------------------------
-- State
------------------------------------------------------------
local state = {
    connected     = false,
    isGM          = false,
    handshakeSent = false,

    -- Quest list
    questListOpen   = { false },
    questList       = {},
    questListLoaded = false,
    selectedQuest   = nil,
    questRewardCache = {},
    trackedQuest    = nil,
    lastStatusPoll  = 0,
};

------------------------------------------------------------
-- Packet helpers
------------------------------------------------------------
local function makePacket()
    local p = {};
    for i = 1, 64 do p[i] = 0; end
    return p;
end

local function sendAction(action)
    local p = makePacket();
    p[5] = action;
    AshitaCore:GetPacketManager():AddOutgoingPacket(PACKET_ID, p);
end

local function sendHandshake()
    local p = makePacket();
    p[5] = C2S.HANDSHAKE;
    p[7] = 1;
    AshitaCore:GetPacketManager():AddOutgoingPacket(PACKET_ID, p);
end

local function sendGetQuestList()
    sendAction(C2S.GET_QUEST_LIST);
end

local function sendUnload()
    sendAction(C2S.UNLOAD);
end

------------------------------------------------------------
-- Read helpers
------------------------------------------------------------
local function readU8(data, offset)
    return struct.unpack('B', data, offset + 1);
end

local function readString(data, offset, maxLen)
    local bytes = {};
    for i = 1, maxLen do
        local b = struct.unpack('B', data, offset + i);
        if b == 0 then break; end
        table.insert(bytes, string.char(b));
    end
    return table.concat(bytes);
end

------------------------------------------------------------
-- Packet handler (S2C)
------------------------------------------------------------
ashita.events.register('packet_in', 'lqs_packet_in', function(e)
    if e.id ~= PACKET_ID then return; end
    e.blocked = true;

    local action = readU8(e.data_modified, 0x04);

    if action == S2C.HANDSHAKE_ACK then
        state.connected = true;
        state.isGM = readU8(e.data_modified, 0x05) > 0;
        local version = readU8(e.data_modified, 0x06);
        return;
    end

    if action == S2C.QUEST_ENTRY then
        local questStatus = readU8(e.data_modified, 0x05);
        local questStep   = readU8(e.data_modified, 0x06);
        local questName   = readString(e.data_modified, 0x08, 31);

        local nameLower = questName:lower();
        for _, q in ipairs(state.questList) do
            if q.name:lower() == nameLower then
                q.status = questStatus;
                q.step   = questStep;
                break;
            end
        end
        if state.selectedQuest and state.selectedQuest.name:lower() == nameLower then
            state.selectedQuest.status = questStatus;
            state.selectedQuest.step   = questStep;
        end
        return;
    end

    if action == S2C.QUEST_LIST_END then
        return;
    end
end);

------------------------------------------------------------
-- Chat watcher (for toast notifications)
------------------------------------------------------------
ashita.events.register('packet_in', 'lqs_chat_watch', function(e)
    toast.checkChat(e);
end);

------------------------------------------------------------
-- Render (d3d_present)
------------------------------------------------------------
ashita.events.register('d3d_present', 'lqs_render', function()
    -- First frame setup
    if not state.handshakeSent then
        state.handshakeSent = true;
        sendHandshake();
        AshitaCore:GetChatManager():QueueCommand(1, string.format('/bind %s /lqs', KEYBIND));
        lqs_plugins.load();
        lqs_plugins.init(lqs_items, lqs_ui);
        tracker.init();

        toast.onQuestEvent = function()
            sendGetQuestList();
        end;
        state.lastStatusPoll = 0;
    end

    -- Poll for quest status updates every 5 seconds when tracking
    if state.questListLoaded and state.trackedQuest then
        local now = os.clock();
        if now - (state.lastStatusPoll or 0) > 5 then
            state.lastStatusPoll = now;
            sendGetQuestList();
        end
    end

    -- Toast notifications
    toast.render();

    -- Quest tracker HUD
    local dailyState = nil;
    for _, entry in ipairs(lqs_plugins.getAll()) do
        if entry.plugin.name == 'Dailies' and entry.plugin.getState then
            dailyState = entry.plugin.getState();
        end
    end
    tracker.update(state.questList, dailyState, state.trackedQuest);
    tracker.render();

    -- Quest panel
    if state.questListOpen[1] then
        questPanel.render(state, nil, {
            requestList = sendGetQuestList,
        }, lqs_plugins.getAll());
    end
end);

------------------------------------------------------------
-- Commands
------------------------------------------------------------
ashita.events.register('command', 'lqs_command', function(e)
    local args = e.command:args();
    if #args == 0 then return; end

    local cmd = args[1]:lower();
    if cmd ~= '/lqs' then return; end

    e.blocked = true;

    if #args == 1 then
        state.questListOpen[1] = not state.questListOpen[1];
        if state.questListOpen[1] and not state.questListLoaded then
            state.questList = {};
            for key, q in pairs(questdata) do
                table.insert(state.questList, {
                    name        = q.name,
                    author      = q.author or '',
                    status      = 0,
                    step        = 0,
                    total       = q.total or 1,
                    hint        = '',
                    category    = q.category or 'quest',
                    subcategory = q.subcategory or '',
                    region      = q.region or '',
                    var         = q.var or '',
                    reward      = q.reward,
                    required    = q.required,
                    steps       = q.steps,
                    feature     = '',
                });
            end
            state.questListLoaded = true;
            sendGetQuestList();
        end
        return;
    end

    local sub = args[2]:lower();

    if sub == 'pos' then
        local entity = GetPlayerEntity();
        if entity then
            local msg = string.format('{ %.3f, %.3f, %.3f, %d }',
                entity.Movement.LastPosition.X,
                entity.Movement.LastPosition.Y,
                entity.Movement.LastPosition.Z,
                entity.Movement.LastPosition.W);
            print(string.format('\30\06[lqs]\30\01 %s', msg));
        end
        return;
    end
end);

------------------------------------------------------------
-- Unload
------------------------------------------------------------
ashita.events.register('unload', 'lqs_unload', function()
    sendUnload();
    toast.cleanup();
    tracker.cleanup();
    lqs_plugins.unload();
    AshitaCore:GetChatManager():QueueCommand(1, string.format('/unbind %s', KEYBIND));

    ashita.events.unregister('d3d_present', 'lqs_render');
    ashita.events.unregister('command', 'lqs_command');
    ashita.events.unregister('packet_in', 'lqs_packet_in');
    ashita.events.unregister('packet_in', 'lqs_chat_watch');

    print('[lqs] Unloaded.');
end);

