<template>
  <el-dialog :model-value="visible" title="剩余药剂退库登记" width="480px"
             top="12vh" destroy-on-close @update:model-value="close">
    <div v-if="requisition" class="return-info">
      <p><b>领用编号：</b>{{ requisition.requisition_no }}</p>
      <p><b>药剂：</b>{{ requisition.pesticide?.name }}</p>
      <p>
        <b>领用数量：</b>{{ formatNumber(requisition.quantity) }} {{ requisition.unit_label }}
        ，领用人 {{ requisition.recipient }}
      </p>
    </div>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
      <el-form-item label="退库数量" prop="returned_quantity" :error="fieldErrors.returned_quantity">
        <el-input-number v-model="form.returned_quantity" :min="0.01" :precision="2"
                         :controls="false" placeholder="实际退库数量" style="width: 100%" />
      </el-form-item>
      <el-form-item label="退库日期" prop="returned_at" :error="fieldErrors.returned_at">
        <el-date-picker v-model="form.returned_at" type="date" value-format="YYYY-MM-DD"
                        placeholder="选择日期" style="width: 100%" />
      </el-form-item>
    </el-form>
    <el-alert type="warning" :closable="false" show-icon>
      <template #title>退库登记后状态变为「已退库」，退库数量将自动回补库存，且不可重复退库。</template>
    </el-alert>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">确认退库</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { pesticideRequisitionApi } from '@/api'
import { formatNumber, today } from '@/utils/format'

const emit = defineEmits(['saved'])

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const requisition = ref(null)
const fieldErrors = ref({})
const form = reactive({ returned_quantity: null, returned_at: today() })

const rules = {
  returned_quantity: [{ required: true, message: '请输入退库数量', trigger: 'blur' }],
  returned_at: [{ required: true, message: '请选择退库日期', trigger: 'change' }],
}

function open(row) {
  requisition.value = row
  form.returned_quantity = row.quantity
  form.returned_at = today()
  fieldErrors.value = {}
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
  try {
    await pesticideRequisitionApi.returns(requisition.value.id, { ...form })
    ElMessage.success('退库登记成功，库存已回补')
    emit('saved')
    close()
  } catch (error) {
    fieldErrors.value = error?.details || {}
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.return-info {
  margin-bottom: 12px;
  color: #606266;
  font-size: 13px;
  line-height: 1.9;
}

.return-info p {
  margin: 0;
}
</style>
