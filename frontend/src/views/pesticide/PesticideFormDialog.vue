<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑药剂档案 · ${form.code}` : '新建药剂档案'"
             width="780px" top="6vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="药剂名称" prop="name" :error="fieldErrors.name">
            <el-input v-model="form.name" placeholder="如：吡虫啉可湿性粉剂" maxlength="128" />
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
          <el-form-item label="毒性" :error="fieldErrors.toxicity">
            <el-select v-model="form.toxicity" style="width: 100%">
              <el-option v-for="item in toxicityOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="剂型" :error="fieldErrors.form">
            <el-select v-model="form.form" style="width: 100%">
              <el-option v-for="item in formOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="有效成分" :error="fieldErrors.active_ingredient">
            <el-input v-model="form.active_ingredient" placeholder="如：吡虫啉 10%" maxlength="128" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="农药登记证号" :error="fieldErrors.registration_no">
            <el-input v-model="form.registration_no" placeholder="如：PD20240001" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="生产企业" :error="fieldErrors.manufacturer">
            <el-input v-model="form.manufacturer" maxlength="128" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="计量单位" :error="fieldErrors.unit">
            <el-select v-model="form.unit" style="width: 100%">
              <el-option v-for="item in unitOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="期初库存" :error="fieldErrors.stock_quantity">
            <el-input-number v-model="form.stock_quantity" :min="0" :precision="2" :controls="false"
                             :disabled="isEdit" style="width: 100%" />
            <div class="form-hint">{{ isEdit ? '建档后库存只能通过入库 / 领用调整' : '建档后可通过入库补货、领用扣减' }}</div>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="库存预警阈值" :error="fieldErrors.stock_low_threshold">
            <el-input-number v-model="form.stock_low_threshold" :min="0" :precision="2" :controls="false"
                             placeholder="库存低于等于该值时预警" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="安全间隔期" prop="safety_interval_days" :error="fieldErrors.safety_interval_days">
            <el-input-number v-model="form.safety_interval_days" :min="0" :max="365" :precision="0"
                             controls-position="right" style="width: 100%" />
            <div class="form-hint">单位：天，按药剂标签登记，用于推算最早可进入时间</div>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="防治对象" :error="fieldErrors.target_pests">
            <el-input v-model="form.target_pests" placeholder="如：蚜虫、飞虱、网蝽" maxlength="255" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="储存条件" :error="fieldErrors.storage_condition">
        <el-input v-model="form.storage_condition" maxlength="255"
                  placeholder="如：阴凉干燥、通风上锁的专用药柜，远离食品与火源" />
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

import { pesticideApi } from '@/api'
import { useEnumOptions } from '@/composables/useEnumOptions'

const emit = defineEmits(['saved'])

const { options: typeOptions } = useEnumOptions('pesticide_type')
const { options: toxicityOptions } = useEnumOptions('pesticide_toxicity')
const { options: formOptions } = useEnumOptions('pesticide_form')
const { options: unitOptions } = useEnumOptions('pesticide_unit')

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
  safety_interval_days: [{ required: true, message: '请填写安全间隔期（天）', trigger: 'blur' }],
}

function emptyForm() {
  return {
    code: '',
    name: '',
    pesticide_type: 'insecticide',
    toxicity: 'low',
    form: 'ec',
    active_ingredient: '',
    registration_no: '',
    manufacturer: '',
    unit: 'bottle',
    stock_quantity: 0,
    stock_low_threshold: 0,
    safety_interval_days: 7,
    target_pests: '',
    storage_condition: '',
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
      ElMessage.success('药剂档案创建成功')
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
