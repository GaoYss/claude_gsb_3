<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑施药记录 · ${form.application_no}` : '登记施药记录'"
             width="800px" top="5vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
      <el-form-item label="施药区域" prop="green_space_id" :error="fieldErrors.green_space_id">
        <GreenSpaceSelect v-model="form.green_space_id" :preset="spacePreset"
                          @update:model-value="onGreenSpaceChange" />
      </el-form-item>
      <el-form-item label="具体位置" :error="fieldErrors.location">
        <el-input v-model="form.location" maxlength="128"
                  placeholder="选填，如：东区草坪 / 南门主入口花境 / 沿河绿篱带" />
      </el-form-item>

      <el-form-item label="使用药剂" prop="pesticide_id" :error="fieldErrors.pesticide_id">
        <PesticideSelect v-model="form.pesticide_id" :preset="pesticidePreset"
                         @change="onPesticideChange" />
      </el-form-item>
      <el-alert v-if="selectedPesticide" :closable="false" class="pesticide-info"
                :type="selectedPesticide.is_low_stock ? 'warning' : 'success'">
        <template #title>
          当前库存 {{ formatNumber(selectedPesticide.stock_quantity) }}
          {{ selectedPesticide.unit_label }} · 登记安全间隔期
          <b>{{ selectedPesticide.safety_interval_days }}</b> 天
          <span v-if="selectedPesticide.is_low_stock" class="low-warn">（库存偏低，领用前请先补货）</span>
        </template>
      </el-alert>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="施药日期" prop="application_date" :error="fieldErrors.application_date">
            <el-date-picker v-model="form.application_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择日期" style="width: 100%" @change="checkInterval" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="施药时刻" :error="fieldErrors.application_time">
            <el-time-picker v-model="form.application_time" format="HH:mm" value-format="HH:mm"
                            placeholder="选填，缺省按当日 00:00" style="width: 100%"
                            @change="checkInterval" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="防治对象" prop="target_pest" :error="fieldErrors.target_pest">
            <el-input v-model="form.target_pest" maxlength="128" placeholder="如：蚜虫 / 白粉病 / 红蜘蛛" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="施药方式" :error="fieldErrors.application_method">
            <el-select v-model="form.application_method" clearable placeholder="请选择" style="width: 100%">
              <el-option v-for="item in methodOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="稀释浓度" :error="fieldErrors.dilution_ratio">
            <el-input v-model="form.dilution_ratio" maxlength="64" placeholder="如：1:1500（倍液）" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="用药量" prop="dosage" :error="fieldErrors.dosage">
            <el-input-number v-model="form.dosage" :min="0.01" :precision="2" :controls="false"
                             placeholder="实际用药量" style="width: calc(100% - 56px)" />
            <span class="unit-suffix">{{ selectedPesticide?.unit_label || '单位' }}</span>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="作业面积（㎡）" :error="fieldErrors.treated_area">
            <el-input-number v-model="form.treated_area" :min="0.01" :precision="2" :controls="false"
                             placeholder="选填" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="施药人员" prop="operator" :error="fieldErrors.operator">
            <el-input v-model="form.operator" maxlength="64" placeholder="如：植保班·吴国强" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="天气" :error="fieldErrors.weather">
            <el-select v-model="form.weather" clearable placeholder="请选择" style="width: 100%">
              <el-option v-for="item in weatherOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-alert v-if="reentryPreview" :closable="false" class="reentry-box"
                :type="intervalConflicts.length ? 'error' : 'info'" show-icon>
        <template #title>
          最早可进入时间：<b>{{ reentryPreview }}</b>（施药时刻 + 安全间隔期
          {{ selectedPesticide?.safety_interval_days }} 天，在此之前禁止人员进入）
        </template>
        <div v-if="intervalConflicts.length" class="conflict-box">
          <div class="conflict-title">
            ⚠ 该区域仍有 {{ intervalConflicts.length }} 条施药处于安全间隔期内：
          </div>
          <div v-for="item in intervalConflicts" :key="item.application_no" class="conflict-item">
            · {{ item.pesticide_name }}（{{ item.application_date }} 施药，最早可进入
            {{ item.earliest_reentry_at }}）
          </div>
          <div class="conflict-tip">间隔期内再次施药，请确认已做好安全防护，保存时需二次确认。</div>
        </div>
      </el-alert>

      <el-form-item label="备注" :error="fieldErrors.remark" style="margin-top: 12px">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="2000" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { pesticideApplicationApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import PesticideSelect from '@/components/common/PesticideSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { formatNumber, today } from '@/utils/format'

const emit = defineEmits(['saved'])

const { options: methodOptions } = useEnumOptions('application_method')
const { options: weatherOptions } = useEnumOptions('weather')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const spacePreset = ref(null)
const pesticidePreset = ref(null)
const selectedPesticide = ref(null)
const intervalConflicts = ref([])
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const rules = {
  green_space_id: [{ required: true, message: '请选择施药区域（绿地）', trigger: 'change' }],
  pesticide_id: [{ required: true, message: '请选择使用药剂', trigger: 'change' }],
  application_date: [{ required: true, message: '请选择施药日期', trigger: 'change' }],
  target_pest: [{ required: true, message: '请输入防治对象', trigger: 'blur' }],
  dosage: [{ required: true, message: '请输入用药量', trigger: 'blur' }],
  operator: [{ required: true, message: '请输入施药人员', trigger: 'blur' }],
}

function emptyForm() {
  return {
    application_no: '',
    green_space_id: null,
    pesticide_id: null,
    location: '',
    application_date: today(),
    application_time: '',
    target_pest: '',
    application_method: 'spray',
    dilution_ratio: '',
    dosage: null,
    treated_area: null,
    operator: '',
    weather: '',
    remark: '',
  }
}

const reentryPreview = computed(() => {
  if (!form.application_date || !selectedPesticide.value) return ''
  return addDays(form.application_date, form.application_time,
                 selectedPesticide.value.safety_interval_days)
})

function addDays(dateText, timeText, days) {
  const [y, m, d] = dateText.split('-').map(Number)
  const [hh, mm] = (timeText || '00:00').split(':').map(Number)
  const dt = new Date(y, m - 1, d, hh || 0, mm || 0)
  dt.setDate(dt.getDate() + Number(days || 0))
  const pad = (n) => `${n}`.padStart(2, '0')
  return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())} ${pad(dt.getHours())}:${pad(dt.getMinutes())}`
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  spacePreset.value = null
  pesticidePreset.value = null
  selectedPesticide.value = null
  intervalConflicts.value = []
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
    form.application_time = (row.applied_at || '').slice(11, 16) || ''
    spacePreset.value = row.green_space || null
    if (row.pesticide) {
      pesticidePreset.value = row.pesticide
      selectedPesticide.value = { ...row.pesticide, unit_label: row.unit_label }
    }
    checkInterval()
  }
  visible.value = true
}

