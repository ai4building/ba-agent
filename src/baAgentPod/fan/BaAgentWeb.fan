// BA-Agent WebHandler — HTTP/WebSocket API for frontend communication
using hx
using web

**
** BaAgentWeb handles HTTP and WebSocket requests from baAgentUI.
** Routes:
**   - POST /api/baAgent/chat    — AI chat interaction
**   - WS   /api/baAgent/ws      — real-time diagnostic push
**   - POST /api/baAgent/confirm — Shadow Mode write confirmation
**
const class BaAgentWeb : HxWeb
{
}
