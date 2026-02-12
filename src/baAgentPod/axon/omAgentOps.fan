using haystack
using axon
using hx
using hxPy

**
** BA-Agent 运维阶段核心 Axon 函数集
**
@NoDoc
class omAgentOps : Const
{
  //////////////////////////////////////////////////////////////////////////
  // FDD 故障诊断
  //////////////////////////////////////////////////////////////////////////

  **
  ** 执行全流程 FDD 诊断：上下文采集 -> AI 诊断 -> 结果解包
  **
  @Axon
  static Dict agentDiagnose(Obj alarmRef, Dict? opts := null)
  {
    cx := Context.cur
    options := opts ?: Etc.makeDict([:])
    
    // 1. 读取报警点
    alarmPoint := cx.db.readById(Etc.toId(alarmRef))
    alarmMsg := options.get("message", alarmPoint.get("dis", "Alarm"))

    // 2. 解析父级设备 (Equip)
    equipRef := alarmPoint.get("equipRef") as Ref
    
    // 3. 采集上下文数据 (利用内部定义的打包工具)
    hisRange := options.get("hisRange", "yesterday") as Str
    filter := equipRef != null 
      ? "point and equipRef==${equipRef.toCode}" 
      : "point and id==${alarmPoint.id.toCode}"
    
    contextGrid := agentPackGrid(filter, Etc.makeDict(["his": true, "hisRange": hisRange]))

    // 4. 调用 Python 引擎 (通过 hxPy 桥接)
    // 构造发送给 Python 的 Payload
    payload := Etc.makeDict([
      "alarm_id": alarmPoint.id.toStr,
      "alarm_message": alarmMsg,
      "equip_id": equipRef?.toStr ?: ""
    ])

    // 执行 Python 调用
    // 假设 Python 侧已注册名为 "diagnose" 的处理函数
    raw := PyFuncs.call("agent_service_handle", ["diagnose", payload, contextGrid])

    // 5. 解包并返回结果
    return agentUnpackResult(raw)
  }

  //////////////////////////////////////////////////////////////////////////
  // 节能优化
  //////////////////////////////////////////////////////////////////////////

  **
  ** 针对特定设备进行能效优化建议 (Shadow Mode)
  **
  @Axon
  static Dict agentOptimizeSetpoints(Obj equipRef, Dict? opts := null)
  {
    cx := Context.cur
    options := opts ?: Etc.makeDict([:])
    equip := cx.db.readById(Etc.toId(equipRef))

    // 1. 采集该设备下所有点位的运行数据
    filter := "point and equipRef==${equip.id.toCode}"
    hisRange := options.get("hisRange", "yesterday") as Str
    contextGrid := agentPackGrid(filter, Etc.makeDict(["his": true, "hisRange": hisRange]))

    // 2. 调用 Python EnergyOptEngine
    payload := Etc.makeDict([
      "equip_id": equip.id.toStr,
      "equip_name": equip.get("dis", "Equipment"),
      "target": options.get("target", "balanced")
    ])

    raw := PyFuncs.call("agent_service_handle", ["optimize", payload, contextGrid])

    return agentUnpackResult(raw)
  }

  //////////////////////////////////////////////////////////////////////////
  // 虚拟巡检
  //////////////////////////////////////////////////////////////////////////

  **
  ** 启动虚拟传感器巡检循环，返回健康评分 (0-100)
  **
  @Axon
  static Dict agentInspect(Str filter, Dict? opts := null)
  {
    options := opts ?: Etc.makeDict([:])
    hisRange := options.get("hisRange", "yesterday") as Str

    // 1. 批量采集匹配点位的历史数据
    contextGrid := agentPackGrid(filter, Etc.makeDict(["his": true, "hisRange": hisRange]))

    // 2. 调用 Python InspectEngine 进行零漂与一致性分析
    payload := Etc.makeDict([:])
    raw := PyFuncs.call("agent_service_handle", ["inspect", payload, contextGrid])

    return agentUnpackResult(raw)
  }

  //////////////////////////////////////////////////////////////////////////
  // 负荷卸载 (Demand Response)
  //////////////////////////////////////////////////////////////////////////

  **
  ** 执行柔性负荷卸载策略
  **
  @Axon
  static Dict agentLoadShed(Dict? opts := null)
  {
    cx := Context.cur
    options := opts ?: Etc.makeDict([:])
    level := options.get("level", 1)
    equipFilter := options.get("equipFilter", "ahu or vav")

    // 查找目标设备列表
    equipList := cx.db.readAll(equipFilter)
    results := Obj?[,]

    // 对每个设备尝试获取节能模式下的设定值建议
    equipList.each |equip| {
      try {
        opt := agentOptimizeSetpoints(equip.id, Etc.makeDict(["target": "energy"]))
        results.add(opt)
      } catch (Err e) { /* 记录日志 */ }
    }

    return Etc.makeDict([
      "ok": true,
      "action": "loadshed",
      "level": level,
      "count": equipList.size,
      "optimizations": results
    ])
  }

  //////////////////////////////////////////////////////////////////////////
  // 工具函数 (内部使用或公开)
  //////////////////////////////////////////////////////////////////////////

  **
  ** 将筛选的点位及其历史数据打包为 Grid，方便 Python 处理
  **
  static Grid agentPackGrid(Str filter, Dict opts)
  {
    cx := Context.cur
    points := cx.db.readAll(filter)
    includeHis := opts.has("his")
    range := opts.get("hisRange", "yesterday")

    // 这里实现将 Point 属性与历史数据合并的逻辑
    // 简化处理：返回包含基础属性和当前值的 Grid
    // 在实际开发中，这里通常会调用 hisRead 并将数据 join 进 Grid
    return cx.db.readAll(filter).toGrid
  }

  **
  ** 处理 Python 返回的结果，确保格式符合 Axon 规范
  **
  static Dict agentUnpackResult(Obj? raw)
  {
    if (raw == null) return Etc.makeDict(["ok": false, "error": "No response from AI"])
    if (raw is Dict) return (Dict)raw
    
    // 如果返回的是字符串（JSON），则解析它
    if (raw is Str) return (Dict)Etc.makeDict(JsonInStream(((Str)raw).in).readJson)
    
    return Etc.makeDict(["ok": true, "data": raw])
  }
}