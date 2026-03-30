"use client";

import { startTransition, useEffect, useState } from "react";
import {
  App,
  Button,
  Card,
  Col,
  Divider,
  Empty,
  Flex,
  Input,
  List,
  Popconfirm,
  Row,
  Space,
  Spin,
  Statistic,
  Steps,
  Table,
  Tag,
  Typography,
  Upload
} from "antd";
import type { RcFile, UploadFile } from "antd/es/upload/interface";
import {
  ClockCircleOutlined,
  DeleteOutlined,
  FileSearchOutlined,
  FolderOpenOutlined,
  HistoryOutlined,
  RocketOutlined,
  SafetyCertificateOutlined,
  UploadOutlined
} from "@ant-design/icons";

import {
  answerInterview,
  clearApiBaseUrlOverride,
  deleteJob,
  freezeProfile,
  getApiBaseUrl,
  getApiBaseUrlOverride,
  getDashboard,
  getEvaluation,
  getJob,
  hasConfiguredApiBaseUrl,
  importJob,
  isStaticPagesHost,
  listJobs,
  setApiBaseUrlOverride,
  submitDecision,
  uploadResumes
} from "../lib/api";
import type {
  DashboardEvaluationItem,
  DashboardResponse,
  EvaluationDetail,
  JobDetail,
  JobSummary,
  QuestionAnswer,
  ScreeningProfileDraft
} from "../lib/types";
import { EvaluationDrawer } from "./evaluation-drawer";

const stepItems = [
  { title: "岗位创建", description: "导入 JD 或粘贴岗位信息" },
  { title: "AI追问", description: "锁定必须项、可放宽项与风险点" },
  { title: "规则确认", description: "冻结岗位画像与 PromptBundle" },
  { title: "筛选看板", description: "批量上传简历并查看结构化报告" }
];

const statusColorMap: Record<string, string> = {
  auto_reject_review: "volcano",
  manual_review: "gold",
  recommend_interview: "green",
  recommend_reject: "red"
};

const evaluationStatusLabels: Record<string, string> = {
  auto_reject_review: "自动淘汰待确认",
  manual_review: "人工复核",
  recommend_interview: "建议面试",
  recommend_reject: "建议淘汰",
};

const submissionStatusLabels: Record<string, string> = {
  uploaded: "已上传",
  processing: "评估中",
  completed: "已完成",
  failed: "处理失败",
};

const jobStatusLabels: Record<string, string> = {
  draft: "草稿",
  interview_pending: "待回答追问",
  profile_draft: "画像草稿",
  screening_ready: "可开始筛选",
  screening_in_progress: "筛选进行中",
};

function formatRuleValue(value: unknown) {
  if (Array.isArray(value)) {
    return value.join(" / ");
  }
  if (typeof value === "object" && value !== null) {
    return JSON.stringify(value);
  }
  return `${value ?? ""}`;
}

