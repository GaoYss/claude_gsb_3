<template>
  <div class="page">
    <PageHeader title="施药记录" description="登记施药区域、防治对象、稀释浓度、用药量与施药人员，自动推算最早可进入时间并管控重复施药">
      <template #actions>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">登记施药记录</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="施药编号 / 防治对象 / 施药人员" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <div style="width: 220px">
          <GreenSpaceSelect v-model="filters.green_space_id" placeholder="按施药区域筛选"
                            @update:model-value="search" />
        </div>
        <div style="width: 220px">
          <PesticideSelect v-model="filters.pesticide_id" placeholder="按药剂筛选"
                           :include-inactive="true" @change="search" />
        </div>
        <el-select v-model="filters.safety_status" placeholder="间隔期状态" clearable
                   @change="search">
          <el-option v-for="item in safetyStatusOptions" :key="item.value"
                     :label="item.value === 'locked' ? `${item.label}（禁止进入）` : item.label"
                     :value="item.value" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" unlink-panels value-format="YYYY-MM-DD"
                        start-placeholder="施药日期起" end-placeholder="施药日期止" @change="onDateChange" />
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="reset">重置</el-button>
      </div>
    </div>

    <div class="stat-grid">
      <StatCard label="施药记录" :value="formatNumber(summary?.total_count ?? 0)" unit="条" icon="Spray" />
      <StatCard label="间隔期内区域" :value="formatNumber(summary?.locked_count ?? 0)" unit="条"
                hint="当前仍在安全间隔期内、禁止人员进入的施药记录"
                :tone="(summary?.locked_count ?? 0) > 0 ? 'danger' : 'default'" icon="Lock" />
      <StatCard label="本月施药" :value="formatNumber(summary?.month_count ?? 0)" unit="条"
                hint="本月已登记的施药次数" tone="info" icon="Calendar" />
      <StatCard label="涉及区域" :value="formatNumber(summary?.area_count ?? 0)" unit="处"
                hint="当前筛选条件下涉及的绿地数量" icon="MapLocation" />
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">
          共 <strong>{{ meta.total }}</strong> 条施药记录，其中
          <strong class="locked-text">{{ summary?.locked_count ?? 0 }}</strong> 条仍在间隔期内
        </span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe :row-class-name="rowClassName">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-detail">
              <span><b>施药面积：</b>{{ row.apply_area === null ? '-' : `${formatNumber(row.apply_area)} ㎡` }}</span>
              <span><b>施药器械：</b>{{ row.equipment || '-' }}</span>
              <span><b>关联养护记录：</b>{{ row.record ? `${row.record.record_no}（${formatDate(row.record.record_date)}）` : '未关联' }}</span>
              <span><b>用药量：</b>{{ formatNumber(row.dosage) }} {{ row.unit_label }}</span>
              <span><b>登记时间：</b>{{ formatDateTime(row.created_at) }}</span>
              <span v-if="row.remark"><b>备注：</b>{{ row.remark }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="application_no" label="施药编号" width="155" />
        <el-table-column label="施药区域" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.green_space?.name || '-' }}</template>
        </el-table-column>
        <el-table-column label="药剂" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <div>{{ row.pesticide?.name || '-' }}</div>
            <EnumTag group="pesticide_toxicity"
                     :value="row.pesticide?.toxicity" :label="row.pesticide?.toxicity_label" />
          </template>
        </el-table-column>
        <el-table-column prop="target_pest" label="防治对象" width="100" />
        <el-table-column prop="dilution_ratio" label="稀释浓度" width="105" />
        <el-table-column label="用药量" width="115" align="right">
          <template #default="{ row }">
            {{ formatNumber(row.dosage) }} {{ row.unit_label }}
          </template>
        </el-table-column>
        <el-table-column prop="operator" label="施药人员" width="95" />
        <el-table-column prop="application_date" label="施药日期" width="105" />
        <el-table-column label="最早可进入" width="160">
          <template #default="{ row }">
            <div class="safety-cell">
              <span>{{ row.earliest_entry_date }}</span>
              <EnumTag group="pesticide_safety_status"
                       :value="row.safety_status"
                       :label="row.safety_status === 'locked'
                         ? `间隔期内 · 余 ${row.days_remaining} 天`
                         : '可进入'" />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="formDialog.open(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pager"
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="meta.total"
        :current-page="meta.page"
        :page-size="meta.page_size"
        :page-sizes="[10, 20, 50]"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <ApplicationFormDialog ref="formDialog" @saved="load" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { pesticideApplicationApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import PesticideSelect from '@/components/common/PesticideSelect.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'
import { formatDate, formatDateTime, formatNumber } from '@/utils/format'

import ApplicationFormDialog from './ApplicationFormDialog.vue'

const route = useRoute()
const formDialog = ref(null)
const dateRange = ref([])

const { options: safetyStatusOptions } = useEnumOptions('pesticide_safety_status')

const { filters, meta, items, summary, loading, load, search, resetFilters,
        handlePageChange, handleSizeChange } = useListQuery(pesticideApplicationApi.list, {
  initialFilters: {
    keyword: '',
    green_space_id: route.query.green_space_id ? Number(route.query.green_space_id) : null,
    pesticide_id: '',
    safety_status: '',
    date_from: '',
    date_to: '',
  },
})

function onDateChange(value) {
  filters.date_from = value?.[0] || ''
  filters.date_to = value?.[1] || ''
  search()
}

function reset() {
  dateRange.value = []
  resetFilters()
}

function rowClassName({ row }) {
  return row.safety_status === 'locked' ? 'row-locked' : ''
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除施药记录「${row.application_no}」吗？`, '删除确认', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
    })
    await pesticideApplicationApi.remove(row.id)
    ElMessage.success('施药记录已删除')
    await load()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
  }
}
</script>

<style scoped>
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}

.locked-text {
  color: #f56c6c;
}

.safety-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.expand-detail {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 6px 16px;
  padding: 4px 12px;
  color: #606266;
  font-size: 13px;
}

:deep(.el-table .row-locked) {
  background-color: #fef6f6;
}

:deep(.el-table .row-locked:hover > td) {
  background-color: #fdecec !important;
}
</style>
