import { useEffect, useMemo, useState } from 'react'

import { getConfig, updateConfig } from '../../api/config'
import type {
  ConfigField,
  ConfigValue,
  EditableModelConfig,
  ProviderKind,
} from '../../api/config'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'
import { Textarea } from '../../components/ui/textarea'

type DraftValue = string | boolean
type DraftState = Record<string, DraftValue>
type ModelConfigState = Record<string, EditableModelConfig>
const LEGACY_MODEL_FIELD_KEYS = new Set([
  'dashscope_api_key',
  'chat_model_name',
  'embedding_model_name',
  'rerank_model_name',
  'rewrite_model_name',
])
const MODEL_ROLE_LABELS: Record<string, string> = {
  chat: '聊天模型',
  rewrite: '改写模型',
  embedding: 'Embedding 模型',
  rerank: 'Rerank 模型',
}

function buildDraft(fields: ConfigField[]): DraftState {
  return Object.fromEntries(
    fields.map((field) => {
      if (field.input_type === 'checkbox') {
        return [field.key, Boolean(field.value)]
      }
      if (field.input_type === 'json-textarea') {
        const fallbackValue: string[] = []
        return [field.key, JSON.stringify(field.value ?? fallbackValue, null, 2)]
      }
      return [field.key, field.value == null ? '' : String(field.value)]
    }),
  )
}

function parseFieldValue(field: ConfigField, draftValue: DraftValue): ConfigValue {
  if (field.input_type === 'checkbox') {
    return Boolean(draftValue)
  }

  const textValue = typeof draftValue === 'string' ? draftValue : String(draftValue)

  if (field.input_type === 'number') {
    const trimmed = textValue.trim()
    if (!trimmed) {
      if (field.nullable) return null
      throw new Error(`${field.label} 不能为空`)
    }

    const numericValue = Number(trimmed)
    if (Number.isNaN(numericValue)) {
      throw new Error(`${field.label} 必须是数字`)
    }
    return numericValue
  }

  if (field.input_type === 'json-textarea') {
    const trimmed = textValue.trim()
    if (!trimmed) return []

    let parsed: unknown
    try {
      parsed = JSON.parse(trimmed)
    } catch {
      throw new Error(`${field.label} 必须是合法的 JSON 数组`)
    }

    if (!Array.isArray(parsed) || parsed.some((item) => typeof item !== 'string')) {
      throw new Error(`${field.label} 必须是字符串数组`)
    }
    return parsed
  }

  return textValue
}

function renderFieldDescription(field: ConfigField) {
  return (
    <div className="config-field__meta">
      <span>{field.description}</span>
      {field.nullable && <span>允许留空</span>}
    </div>
  )
}