function parseLooseValue(raw: string) {
  if (!raw.trim()) {
    return "";
  }
  if (/^\d+$/.test(raw.trim())) {
    return Number(raw.trim());
  }
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

function formatJdTextForDisplay(value: string) {
  return value
    .replace(/\s*(岗位职责[:：]|任职要求[:：]|职位描述[:：]|岗位描述[:：]|福利待遇[:：]|工作内容[:：])/g, "\n$1\n")
    .replace(/\s*(\d+[.、])\s*/g, "\n$1 ")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function buildJobRequirementHighlights(job: JobDetail) {
  const highlights: string[] = [];
  if (job.parsed_jd.experience_years) {
    highlights.push(`经验要求：${job.parsed_jd.experience_years} 年及以上`);
  }
  if (job.parsed_jd.degree_requirement) {
    highlights.push(`学历要求：${job.parsed_jd.degree_requirement} 及以上`);
  }
  if (job.parsed_jd.language_requirements.length) {
    highlights.push(`语言要求：${job.parsed_jd.language_requirements.join(" / ")}`);
  }
  if (job.parsed_jd.risk_flags.length) {
    highlights.push(`重点核验：${job.parsed_jd.risk_flags.join("；")}`);
  }
  return highlights;
}

function normalizeUploadFile(file: RcFile): UploadFile<RcFile> {
  return {
    uid: file.uid,
    name: file.name,
    size: file.size,
    type: file.type,
    status: "done",
    originFileObj: file
  };
}

function getNativeFile(file?: UploadFile | null): File | null {
  const candidate = file?.originFileObj;
  if (candidate instanceof File) {
    return candidate;
  }
  return null;
}

type ProfileTextListField = "output_requirements" | "interview_focus" | "boundaries";

export function ResumeScreeningApp() {
  const { message } = App.useApp();
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [selectedJob, setSelectedJob] = useState<JobDetail | null>(null);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [evaluationDetail, setEvaluationDetail] = useState<EvaluationDetail | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [jdText, setJdText] = useState("");
  const [jdFiles, setJdFiles] = useState<UploadFile[]>([]);
  const [resumeFiles, setResumeFiles] = useState<UploadFile[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [profileDraft, setProfileDraft] = useState<ScreeningProfileDraft | null>(null);
  const [selectedEvaluationId, setSelectedEvaluationId] = useState<string | null>(null);
  const [apiBaseUrlInput, setApiBaseUrlInput] = useState("");
  const [backendReachable, setBackendReachable] = useState(true);

  useEffect(() => {
    // On static pages host, only pre-fill if the user has explicitly set an override.
    // Do NOT fall back to window.location.origin (the GitHub Pages URL itself).
    const override = getApiBaseUrlOverride();
    if (override) {
      setApiBaseUrlInput(override);
    } else if (!isStaticPagesHost()) {
      setApiBaseUrlInput(getApiBaseUrl());
    }
    void initialize();
  }, []);

  useEffect(() => {
    if (!selectedJob?.current_profile_version) {
      return;
    }
    const timer = window.setInterval(() => {
      void refreshDashboard(selectedJob.id, false);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [selectedJob?.id, selectedJob?.current_profile_version]);

  async function initialize() {
    setPageLoading(true);
    try {
      if (isStaticPagesHost() && !hasConfiguredApiBaseUrl()) {
        setBackendReachable(false);
        clearSelectedWorkspace();
        setJobs([]);
        return;
      }
      // Health check before loading data (retry for Render free-tier cold starts)
      const healthUrl = `${getApiBaseUrl()}/health`;
      let healthy = false;
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          const healthResp = await fetch(healthUrl, { cache: "no-store", signal: AbortSignal.timeout(attempt === 0 ? 15000 : 30000) });
          if (healthResp.ok) { healthy = true; break; }
        } catch {
          // wait before retry on cold-start timeout
          if (attempt < 2) await new Promise(r => setTimeout(r, 3000));
        }
      }
      if (!healthy) {
        if (isStaticPagesHost()) {
          setBackendReachable(false);
          clearSelectedWorkspace();
          setJobs([]);
          return;
        }
      }
      setBackendReachable(true);
      const jobList = await listJobs();
      setJobs(jobList.items);
      if (jobList.items[0]) {
        await loadJob(jobList.items[0].id);
      } else {
        clearSelectedWorkspace();
      }
    } catch (error) {
      if (isStaticPagesHost()) {
        setBackendReachable(false);
        clearSelectedWorkspace();
        setJobs([]);
      } else {
        message.error(error instanceof Error ? error.message : "初始化失败");
      }
    } finally {
      setPageLoading(false);
    }
  }

  function clearSelectedWorkspace() {
    setSelectedJob(null);
    setDashboard(null);
    setEvaluationDetail(null);
    setDrawerOpen(false);
    setProfileDraft(null);
    setAnswers({});
    setSelectedEvaluationId(null);
    setResumeFiles([]);
  }

  async function refreshJobs(preferredJobId?: string) {
    const jobList = await listJobs();
    setJobs(jobList.items);
    const candidateIds = new Set(jobList.items.map((job) => job.id));
    const targetId =
      (preferredJobId && candidateIds.has(preferredJobId) ? preferredJobId : null) ??
      (selectedJob?.id && candidateIds.has(selectedJob.id) ? selectedJob.id : null) ??
      jobList.items[0]?.id;
    if (targetId) {
      await loadJob(targetId);
      return;
    }
    clearSelectedWorkspace();
  }

  async function loadJob(jobId: string) {
    const response = await getJob(jobId);
    startTransition(() => {
      setSelectedJob(response.job);
      const questionAnswers = Object.fromEntries(
        (response.job.interview_session?.answers ?? []).map((item) => [item.question_id, item.answer])
      );
      setAnswers(questionAnswers);
      setProfileDraft(response.job.current_profile ?? response.job.interview_session?.draft_profile ?? null);
    });
    if (response.job.current_profile_version) {
      await refreshDashboard(jobId, true);
    } else {
      setDashboard(null);
    }
  }

  async function refreshDashboard(jobId: string, showError: boolean) {
    try {
      const nextDashboard = await getDashboard(jobId);
      setDashboard(nextDashboard);
      setSelectedJob(nextDashboard.job);
      if (selectedEvaluationId) {
        const detail = await getEvaluation(selectedEvaluationId);
        setEvaluationDetail(detail);
      }
    } catch (error) {
      if (showError) {
        message.error(error instanceof Error ? error.message : "加载筛选看板失败");
      }
    }
  }

  async function handleImportJob() {
    if (!jdText.trim() && jdFiles.length === 0) {
      message.warning("请先粘贴 JD 或上传文档");
      return;
    }
    setActionLoading(true);
    try {
      const response = await importJob({
        jdText: jdText.trim() || undefined,
        file: getNativeFile(jdFiles[0])
      });
      setJdText("");
      setJdFiles([]);
      await refreshJobs(response.job.id);
      message.success("岗位已导入，进入 AI 追问阶段");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "岗位导入失败");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleGenerateProfile() {
    if (!selectedJob?.interview_session?.questions.length) {
      return;
    }
    const payload: QuestionAnswer[] = selectedJob.interview_session.questions.map((question) => ({
      question_id: question.id,
      answer: answers[question.id] ?? ""
    }));
    setActionLoading(true);
    try {
      const draft = await answerInterview(selectedJob.id, payload);
      setProfileDraft(draft);
      await loadJob(selectedJob.id);
      message.success("岗位画像草稿已生成");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "岗位画像生成失败");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleFreezeProfile() {
    if (!selectedJob || !profileDraft) {
      return;
    }
    setActionLoading(true);
    try {
      await freezeProfile(selectedJob.id, profileDraft);
      await refreshJobs(selectedJob.id);
      message.success("岗位画像已冻结，可以开始筛选简历");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "冻结岗位画像失败");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleUploadResumes() {
    if (!selectedJob || resumeFiles.length === 0) {
      message.warning("请先选择需要上传的简历文件");
      return;
    }
    setActionLoading(true);
    try {
      const files = resumeFiles.map((file) => getNativeFile(file)).filter((file): file is File => Boolean(file));
      if (files.length === 0) {
        message.error("未读取到有效的简历文件，请重新选择后再上传");
        return;
      }
      await uploadResumes(selectedJob.id, files);
      setResumeFiles([]);
      await refreshDashboard(selectedJob.id, true);
      message.success("简历已进入评估队列");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "简历上传失败");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleDeleteJob(job: JobSummary) {
    setActionLoading(true);
    try {
      const result = await deleteJob(job.id);
      await refreshJobs();
      message.success(`岗位“${result.deleted_title}”已删除`);
      if (result.cleanup_warnings.length > 0) {
        message.warning("岗位记录已删除，但有部分文件清理失败。");
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : "删除岗位失败");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleSaveApiBaseUrl() {
    const normalized = setApiBaseUrlOverride(apiBaseUrlInput);
    if (!normalized) {
      message.warning("请输入可访问的后端地址");
      return;
    }
    setApiBaseUrlInput(normalized);
    clearSelectedWorkspace();
    setJobs([]);
    await initialize();
    message.success("后端地址已更新");
  }

  async function handleResetApiBaseUrl() {
    clearApiBaseUrlOverride();
    const fallback = getApiBaseUrl();
    setApiBaseUrlInput(fallback);
    clearSelectedWorkspace();
    setJobs([]);
    await initialize();
    message.success("已恢复默认后端地址");
  }

  async function openEvaluation(item: DashboardEvaluationItem) {
    if (!item.evaluation_id) {
      return;
    }
    setActionLoading(true);
    try {
      const detail = await getEvaluation(item.evaluation_id);
      setSelectedEvaluationId(item.evaluation_id);
      setEvaluationDetail(detail);
      setDrawerOpen(true);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "加载报告失败");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleSubmitDecision(decision: string, comment: string) {
    if (!evaluationDetail) {
      return;
    }
    const nextDetail = await submitDecision(evaluationDetail.id, {
      decision,
      reviewer_name: "Recruiter",
      comment
    });
    setEvaluationDetail(nextDetail);
    if (selectedJob) {
      await refreshDashboard(selectedJob.id, false);
    }
    message.success("人工结论已保存");
  }

  function updateDraft(mutator: (draft: ScreeningProfileDraft) => ScreeningProfileDraft) {
    setProfileDraft((current) => (current ? mutator(current) : current));
  }

  function updateDraftTextList(field: ProfileTextListField, index: number, value: string) {
    updateDraft((draft) => {
      const nextItems = [...draft[field]];
      nextItems[index] = value;
      return { ...draft, [field]: nextItems };
    });
  }

  function currentStep() {
    if (!selectedJob) {
      return 0;
    }
    if (selectedJob.current_profile_version) {
      return 3;
    }
    if (selectedJob.interview_session?.draft_profile || profileDraft) {
      return 2;
    }
    return 1;
  }

  const jobColumns = [
    {
      title: "候选人",
      dataIndex: "candidate_name",
      key: "candidate_name",
      render: (value: string | null, item: DashboardEvaluationItem) => value ?? item.filename
    },
    {
      title: "状态",
      dataIndex: "evaluation_status",
      key: "evaluation_status",
      render: (value: string | null, item: DashboardEvaluationItem) =>
        value ? (
          <Tag color={statusColorMap[value] ?? "default"}>{evaluationStatusLabels[value] ?? value}</Tag>
        ) : (
          <Tag>{submissionStatusLabels[item.submission_status] ?? item.submission_status}</Tag>
        )
    },
    {
      title: "得分",
      dataIndex: "overall_score",
      key: "overall_score",
      render: (value: number | null) => value ?? "--"
    },
    {
      title: "风险摘要",
      dataIndex: "risk_summary",
      key: "risk_summary",
      render: (value: string[]) =>
        value.length ? (
          <Space wrap>
            {value.map((item) => (
              <Tag key={item} color="gold">
                {item}
              </Tag>
            ))}
          </Space>
        ) : (
          <Typography.Text type="secondary">无</Typography.Text>
        )
    },
    {
      title: "操作",
      key: "actions",
      render: (_: unknown, item: DashboardEvaluationItem) => (
        <Button type="link" icon={<FileSearchOutlined />} disabled={!item.evaluation_id} onClick={() => void openEvaluation(item)}>
          查看报告
        </Button>
      )
    }
  ];

  return (
    <div className="app-shell">
        <Row gutter={24} style={{ minHeight: "calc(100vh - 56px)" }}>
          <Col xs={24} lg={6} xl={5}>
            <Card className="glass-card" style={{ borderRadius: 28, height: "100%" }}>
              <Space direction="vertical" size={18} style={{ width: "100%" }}>
                <div>
                  <Tag color="green">内部工作台</Tag>
                  <Typography.Title level={2} className="panel-title" style={{ marginTop: 12, marginBottom: 8 }}>
                    简历初筛中枢
                  </Typography.Title>
                  <Typography.Paragraph style={{ color: "var(--text-subtle)", marginBottom: 0 }}>
                    用岗位画像冻结标准，再把简历看成证据，不再靠感觉筛选。
                  </Typography.Paragraph>
                </div>

                <Card
                  style={{
                    borderRadius: 20,
                    background: "linear-gradient(135deg, rgba(20,125,100,0.08), rgba(15,108,128,0.08))"
                  }}
                >
                  <Space direction="vertical" size={6}>
                    <Typography.Text strong>当前节奏</Typography.Text>
                    <Space wrap>
                      <span className="stat-chip">单岗位多简历</span>
                      <span className="stat-chip">结构化报告</span>
                      <span className="stat-chip">人工最终确认</span>
                    </Space>
                  </Space>
                </Card>

                <Card
                  style={{
                    borderRadius: 20,
                    border: !backendReachable ? "2px solid #fa8c16" : undefined,
                    background: !backendReachable ? "linear-gradient(135deg, rgba(250,140,22,0.08), rgba(250,84,28,0.06))" : undefined,
                  }}
                >
                  <Space direction="vertical" size={10} style={{ width: "100%" }}>
                    <Typography.Text strong>
                      {!backendReachable ? "⚠ 后端未连接" : "后端地址"}
                    </Typography.Text>
                    {!backendReachable ? (
                      <Typography.Text type="warning">
                        无法连接到后端服务。请在下方输入可访问的后端地址后点击"连接"。
                        如果你还没有启动后端，请先参考文档部署后端服务。
                      </Typography.Text>
                    ) : (
                      <Typography.Text type="secondary">
                        如果前端挂在 GitHub Pages，而后端还在你的电脑上，请把后端公网地址填在这里。
                      </Typography.Text>
                    )}
                    <Input
                      value={apiBaseUrlInput}
                      placeholder="例如 https://api.example.com 或 http://127.0.0.1:8010"
                      onChange={(event) => setApiBaseUrlInput(event.target.value)}
                      status={!backendReachable ? "warning" : undefined}
                    />
                    <Space wrap>
                      <Button type={!backendReachable ? "primary" : "default"} onClick={() => void handleSaveApiBaseUrl()}>
                        {!backendReachable ? "连接" : "保存地址"}
                      </Button>
                      <Button onClick={() => void handleResetApiBaseUrl()}>恢复默认</Button>
                    </Space>
                  </Space>
                </Card>

                <Divider style={{ margin: 0 }} />

                <Flex justify="space-between" align="center">
                  <Typography.Title level={4} style={{ margin: 0 }}>
                    <HistoryOutlined /> 岗位历史
                  </Typography.Title>
                  <Button type="link" onClick={() => void refreshJobs()}>
                    刷新
                  </Button>
                </Flex>

                {jobs.length === 0 ? (
                  <Empty description="还没有岗位，先创建一个" />
                ) : (
                  <List
                    dataSource={jobs}
                    renderItem={(job) => (
                      <List.Item
                        style={{
                          borderRadius: 18,
                          padding: 14,
                          marginBottom: 10,
                          cursor: "pointer",
                          border: job.id === selectedJob?.id ? "1px solid rgba(20,125,100,0.28)" : "1px solid transparent",
                          background: job.id === selectedJob?.id ? "rgba(20,125,100,0.08)" : "rgba(255,255,255,0.54)"
                        }}
                        onClick={() => void loadJob(job.id)}
                      >
                        <Flex align="flex-start" justify="space-between" style={{ width: "100%", gap: 12 }}>
                          <List.Item.Meta
                            title={<Typography.Text strong>{job.title}</Typography.Text>}
                            description={
                              <Space direction="vertical" size={4}>
                                <Tag color="blue">{jobStatusLabels[job.status] ?? job.status}</Tag>
                                <Typography.Text type="secondary">{new Date(job.updated_at).toLocaleString()}</Typography.Text>
                              </Space>
                            }
                          />
                          <Popconfirm
                            title="删除这个岗位历史？"
                            description="岗位、简历、报告和筛选记录会一起删除。"
                            okText="删除"
                            cancelText="取消"
                            okButtonProps={{ danger: true }}
                            onConfirm={() => void handleDeleteJob(job)}
                          >
                            <Button
                              type="text"
                              danger
                              icon={<DeleteOutlined />}
                              aria-label={`删除岗位 ${job.title}`}
                              onClick={(event) => event.stopPropagation()}
                            />
                          </Popconfirm>
                        </Flex>
                      </List.Item>
                    )}
                  />
                )}
              </Space>
            </Card>
          </Col>

          <Col xs={24} lg={18} xl={19}>
            <Space direction="vertical" size={24} style={{ width: "100%" }}>
              <Card className="glass-card" style={{ borderRadius: 28 }}>
                <Space direction="vertical" size={20} style={{ width: "100%" }}>
                  <Space direction="vertical" size={4}>
                    <Typography.Title level={1} className="panel-title" style={{ margin: 0 }}>
                      招聘人员的岗位冻结台
                    </Typography.Title>
                    <Typography.Text type="secondary">
                      先把岗位标准问清楚，再让模型批量筛简历。
                    </Typography.Text>
                  </Space>
                  <Steps current={currentStep()} items={stepItems} />
                </Space>
              </Card>

              {pageLoading ? (
                <Card className="glass-card" style={{ borderRadius: 28 }}>
                  <Flex align="center" justify="center" style={{ minHeight: 360 }}>
                    <Spin size="large" />
                  </Flex>
                </Card>
              ) : (
                <Space direction="vertical" size={24} style={{ width: "100%" }}>
                  <Card className="glass-card" style={{ borderRadius: 28 }}>
                    <Space direction="vertical" size={18} style={{ width: "100%" }}>
                      <Flex justify="space-between" align="center">
                        <div>
                          <Typography.Title level={3} style={{ marginBottom: 4 }}>
                            <FolderOpenOutlined /> 1. 岗位创建
                          </Typography.Title>
                          <Typography.Text type="secondary">
                            支持粘贴 JD 文本，或上传 PDF / DOCX / TXT 文档。
                          </Typography.Text>
                        </div>
                        <Button type="primary" icon={<RocketOutlined />} loading={actionLoading} onClick={() => void handleImportJob()}>
                          导入岗位
                        </Button>
                      </Flex>

                      <Row gutter={16}>
                        <Col xs={24} xl={14}>
                          <Input.TextArea
                            rows={10}
                            placeholder="直接粘贴岗位 JD..."
                            value={jdText}
                            onChange={(event) => setJdText(event.target.value)}
                          />
                        </Col>
                        <Col xs={24} xl={10}>
                          <Upload
                            fileList={jdFiles}
                            beforeUpload={(file) => {
                              setJdFiles([normalizeUploadFile(file)]);
                              return false;
                            }}
                            onRemove={() => {
                              setJdFiles([]);
                              return true;
                            }}
                            maxCount={1}
                          >
                            <Button icon={<UploadOutlined />}>选择 JD 文件</Button>
                          </Upload>

                          {selectedJob ? (
                            <Card
                              size="small"
                              style={{
                                borderRadius: 18,
                                marginTop: 16,
                                background: "rgba(20,125,100,0.05)"
                              }}
                            >
                              <Space direction="vertical" size={8}>
                                <Tag color="green">当前岗位</Tag>
                                <Typography.Title level={4} style={{ margin: 0 }}>
                                  {selectedJob.title}
                                </Typography.Title>
                                <Typography.Paragraph
                                  type="secondary"
                                  style={{ marginBottom: 0, whiteSpace: "pre-wrap", lineHeight: 1.75 }}
                                >
                                  {selectedJob.parsed_jd.summary}
                                </Typography.Paragraph>

                                {buildJobRequirementHighlights(selectedJob).length ? (
                                  <Card
                                    size="small"
                                    style={{
                                      borderRadius: 14,
                                      background: "rgba(255,255,255,0.7)",
                                      border: "1px solid rgba(20,125,100,0.12)",
                                    }}
                                  >
                                    <Space direction="vertical" size={6} style={{ width: "100%" }}>
                                      <Typography.Text strong>关键要求</Typography.Text>
                                      {buildJobRequirementHighlights(selectedJob).map((item) => (
                                        <Typography.Text key={item} type="secondary" style={{ lineHeight: 1.7 }}>
                                          {item}
                                        </Typography.Text>
                                      ))}
                                    </Space>
                                  </Card>
                                ) : null}

                                <Card
                                  size="small"
                                  style={{
                                    borderRadius: 14,
                                    background: "rgba(255,255,255,0.78)",
                                    border: "1px solid rgba(15,108,128,0.12)",
                                  }}
                                >
                                  <Space direction="vertical" size={6} style={{ width: "100%" }}>
                                    <Flex justify="space-between" align="center">
                                      <Typography.Text strong>JD 要求全文</Typography.Text>
                                      <Typography.Text type="secondary">可滚动查看</Typography.Text>
                                    </Flex>
                                    <div
                                      style={{
                                        maxHeight: 220,
                                        overflowY: "auto",
                                        paddingRight: 4,
                                      }}
                                    >
                                      <Typography.Paragraph
                                        style={{
                                          marginBottom: 0,
                                          whiteSpace: "pre-wrap",
                                          lineHeight: 1.8,
                                          color: "var(--text-subtle)",
                                        }}
                                      >
                                        {formatJdTextForDisplay(selectedJob.jd_text)}
                                      </Typography.Paragraph>
                                    </div>
                                  </Space>
                                </Card>

                                <Space wrap>
                                  {selectedJob.parsed_jd.industry_tags.map((tag) => (
                                    <Tag key={tag}>{tag}</Tag>
                                  ))}
                                  {selectedJob.parsed_jd.language_requirements.map((tag) => (
                                    <Tag key={tag} color="cyan">
                                      {tag}
                                    </Tag>
                                  ))}
                                </Space>
                              </Space>
                            </Card>
                          ) : null}
                        </Col>
                      </Row>
                    </Space>
                  </Card>

                  <Card className="glass-card" style={{ borderRadius: 28 }}>
                    <Space direction="vertical" size={18} style={{ width: "100%" }}>
                      <Flex justify="space-between" align="center">
                        <div>
                          <Typography.Title level={3} style={{ marginBottom: 4 }}>
                            <SafetyCertificateOutlined /> 2. AI追问
                          </Typography.Title>
                          <Typography.Text type="secondary">
                            招聘方回答完，系统才会编译岗位画像。
                          </Typography.Text>
                        </div>
                        <Button
                          type="primary"
                          loading={actionLoading}
                          onClick={() => void handleGenerateProfile()}
                          disabled={!selectedJob?.interview_session?.questions?.length}
                        >
                          生成岗位画像
                        </Button>
                      </Flex>

                      {selectedJob?.interview_session?.questions?.length ? (
                        <List
                          dataSource={selectedJob.interview_session.questions}
                          renderItem={(question) => (
                            <List.Item style={{ display: "block", paddingInline: 0 }}>
                              <Card size="small" style={{ borderRadius: 18 }}>
                                <Space direction="vertical" size={10} style={{ width: "100%" }}>
                                  <Flex justify="space-between" align="center">
                                    <Typography.Text strong>{question.title}</Typography.Text>
                                    <Tag color="blue">{question.category}</Tag>
                                  </Flex>
                                  <Typography.Text type="secondary">{question.prompt}</Typography.Text>
                                  <Input.TextArea
                                    rows={3}
                                    value={answers[question.id] ?? ""}
                                    placeholder="请输入招聘方答案"
                                    onChange={(event) =>
                                      setAnswers((current) => ({ ...current, [question.id]: event.target.value }))
                                    }
                                  />
                                </Space>
                              </Card>
                            </List.Item>
                          )}
                        />
                      ) : (
                        <Empty description="先导入岗位后，这里会出现 AI 追问" />
                      )}
                    </Space>
                  </Card>

                  <Card className="glass-card" style={{ borderRadius: 28 }}>
                    <Space direction="vertical" size={18} style={{ width: "100%" }}>
                      <Flex justify="space-between" align="center">
                        <div>
                          <Typography.Title level={3} style={{ marginBottom: 4 }}>
                            <ClockCircleOutlined /> 3. 规则确认
                          </Typography.Title>
                          <Typography.Text type="secondary">
                            允许人工改写规则，再冻结为岗位版本。
                          </Typography.Text>
                        </div>
                        <Button type="primary" loading={actionLoading} onClick={() => void handleFreezeProfile()} disabled={!profileDraft}>
                          冻结岗位画像
                        </Button>
                      </Flex>

                      {profileDraft ? (
                        <Space direction="vertical" size={18} style={{ width: "100%" }}>
                          <Input.TextArea
                            rows={3}
                            value={profileDraft.role_summary}
                            onChange={(event) =>
                              updateDraft((draft) => ({ ...draft, role_summary: event.target.value }))
                            }
                          />

                          <Row gutter={16}>
                            <Col xs={24} xl={12}>
                              <Card size="small" title="硬性门槛" style={{ borderRadius: 18, height: "100%" }}>
                                <Space direction="vertical" size={12} style={{ width: "100%" }}>
                                  {profileDraft.hard_constraints.map((rule, index) => (
                                    <Card key={rule.id} size="small" style={{ borderRadius: 14 }}>
                                      <Space direction="vertical" size={10} style={{ width: "100%" }}>
                                        <Input
                                          value={rule.label}
                                          onChange={(event) =>
                                            updateDraft((draft) => {
                                              const next = [...draft.hard_constraints];
                                              next[index] = { ...next[index], label: event.target.value };
                                              return { ...draft, hard_constraints: next };
                                            })
                                          }
                                        />
                                        <Input.TextArea
                                          rows={2}
                                          value={rule.description}
                                          onChange={(event) =>
                                            updateDraft((draft) => {
                                              const next = [...draft.hard_constraints];
                                              next[index] = { ...next[index], description: event.target.value };
                                              return { ...draft, hard_constraints: next };
                                            })
                                          }
                                        />
                                        <Input
                                          value={formatRuleValue(rule.value)}
                                          onChange={(event) =>
                                            updateDraft((draft) => {
                                              const next = [...draft.hard_constraints];
                                              next[index] = { ...next[index], value: parseLooseValue(event.target.value) };
                                              return { ...draft, hard_constraints: next };
                                            })
                                          }
                                        />
                                      </Space>
                                    </Card>
                                  ))}
                                </Space>
                              </Card>
                            </Col>
                            <Col xs={24} xl={12}>
                              <Card size="small" title="可放宽条件" style={{ borderRadius: 18, height: "100%" }}>
                                <Space direction="vertical" size={12} style={{ width: "100%" }}>
                                  {profileDraft.soft_constraints.map((rule, index) => (
                                    <Card key={rule.id} size="small" style={{ borderRadius: 14 }}>
                                      <Space direction="vertical" size={10} style={{ width: "100%" }}>
                                        <Input
                                          value={rule.label}
                                          onChange={(event) =>
                                            updateDraft((draft) => {
                                              const next = [...draft.soft_constraints];
                                              next[index] = { ...next[index], label: event.target.value };
                                              return { ...draft, soft_constraints: next };
                                            })
                                          }
                                        />
                                        <Input.TextArea
                                          rows={2}
                                          value={rule.description}
                                          onChange={(event) =>
                                            updateDraft((draft) => {
                                              const next = [...draft.soft_constraints];
                                              next[index] = { ...next[index], description: event.target.value };
                                              return { ...draft, soft_constraints: next };
                                            })
                                          }
                                        />
                                      </Space>
                                    </Card>
                                  ))}
                                </Space>
                              </Card>
                            </Col>
                          </Row>

                          <Card size="small" title="评分维度" style={{ borderRadius: 18 }}>
                            <Space direction="vertical" size={12} style={{ width: "100%" }}>
                              {profileDraft.scoring_dimensions.map((dimension, index) => (
                                <Card key={dimension.id} size="small" style={{ borderRadius: 14 }}>
                                  <Row gutter={12}>
                                    <Col xs={24} md={8}>
                                      <Input
                                        value={dimension.name}
                                        onChange={(event) =>
                                          updateDraft((draft) => {
                                            const next = [...draft.scoring_dimensions];
                                            next[index] = { ...next[index], name: event.target.value };
                                            return { ...draft, scoring_dimensions: next };
                                          })
                                        }
                                      />
                                    </Col>
                                    <Col xs={24} md={4}>
                                      <Input
                                        value={dimension.weight}
                                        onChange={(event) =>
                                          updateDraft((draft) => {
                                            const next = [...draft.scoring_dimensions];
                                            next[index] = { ...next[index], weight: Number(event.target.value) || 0 };
                                            return { ...draft, scoring_dimensions: next };
                                          })
                                        }
                                      />
                                    </Col>
                                    <Col xs={24} md={12}>
                                      <Input
                                        value={dimension.description}
                                        onChange={(event) =>
                                          updateDraft((draft) => {
                                            const next = [...draft.scoring_dimensions];
                                            next[index] = { ...next[index], description: event.target.value };
                                            return { ...draft, scoring_dimensions: next };
                                          })
                                        }
                                      />
                                    </Col>
                                  </Row>
                                </Card>
                              ))}
                            </Space>
                          </Card>

                          <Row gutter={16}>
                            <Col xs={24} xl={12}>
                              <Card size="small" title="输出要求" style={{ borderRadius: 18, height: "100%" }}>
                                <Space direction="vertical" size={12} style={{ width: "100%" }}>
                                  {profileDraft.output_requirements.map((item, index) => (
                                    <Input.TextArea
                                      key={`${index}-${item}`}
                                      rows={2}
                                      value={item}
                                      onChange={(event) =>
                                        updateDraftTextList("output_requirements", index, event.target.value)
                                      }
                                    />
                                  ))}
                                </Space>
                              </Card>
                            </Col>
                            <Col xs={24} xl={12}>
                              <Card size="small" title="面试追问重点" style={{ borderRadius: 18, height: "100%" }}>
                                <Space direction="vertical" size={12} style={{ width: "100%" }}>
                                  {profileDraft.interview_focus.map((item, index) => (
                                    <Input.TextArea
                                      key={`${index}-${item}`}
                                      rows={2}
                                      value={item}
                                      onChange={(event) =>
                                        updateDraftTextList("interview_focus", index, event.target.value)
                                      }
                                    />
                                  ))}
                                </Space>
                              </Card>
                            </Col>
                          </Row>

                          <Card size="small" title="边界条件与失败画像" style={{ borderRadius: 18 }}>
                            <Space direction="vertical" size={12} style={{ width: "100%" }}>
                              {profileDraft.boundaries.map((item, index) => (
                                <Input.TextArea
                                  key={`${index}-${item}`}
                                  rows={2}
                                  value={item}
                                  onChange={(event) => updateDraftTextList("boundaries", index, event.target.value)}
                                />
                              ))}
                            </Space>
                          </Card>

                          <Card size="small" title="PromptBundle 预览" style={{ borderRadius: 18 }}>
                            <Space direction="vertical" size={8} style={{ width: "100%" }}>
                              <Typography.Text type="secondary">冻结岗位画像时，会按你当前编辑后的规则重新生成。</Typography.Text>
                              <Input.TextArea
                                readOnly
                                autoSize={{ minRows: 8, maxRows: 18 }}
                                value={profileDraft.prompt_bundle.rendered_prompt}
                              />
                            </Space>
                          </Card>
                        </Space>
                      ) : (
                        <Empty description="回答 AI 追问后，这里会出现可编辑的岗位画像草稿" />
                      )}
                    </Space>
                  </Card>

                  <Card className="glass-card" style={{ borderRadius: 28 }}>
                    <Space direction="vertical" size={18} style={{ width: "100%" }}>
                      <Flex justify="space-between" align="center">
                        <div>
                          <Typography.Title level={3} style={{ marginBottom: 4 }}>
                            <FileSearchOutlined /> 4. 筛选看板
                          </Typography.Title>
                          <Typography.Text type="secondary">
                            上传简历，查看自动初筛与人工复核入口。
                          </Typography.Text>
                        </div>
                        <Space>
                          <Upload
                            fileList={resumeFiles}
                            beforeUpload={(file) => {
                              setResumeFiles((current) => [...current, normalizeUploadFile(file)]);
                              return false;
                            }}
                            onRemove={(file) => {
                              setResumeFiles((current) => current.filter((item) => item.uid !== file.uid));
                              return true;
                            }}
                            multiple
                          >
                            <Button icon={<UploadOutlined />}>选择简历</Button>
                          </Upload>
                          <Button
                            type="primary"
                            loading={actionLoading}
                            onClick={() => void handleUploadResumes()}
                            disabled={!selectedJob?.current_profile_version}
                          >
                            批量上传并评估
                          </Button>
                        </Space>
                      </Flex>

                      {dashboard ? (
                        <Space direction="vertical" size={18} style={{ width: "100%" }}>
                          <Row gutter={16}>
                            <Col xs={12} md={6}>
                              <Card size="small" style={{ borderRadius: 18 }}>
                                <Statistic title="总简历数" value={dashboard.stats.total} />
                              </Card>
                            </Col>
                            <Col xs={12} md={6}>
                              <Card size="small" style={{ borderRadius: 18 }}>
                                <Statistic title="建议面试" value={dashboard.stats.recommend_interview} />
                              </Card>
                            </Col>
                            <Col xs={12} md={6}>
                              <Card size="small" style={{ borderRadius: 18 }}>
                                <Statistic title="人工复核" value={dashboard.stats.manual_review} />
                              </Card>
                            </Col>
                            <Col xs={12} md={6}>
                              <Card size="small" style={{ borderRadius: 18 }}>
                                <Statistic title="自动淘汰待确认" value={dashboard.stats.auto_reject_review} />
                              </Card>
                            </Col>
                          </Row>

                          <Table
                            rowKey="submission_id"
                            columns={jobColumns}
                            dataSource={dashboard.evaluations}
                            pagination={false}
                            scroll={{ x: 860 }}
                          />
                        </Space>
                      ) : (
                        <Empty description="冻结岗位画像后，这里会出现筛选看板与候选人报告" />
                      )}
                    </Space>
                  </Card>
                </Space>
              )}
            </Space>
          </Col>
        </Row>

        <EvaluationDrawer
          open={drawerOpen}
          loading={actionLoading}
          evaluation={evaluationDetail}
          onClose={() => setDrawerOpen(false)}
          onSubmitDecision={handleSubmitDecision}
        />
      </div>
  );
}
