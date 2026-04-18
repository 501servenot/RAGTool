export type ConfigInputType =
  | 'text'
  | 'password'
  | 'number'
  | 'checkbox'
  | 'json-textarea'
export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue }
export type ConfigValue = JsonValue

export interface ConfigField {
  key: string
  label: string
  description: string
  group: string
  input_type: ConfigInputType
  advanced: boolean
  sensitive: boolean
  nullable: boolean
  value: ConfigValue
}

export type ProviderKind = 'openai_compatible' | 'dashscope'

export interface EditableModelConfig {
  provider_kind: ProviderKind
  model: string
  base_url: string
  api_key: string
}

export interface ConfigStateResponse {
  fields: ConfigField[]
  model_configs: Record<string, EditableModelConfig>
}

export interface ConfigUpdateRequest {
  values: Record<string, ConfigValue>
  model_configs: Record<string, EditableModelConfig>
}

export interface ConfigUpdateResponse {
  message: string
  fields: ConfigField[]
  model_configs: Record<string, EditableModelConfig>
}

export async function getConfig(): Promise<ConfigStateResponse> {
  const res = await fetch('/api/v1/config')

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`获取配置失败 (${res.status}): ${text || res.statusText}`)
  }

  return (await res.json()) as ConfigStateResponse
}

export async function updateConfig(
  payload: ConfigUpdateRequest,
): Promise<ConfigUpdateResponse> {
  const res = await fetch('/api/v1/config', {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`保存配置失败 (${res.status}): ${text || res.statusText}`)
  }

  return (await res.json()) as ConfigUpdateResponse
}
