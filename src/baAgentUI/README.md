# BA Agent UI - Modern Chat Interface

基于 React + TypeScript + Tailwind CSS 的现代化建筑自动化 AI 助手界面，深度整合 **EPC (工程部署)**、**O&M (运维)** 和 **HMI (自动生成)** 三大核心子系统。

## 设计亮点

### 双脑架构可视化
- **左侧边栏** 实时显示 Fantom (左脑) 和 Python (右脑) 的运行状态
- 负载进度条动态变化，反映实时处理压力
- 活动任务状态监控（数据采集、异常检测、能耗优化）

### 现代化 UI 设计
- **磨砂玻璃效果** (Backdrop Blur): 输入框和头部采用半透明背景 `backdrop-blur-xl bg-white/80`
- **渐变色彩**: 蓝色到靛蓝的专业配色 `from-blue-500 to-indigo-500`
- **圆角阴影**: 所有卡片采用 `rounded-xl` 和柔和阴影 `shadow-lg`
- **丝滑动画**: Tailwind `animate-in` 配合自定义过渡效果

### 对话功能
- **气泡样式**:
  - 用户: 蓝色渐变 + 右对齐 + 圆角优化
  - AI: 白色背景 + 边框 + 左对齐
- **打字机动画**: 三个跳跃圆点模拟 AI 思考状态
- **消息复制**: hover 显示复制按钮，点击后显示"已复制"反馈
- **自动滚动**: 新消息自动滚动到底部
- **快捷指令**: 底部建议芯片，一键填入常用查询

### 智能输入框
- **键盘快捷键**: Enter 发送 / Shift+Enter 换行
- **自动高度调整**: 随内容增长，最高 200px
- **字符计数**: 实时显示输入字符数
- **附件/插件**: UI 占位，为未来功能预留
- **发送按钮**: 渐变色 + 阴影，禁用时变灰

### 三大场景支持

#### O&M (运维诊断)
```tsx
import { DiagnosticCard } from './components/AdvancedCards';

<DiagnosticCard
  diagnosis={{
    equip_id: '@ahu-3f-roof',
    equip_name: 'AHU-3F-Roof',
    issue_type: '送风温度异常偏高',
    severity: 'warning',
    root_cause: 'VAV 末端阀门卡死...',
    confidence: 87,
    current_values: { ... },
    recommended_actions: [ ... ]
  }}
  onExecuteAction={(action) => console.log('执行 AXON:', action)}
  onCreateTicket={() => console.log('创建工单')}
/>
```

#### HMI (自动生成)
```tsx
import { HmiPreview } from './components/AdvancedCards';

<HmiPreview
  layout={{
    equip_id: '@ahu-3f-roof',
    equip_name: 'AHU-3F-Roof',
    confidence: 92,
    pages: [ ... ],
    matched_components: 12,
    total_components: 13
  }}
  onConfirm={() => console.log('确认发布到 FIN')}
  onExport={() => console.log('导出配置')}
/>
```

#### EPC (自动上点)
```tsx
import { TagSuggestionCard } from './components/AdvancedCards';

<TagSuggestionCard
  data={{
    equip_id: '@ahu-3f-roof',
    equip_name: 'AHU-3F-Roof',
    discovered_points: 24,
    tags: [ ... ],
    coverage_percent: 95
  }}
  onApplyTags={(tags) => console.log('批量应用标签:', tags)}
  onApplySingle={(tag, value) => console.log('应用单个标签:', tag, value)}
/>
```

## 组件结构

```
src/
├── components/
│   ├── ChatInterface/          # 主聊天界面
│   │   ├── ChatInterface.tsx   # 主容器
│   │   ├── ChatMessage.tsx     # 消息气泡
│   │   ├── TypingIndicator.tsx # 思考动画
│   │   ├── SuggestionChips.tsx # 快捷指令
│   │   └── index.ts
│   └── AdvancedCards/         # 高级卡片组件
│       ├── DiagnosticCard.tsx   # 故障诊断卡片
│       ├── HmiPreview.tsx      # HMI 预览
│       ├── TagSuggestionCard.tsx # 标签推荐
│       └── index.ts
├── services/
│   └── haystack.ts            # Haystack 3.0 客户端
├── utils/
│   └── cn.ts                 # className 合并工具
└── App.tsx                   # 主应用入口
```

## 开发命令

```bash
# 安装依赖
npm install

# 启动开发服务器 (代理到 localhost:8080)
npm run dev

# TypeScript 类型检查
npm run type-check

# 生产构建
npm run build
```

## 技术栈

- **React 18** - 函数组件 + Hooks
- **TypeScript** - 严格类型检查
- **Vite** - 快速构建工具
- **Tailwind CSS** (v4+) - 原子化 CSS
- **Lucide React** - 图标库
- **haystack-core** - Haystack 3.0 类型定义
- **haystack-nclient** - Haystack HTTP 客户端

## 浏览器支持

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## License

Copyright (c) 2024 AI4Building Project
