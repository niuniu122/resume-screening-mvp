"use client";

import { useState } from "react";
import { Alert, Button, Descriptions, Divider, Drawer, Input, Radio, Space, Tag, Typography } from "antd";
import ReactMarkdown from "react-markdown";

import type { EvaluationDetail } from "../lib/types";

const decisionOptions = ["进入面试", "人工复核", "淘汰"];
const evaluationStatusLabels: Record<string, string> = {
  auto_reject_review: "自动淘汰待确认",
  manual_review: "人工复核",
  recommend_interview: "建议面试",
  recommend_reject: "建议淘汰",
};

const hardRuleStatusLabels: Record<string, string> = {
  met: "已满足",
  unmet: "不满足",
  unknown: "待核实",
};

function inferDisplayName(evaluation: EvaluationDetail): string {
  const fallbackFromFilename = evaluation.filename.replace(/\.[^.]+$/, "");
  return evaluation.candidate_name || fallbackFromFilename || "未识别候选人";
}

function normalizeReportMarkdown(evaluation: EvaluationDetail): string {
  const displayName = inferDisplayName(evaluation);
  return evaluation.markdown_report
    .replace(/- 候选人：.*$/m, `- 候选人：${displayName}`)
    .replace(
      /- 当前状态：\*\*.*\*\*/m,
      `- 当前状态：**${evaluationStatusLabels[evaluation.status] ?? evaluation.status}**`
    )
    .replace(/：met；/g, `：${hardRuleStatusLabels.met}；`)
    .replace(/：unmet；/g, `：${hardRuleStatusLabels.unmet}；`)
    .replace(/：unknown；/g, `：${hardRuleStatusLabels.unknown}；`);
}

interface EvaluationDrawerProps {
  open: boolean;
  loading: boolean;
  evaluation: EvaluationDetail | null;
  onClose: () => void;
  onSubmitDecision: (decision: string, comment: string) => Promise<void>;
}

export function EvaluationDrawer(props: EvaluationDrawerProps) {
  const { open, loading, evaluation, onClose, onSubmitDecision } = props;
  const [decision, setDecision] = useState("人工复核");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const displayName = evaluation ? inferDisplayName(evaluation) : "未识别候选人";
  const displayMarkdownReport = evaluation ? normalizeReportMarkdown(evaluation) : "";

  async function handleSubmit() {
    if (!decision) {
      return;
    }
    setSubmitting(true);
    try {
      await onSubmitDecision(decision, comment);
      setComment("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Drawer
      width={720}
      open={open}
      onClose={onClose}
      title={evaluation ? `${displayName} · 诊断报告` : "候选人报告"}
      extra={
        <Tag color="processing">
          {evaluation ? evaluationStatusLabels[evaluation.status] ?? evaluation.status : "加载中"}
        </Tag>
      }
    >
      {evaluation ? (
        <Space direction="vertical" size={20} style={{ width: "100%" }}>
          <Descriptions
            bordered
            size="small"
            column={1}
            items={[
              { key: "job", label: "目标岗位", children: evaluation.job_title },
              { key: "file", label: "文件", children: evaluation.filename },
              {
                key: "score",
                label: "综合分",
                children: evaluation.overall_score ? `${evaluation.overall_score}` : "待计算"
              },
              {
                key: "manual",
                label: "人工结论",
                children: evaluation.manual_decision ?? "尚未确认"
              }
            ]}
          />

          {evaluation.warnings.length > 0 ? (
            <Alert
              type="warning"
              showIcon
              message="履历伪装预警"
              description={
                <Space wrap>
                  {evaluation.warnings.map((warning) => (
                    <Tag key={warning} color="gold">
                      {warning}
                    </Tag>
                  ))}
                </Space>
              }
            />
          ) : null}

          {evaluation.info_gaps.length > 0 ? (
            <Alert
              type="info"
              showIcon
              message="信息缺口"
              description={
                <Space direction="vertical" size={4}>
                  {evaluation.info_gaps.map((gap) => (
                    <Typography.Text key={gap}>{gap}</Typography.Text>
                  ))}
                </Space>
              }
            />
          ) : null}

          <div>
            <Typography.Title level={5}>压力面试建议</Typography.Title>
            <Space direction="vertical" size={8}>
              {evaluation.interview_questions.map((question, index) => (
                <Typography.Paragraph key={question} style={{ marginBottom: 0 }}>
                  {index + 1}. {question}
                </Typography.Paragraph>
              ))}
            </Space>
          </div>

          <Divider style={{ margin: "4px 0" }} />

          <div className="markdown-report">
            <ReactMarkdown>{displayMarkdownReport}</ReactMarkdown>
          </div>

          <Divider />

          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Typography.Title level={5}>人工复核结论</Typography.Title>
            <Radio.Group
              optionType="button"
              buttonStyle="solid"
              value={decision}
              onChange={(event) => setDecision(event.target.value)}
              options={decisionOptions.map((item) => ({ label: item, value: item }))}
            />
            <Input.TextArea
              rows={4}
              placeholder="补充说明为什么要推进、复核或淘汰"
              value={comment}
              onChange={(event) => setComment(event.target.value)}
            />
            <Button type="primary" loading={submitting || loading} onClick={handleSubmit}>
              保存人工结论
            </Button>
          </Space>
        </Space>
      ) : (
        <Typography.Text type="secondary">请选择一位候选人查看诊断结果。</Typography.Text>
      )}
    </Drawer>
  );
}
