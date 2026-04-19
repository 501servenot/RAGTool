import { Alert, Button, Card, Checkbox, Input, Select, Tag } from 'antd'
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { gsap } from 'gsap'
import { ChevronDown } from 'lucide-react'

import { getConfig, updateConfig } from '../../api/config'
import type {
  ConfigField,
  ConfigValue,
  EditableModelConfig,
  ProviderKind,
} from '../../api/config'
import { useConfigNavigationGuard } from '../../contexts/ConfigNavigationGuard'

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
const MODEL_PROVIDER_OPTIONS: Array<{ label: string; value: ProviderKind }> = [
  { label: 'OpenAI Compatible', value: 'openai_compatible' },
  { label: 'DashScope', value: 'dashscope' },
]
const { TextArea } = Input

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

function getStatusTagColor(status: 'success' | 'warning' | 'outline') {
  if (status === 'success') return 'success'
  if (status === 'warning') return 'warning'
  return 'default'
}

export default function ConfigPage() {
  const {
    clearUnsavedWarning,
    setConfigDirty,
    unsavedWarning,
  } = useConfigNavigationGuard()
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
  const advancedBodyRef = useRef<HTMLDivElement | null>(null)
  const advancedIconRef = useRef<HTMLSpanElement | null>(null)
  const didInitAdvancedRef = useRef(false)

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

  useEffect(() => {
    setConfigDirty(isDirty)
    if (!isDirty) {
      clearUnsavedWarning()
    }

    return () => {
      setConfigDirty(false)
    }
  }, [clearUnsavedWarning, isDirty, setConfigDirty])

  useLayoutEffect(() => {
    const body = advancedBodyRef.current
    const icon = advancedIconRef.current
    if (!body || !icon) return

    if (!didInitAdvancedRef.current) {
      gsap.set(body, {
        height: 0,
        autoAlpha: 0,
        overflow: 'hidden',
      })
      gsap.set(icon, { rotation: 0, transformOrigin: '50% 50%' })
      didInitAdvancedRef.current = true
    }

    const timeline = gsap.timeline({
      defaults: { duration: 0.35, ease: 'power2.inOut' },
    })

    timeline.to(
      body,
      {
        height: advancedOpen ? 'auto' : 0,
        autoAlpha: advancedOpen ? 1 : 0,
        overflow: 'hidden',
      },
      0,
    )
    timeline.to(
      icon,
      {
        rotation: advancedOpen ? 180 : 0,
        ease: 'power3.out',
      },
      0,
    )

    return () => {
      timeline.kill()
    }
  }, [advancedOpen])

  const handleChange = (key: string, value: DraftValue) => {
    setDraft((prev) => ({ ...prev, [key]: value }))
    setError(null)
    setSuccess(null)
    clearUnsavedWarning()
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
    clearUnsavedWarning()
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
    <div className="page page-antd">
      <header className="page-header">
        <div>
          <h2 className="page-title">配置</h2>
          <p className="page-description">
            统一管理 API Key、模型参数和检索策略。保存后会把 JSON 配置提交到后端并刷新运行中的服务。
          </p>
        </div>
        <Tag color={getStatusTagColor(success ? 'success' : isDirty ? 'warning' : 'outline')}>
          {statusText}
        </Tag>
      </header>

      <div className="config-page-main">
        <Card className="panel antd-panel-card" styles={{ body: { padding: 0 } }}>
          <div className="page-antd-card-header">
            <div className="page-antd-card-title">常用配置</div>
            <div className="page-antd-card-description">
              高频参数集中展示，适合日常调整模型与主流程策略。
            </div>
          </div>
          <div className="panel-content page-antd-card-body">
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
                      {field.sensitive && <Tag>敏感</Tag>}
                    </div>

                    {field.input_type === 'checkbox' ? (
                      <Checkbox
                        className="config-checkbox-antd"
                        id={`config-${field.key}`}
                        checked={Boolean(draft[field.key])}
                        onChange={(e) => handleChange(field.key, e.target.checked)}
                      >
                        启用
                      </Checkbox>
                    ) : field.input_type === 'json-textarea' ? (
                      <TextArea
                        id={`config-${field.key}`}
                        rows={5}
                        value={String(draft[field.key] ?? '')}
                        onChange={(e) => handleChange(field.key, e.target.value)}
                      />
                    ) : field.input_type === 'password' ? (
                      <Input.Password
                        id={`config-${field.key}`}
                        className="config-ant-control"
                        value={String(draft[field.key] ?? '')}
                        onChange={(e) => handleChange(field.key, e.target.value)}
                      />
                    ) : (
                      <Input
                        id={`config-${field.key}`}
                        className="config-ant-control"
                        type={field.input_type}
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
          </div>
        </Card>

        {Object.keys(modelConfigs).length > 0 && (
          <Card className="panel antd-panel-card" styles={{ body: { padding: 0 } }}>
            <div className="page-antd-card-header">
              <div className="page-antd-card-title">模型配置</div>
              <div className="page-antd-card-description">
                分别配置聊天、改写、Embedding 和 Rerank 模型的 provider、模型名、接口地址与
                API key。
              </div>
            </div>
            <div className="panel-content page-antd-card-body">
              <div className="config-form-grid config-model-antd">
                {Object.entries(modelConfigs).map(([role, modelConfig]) => (
                  <div key={role} className="config-field">
                    <div className="config-field__header">
                      <label className="field-label">{MODEL_ROLE_LABELS[role] ?? role}</label>
                      <Tag>{role}</Tag>
                    </div>

                    <div className="config-field__stack">
                      <label className="field-label" htmlFor={`model-provider-${role}`}>
                        Provider
                      </label>
                      <Select<ProviderKind>
                        id={`model-provider-${role}`}
                        aria-label={`${MODEL_ROLE_LABELS[role] ?? role} Provider`}
                        className="config-model-control config-model-control--select"
                        value={modelConfig.provider_kind}
                        options={MODEL_PROVIDER_OPTIONS}
                        onChange={(value) => handleModelConfigChange(role, 'provider_kind', value)}
                        getPopupContainer={(node) => node.parentElement ?? document.body}
                      />
                    </div>

                    <div className="config-field__stack">
                      <label className="field-label" htmlFor={`model-name-${role}`}>
                        模型名称
                      </label>
                      <Input
                        id={`model-name-${role}`}
                        aria-label={`${MODEL_ROLE_LABELS[role] ?? role} 模型名称`}
                        className="config-model-control"
                        value={modelConfig.model}
                        onChange={(e) => handleModelConfigChange(role, 'model', e.target.value)}
                      />
                    </div>

                    <div className="config-field__stack">
                      <label className="field-label" htmlFor={`model-url-${role}`}>
                        URL
                      </label>
                      <Input
                        id={`model-url-${role}`}
                        aria-label={`${MODEL_ROLE_LABELS[role] ?? role} URL`}
                        className="config-model-control"
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
                      <Input.Password
                        id={`model-api-key-${role}`}
                        aria-label={`${MODEL_ROLE_LABELS[role] ?? role} API Key`}
                        className="config-model-control"
                        value={modelConfig.api_key}
                        onChange={(e) => handleModelConfigChange(role, 'api_key', e.target.value)}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        )}

        <Card className="panel config-advanced-panel antd-panel-card" styles={{ body: { padding: 0 } }}>
          <Button
            htmlType="button"
            type="text"
            className="config-advanced-toggle"
            onClick={() => setAdvancedOpen((prev) => !prev)}
            aria-expanded={advancedOpen}
          >
            <div className="config-advanced-toggle__copy">
              <h3 className="config-advanced-toggle__title">高级设置</h3>
              <p className="config-advanced-toggle__description">
                包含路径、文本切分、重排和 Query Rewrite 的详细参数。
              </p>
            </div>
            <span ref={advancedIconRef} className="config-advanced-toggle__icon" aria-hidden="true">
              <ChevronDown size={18} strokeWidth={2.2} />
            </span>
          </Button>
          <div ref={advancedBodyRef} className="config-advanced-body">
            <div className="panel-content page-antd-card-body">
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
                          <Checkbox
                            className="config-checkbox-antd"
                          id={`config-${field.key}`}
                          checked={Boolean(draft[field.key])}
                          onChange={(e) => handleChange(field.key, e.target.checked)}
                          >
                            启用
                          </Checkbox>
                        ) : field.input_type === 'json-textarea' ? (
                          <TextArea
                            id={`config-${field.key}`}
                            rows={5}
                            value={String(draft[field.key] ?? '')}
                            onChange={(e) => handleChange(field.key, e.target.value)}
                          />
                        ) : field.input_type === 'password' ? (
                          <Input.Password
                            id={`config-${field.key}`}
                            className="config-ant-control"
                            value={String(draft[field.key] ?? '')}
                            onChange={(e) => handleChange(field.key, e.target.value)}
                          />
                        ) : (
                          <Input
                            id={`config-${field.key}`}
                            className="config-ant-control"
                            type={field.input_type}
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
            </div>
          </div>
        </Card>

        <div className="config-bottom-actions">
          <div className="config-actions">
            <Button
              type="primary"
              onClick={handleSave}
              disabled={loading || saving || fields.length === 0 || !isDirty}
            >
              {saving ? '保存中...' : '保存配置'}
            </Button>
            <Button
              onClick={handleReset}
              disabled={loading || saving || !isDirty}
            >
              重置修改
            </Button>
          </div>

          {unsavedWarning && <Alert type="warning" showIcon message={unsavedWarning} />}
          {error && <Alert type="error" showIcon message={error} />}
          {success && <Alert type="success" showIcon message={success} />}
        </div>
      </div>
    </div>
  )
}