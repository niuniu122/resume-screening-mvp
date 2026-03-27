# 模块日志：批量上传简历修复

## 时间
- 2026-03-27

## 问题描述
- 用户反馈在第 4 步“筛选看板”点击“批量上传并评估”时，简历无法上传。

## 根因定位
- 后端 `/jobs/{job_id}/resumes` 接口本身可用，直接通过 HTTP 上传测试简历可以成功返回 `200`。
- 问题出在前端上传组件：
  - `Upload` 的 `beforeUpload` 里把 `RcFile` 直接塞进了 `fileList` 状态。
  - 真正提交时又通过 `file.originFileObj` 取原始文件。
  - 这会导致页面看起来“已经选中文件”，但实际提交阶段拿不到稳定的原始 `File` 对象。

## 修复内容
- 文件：`frontend/components/resume-screening-app.tsx`
- 增加 `normalizeUploadFile(file: RcFile)`，统一把上传选择结果转成可控的 `UploadFile`。
- 增加 `getNativeFile(file?: UploadFile | null)`，只从 `originFileObj` 读取真实文件对象。
- JD 上传和简历批量上传都改为走统一文件归一化逻辑。
- 在批量上传前增加保护：
  - 如果最终没有取到有效原始文件，直接给出错误提示，不再发空请求。

## 验证结果
- 前端执行 `npm run build` 通过。
- 后端本地健康检查正常：`/health -> 200`。
- 直接调用简历上传接口仍可正常返回成功。

## 影响范围
- 修复了第 4 步批量上传简历失败的问题。
- 顺带修复了第 1 步通过文件上传 JD 时可能遇到的同类问题。

## 后续说明
- 当前公网地址如果之前已经打开过旧页面，需要强制刷新一次浏览器缓存后再试。
