<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑施药记录 · ${form.application_no}` : '登记施药记录'"
             width="780px" top="5vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-form-item label="施药区域" prop="green_space_id" :error="fieldErrors.green_space_id">
        <GreenSpaceSelect v-model="form.green_space_id" :preset="spacePreset"
                          @update:model-value="onGreenSpaceChange" />
      </el-form-item>
      <el-form-item label="施用药剂" prop="pesticide_id" :error="fieldErrors.pesticide_id">
        <PesticideSelect v-model="form.pesticide_id" :preset="pesticidePreset"
                         @change="onPesticideChange" />
      </el-form-item>

      <el-alert v-if="selectedPesticide" :closable="false" class="safety-alert"
                :type="intervalDays > 0 ? 'warning' : 'success'" show-icon>
        <template #title>
          <span>
            该药剂安全间隔期为 <b>{{ intervalDays }}</b> 天。
            施药日期 {{ form.application_date || '—' }}，
            <b>最早可进入时间：{{ earliestEntry || '请选择施药日期' }}</b>
            <span v-if="intervalDays === 0">（该药剂无间隔期要求）</span>
          </span>
        </template>
      </el-alert>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="施药日期" prop="application_date" :error="fieldErrors.application_date">
            <el-date-picker v-model="form.application_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择日期" :disabled-date="disableFuture" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="防治对象" prop="target_pest" :error="fieldErrors.target_pest">
            <el-input v-model="form.target_pest" placeholder="如：蚜虫 / 白粉病" maxlength="128" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="稀释浓度" prop="dilution_ratio" :error="fieldErrors.dilution_ratio">
            <el-input v-model="form.dilution_ratio" placeholder="如：1:1500 或 1000 倍液" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="用药量" prop="dosage" :error="fieldErrors.dosage">
            <el-input-number v-model="form.dosage" :min="0.01" :precision="2"
                             :controls="false" placeholder="实际用药量" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="施药面积（㎡）" :error="fieldErrors.apply_area">
            <el-input-number v-model="form.apply_area" :min="0.01" :precision="2"
                             :controls="false" placeholder="选填" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="施药人员" prop="operator" :error="fieldErrors.operator">
            <el-input v-model="form.operator" maxlength="64" placeholder="实际施药人" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="施药器械" :error="fieldErrors.equipment">
            <el-input v-model="form.equipment" maxlength="64" placeholder="如：背负式电动喷雾器" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="关联养护记录" :error="fieldErrors.maintenance_record_id">
            <RecordSelect v-model="form.maintenance_record_id" :green-space-id="form.green_space_id"
                          :preset="recordPreset" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="备注" :error="fieldErrors.remark">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="2000"
                  placeholder="可登记天气、防护措施、现场警示设置等情况" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit(false)">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, h, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { pesticideApplicationApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import PesticideSelect from '@/components/common/PesticideSelect.vue'
import RecordSelect from '@/components/common/RecordSelect.vue'
import { addDays, today } from '@/utils/format'

const emit = defineEmits(['saved'])

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const spacePreset = ref(null)
const pesticidePreset = ref(null)
const recordPreset = ref(null)
const selectedPesticide = ref(null)
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)
const intervalDays = computed(() => Number(selectedPesticide.value?.safety_interval_days ?? 0))
const earliestEntry = computed(() => {
  if (!form.application_date) return ''
  return addDays(form.application_date, intervalDays.value)
})

const rules = {
  green_space_id: [{ required: true, message: '请选择施药区域', trigger: 'change' }],
  pesticide_id: [{ required: true, message: '请选择施用药剂', trigger: 'change' }],
  application_date: [{ required: true, message: '请选择施药日期', trigger: 'change' }],
  target_pest: [{ required: true, message: '请输入防治对象', trigger: 'blur' }],
  dilution_ratio: [{ required: true, message: '请填写稀释浓度', trigger: 'blur' }],
  dosage: [{ required: true, message: '请填写用药量', trigger: 'blur' }],
  operator: [{ required: true, message: '请填写施药人员', trigger: 'blur' }],
}

function emptyForm() {
  return {
    application_no: '',
    pesticide_id: null,
    green_space_id: null,
    maintenance_record_id: null,
    application_date: today(),
    target_pest: '',
    apply_area: null,
    dilution_ratio: '',
    dosage: null,
    operator: '',
    equipment: '',
    remark: '',
  }
}

function disableFuture(date) {
  return date.getTime() > Date.now()
}

function onPesticideChange(item) {
  selectedPesticide.value = item
}

function onGreenSpaceChange() {
  form.maintenance_record_id = null
  recordPreset.value = null
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  spacePreset.value = null
  pesticidePreset.value = null
  recordPreset.value = null
  selectedPesticide.value = null
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
    spacePreset.value = row.green_space || null
    pesticidePreset.value = row.pesticide || null
    selectedPesticide.value = row.pesticide
      ? { ...row.pesticide, safety_interval_days: row.safety_interval_days }
      : null
    recordPreset.value = row.record ? { ...row.record, id: row.maintenance_record_id } : null
  }
  visible.value = true
}

function close() {
  visible.value = false
}

function buildPayload() {
  const payload = { ...form }
  delete payload.application_no
  if (!payload.maintenance_record_id) payload.maintenance_record_id = null
  if (payload.apply_area === '' || payload.apply_area === null) {
    delete payload.apply_area
  }
  return payload
}

async function persist(force) {
  const payload = buildPayload()
  if (isEdit.value) {
    return pesticideApplicationApi.update(editingId.value, payload, { force })
  }
  return pesticideApplicationApi.create(payload, { force })
}

async function submit(force) {
  if (!force) {
    const valid = await formRef.value?.validate().catch(() => false)
    if (!valid) return
  }
  submitting.value = true
  fieldErrors.value = {}
  try {
    await persist(force)
    ElMessage.success(isEdit.value ? '施药记录已更新' : '施药记录登记成功')
    emit('saved')
    close()
  } catch (error) {
    fieldErrors.value = error?.details || {}
    // 间隔期内重复施药：展示冲突明细并要求人工确认
    if (error?.details?.force_required && !force) {
      const conflicts = error.details.conflicts || []
      const messageNode = h('div', { class: 'pesticide-warning' }, [
        h('p', { class: 'pesticide-warning__lead' }, error.message),
        h(
          'ul',
          { class: 'pesticide-warning__list' },
          conflicts.map((item) =>
            h('li', [
              `${item.application_date} 施用「${item.pesticide_name}」，最早可进入 ` +
              `${item.earliest_entry_date}（剩余 ${item.days_remaining} 天）`,
            ]),
          ),
        ),
        h('p', { class: 'pesticide-warning__foot' },
          '再次施药可能导致药剂残留超标、危害人员安全。请确认现场已评估风险并设置警示。'),
      ])
      try {
        await ElMessageBox.confirm(messageNode, '安全间隔期内重复施药预警', {
          type: 'warning',
          confirmButtonText: '已知晓风险，仍要登记',
          cancelButtonText: '取消',
        })
        await submit(true)
      } catch (confirmError) {
        if (confirmError === 'cancel' || confirmError === 'close') return
        fieldErrors.value = confirmError?.details || {}
      }
    }
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.safety-alert {
  margin: -6px 0 16px 120px;
}

.safety-alert :deep(.el-alert__title) {
  line-height: 1.6;
}
</style>
