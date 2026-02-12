// BA-Agent hxPy Bridge — session lifecycle manager
using hx
using haystack

**
** BaAgentBridge manages the hxPy PySession lifecycle for the BA-Agent pod.
**
** This is NOT a PySession subclass — it is a session manager that creates,
** caches, and cleans up hxPy sessions. AXON functions in utilOps/omOps use
** this bridge to obtain a ready-to-use Python session with BaAgentService
** already loaded.
**
** Design:
**   - One session per Haxall Task context (reused across calls)
**   - Session auto-initializes BaAgentService on first use
**   - Handles container image configuration
**   - Provides clean shutdown on Task/Extension stop
**
** Usage from AXON:
**   bridge: ext("baAgent").bridge
**   session: bridge.getSession()
**   pyEval(session, "svc.handle(action='ping')")
**
const class BaAgentBridge
{
  ** Docker image for the hxPy container
  const Str image := "ba-agent-py:latest"

  ** Python import statement executed once per session
  const Str initCode :=
    "import sys; sys.path.insert(0, '/io'); " +
    "from baAgentPy.main import BaAgentService; " +
    "svc = BaAgentService()"

  ** Create a new bridge with optional custom image name.
  new make(Str image := "ba-agent-py:latest")
  {
    this.image = image
  }

  ** Get or create a Python session for the current context.
  ** The session will have BaAgentService already instantiated as `svc`.
  **
  ** Caller is responsible for session lifecycle when used outside
  ** a Haxall Task context (call closeSession when done).
  **
  ** Returns the opaque session object for use with pyDefine/pyEval.
  Obj getSession(HxContext cx)
  {
    // Use AXON runtime to create session via py()
    // py(image: "ba-agent-py:latest") → PySession
    session := cx.eval(
      Str<|py(image: "$image")|>.replace("\$image", image)
    )

    // Initialize BaAgentService in the session
    cx.eval(
      Str<|pyExec($session, "$code")|>
        .replace("\$session", "session")
        .replace("\$code", initCode)
    )

    return session
  }

  ** Execute an action on BaAgentService via a cached session.
  **
  ** This is the primary high-level API: pack data, call Python, unpack result.
  **
  **   bridge.call(cx, "diagnose", dataGrid)
  **
  Grid call(HxContext cx, Str action, Grid? data := null)
  {
    session := getSession(cx)

    // If data grid provided, define it in the Python session
    if (data != null)
    {
      cx.eval(
        Str<|pyDefine($session, {grid: $data})|>
          .replace("\$session", "session")
          .replace("\$data", "data")
      )
    }

    // Build the pyEval expression
    expr := data != null
      ? "svc.handle(action='${action}', grid=grid)"
      : "svc.handle(action='${action}')"

    // Execute and return raw Grid result
    result := cx.eval(
      Str<|pyEval($session, "$expr")|>
        .replace("\$session", "session")
        .replace("\$expr", expr.replace("'", "\\'"))
    )

    return result as Grid ?: Grid.makeListGrid(null, Str[,], Obj?[,], Obj?[][,])
  }

  ** Close a specific session, releasing the Docker container.
  Void closeSession(HxContext cx, Obj session)
  {
    try
      cx.eval(Str<|pyClose($session)|>.replace("\$session", "session"))
    catch (Err e)
      cx.rt.log.err("BaAgentBridge.closeSession", e)
  }
}
