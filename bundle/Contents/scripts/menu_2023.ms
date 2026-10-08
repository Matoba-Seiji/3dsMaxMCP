-- 3ds Max 2023 legacy menu. Loaded after the UI is ready.
(
    local scriptDir = getFilenamePath (getSourceFileName())
    python.ExecuteFile (scriptDir + @"bootstrap.py")

    macroScript MaxMCPStart category:"3dsMaxMCP" tooltip:"启动 3ds Max MCP 服务" buttonText:"启动服务"
    (
        on execute do python.Execute "import max_mcp.ui.service as service; service.start()"
    )
    macroScript MaxMCPStop category:"3dsMaxMCP" tooltip:"停止 3ds Max MCP 服务" buttonText:"停止服务"
    (
        on execute do python.Execute "import max_mcp.ui.service as service; service.stop()"
    )
    macroScript MaxMCPRestart category:"3dsMaxMCP" tooltip:"重启 3ds Max MCP 服务" buttonText:"重启服务"
    (
        on execute do python.Execute "import max_mcp.ui.service as service; service.restart()"
    )
    macroScript MaxMCPStatus category:"3dsMaxMCP" tooltip:"查看 3ds Max MCP 服务状态" buttonText:"查看状态"
    (
        on execute do python.Execute "import max_mcp.ui.service as service; service.status()"
    )

    local menuTitle = "3dsMax MCP"
    local mainBar = menuMan.getMainMenuBar()
    local menu = menuMan.findMenu menuTitle
    if menu == undefined do menu = menuMan.findMenu "3ds Max MCP 工具"

    if menu == undefined then (
        menuMan.registerMenuContext 0x5A4D4350
        menu = menuMan.createMenu menuTitle
        mainBar.addItem (menuMan.createSubMenuItem menuTitle menu) (mainBar.numItems() - 1)
    ) else (
        -- Rename an already registered English menu without duplicating it.
        menu.setTitle menuTitle
        for i = 0 to (mainBar.numItems() - 1) do (
            local item = mainBar.getItem i
            if item.getSubMenu() == menu do item.setTitle menuTitle
        )
    )

    -- Refresh our four action items so a saved English menu does not retain
    -- stale labels. Keep the stable macroScript names and category unchanged.
    for i = (menu.numItems() - 1) to 0 by -1 do menu.removeItemByPosition i
    local actionNames = #("MaxMCPStart", "MaxMCPStop", "MaxMCPRestart", "MaxMCPStatus")
    local actionTitles = #("启动服务", "停止服务", "重启服务", "查看状态")
    for i = 1 to 4 do (
        local item = menuMan.createActionItem actionNames[i] "3dsMaxMCP"
        item.setTitle actionTitles[i]
        item.setUseCustomTitle true
        menu.addItem item -1
    )
    menuMan.updateMenuBar()
)
