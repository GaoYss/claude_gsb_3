<template>
  <div class="page">
    <PageHeader title="药剂领用" description="登记药剂领用出库并自动扣减库存，剩余药剂退库时回补库存">
      <template #actions>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">登记领用</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="领用编号 / 领用人 / 用途" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <div style="width: 240px">
          <PesticideSelect v-model="filters.pesticide_id" placeholder="按药剂筛选"
                           :include-inactive="true" @change="search" />
        </div>
        <el-select v-model="filters.status" placeholder="领用状态" clearable @change="search">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" unlink-panels value-format="YYYY-MM-DD"
                        start-placeholder="领用日期起" end-placeholder="领用日期止" @change="onDateChange" />
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="reset">重置</el-button>
      </div>
    </div>

    <div class="stat-grid">
      <StatCard label="领用记录" :value="formatNumber(summary?.total_count ?? 0)" unit="条" icon="Document" />
      <StatCard label="领用总量" :value="formatNumber(summary?.issued_quantity ?? 0)"
                hint="各药剂按自身计量单位汇总" tone="info" icon="Goods" />
      <StatCard label="已退库" :value="formatNumber(summary?.returned_count ?? 0)" unit="条"
                :hint="`退库数量 ${formatNumber(summary?.returned_quantity ?? 0)}`" tone="default" icon="RefreshLeft" />
      <StatCard label="库存口径" value="领用出库 / 退库回补"
                hint="库存数量由领用与退库自动维护" icon="InfoFilled" />
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">
          共 <strong>{{ meta.total }}</strong> 条领用记录，领用总量
          <strong>{{ formatNumber(summary?.issued_quantity ?? 0) }}</strong>
        </span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-detail">
              <span><b>用途说明：</b>{{ row.purpose || '-' }}</span>
              <span><b>发放人：</b>{{ row.operator || '-' }}</span>
              <span><b>退库数量：</b>{{ row.returned_quantity === null ? '-' : formatNumber(row.returned_quantity) }}</span>
              <span><b>退库日期：</b>{{ row.returned_at || '-' }}</span>
              <span><b>登记时间：</b>{{ formatDateTime(row.created_at) }}</span>
              <span v-if="row.remark"><b>备注：</b>{{ row.remark }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="requisition_no" label="领用编号" width="160" />
        <el-table-column label="药剂" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div>{{ row.pesticide?.name || '-' }}</div>
            <EnumTag group="pesticide_toxicity"
                     :value="row.pesticide?.toxicity" :label="row.pesticide?.toxicity_label" />
          </template>
        </el-table-column>
        <el-table-column label="领用数量" width="130" align="right">
          <template #default="{ row }">
            {{ formatNumber(row.quantity) }} {{ row.unit_label }}
          </template>
        </el-table-column>
        <el-table-column prop="recipient" label="领用人" width="100" />
        <el-table-column prop="issue_date" label="领用日期" width="110" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <EnumTag group="requisition_status" :value="row.status" :label="row.status_label" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="formDialog.open(row)">编辑</el-button>
            <el-button v-if="row.status === 'issued'" link type="warning"
                       @click="returnDialog.open(row)">退库</el-button>
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

    <RequisitionFormDialog ref="formDialog" @saved="load" />
    <RequisitionReturnDialog ref="returnDialog" @saved="load" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { pesticideRequisitionApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import PesticideSelect from '@/components/common/PesticideSelect.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'
import { formatDateTime, formatNumber } from '@/utils/format'

import RequisitionFormDialog from './RequisitionFormDialog.vue'
import RequisitionReturnDialog from './RequisitionReturnDialog.vue'

const route = useRoute()
const formDialog = ref(null)
const returnDialog = ref(null)
const dateRange = ref([])

const { options: statusOptions } = useEnumOptions('requisition_status')

const { filters, meta, items, summary, loading, load, search, resetFilters,
        handlePageChange, handleSizeChange } = useListQuery(pesticideRequisitionApi.list, {
  initialFilters: {
    keyword: '',
    pesticide_id: route.query.pesticide_id ? Number(route.query.pesticide_id) : null,
    status: '',
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
      `确认删除领用记录「${row.requisition_no}」吗？将自动回补其净占用库存。`,
      '删除确认', {
        type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
      },
    )
    await pesticideRequisitionApi.remove(row.id)
    ElMessage.success('药剂领用记录已删除')
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

.expand-detail {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 6px 16px;
  padding: 4px 12px;
  color: #606266;
  font-size: 13px;
}
</style>
