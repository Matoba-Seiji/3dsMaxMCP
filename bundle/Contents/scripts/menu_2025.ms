-- 3ds Max 2025 CUI menu. Loaded as a pre-start-up package component.
(
    local scriptDir = getFilenamePath (getSourceFileName())
    python.ExecuteFile (scriptDir + @"bootstrap.py")

    macroScript MaxMCPStart1 category:"3dsMaxMCP" tooltip:"启动 3ds Max MCP 服务（实例 1，端口 50012）" buttonText:"启动服务（实例1·50012）"
    (
        on execute do python.Execute "import max_mcp.ui.service as service; service.start(50012)"
    )
    macroScript MaxMCPStart2 category:"3dsMaxMCP" tooltip:"启动 3ds Max MCP 服务（实例 2，端口 50013）" buttonText:"启动服务（实例2·50013）"
    (
        on execute do python.Execute "import max_mcp.ui.service as service; service.start(50013)"
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
        menu.CreateAction "B1A2C3D4-5E6F-4A7B-8C9D-0E1F2A3B4C5D" 647394 "MaxMCPStart1`3dsMaxMCP" title:"启动服务（实例1·50012）"
        menu.CreateAction "C2B3D4E5-6F7A-4B8C-9D0E-1F2A3B4C5D6E" 647394 "MaxMCPStart2`3dsMaxMCP" title:"启动服务（实例2·50013）"
        menu.CreateAction "D17CF9A0-5E48-49DD-A832-3E4F56454F96" 647394 "MaxMCPStop`3dsMaxMCP" title:"停止服务"
        menu.CreateAction "8EF7F7C7-0992-41C8-A7A3-57496D6F134A" 647394 "MaxMCPRestart`3dsMaxMCP" title:"重启服务"
        menu.CreateAction "F9046D46-C18A-4203-83DB-69CF7F48EDB4" 647394 "MaxMCPStatus`3dsMaxMCP" title:"查看状态"
    )
    callbacks.removeScripts id:#MaxMCPMenu
    callbacks.addScript #cuiRegisterMenus "maxMcpRegisterMenu()" id:#MaxMCPMenu
)
