// BA-Agent Haxall Extension — plugin entry point
using hx

**
** BaAgentExt is the main extension for the BA-Agent pod.
** It registers AXON functions, initializes the hxPy bridge,
** and manages the AI service lifecycle.
**
** Access from AXON:
**   ext("baAgent").bridge      — raw hxPy session manager
**   ext("baAgent").pyManager   — health-checked session manager with auto-reconnect
**
const class BaAgentExt : HxExt
{
  static HxExtDef def() { HxExtDef.cur }

  ** The hxPy session manager for Python AI service calls.
  const BaAgentBridge bridge := BaAgentBridge()

  ** Health-checked Python session manager with auto-reconnect.
  ** AXON ops should prefer pyManager.safeCall() over bridge.call().
  const PyManager pyManager := PyManager(bridge)
}
