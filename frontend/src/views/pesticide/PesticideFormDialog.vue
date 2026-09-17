<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑药剂档案 · ${form.code}` : '建立药剂档案'"
             width="760px" top="6vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="130px">
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="药剂名称" prop="name" :error="fieldErrors.name">
            <el-input v-model="form.name" placeholder="如：10% 吡虫啉可湿性粉剂" maxlength="128" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="农药登记证号" :error="fieldErrors.registration_no">
            <el-input v-model="form.registration_no" placeholder="如：PD20181234" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="药剂类别" prop="pesticide_type" :error="fieldErrors.pesticide_type">
            <el-select v-model="form.pesticide_type" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="毒性级别" prop="toxicity" :error="fieldErrors.toxicity">
            <el-select v-model="form.toxicity" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in toxicityOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="有效成分" :error="fieldErrors.active_ingredient">
            <el-input v-model="form.active_ingredient" placeholder="如：吡虫啉 10%" maxlength="128" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="剂型" :error="fieldErrors.formulation">
            <el-input v-model="form.formulation" placeholder="如：可湿性粉剂 / 乳油" maxlength="32" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="生产厂家" :error="fieldErrors.manufacturer">
            <el-input v-model="form.manufacturer" placeholder="生产企业名称" maxlength="128" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="安全间隔期" prop="safety_interval_days"
                      :error="fieldErrors.safety_interval_days">
            <el-input-number v-model="form.safety_interval_days" :min="0" :max="365"
                             controls-position="right" style="width: 100%" />
            <div class="form-hint">施药后须经过的天数，施药记录据此自动推算最早可进入时间。</div>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="库存数量" :error="fieldErrors.stock_quantity">
            <el-input-number v-model="form.stock_quantity" :min="0" :precision="2"
                             :controls="false" placeholder="0" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="计量单位" prop="unit" :error="fieldErrors.unit">
            <el-select v-model="form.unit" style="width: 100%">
              <el-option v-for="item in unitOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="档案状态" prop="status" :error="fieldErrors.status">
            <el-select v-model="form.status" style="width: 100%">
              <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
            <div class="form-hint">停用/禁用药剂将被禁止领用与施用。</div>
          </el-form-item>
        </el-col>
      </el-row>
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

import { pesticideApi } from '@/api'
import { useEnumOptions } from '@/composables/useEnumOptions'

const emit = defineEmits(['saved'])

const { options: typeOptions } = useEnumOptions('pesticide_type')
const { options: toxicityOptions } = useEnumOptions('pesticide_toxicity')
const { options: unitOptions } = useEnumOptions('pesticide_unit')
const { options: statusOptions } = useEnumOptions('pesticide_status')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const rules = {
  name: [{ required: true, message: '请输入药剂名称', trigger: 'blur' }],
  pesticide_type: [{ required: true, message: '请选择药剂类别', trigger: 'change' }],
  toxicity: [{ required: true, message: '请选择毒性级别', trigger: 'change' }],
  safety_interval_days: [{ required: true, message: '请填写安全间隔期', trigger: 'blur' }],
}

function emptyForm() {
  return {
    code: '',
    name: '',
    registration_no: '',
    pesticide_type: 'insecticide',
    toxicity: 'low',
    active_ingredient: '',
    formulation: '',
    manufacturer: '',
    safety_interval_days: 7,
    stock_quantity: 0,
    unit: 'milliliter',
    status: 'in_use',
    remark: '',
  }
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
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
  if (!payload.code) delete payload.code
  try {
    if (isEdit.value) {
      await pesticideApi.update(editingId.value, payload)
      ElMessage.success('药剂档案已更新')
    } else {
      await pesticideApi.create(payload)
      ElMessage.success('药剂档案建立成功')
    }
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
.form-hint {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}
</style>
