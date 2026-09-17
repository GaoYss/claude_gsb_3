<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑领用记录 · ${form.requisition_no}` : '登记药剂领用'"
             width="640px" top="8vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
      <el-form-item label="领用药剂" prop="pesticide_id" :error="fieldErrors.pesticide_id">
        <PesticideSelect v-model="form.pesticide_id" :preset="pesticideDetail"
                         :include-inactive="isEdit" :disabled="isEdit"
                         @change="onPesticideChange" />
        <div v-if="isEdit" class="form-hint">领用记录创建后不能改换药剂。</div>
      </el-form-item>

      <el-alert v-if="selectedPesticide" :closable="false" class="stock-alert"
                :type="Number(selectedPesticide.stock_quantity) > 0 ? 'info' : 'error'"
                show-icon>
        <template #title>
          当前库存：{{ formatNumber(selectedPesticide.stock_quantity) }}
          {{ selectedPesticide.unit_label }}，
          安全间隔期 {{ selectedPesticide.safety_interval_days }} 天
        </template>
      </el-alert>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="领用数量" prop="quantity" :error="fieldErrors.quantity">
            <el-input-number v-model="form.quantity" :min="0.01" :precision="2"
                             :controls="false" placeholder="请输入" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="领用人" prop="recipient" :error="fieldErrors.recipient">
            <el-input v-model="form.recipient" maxlength="64" placeholder="实际领用人" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="领用日期" prop="issue_date" :error="fieldErrors.issue_date">
            <el-date-picker v-model="form.issue_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择日期" :disabled-date="disableFuture" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="发放人" :error="fieldErrors.operator">
            <el-input v-model="form.operator" maxlength="64" placeholder="库房发放人" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="用途说明" :error="fieldErrors.purpose">
        <el-input v-model="form.purpose" maxlength="255" placeholder="如：武林广场蚜虫防治用药" />
      </el-form-item>
      <el-form-item label="备注" :error="fieldErrors.remark">
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
import { ElMessage } from 'element-plus'

import { pesticideApi, pesticideRequisitionApi } from '@/api'
import PesticideSelect from '@/components/common/PesticideSelect.vue'
import { formatNumber, today } from '@/utils/format'

const emit = defineEmits(['saved'])

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const pesticideDetail = ref(null)
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const selectedPesticide = computed(() => pesticideDetail.value)

const rules = {
  pesticide_id: [{ required: true, message: '请选择领用药剂', trigger: 'change' }],
  quantity: [{ required: true, message: '请输入领用数量', trigger: 'blur' }],
  recipient: [{ required: true, message: '请输入领用人', trigger: 'blur' }],
  issue_date: [{ required: true, message: '请选择领用日期', trigger: 'change' }],
}

function emptyForm() {
  return {
    requisition_no: '',
    pesticide_id: null,
    quantity: null,
    recipient: '',
    issue_date: today(),
    purpose: '',
    status: 'issued',
    operator: '',
    remark: '',
  }
}

function disableFuture(date) {
  return date.getTime() > Date.now()
}

async function loadPesticideDetail(id) {
  if (!id) {
    pesticideDetail.value = null
    return
  }
  try {
    pesticideDetail.value = await pesticideApi.detail(id)
  } catch {
    pesticideDetail.value = null
  }
}

function onPesticideChange(item) {
  if (item) {
    loadPesticideDetail(item.id)
  } else {
    pesticideDetail.value = null
  }
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  pesticideDetail.value = null
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
    if (row.pesticide) {
      loadPesticideDetail(row.pesticide_id)
    }
  }
  visible.value = true
}

function close() {
  visible.value = false
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  fieldErrors.value = {}
  const payload = { ...form }
  delete payload.requisition_no
  try {
    if (isEdit.value) {
      await pesticideRequisitionApi.update(editingId.value, payload)
      ElMessage.success('药剂领用记录已更新')
    } else {
      await pesticideRequisitionApi.create(payload)
      ElMessage.success('药剂领用登记成功，库存已扣减')
    }
    emit('saved')
    close()
  } catch (error) {
    fieldErrors.value = error?.details || {}
    if (error?.details?.stock_quantity) {
      await loadPesticideDetail(form.pesticide_id)
    }
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.stock-alert {
  margin: -6px 0 16px 110px;
}
</style>
