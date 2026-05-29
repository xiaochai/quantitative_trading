# 项目文档目录

## 目录结构

```
doc/
├── requirements/          # 需求文档
│   └── data_requirements.md    # 数据需求文档（已创建）
│   └── functional_requirements.md  # 功能需求文档
│   └── user_stories.md         # 用户故事
├── design/                # 设计文档
│   └── architecture.md         # 系统架构设计
│   └── database_design.md      # 数据库设计
│   └── api_design.md           # API接口设计
│   └── ui_design.md            # 前端UI设计
├── development/           # 开发文档
│   └── setup_guide.md          # 环境搭建指南
│   └── coding_standards.md     # 编码规范
│   └── deployment.md           # 部署说明
├── iteration/             # 迭代文档
│   └── iteration_001.md        # 迭代1：数据模块
│   └── iteration_002.md        # 迭代2：策略模块
│   └── iteration_003.md        # 迭代3：回测模块
├── bugs/                  # Bug修复记录
│   └── bug_001.md              # Bug记录模板
├── usage/                 # 使用说明
│   └── user_guide.md           # 用户使用指南
│   └── api_reference.md        # API使用参考
└── README.md              # 文档目录说明（本文件）
```

## 文档管理规范

### 1. 需求文档 (requirements/)
- 存放产品需求、数据需求、用户故事等
- 文件名格式：`{type}_requirements.md` 或 `user_stories.md`

### 2. 设计文档 (design/)
- 存放系统架构、数据库设计、API设计、UI设计等
- 文件名格式：`{module}_design.md`

### 3. 开发文档 (development/)
- 存放环境搭建、编码规范、部署说明等
- 面向开发人员

### 4. 迭代文档 (iteration/)
- 存放各迭代周期的计划、进度、总结
- 文件名格式：`iteration_{000}.md`

### 5. Bug修复记录 (bugs/)
- 存放bug报告和修复记录
- 文件名格式：`bug_{000}.md`

### 6. 使用说明 (usage/)
- 存放用户指南、API文档等
- 面向最终用户

## 文档状态标识

| 状态 | 标识 | 说明 |
|------|------|------|
| 草稿 | [DRAFT] | 正在编写中 |
| 审核中 | [REVIEW] | 等待审核 |
| 已发布 | [RELEASED] | 已正式发布 |
| 已废弃 | [DEPRECATED] | 不再使用 |

## 版本控制

- 所有文档使用Markdown格式编写
- 遵循Git版本控制流程
- 重大变更需在文档中记录变更历史