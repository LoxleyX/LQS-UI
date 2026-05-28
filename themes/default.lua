--[[
* trove/themes/default.lua — Default Trove theme
*
* Copy this file and modify to create custom themes.
* Set the theme in trove.lua: local THEME = 'mytheme'
* Place your theme at: themes/mytheme.lua
*
* Colors are RGBA tables: { R, G, B, A } where each value is 0.0 to 1.0
]]--

return {
    -- Window chrome
    windowBg         = { 0.06, 0.05, 0.09, 0.92 },
    windowTitleBg    = { 0.12, 0.08, 0.18, 0.95 },
    windowTitleBgAct = { 0.18, 0.12, 0.25, 0.95 },
    windowBorder     = { 0.30, 0.20, 0.45, 0.60 },
    childBg          = { 0.14, 0.12, 0.20, 0.80 },
    tooltipBg        = { 0.08, 0.06, 0.12, 0.95 },
    panelBg          = { 0.10, 0.08, 0.15, 0.95 },

    -- Frame / input
    frameBg          = { 0.14, 0.10, 0.20, 0.80 },
    frameBgHovered   = { 0.20, 0.15, 0.30, 0.80 },

    -- Scrollbar
    scrollbarBg      = { 0.06, 0.05, 0.09, 0.50 },
    scrollbarGrab    = { 0.30, 0.20, 0.45, 0.60 },
    scrollbarHover   = { 0.40, 0.30, 0.55, 0.80 },
    scrollbarActive  = { 0.50, 0.38, 0.65, 1.00 },

    -- Tabs
    tab              = { 0.18, 0.12, 0.25, 0.95 },
    tabHovered       = { 0.30, 0.20, 0.45, 0.95 },
    tabActive        = { 0.35, 0.25, 0.55, 0.95 },

    -- Selectable / header (list items, menu items)
    selectHeader     = { 0.30, 0.22, 0.42, 0.60 },
    selectHovered    = { 0.40, 0.28, 0.55, 0.55 },
    selectActive     = { 0.50, 0.35, 0.70, 0.75 },

    -- Text
    header           = { 0.80, 0.60, 1.00, 1.00 },
    accent           = { 0.65, 0.45, 0.90, 1.00 },
    dimmed           = { 0.50, 0.50, 0.55, 1.00 },
    white            = { 1.00, 1.00, 1.00, 1.00 },
    desc             = { 0.70, 0.70, 0.75, 1.00 },
    yellow           = { 1.00, 0.92, 0.60, 1.00 },
    blue             = { 0.55, 0.75, 1.00, 1.00 },
    green            = { 0.55, 0.90, 0.55, 1.00 },
    red              = { 1.00, 0.55, 0.55, 1.00 },

    -- Status
    statusOk         = { 0.55, 0.90, 0.55, 1.00 },
    statusErr        = { 1.00, 0.55, 0.55, 1.00 },
    statusWarn       = { 1.00, 0.85, 0.30, 1.00 },

    -- Items
    rare             = { 1.00, 0.85, 0.30, 1.00 },
    ex               = { 0.40, 0.90, 0.40, 1.00 },
    rareBg           = { 0.40, 0.35, 0.10, 0.80 },
    exBg             = { 0.10, 0.35, 0.15, 0.80 },
    qty              = { 0.90, 0.75, 1.00, 1.00 },
    qtyLow           = { 1.00, 0.70, 0.40, 1.00 },
    empty            = { 0.60, 0.55, 0.70, 0.80 },
    slotText         = { 0.80, 0.80, 0.85, 1.00 },
    jobText          = { 0.85, 0.80, 0.95, 1.00 },

    -- Categories & navigation
    category         = { 0.55, 0.80, 0.55, 1.00 },
    headerBg         = { 0.18, 0.12, 0.25, 1.00 },
    catBtnBg         = { 0.14, 0.10, 0.20, 1.00 },
    selected         = { 0.25, 0.18, 0.38, 0.90 },
    searchHint       = { 0.40, 0.40, 0.45, 1.00 },
    breadcrumb       = { 0.70, 0.65, 0.85, 1.00 },

    -- Buttons: primary action
    btnPrimary       = { 0.35, 0.25, 0.55, 1.00 },
    btnPrimaryHover  = { 0.45, 0.35, 0.65, 1.00 },
    btnPrimaryActive = { 0.55, 0.40, 0.75, 1.00 },
    btnDimmed        = { 0.20, 0.18, 0.25, 0.50 },

    -- Buttons: feature (secondary)
    btnFeature       = { 0.30, 0.30, 0.50, 1.00 },
    btnFeatureHover  = { 0.40, 0.40, 0.60, 1.00 },
    btnFeatureActive = { 0.50, 0.50, 0.70, 1.00 },

    -- Buttons: positive (store/confirm)
    btnPositive      = { 0.25, 0.45, 0.30, 1.00 },
    btnPositiveHover = { 0.30, 0.55, 0.35, 1.00 },
    btnPositiveActive= { 0.35, 0.65, 0.40, 1.00 },

    -- Buttons: back/cancel
    btnBack          = { 0.25, 0.22, 0.32, 1.00 },
    btnBackHover     = { 0.35, 0.30, 0.45, 1.00 },
    btnBackActive    = { 0.45, 0.38, 0.55, 1.00 },

    -- Currency / Points
    currencyName     = { 0.95, 0.90, 0.70, 1.00 },
    currencyTotal    = { 1.00, 0.95, 0.75, 1.00 },
    currencyBrk      = { 0.65, 0.65, 0.70, 1.00 },
    pointsGroup      = { 0.55, 0.75, 1.00, 1.00 },
    pointsLabel      = { 0.90, 0.90, 0.95, 1.00 },
    pointsValue      = { 1.00, 0.95, 0.75, 1.00 },

    -- VNM-specific (plugins can extend the theme)
    alertGlow        = { 1.00, 0.85, 0.30, 1.00 },
    ownedTick        = { 0.40, 0.90, 0.40, 1.00 },
    notOwned         = { 0.30, 0.20, 0.20, 1.00 },
    dimText          = { 0.50, 0.50, 0.55, 1.00 },
};
