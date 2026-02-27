// BA-Agent Python Container Lifecycle Manager
using haystack
using hx

**
** PyManager wraps BaAgentBridge with health-check, auto-reconnect,
** and safe-call semantics for resilient Python session management.
**
** BaAgentBridge handles raw session creation/invocation/closure.
** PyManager adds:
**   - Heartbeat detection (pyEval "1+1") before each call
**   - Automatic session restart on container failure
**   - Retry logic with configurable max attempts
**
** Usage from AXON:
**   ext("baAgent").pyManager.safeCall(cx, "diagnose", dataGrid)
**
const class PyManager
{
  ** The underlying bridge for raw hxPy session operations.
  const BaAgentBridge bridge

  ** Maximum retry attempts for session recovery.
  const Int maxRetries := 3

  ** Create a PyManager wrapping the given bridge.
  new make(BaAgentBridge bridge)
  {
    this.bridge = bridge
  }

  ** Get a healthy Python session, verifying it responds to heartbeat.
  ** If the existing session is dead, closes it and creates a new one.
  ** Retries up to maxRetries times before throwing.
  Obj getHealthySession(HxContext cx)
  {
    retries := 0
    while (retries < maxRetries)
    {
      session := bridge.getSession(cx)
      if (isAlive(cx, session)) return session

      // Session is unresponsive — close and retry
      cx.rt.log.warn("PyManager: session heartbeat failed, attempt ${retries + 1}/${maxRetries}")
      try { bridge.closeSession(cx, session) } catch {}
      retries++
    }
    throw Err("PyManager: failed to obtain healthy Python session after $maxRetries attempts")
  }

  ** Heartbeat check — evaluates a trivial expression to verify the session is alive.
  Bool isAlive(HxContext cx, Obj session)
  {
    try
    {
      result := cx.eval(
        Str<|pyEval($session, "1+1")|>.replace("\$session", "session")
      )
      return result == Number(2)
    }
    catch (Err e)
    {
      cx.rt.log.debug("PyManager.isAlive: heartbeat failed", e)
      return false
    }
  }

  ** Execute an action with automatic health check and single retry on failure.
  **
  ** Flow:
  **   1. Get healthy session (with heartbeat)
  **   2. Call bridge.call()
  **   3. On failure: close session, get new healthy session, retry once
  **
  Grid safeCall(HxContext cx, Str action, Grid? data := null)
  {
    try
    {
      // First attempt with health-checked session
      getHealthySession(cx)
      return bridge.call(cx, action, data)
    }
    catch (Err e)
    {
      cx.rt.log.warn("PyManager.safeCall: first attempt failed for '$action', retrying", e)

      // Retry once with fresh session
      try
      {
        getHealthySession(cx)
        return bridge.call(cx, action, data)
      }
      catch (Err e2)
      {
        cx.rt.log.err("PyManager.safeCall: retry failed for '$action'", e2)
        throw e2
      }
    }
  }

  ** Gracefully shut down a session.
  Void shutdown(HxContext cx, Obj session)
  {
    bridge.closeSession(cx, session)
  }
}
