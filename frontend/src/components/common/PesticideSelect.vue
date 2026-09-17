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
    @update:model-value="onSelect"
  >
    <el-option
      v-for="item in options"
      :key="item.id"
      :label="`${item.code} ${item.name}`"
      :value="item.id"
    >
      <span>{{ item.code }} {{ item.name }}</span>
      <span class="pesticide-option__meta">
        库存 {{ formatNumber(item.stock_quantity) }} {{ item.unit_label }} · 间隔期
        {{ item.safety_interval_days }} 天
      </span>
    </el-option>
  </el-select>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import { pesticideApi } from '@/api'
import { formatNumber } from '@/utils/format'

const props = defineProps({
  modelValue: { type: [Number, String], default: null },
  preset: { type: Object, default: null },
  placeholder: { type: String, default: '请选择药剂' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'change'])

const options = ref([])
const loading = ref(false)

function merge(items) {
  const map = new Map()
  items.filter(Boolean).forEach((item) => map.set(item.id, item))
  if (props.preset) {
    map.set(props.preset.id, {
      stock_quantity: null,
      unit_label: '',
      safety_interval_days: null,
      ...props.preset,
    })
  }
  options.value = [...map.values()]
}

async function load(keyword) {
  loading.value = true
  try {
    const data = await pesticideApi.options(keyword ? { keyword } : undefined)
    merge(data?.items || [])
  } finally {
    loading.value = false
  }
}

function remoteSearch(keyword) {
  return load(keyword?.trim() || undefined)
}

function onSelect(value) {
  emit('update:modelValue', value)
  emit('change', options.value.find((item) => item.id === value) || null)
}

onMounted(() => load())
</script>

<style scoped>
.pesticide-option__meta {
  float: right;
  color: #909399;
  font-size: 12px;
}
</style>
