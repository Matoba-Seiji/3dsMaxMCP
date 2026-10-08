-- 3ds Max 2025 CUI menu. Loaded as a pre-start-up package component.
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

    global maxMcpRegisterMenu
    fn maxMcpRegisterMenu = (
        local manager = callbacks.notificationParam()
        local menu = manager.mainMenuBar.CreateSubMenu "8FA485C0-4A12-4F43-9A6C-2B6F99CD4040" "3dsMax MCP"
        menu.CreateAction "A509E65E-6A13-4D52-8910-9362D004A5EA" 647394 "MaxMCPStart`3dsMaxMCP" title:"启动服务"
        menu.CreateAction "D17CF9A0-5E48-49DD-A832-3E4F56454F96" 647394 "MaxMCPStop`3dsMaxMCP" title:"停止服务"
        menu.CreateAction "8EF7F7C7-0992-41C8-A7A3-57496D6F134A" 647394 "MaxMCPRestart`3dsMaxMCP" title:"重启服务"
        menu.CreateAction "F9046D46-C18A-4203-83DB-69CF7F48EDB4" 647394 "MaxMCPStatus`3dsMaxMCP" title:"查看状态"
    )
    callbacks.removeScripts id:#MaxMCPMenu
    callbacks.addScript #cuiRegisterMenus "maxMcpRegisterMenu()" id:#MaxMCPMenu
)
