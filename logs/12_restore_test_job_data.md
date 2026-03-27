# 模块日志：恢复测试岗位数据

## 时间
- 2026-03-27

## 目标
- 恢复之前用于演示和测试的“外贸经理”岗位及候选人数据。

## 现状确认
- 本轮自动化测试执行后，数据库里的历史岗位基本被清空，只剩一条新的测试岗位。
- `backend/storage/resumes/` 目录中仍保留了之前上传过的候选人文件，可作为恢复来源。
- 其中可直接复用的文件包括：
  - `backend/storage/resumes/8c97de02-41a4-4ad0-a638-8c62dbdf594f.pdf`：蓝小姐简历 PDF
  - `backend/storage/resumes/e3cfb523-70fc-4171-985c-e4190d04cee2.txt`：张三对照样本

## 执行内容
- 新增恢复脚本：
  - `backend/scripts/restore_previous_test_job.py`
- 新增展示修正脚本：
  - `backend/scripts/fix_restored_trade_manager_display.py`
- 通过脚本恢复出岗位：
  - 岗位名称：`外贸经理`
  - 岗位 ID：`9062bbe7-5f0b-4b5a-8541-5680bfe7f333`
- 恢复候选人：
  - 蓝小姐
  - 张三
- 清理了一条因命令行编码问题生成的乱码岗位，避免页面出现重复脏数据。

## 恢复结果
- 当前岗位列表仅保留恢复后的 `外贸经理`
- 看板数据：
  - 总简历数：2
  - 蓝小姐：`manual_review`
  - 张三：`manual_review`
- 报告顶部姓名已恢复：
  - `候选人：蓝小姐`
  - `候选人：张三`

## 验证方式
- 本地接口验证：
  - `GET /jobs`
  - `GET /jobs/9062bbe7-5f0b-4b5a-8541-5680bfe7f333/dashboard`
  - `GET /evaluations/{id}`

## 后续建议
- 如果后续还需要把这套演示数据恢复回来，直接执行：
  - `python backend/scripts/restore_previous_test_job.py`
  - `python backend/scripts/fix_restored_trade_manager_display.py`