function close() {
  visible.value = false
}

function onGreenSpaceChange() {
  checkInterval()
}

function onPesticideChange(pesticide) {
  selectedPesticide.value = pesticide
}

let checkToken = 0
async function checkInterval() {
  const token = ++checkToken
  intervalConflicts.value = []
  if (!form.green_space_id || !form.application_date) return
  try {
    const data = await pesticideApplicationApi.intervalCheck({
      green_space_id: form.green_space_id,
      application_date: form.application_date,
      application_time: form.application_time || undefined,
      exclude_id: isEdit.value ? editingId.value : undefined,
    })
    if (token !== checkToken) return
    intervalConflicts.value = data?.within_interval || []
  } catch {
    // 预检失败不阻断录入，保存时后端仍会强校验
  }
}

function buildPayload() {
  const payload = { ...form }
  if (!payload.application_no) delete payload.application_no
  payload.application_time = payload.application_time || null
  payload.application_method = payload.application_method || null
  payload.weather = payload.weather || null
  payload.location = payload.location || null
  payload.dilution_ratio = payload.dilution_ratio || null
  payload.treated_area = payload.treated_area === '' ? null : payload.treated_area
  return payload
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  fieldErrors.value = {}
  try {
    await save(buildPayload(), false)
  } catch (error) {
    if (error?.details?.confirm_required) {
      await handleConflict(buildPayload(), error.details)
    } else {
      fieldErrors.value = sanitizeFieldErrors(error?.details)
    }
  } finally {
    submitting.value = false
  }
}

async function handleConflict(payload, details) {
  const conflictLines = (details.conflicts || [])
    .map((c) => `· ${c.pesticide_name}（${c.application_date} 施药，最早可进入 ${c.earliest_reentry_at}）`)
    .join('\n')
  try {
    await ElMessageBox.confirm(
      `该区域仍有 ${details.conflicts?.length || 0} 条施药处于安全间隔期内：\n${conflictLines}\n\n`
      + '间隔期内再次施药存在安全风险，请确认已设置警示标识、做好人员防护。是否仍要登记？',
      '安全间隔期提醒',
      { type: 'warning', confirmButtonText: '确认风险并保存', cancelButtonText: '返回修改',
        customClass: 'interval-confirm' },
    )
  } catch {
    return
  }
  submitting.value = true
  try {
    await save(payload, true)
  } catch (error) {
    fieldErrors.value = sanitizeFieldErrors(error?.details)
  } finally {
    submitting.value = false
  }
}

async function save(payload, confirm) {
  if (isEdit.value) {
    await pesticideApplicationApi.update(editingId.value, payload, confirm)
    ElMessage.success('施药记录已更新')
  } else {
    await pesticideApplicationApi.create(payload, confirm)
    ElMessage.success('施药记录登记成功')
  }
  emit('saved')
  close()
}

// 409 软警告的 details 是冲突说明而非字段错误，提取其中真正的字段级错误
function sanitizeFieldErrors(details) {
  if (!details || typeof details !== 'object') return {}
  if (details.confirm_required) return {}
  return details
}

defineExpose({ open })
</script>

<style scoped>
.pesticide-info,
.reentry-box {
  margin: 0 0 16px 110px;
}

.unit-suffix {
  margin-left: 8px;
  color: #606266;
}

.low-warn {
  color: #e6a23c;
}

.conflict-box {
  margin-top: 6px;
  line-height: 1.7;
}

.conflict-title {
  font-weight: 600;
}

.conflict-item {
  font-size: 13px;
}

.conflict-tip {
  margin-top: 4px;
  font-size: 12px;
  color: #f56c6c;
}
</style>