export default function ConfigPage() {
  const [fields, setFields] = useState<ConfigField[]>([])
  const [draft, setDraft] = useState<DraftState>({})
  const [initialDraft, setInitialDraft] = useState<DraftState>({})
  const [modelConfigs, setModelConfigs] = useState<ModelConfigState>({})
  const [initialModelConfigs, setInitialModelConfigs] = useState<ModelConfigState>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [advancedOpen, setAdvancedOpen] = useState(false)

  useEffect(() => {
    let cancelled = false

    const loadConfig = async () => {
      try {
        const response = await getConfig()
        if (cancelled) return

        const nextDraft = buildDraft(response.fields)
        setFields(response.fields)
        setDraft(nextDraft)
        setInitialDraft(nextDraft)
        setModelConfigs(response.model_configs)
        setInitialModelConfigs(response.model_configs)
        setError(null)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void loadConfig()

    return () => {
      cancelled = true
    }
  }, [])

  const commonFields = useMemo(
    () =>
      fields.filter(
        (field) => !field.advanced && !LEGACY_MODEL_FIELD_KEYS.has(field.key),
      ),
    [fields],
  )

  const advancedGroups = useMemo(() => {
    return fields
      .filter((field) => field.advanced && !LEGACY_MODEL_FIELD_KEYS.has(field.key))
      .reduce<Record<string, ConfigField[]>>((acc, field) => {
        acc[field.group] ??= []
        acc[field.group].push(field)
        return acc
      }, {})
  }, [fields])

  const isDirty =
    JSON.stringify(draft) !== JSON.stringify(initialDraft) ||
    JSON.stringify(modelConfigs) !== JSON.stringify(initialModelConfigs)
  const statusText = loading
    ? '加载中'
    : saving
      ? '保存中'
      : success
        ? '已保存'
        : isDirty
          ? '有未保存更改'
          : '配置已同步'

  const handleChange = (key: string, value: DraftValue) => {
    setDraft((prev) => ({ ...prev, [key]: value }))
    setError(null)
    setSuccess(null)
  }

  const handleReset = () => {
    setDraft(initialDraft)
    setModelConfigs(initialModelConfigs)
    setError(null)
    setSuccess(null)
  }

  const handleModelConfigChange = (
    role: string,
    key: keyof EditableModelConfig,
    value: string,
  ) => {
    setModelConfigs((prev) => ({
      ...prev,
      [role]: {
        ...prev[role],
        [key]: key === 'provider_kind' ? (value as ProviderKind) : value,
      },
    }))
    setError(null)
    setSuccess(null)
  }

  const handleSave = async () => {
    if (saving || loading) return

    try {
      const values = Object.fromEntries(
        fields.map((field) => [field.key, parseFieldValue(field, draft[field.key])]),
      ) as Record<string, ConfigValue>

      setSaving(true)
      setError(null)
      setSuccess(null)

      const response = await updateConfig({ values, model_configs: modelConfigs })
      const nextDraft = buildDraft(response.fields)
      setFields(response.fields)
      setDraft(nextDraft)
      setInitialDraft(nextDraft)
      setModelConfigs(response.model_configs)
      setInitialModelConfigs(response.model_configs)
      setSuccess(response.message)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h2 className="page-title">配置</h2>
          <p className="page-description">
            统一管理 API Key、模型参数和检索策略。保存后会把 JSON 配置提交到后端并刷新运行中的服务。
          </p>
        </div>
        <Badge variant={success ? 'success' : isDirty ? 'warning' : 'outline'}>{statusText}</Badge>
      </header>

      <Card className="panel">
        <CardHeader>
          <CardTitle>保存策略</CardTitle>
          <CardDescription>
            修改将写入项目根目录 `.env`，随后立即刷新配置缓存与主要运行服务。
          </CardDescription>
        </CardHeader>
        <CardContent className="panel-content">
          <div className="config-actions">
            <Button onClick={handleSave} disabled={loading || saving || fields.length === 0}>
              {saving ? '保存中...' : '保存配置'}
            </Button>
            <Button
              variant="secondary"
              onClick={handleReset}
              disabled={loading || saving || !isDirty}
            >
              重置修改
            </Button>
            <Button
              variant="ghost"
              onClick={() => setAdvancedOpen((prev) => !prev)}
              disabled={loading || fields.length === 0}
            >
              {advancedOpen ? '收起高级设置' : '展开高级设置'}
            </Button>
          </div>

          {error && <div className="ui-alert ui-alert--error">{error}</div>}
          {success && <div className="ui-alert">{success}</div>}
        </CardContent>
      </Card>

      <Card className="panel">
        <CardHeader>
          <CardTitle>常用配置</CardTitle>
          <CardDescription>高频参数集中展示，适合日常调整模型与主流程策略。</CardDescription>
        </CardHeader>
        <CardContent className="panel-content">
          {loading ? (
            <div className="empty-box">正在加载配置...</div>
          ) : (
            <div className="config-form-grid">
              {commonFields.map((field) => (
                <div key={field.key} className="config-field">
                  <div className="config-field__header">
                    <label className="field-label" htmlFor={`config-${field.key}`}>
                      {field.label}
                    </label>
                    {field.sensitive && <Badge variant="outline">敏感</Badge>}
                  </div>

                  {field.input_type === 'checkbox' ? (
                    <label className="config-checkbox" htmlFor={`config-${field.key}`}>
                      <input
                        id={`config-${field.key}`}
                        type="checkbox"
                        checked={Boolean(draft[field.key])}
                        onChange={(e) => handleChange(field.key, e.target.checked)}
                      />
                      <span>启用</span>
                    </label>
                  ) : field.input_type === 'json-textarea' ? (
                    <Textarea
                      id={`config-${field.key}`}
                      rows={5}
                      value={String(draft[field.key] ?? '')}
                      onChange={(e) => handleChange(field.key, e.target.value)}
                    />
                  ) : (
                    <input
                      id={`config-${field.key}`}
                      className="config-input"
                      type={field.input_type === 'password' ? 'password' : field.input_type}
                      step={field.input_type === 'number' ? 'any' : undefined}
                      value={String(draft[field.key] ?? '')}
                      onChange={(e) => handleChange(field.key, e.target.value)}
                    />
                  )}

                  {renderFieldDescription(field)}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {Object.keys(modelConfigs).length > 0 && (
        <Card className="panel">
          <CardHeader>
            <CardTitle>模型配置</CardTitle>
            <CardDescription>
              分别配置聊天、改写、Embedding 和 Rerank 模型的 provider、模型名、接口地址与
              API key。
            </CardDescription>
          </CardHeader>
          <CardContent className="panel-content">
            <div className="config-form-grid">
              {Object.entries(modelConfigs).map(([role, modelConfig]) => (
                <div key={role} className="config-field">
                  <div className="config-field__header">
                    <label className="field-label">{MODEL_ROLE_LABELS[role] ?? role}</label>
                    <Badge variant="outline">{role}</Badge>
                  </div>

                  <div className="config-field__stack">
                    <label className="field-label" htmlFor={`model-provider-${role}`}>
                      Provider
                    </label>
                    <select
                      id={`model-provider-${role}`}
                      className="config-input"
                      value={modelConfig.provider_kind}
                      onChange={(e) =>
                        handleModelConfigChange(role, 'provider_kind', e.target.value)
                      }
                    >
                      <option value="openai_compatible">OpenAI Compatible</option>
                      <option value="dashscope">DashScope</option>
                    </select>
                  </div>

                  <div className="config-field__stack">
                    <label className="field-label" htmlFor={`model-name-${role}`}>
                      模型名称
                    </label>
                    <input
                      id={`model-name-${role}`}
                      className="config-input"
                      value={modelConfig.model}
                      onChange={(e) => handleModelConfigChange(role, 'model', e.target.value)}
                    />
                  </div>

                  <div className="config-field__stack">
                    <label className="field-label" htmlFor={`model-url-${role}`}>
                      URL
                    </label>
                    <input
                      id={`model-url-${role}`}
                      className="config-input"
                      value={modelConfig.base_url}
                      placeholder={
                        modelConfig.provider_kind === 'dashscope'
                          ? 'DashScope 可留空'
                          : 'https://your-openai-compatible-host/v1'
                      }
                      onChange={(e) => handleModelConfigChange(role, 'base_url', e.target.value)}
                    />
                  </div>

                  <div className="config-field__stack">
                    <label className="field-label" htmlFor={`model-api-key-${role}`}>
                      API Key
                    </label>
                    <input
                      id={`model-api-key-${role}`}
                      className="config-input"
                      type="password"
                      value={modelConfig.api_key}
                      onChange={(e) => handleModelConfigChange(role, 'api_key', e.target.value)}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {advancedOpen && (
        <Card className="panel">
          <CardHeader>
            <CardTitle>高级设置</CardTitle>
            <CardDescription>包含路径、文本切分、重排和 Query Rewrite 的完整参数。</CardDescription>
          </CardHeader>
          <CardContent className="panel-content">
            {Object.entries(advancedGroups).map(([groupName, groupFields]) => (
              <section key={groupName} className="config-group">
                <div className="config-group__header">
                  <h3>{groupName}</h3>
                  <span>{groupFields.length} 项</span>
                </div>

                <div className="config-form-grid">
                  {groupFields.map((field) => (
                    <div key={field.key} className="config-field">
                      <label className="field-label" htmlFor={`config-${field.key}`}>
                        {field.label}
                      </label>

                      {field.input_type === 'checkbox' ? (
                        <label className="config-checkbox" htmlFor={`config-${field.key}`}>
                          <input
                            id={`config-${field.key}`}
                            type="checkbox"
                            checked={Boolean(draft[field.key])}
                            onChange={(e) => handleChange(field.key, e.target.checked)}
                          />
                          <span>启用</span>
                        </label>
                      ) : field.input_type === 'json-textarea' ? (
                        <Textarea
                          id={`config-${field.key}`}
                          rows={5}
                          value={String(draft[field.key] ?? '')}
                          onChange={(e) => handleChange(field.key, e.target.value)}
                        />
                      ) : (
                        <input
                          id={`config-${field.key}`}
                          className="config-input"
                          type={field.input_type === 'password' ? 'password' : field.input_type}
                          step={field.input_type === 'number' ? 'any' : undefined}
                          value={String(draft[field.key] ?? '')}
                          onChange={(e) => handleChange(field.key, e.target.value)}
                        />
                      )}

                      {renderFieldDescription(field)}
                    </div>
                  ))}
                </div>
              </section>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}