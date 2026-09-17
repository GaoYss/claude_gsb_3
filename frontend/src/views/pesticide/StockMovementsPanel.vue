<template>
  <div>
    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="单号 / 领用人 / 用途" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <div style="width: 220px">
          <PesticideSelect v-model="filters.pesticide_id" placeholder="按药剂筛选"
                           @update:model-value="search" />
        </div>
        <el-select v-model="filters.movement_type" placeholder="出入库类型" clearable @change="search">
          <el-option v-for="item in movementTypeOptions" :key="item.value"
                     :label="item.label" :value="item.value" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" unlink-panels value-format="YYYY-MM-DD"
                        start-placeholder="日期起" end-placeholder="日期止" @change="onDateChange" />
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="reset">重置</el-button>
        <span class="filter-bar__spacer"></span>
        <el-button type="success" plain :icon="'Top'" @click="movementDialog.open({ movement_type: 'in' })">
          入库补货
        </el-button>
        <el-button type="warning" plain :icon="'Bottom'" @click="movementDialog.open({ movement_type: 'out' })">
          领用出库
        </el-button>
      </div>
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">共 <strong>{{ meta.total }}</strong> 条出入库记录</span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>
      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column prop="movement_no" label="单号" width="160" />
        <el-table-column label="药剂" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <div>{{ row.pesticide?.name || '-' }}</div>
            <div class="sub-text">{{ row.pesticide?.code }}</div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <EnumTag group="stock_movement_type" :value="row.movement_type"
                     :label="row.movement_type_label" />
          </template>
        </el-table-column>
        <el-table-column label="数量" width="120" align="right">
          <template #default="{ row }">
            <span :class="row.movement_type === 'in' ? 'qty-in' : 'qty-out'">
              {{ row.movement_type === 'in' ? '+' : '-' }}{{ formatNumber(row.quantity) }} {{ row.unit_label }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="movement_date" label="日期" width="110" />
        <el-table-column prop="receiver" label="领用人 / 经办人" width="150">
          <template #default="{ row }">{{ row.receiver || '-' }}</template>
        </el-table-column>
        <el-table-column label="领用绿地" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.green_space?.name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="purpose" label="用途" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.purpose || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
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

    <StockMovementDialog ref="movementDialog" @saved="load" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { stockMovementApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import PesticideSelect from '@/components/common/PesticideSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'
import { formatNumber } from '@/utils/format'

import StockMovementDialog from './StockMovementDialog.vue'

const movementDialog = ref(null)
const dateRange = ref([])
const { options: movementTypeOptions } = useEnumOptions('stock_movement_type')

const { filters, meta, items, loading, load, search, resetFilters,
        handlePageChange, handleSizeChange } = useListQuery(stockMovementApi.list, {
  initialFilters: {
    keyword: '',
    pesticide_id: null,
    movement_type: '',
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

async function remove(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除${row.movement_type_label}记录「${row.movement_no}」吗？删除后库存将自动回滚。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await stockMovementApi.remove(row.id)
    ElMessage.success('记录已删除，库存已回滚')
    await load()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
  }
}
</script>

<style scoped>
.sub-text {
  color: #909399;
  font-size: 12px;
}

.qty-in {
  color: #67c23a;
  font-weight: 600;
}

.qty-out {
  color: #e6a23c;
  font-weight: 600;
}
</style>
