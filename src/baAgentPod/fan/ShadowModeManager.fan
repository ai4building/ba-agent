// BA-Agent Shadow Mode Manager — "suggest → confirm → execute" controlled write flow
using haystack
using hx

**
** ShadowModeManager implements the safety barrier for AI-initiated writes.
**
** All AI write recommendations are staged at Priority 16 (shadow level) with
** `aiSuggestedVal` and `aiReason` tags. A human operator must explicitly confirm
** before the value is promoted to Priority 8 (operational level).
**
** Life-safety points (fire, smoke, sprinkler, emergency systems) are strictly
** read-only and cannot be written at any priority level.
**
** Frontend Integration:
**   - `applyShadowVal` → Python optimization result triggers this via AXON ops
**   - `commitAiChange` → Frontend `approve` action calls POST /api/baAgent/confirm
**   - `cancelAiChange` → Frontend `reject` action
**   - `criticalTags` → Synchronized with frontend `LIFE_SAFETY_TAGS` in AuditActionController.ts
**
const class ShadowModeManager
{
  ** Life-safety tags — points with any of these tags are NEVER writable by AI.
  ** Must stay in sync with frontend LIFE_SAFETY_TAGS in AuditActionController.ts.
  private static const Str[] criticalTags := [
    "fire", "smoke", "sprinkler", "emergencyPower",
    "fireAlarm", "smokeDetector", "emergencyShutdown",
    "fireSuppression", "emergencyExhaust"
  ]

  ** Check whether a point is a life-safety point (read-only for AI).
  static Bool isCritical(Dict point)
  {
    return criticalTags.any |tag| { point.has(tag) }
  }

  ** Stage an AI-recommended value at Priority 16 (shadow mode).
  **
  ** The value is NOT immediately applied to the field controller.
  ** Instead, it is written at Priority 16 and tagged with `aiSuggestedVal`
  ** and `aiReason` for the frontend AuditActionController to detect and
  ** present to the operator for approval.
  **
  ** Throws if the point is a life-safety point.
  static Void applyShadowVal(HxContext cx, Ref id, Obj newVal, Str reason)
  {
    // 1. Read the point and enforce life-safety barrier
    point := cx.db.readById(id)
    if (isCritical(point))
      throw Err("ShadowModeManager: cannot write to life-safety point $id")

    // 2. Write the suggested value at Priority 16 (shadow level)
    cx.eval(
      Str<|pointWrite($id, $val, 16)|>
        .replace("\$id", id.toCode)
        .replace("\$val", newVal.toStr)
    )

    // 3. Tag the point with aiSuggestedVal and aiReason for frontend detection
    cx.eval(
      Str<|readById($id).toRec.set("aiSuggestedVal", $val).set("aiReason", $reason).commit|>
        .replace("\$id", id.toCode)
        .replace("\$val", newVal.toStr)
        .replace("\$reason", reason)
    )
  }

  ** Commit an approved AI change: promote from Priority 16 to Priority 8.
  **
  ** Called when a human operator approves the suggested value via the
  ** ActionApprovalPanel in the frontend.
  **
  ** Returns a Dict with: ok, pointId, previousVal, newVal, operator, timestamp
  static Dict commitAiChange(HxContext cx, Ref id)
  {
    // 1. Read the point and its staged value
    point := cx.db.readById(id)
    suggestedVal := point.get("aiSuggestedVal")
    if (suggestedVal == null)
      throw Err("ShadowModeManager: no pending AI suggestion for point $id")

    // Life-safety double-check
    if (isCritical(point))
      throw Err("ShadowModeManager: cannot commit write to life-safety point $id")

    previousVal := point.get("curVal")
    operator := cx.user.dis

    // 2. Promote to Priority 8 (operational level)
    cx.eval(
      Str<|pointWrite($id, $val, 8)|>
        .replace("\$id", id.toCode)
        .replace("\$val", suggestedVal.toStr)
    )

    // 3. Clear Priority 16 shadow value
    cx.eval(
      Str<|pointWrite($id, null, 16)|>
        .replace("\$id", id.toCode)
    )

    // 4. Clean up AI tags and add commit audit trail
    now := DateTime.now
    cx.eval(
      Str<|readById($id).toRec.remove("aiSuggestedVal").remove("aiReason").set("aiCommitBy", $op).set("aiCommitTs", $ts).commit|>
        .replace("\$id", id.toCode)
        .replace("\$op", operator)
        .replace("\$ts", now.toStr)
    )

    // 5. Return audit result
    return Etc.makeDict([
      "ok": true,
      "pointId": id.toStr,
      "previousVal": previousVal ?: "unknown",
      "newVal": suggestedVal,
      "operator": operator,
      "timestamp": now
    ])
  }

  ** Cancel a pending AI suggestion, clearing the shadow value and tags.
  **
  ** Called when a human operator rejects the suggested value.
  static Dict cancelAiChange(HxContext cx, Ref id)
  {
    // 1. Clear Priority 16 shadow value
    cx.eval(
      Str<|pointWrite($id, null, 16)|>
        .replace("\$id", id.toCode)
    )

    // 2. Clean up AI tags
    cx.eval(
      Str<|readById($id).toRec.remove("aiSuggestedVal").remove("aiReason").commit|>
        .replace("\$id", id.toCode)
    )

    return Etc.makeDict([
      "ok": true,
      "pointId": id.toStr,
      "cancelled": true
    ])
  }
}
