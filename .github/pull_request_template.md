## 概要

<!-- 这个 PR 做了什么？ -->

## 为什么

<!-- 解决什么问题 / 对应哪条需求或 issue？ -->

## 变更

- 

## 验证

- [ ] `python .github/scripts/check_public_repo.py`
- [ ] 后端 `python manage.py test` 通过
- [ ] `python manage.py makemigrations --check --dry-run` 无漂移（如涉及模型）
- [ ] 前端 `npm run typecheck` / `npm run build` 通过（如涉及前端）
- [ ] 涉及认证、权限、爬虫、上传、反代、数据口径时已说明威胁模型 / 数据影响与回滚方案

## 风险与回滚

<!-- 可能影响哪些用户/接口/数据？出问题如何回滚？ -->

## 公开仓库检查

- [ ] 没有提交真实 `.env`、密码、Token、私钥、数据库连接串
- [ ] 没有提交服务器 IP、root/SSH 账号、面板地址、宿主路径、容器名
- [ ] 没有提交交接文档、上线验证报告、事故复盘、部署 runbook
- [ ] 没有提交构建缓存、截图、临时脚本或 Agent 工作日志
