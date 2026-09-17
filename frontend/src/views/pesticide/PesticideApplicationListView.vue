<template>
  <div class="page">
    <PageHeader title="施药记录与安全间隔期"
               description="登记施药区域、防治对象、稀释浓度、用药量与施药人员；按药剂登记的安全间隔期自动推算最早可进入时间">
      <template #actions>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">登记施药记录</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="单号 / 药剂 / 防治对象 / 人员 / 位置" clearable
                  :prefix-icon="'Search'" style="width: 260px"
                  @keyup.enter="search" @clear="search" />
        <div style="width: 200px">
          <GreenSpaceSelect v-model="filters.green_space_id" placeholder="按施药区域筛选"
                            @update:model-value="search" />
        </div>
        <div style="width: 200px">
          <PesticideSelect v-model="filters.pesticide_id" placeholder="按药剂筛选"
                           @update:model-value="search" />
        </div>
        <el-select v-model="filters.interval_status" placeholder="间隔期状态" clearable @change="search">
          <el-option label="安全间隔期内" value="within" />
          <el-option label="已可进入" value="releasable" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" unlink-panels value-format="YYYY-MM-DD"
                        start-placeholder="施药日期起" end-placeholder="施药日期止" @change="onDateChange" />
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="reset">重置</el-button>
      </div>
    </div>

    <div class="stat-grid">
      <StatCard label="施药记录" :value="formatNumber(summary?.total_count ?? 0)" unit="条"
                hint="按当前筛选条件统计" icon="Aim" />
      <StatCard label="安全间隔期内" :value="formatNumber(summary?.within_interval_count ?? 0)" unit="处"
                :hint="withinHint" tone="danger" icon="WarningFilled" />
      <StatCard label="今日解除管控" :value="formatNumber(summary?.releasable_today_count ?? 0)" unit="处"
                hint="最早可进入时间落在今天的区域" tone="warning" icon="Timer" />
      <StatCard label="已可进入"
                :value="formatNumber(Math.max((summary?.total_count ?? 0) - (summary?.within_interval_count ?? 0), 0))"
                unit="处"
                hint="已超过最早可进入时间，可正常作业" tone="info" icon="CircleCheck" />
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">
          共 <strong>{{ meta.total }}</strong> 条施药记录，其中
          <strong class="text-danger">{{ formatNumber(summary?.within_interval_count ?? 0) }}</strong>
          处区域仍在安全间隔期内
        </span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe :row-class-name="rowClass">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-detail">
              <span><b>施药方式：</b>{{ row.application_method_label || '-' }}</span>
              <span><b>具体位置：</b>{{ row.location || '-' }}</span>
              <span><b>作业面积：</b>{{ row.treated_area ? `${formatNumber(row.treated_area)} ㎡` : '-' }}</span>
              <span><b>天气：</b>{{ weatherLabel(row.weather) }}</span>
              <span><b>安全间隔期：</b>{{ row.safety_interval_days }} 天</span>
              <span><b>施药时刻：</b>{{ row.applied_at }}</span>
              <span v-if="row.remark"><b>备注：</b>{{ row.remark }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="application_no" label="单号" width="160" />
        <el-table-column label="施药区域" min-width="170" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="name-cell">{{ row.green_space?.name || '-' }}</div>
            <div class="sub-text">{{ row.location || '整片区域' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="使用药剂" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <div>{{ row.pesticide_name }}</div>
            <div class="sub-text">{{ row.pesticide?.code || '档案已删除' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="target_pest" label="防治对象" width="110" />
        <el-table-column prop="dilution_ratio" label="稀释浓度" width="100">
          <template #default="{ row }">{{ row.dilution_ratio || '-' }}</template>
        </el-table-column>
        <el-table-column label="用药量" width="110" align="right">
          <template #default="{ row }">{{ formatNumber(row.dosage) }} {{ row.unit_label }}</template>
        </el-table-column>
        <el-table-column prop="operator" label="施药人员" width="130" />
        <el-table-column prop="application_date" label="施药日期" width="105" />
        <el-table-column label="最早可进入" width="160">
          <template #default="{ row }">
            <span :class="row.is_within_interval ? 'reentry-locked' : 'reentry-ok'">
              {{ row.earliest_reentry_at }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <EnumTag group="application_status" :value="row.reentry_status"
                    :label="row.is_within_interval ? '间隔期内' : '可进入'" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
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

    <PesticideApplicationFormDialog ref="formDialog" @saved="load" />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
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
import { formatNumber } from '@/utils/format'

import PesticideApplicationFormDialog from './PesticideApplicationFormDialog.vue'

const route = useRoute()
const formDialog = ref(null)
const dateRange = ref([])
const { label: weatherLabel } = useEnumOptions('weather')

const { filters, meta, items, summary, loading, load, search, resetFilters,
        handlePageChange, handleSizeChange } = useListQuery(pesticideApplicationApi.list, {
  initialFilters: {
    keyword: '',
    green_space_id: route.query.green_space_id ? Number(route.query.green_space_id) : null,
    pesticide_id: null,
    interval_status: '',
    date_from: '',
    date_to: '',
  },
})

const withinHint = computed(() => {
  const count = summary.value?.within_interval_count ?? 0
  return count > 0 ? `${count} 处区域暂不可进入，请勿安排人员作业` : '当前无处于间隔期内的区域'
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

function rowClass({ row }) {
  return row.is_within_interval ? 'row-locked' : ''
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除施药记录「${row.application_no}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
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
.name-cell {
  font-weight: 600;
}

.sub-text {
  color: #909399;
  font-size: 12px;
}

.text-danger,
.reentry-locked {
  color: #f56c6c;
  font-weight: 600;
}

.reentry-ok {
  color: #67c23a;
}

.expand-detail {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 6px 16px;
  padding: 4px 12px;
  color: #606266;
  font-size: 13px;
}

:deep(.row-locked) {
  background-color: #fef6f6;
}

:deep(.row-locked:hover > td) {
  background-color: #fdecec !important;
}
</style>
