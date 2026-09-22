# BagRoute

投递装袋：按路线订户顺序装袋，重量与体积双约束，超限拒收。

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4300 |
| API | http://localhost:9300 |
| API 文档 | http://localhost:9300/docs |
| Postgres | localhost:5444 |

健康检查：`GET http://localhost:9300/api/health`

## 页面

- `/routes` — 路线
- `/stops` — 订户点
- `/pack` — 装袋
- `/bags` — 袋明细
- `/rejects` — 拒收
- `/weights` — 袋重

## 使用说明

1. 查看路线与订户点顺序。
2. 在订户点页可标记停投：停投站点不参与装袋，既不进入任何袋，也不写入拒收；状态持久保存，恢复投递后可再次装入。
3. 在装袋页选择路线，按剩余（未停投）站点执行双约束装袋。
4. 袋明细与袋重查看结果，拒收页查看超限订户。

## 开发与测试

```bash
docker compose exec api pytest -q
```
