// BA-Agent Haxall Extension — plugin entry point
using hx

**
** BaAgentExt is the main extension for the BA-Agent pod.
** It registers AXON functions, initializes the hxPy bridge,
** and manages the AI service lifecycle.
**
** Access the bridge from AXON:
**   bridge: ext("baAgent").bridge
**
const class BaAgentExt : HxExt
{
  static HxExtDef def() { HxExtDef.cur }

  ** The hxPy session manager for Python AI service calls.
  const BaAgentBridge bridge := BaAgentBridge()
}
