// BA-Agent WebHandler — HTTP/WebSocket API for frontend communication
using hx
using web
using haystack
using util

**
** BaAgentWeb handles HTTP and WebSocket requests from baAgentUI.
**
** Routes:
**   - POST /api/baAgent/chat    — synchronous AI chat interaction
**   - GET  /api/baAgent/ws      — WebSocket upgrade for streaming AI responses
**   - POST /api/baAgent/confirm — Shadow Mode write confirmation (approve/reject)
**
** All responses are sanitized via DataSanitizer to strip sensitive fields.
**
** WebSocket frame protocol aligns with frontend WsFrame types:
**   - message:  { type:"message",  id, timestamp, content, context? }
**   - progress: { type:"progress", id, timestamp, percent, stage }
**   - result:   { type:"result",   id, timestamp, result, content }
**   - error:    { type:"error",    id, timestamp, code, message }
**
const class BaAgentWeb : HxWeb
{
  //////////////////////////////////////////////////////////////////////////
  // Routing
  //////////////////////////////////////////////////////////////////////////

  ** Main entry point — route based on request path and method.
  override Void onService(WebReq req, WebRes res)
  {
    path := req.modRel.path

    try
    {
      // Match routes
      if (path.size >= 1)
      {
        seg := path.last
        if (seg == "chat" && req.method == "POST")
          { handleChat(req, res); return }
        if (seg == "confirm" && req.method == "POST")
          { handleConfirm(req, res); return }
        if (seg == "ws" && req.method == "GET")
          { handleWebSocket(req, res); return }
      }

      // No route matched
      res.statusCode = 404
      writeJson(res, Etc.makeDict(["error": "Not found"]))
    }
    catch (Err e)
    {
      cx.rt.log.err("BaAgentWeb", e)
      res.statusCode = 500
      writeJson(res, Etc.makeDict([
        "type": "error",
        "code": "INTERNAL_ERROR",
        "message": e.msg
      ]))
    }
  }

  //////////////////////////////////////////////////////////////////////////
  // POST /chat — Synchronous AI Chat
  //////////////////////////////////////////////////////////////////////////

  ** Handle a synchronous chat request.
  ** Reads JSON body with {action, message, context?}, invokes the AI agent
  ** via PyManager, sanitizes the result, and returns JSON.
  private Void handleChat(WebReq req, WebRes res)
  {
    // Parse JSON request body
    body := (Str:Obj?) JsonInStream(req.in).readJson

    action := body.get("action", "general") as Str ?: "general"
    message := body.get("message", "") as Str ?: ""

    // Build context-enriched message dict
    msgDict := Etc.makeDict([
      "action": action,
      "message": message
    ])
    msgDict = attachContext(msgDict, cx)

    // Get the AI extension and call Python via PyManager
    ext := cx.rt.ext("baAgent") as BaAgentExt
    resultGrid := ext.pyManager.safeCall(cx, action, null)

    // Sanitize the result before returning
    sanitized := DataSanitizer.sanitizeGrid(resultGrid)

    // Build response matching AgentResponse type
    responseDict := Etc.makeDict([
      "ok": true,
      "action": action,
      "data": sanitized.first ?: Etc.emptyDict
    ])

    writeJson(res, DataSanitizer.sanitize(responseDict))
  }

  //////////////////////////////////////////////////////////////////////////
  // POST /confirm — Shadow Mode Approve/Reject
  //////////////////////////////////////////////////////////////////////////

  ** Handle Shadow Mode write confirmation.
  ** Expects JSON body: {pointId, decision: "approve"|"reject"}
  private Void handleConfirm(WebReq req, WebRes res)
  {
    body := (Str:Obj?) JsonInStream(req.in).readJson

    pointIdStr := body.get("pointId") as Str
    decision := body.get("decision") as Str

    if (pointIdStr == null || decision == null)
    {
      res.statusCode = 400
      writeJson(res, Etc.makeDict(["error": "Missing pointId or decision"]))
      return
    }

    pointId := Ref.make(pointIdStr)
    Dict result

    if (decision == "approve")
      result = ShadowModeManager.commitAiChange(cx, pointId)
    else if (decision == "reject")
      result = ShadowModeManager.cancelAiChange(cx, pointId)
    else
    {
      res.statusCode = 400
      writeJson(res, Etc.makeDict(["error": "Invalid decision: must be 'approve' or 'reject'"]))
      return
    }

    writeJson(res, DataSanitizer.sanitize(result))
  }

  //////////////////////////////////////////////////////////////////////////
  // GET /ws — WebSocket Upgrade
  //////////////////////////////////////////////////////////////////////////

  ** Upgrade to WebSocket and run a message loop.
  ** Each incoming frame is a JSON WsMessageFrame from the frontend.
  ** Responses are sent as WsResultFrame / WsProgressFrame / WsErrorFrame.
  private Void handleWebSocket(WebReq req, WebRes res)
  {
    socket := WebSocket.upgrade(req, res)

    try
    {
      // Message loop
      while (true)
      {
        msgStr := socket.receive
        if (msgStr == null) break  // client disconnected

        frameId := Uuid().toStr
        try
        {
          // Parse incoming message
          incoming := (Str:Obj?) JsonInStream(msgStr.in).readJson
          action := incoming.get("action", "general") as Str ?: "general"
          content := incoming.get("content", "") as Str ?: ""

          // Send progress frame
          sendWsFrame(socket, Str:Obj?[
            "type": "progress",
            "id": frameId,
            "timestamp": DateTime.now.toStr,
            "percent": Number(0),
            "stage": "Processing '$action' request..."
          ])

          // Build context-enriched message
          msgDict := Etc.makeDict([
            "action": action,
            "message": content
          ])
          msgDict = attachContext(msgDict, cx)

          // Call Python AI engine
          ext := cx.rt.ext("baAgent") as BaAgentExt
          resultGrid := ext.pyManager.safeCall(cx, action, null)
          sanitized := DataSanitizer.sanitizeGrid(resultGrid)
          resultDict := sanitized.first ?: Etc.emptyDict

          // Send result frame (aligned with WsResultFrame type)
          sendWsFrame(socket, Str:Obj?[
            "type": "result",
            "id": frameId,
            "timestamp": DateTime.now.toStr,
            "result": Str:Obj?[
              "action": action,
              "ok": true,
              "data": resultDict,
              "summary": resultDict.get("summary", "")
            ],
            "content": resultDict.get("summary", "AI analysis complete.") as Str
          ])
        }
        catch (Err e)
        {
          cx.rt.log.err("BaAgentWeb.ws", e)
          // Send error frame (aligned with WsErrorFrame type)
          sendWsFrame(socket, Str:Obj?[
            "type": "error",
            "id": frameId,
            "timestamp": DateTime.now.toStr,
            "code": "AGENT_ERROR",
            "message": e.msg
          ])
        }
      }
    }
    finally
    {
      socket.close
    }
  }

  //////////////////////////////////////////////////////////////////////////
  // Helpers
  //////////////////////////////////////////////////////////////////////////

  ** Attach site/user context from the current HxContext to an outgoing message.
  private Dict attachContext(Dict msg, HxContext cx)
  {
    tags := Str:Obj?[:]
    msg.each |v, k| { tags[k] = v }

    // Attach user info
    tags["userId"] = cx.user.id.toStr
    tags["userName"] = cx.user.dis

    return Etc.makeDict(tags)
  }

  ** Write a JSON response Dict to the WebRes output stream.
  private Void writeJson(WebRes res, Dict dict)
  {
    res.headers["Content-Type"] = "application/json"
    json := Str:Obj?[:]
    dict.each |v, k| { json[k] = v }
    JsonOutStream(res.out).writeJson(json).flush
  }

  ** Send a JSON frame over a WebSocket connection.
  private Void sendWsFrame(WebSocket socket, Str:Obj? frame)
  {
    buf := StrBuf()
    JsonOutStream(buf.out).writeJson(frame)
    socket.send(buf.toStr)
  }
}
