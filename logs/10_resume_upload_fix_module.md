# 批量上传简历修复日志

- 时间：2026-03-27
- 模块：前端简历批量上传

## 问题现象

- 在“筛选看板”最后一步点击“批量上传并评估”后，简历无法成功上传。
- 直接调用后端 `POST /jobs/{job_id}/resumes` 接口时，本地和公网入口都能成功返回 `200`，说明问题不在后端上传接口或公网隧道本身。

## 根因定位

- 前端使用 Ant Design `Upload` 组件时，在 `beforeUpload` 中把原始 `RcFile` 直接放进了 `resumeFiles` / `jdFiles` 状态。
- 后续真正提交时，代码只从 `originFileObj` 取文件：
  - JD 导入：`jdFiles[0]?.originFileObj`
  - 简历上传：`resumeFiles.map((file) => file.originFileObj)`
- 这会导致前端状态里虽然显示“已选中文件”，但真正发请求时可能取不到有效文件对象，最终形成空上传或上传失败。

## 修复内容

- 在前端新增统一的上传文件归一化逻辑，把 `RcFile` 转成带 `originFileObj` 的受控 `UploadFile`。
- 在导入 JD 和批量上传简历时，统一通过 `getNativeFile(...)` 提取原始浏览器 `File`。
- 当选中的文件列表无法提取出有效 `File` 时，前端会直接提示“未读取到有效的简历文件，请重新选择后再上传”，避免无意义请求。

## 涉及文件

- `frontend/components/resume-screening-app.tsx`

## 验证结果

- 公网与本地上传接口直连验证：通过
- 前端生产构建 `npm run build`：通过

## 备注

- 当前公网测试版由后端直接托管 `frontend/out/`，前端重新构建后即可加载修复后的静态资源。
