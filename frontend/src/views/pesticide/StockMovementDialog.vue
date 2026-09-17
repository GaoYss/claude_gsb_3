<template>
  <el-dialog :model-value="visible"
             :title="form.movement_type === 'in' ? '药剂入库登记' : '药剂领用登记'"
             width="640px" top="8vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
      <el-form-item label="出入库类型" prop="movement_type">
        <el-radio-group v-model="form.movement_type">
          <el-radio-button label="in">入库补货</el-radio-button>
          <el-radio-button label="out">领用出库</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="药剂" prop="pesticide_id" :error="fieldErrors.pesticide_id">
        <PesticideSelect v-model="form.pesticide_id" :preset="pesticidePreset"
                         @change="onPesticideChange" />
      </el-form-item>
      <el-form-item v-if="selected" label="当前库存">
        <el-tag :type="selected.is_low_stock ? 'danger' : 'info'" effect="plain">
          {{ formatNumber(selected.stock_quantity) }} {{ selected.unit_label }}
        </el-tag>
        <span v-if="selected.is_low_stock" class="low-stock-hint">已低于库存预警阈值</span>
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item :label="form.movement_type === 'in' ? '入库数量' : '领用数量'"
                        prop="quantity" :error="fieldErrors.quantity">
            <el-input-number v-model="form.quantity" :min="0.01" :precision="2" :controls="false"
                             placeholder="请输入数量" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="单位">
            <el-input :model-value="selected?.unit_label || '-'" disabled />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="日期" prop="movement_date" :error="fieldErrors.movement_date">
            <el-date-picker v-model="form.movement_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item :label="form.movement_type === 'in' ? '经办人' : '领用人'"
                        :error="fieldErrors.receiver">
            <el-input v-model="form.receiver" maxlength="64"
                      :placeholder="form.movement_type === 'in' ? '如：药库管理员' : '如：植保班·吴国强'" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item v-if="form.movement_type === 'out'" label="领用绿地" :error="fieldErrors.green_space_id">
        <GreenSpaceSelect v-model="form.green_space_id" :preset="spacePreset" />
      </el-form-item>
      <el-form-item label="用途" :error="fieldErrors.purpose">
        <el-input v-model="form.purpose" maxlength="255"
                  :placeholder="form.movement_type === 'out' ? '如：蚜虫防治领用' : '如：季度药剂集中采购入库'" />
      </el-form-item>
      <el-form-item label="登记人" :error="fieldErrors.operator">
        <el-input v-model="form.operator" maxlength="64" />
      </el-form-item>
      <el-form-item label="备注" :error="fieldErrors.remark">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="2000" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">
        {{ form.movement_type === 'in' ? '确认入库' : '确认领用' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { stockMovementApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import PesticideSelect from '@/components/common/PesticideSelect.vue'
import { formatNumber, today } from '@/utils/format'

const emit = defineEmits(['saved'])

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const fieldErrors = ref({})
const pesticidePreset = ref(null)
const spacePreset = ref(null)
const selected = ref(null)
const form = reactive(emptyForm())

const rules = {
  movement_type: [{ required: true, message: '请选择出入库类型', trigger: 'change' }],
  pesticide_id: [{ required: true, message: '请选择药剂', trigger: 'change' }],
  quantity: [{ required: true, message: '请输入数量', trigger: 'blur' }],
  movement_date: [{ required: true, message: '请选择日期', trigger: 'change' }],
}

function emptyForm() {
  return {
    pesticide_id: null,
    movement_type: 'in',
    quantity: null,
    movement_date: today(),
    receiver: '',
    green_space_id: null,
    purpose: '',
    operator: '',
    remark: '',
  }
}

function open(options = {}) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  pesticidePreset.value = null
  spacePreset.value = null
  selected.value = null
  if (options.pesticide) {
    pesticidePreset.value = options.pesticide
    selected.value = options.pesticide
    form.pesticide_id = options.pesticide.id
  }
  if (options.movement_type) form.movement_type = options.movement_type
  visible.value = true
}

function close() {
  visible.value = false
}

function onPesticideChange(pesticide) {
  selected.value = pesticide
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  fieldErrors.value = {}
  const payload = { ...form }
  if (!payload.green_space_id) payload.green_space_id = null
  try {
    await stockMovementApi.create(payload)
    ElMessage.success(form.movement_type === 'out' ? '领用登记成功，库存已扣减' : '入库登记成功，库存已补充')
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
.low-stock-hint {
  margin-left: 8px;
  color: #f56c6c;
  font-size: 12px;
}
</style>
