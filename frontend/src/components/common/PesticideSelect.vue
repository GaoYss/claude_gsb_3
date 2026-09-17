<template>
  <el-select
    :model-value="modelValue"
    filterable
    remote
    clearable
    :remote-method="remoteSearch"
    :loading="loading"
    :placeholder="placeholder"
    :disabled="disabled"
    :style="{ width: '100%' }"
    @update:model-value="emit('update:modelValue', $event)"
    @change="onChange"
  >
    <el-option
      v-for="item in options"
      :key="item.id"
      :label="`${item.code} ${item.name}（间隔期 ${item.safety_interval_days} 天）`"
      :value="item.id"
    >
      <span>{{ item.code }} {{ item.name }}</span>
      <span style="float: right; color: #909399; font-size: 12px">
        间隔期 {{ item.safety_interval_days }} 天
      </span>
    </el-option>
  </el-select>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import { pesticideApi } from '@/api'

const props = defineProps({
  modelValue: { type: [Number, String], default: null },
  preset: { type: Object, default: null },
  placeholder: { type: String, default: '请选择药剂' },
  disabled: { type: Boolean, default: false },
  includeInactive: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'change'])

const options = ref([])
const loading = ref(false)

async function load(keyword) {
  loading.value = true
  try {
    const params = {}
    if (keyword) params.keyword = keyword
    if (props.includeInactive) params.include_inactive = true
    const data = await pesticideApi.options(params)
    const map = new Map()
    ;(data?.items || []).forEach((item) => map.set(item.id, item))
    if (props.preset) map.set(props.preset.id, props.preset)
    options.value = [...map.values()]
  } finally {
    loading.value = false
  }
}

function remoteSearch(keyword) {
  return load(keyword?.trim() || undefined)
}

function onChange(value) {
  const item = options.value.find((option) => option.id === value) || null
  emit('change', item)
}

onMounted(() => load())
defineExpose({ reload: load })
</script>
