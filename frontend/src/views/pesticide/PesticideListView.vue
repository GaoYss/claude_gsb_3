<template>
  <div class="page">
    <PageHeader title="药剂档案" description="建立农药台账，登记毒性、安全间隔期与库存，作为领用与施药管控依据">
      <template #actions>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">建立药剂档案</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="编号 / 名称 / 登记证号 / 厂家" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <el-select v-model="filters.pesticide_type" placeholder="药剂类别" clearable @change="search">
          <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.toxicity" placeholder="毒性级别" clearable @change="search">
          <el-option v-for="item in toxicityOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.status" placeholder="档案状态" clearable @change="search">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="reset">重置</el-button>
      </div>
    </div>

    <div class="stat-grid">
      <StatCard label="药剂档案" :value="formatNumber(summary?.total_count ?? 0)" unit="个"
                :hint="`在用 ${summary?.by_status?.in_use ?? 0} 个`" icon="FirstAidKit" />
      <StatCard label="库存总量" :value="formatNumber(summary?.total_stock_quantity ?? 0)"
                hint="各药剂按自身计量单位汇总，仅供总量参考" tone="info" icon="Box" />
      <StatCard label="累计领用" :value="formatNumber(summary?.requisition_count ?? 0)" unit="条"
                hint="全部领用登记条数" icon="Document" />
      <StatCard label="累计施药" :value="formatNumber(summary?.application_count ?? 0)" unit="条"
                hint="全部施药记录条数" tone="warning" icon="Spray" />
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">
          共 <strong>{{ meta.total }}</strong> 个药剂档案
        </span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-detail">
              <span><b>农药登记证号：</b>{{ row.registration_no || '-' }}</span>
              <span><b>有效成分：</b>{{ row.active_ingredient || '-' }}</span>
              <span><b>剂型：</b>{{ row.formulation || '-' }}</span>
              <span><b>生产厂家：</b>{{ row.manufacturer || '-' }}</span>
              <span><b>计量单位：</b>{{ row.unit_label }}</span>
              <span><b>建档时间：</b>{{ formatDateTime(row.created_at) }}</span>
              <span v-if="row.remark"><b>备注：</b>{{ row.remark }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="code" label="编号" width="140" />
        <el-table-column prop="name" label="药剂名称" min-width="200" show-overflow-tooltip />
        <el-table-column label="类别" width="100">
          <template #default="{ row }">
            <EnumTag group="pesticide_type" :value="row.pesticide_type" :label="row.pesticide_type_label" />
          </template>
        </el-table-column>
        <el-table-column label="毒性" width="90">
          <template #default="{ row }">
            <EnumTag group="pesticide_toxicity" :value="row.toxicity" :label="row.toxicity_label" />
          </template>
        </el-table-column>
        <el-table-column label="安全间隔期" width="110" align="center">
          <template #default="{ row }">
            <span class="interval-text">{{ row.safety_interval_days }} 天</span>
          </template>
        </el-table-column>
        <el-table-column label="库存" width="130" align="right">
          <template #default="{ row }">
            <span :class="{ 'stock-empty': Number(row.stock_quantity) === 0 }">
              {{ formatNumber(row.stock_quantity) }} {{ row.unit_label }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <EnumTag group="pesticide_status" :value="row.status" :label="row.status_label" />
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

    <PesticideFormDialog ref="formDialog" @saved="load" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { pesticideApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'
import { formatDateTime, formatNumber } from '@/utils/format'

import PesticideFormDialog from './PesticideFormDialog.vue'

const formDialog = ref(null)

const { options: typeOptions } = useEnumOptions('pesticide_type')
const { options: toxicityOptions } = useEnumOptions('pesticide_toxicity')
const { options: statusOptions } = useEnumOptions('pesticide_status')

const { filters, meta, items, summary, loading, load, search, resetFilters,
        handlePageChange, handleSizeChange } = useListQuery(pesticideApi.list, {
  initialFilters: { keyword: '', pesticide_type: '', toxicity: '', status: '' },
})

function reset() {
  resetFilters()
}

async function remove(row) {
  const doDelete = async (force) => {
    await pesticideApi.remove(row.id, force ? { force: true } : undefined)
    ElMessage.success('药剂档案已删除')
    await load()
  }
  try {
    await ElMessageBox.confirm(`确认删除药剂档案「${row.name}」吗？`, '删除确认', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
    })
    await doDelete(false)
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    if (error?.status === 409) {
      const counts = error.details || {}
      try {
        await ElMessageBox.confirm(
          `该药剂已有领用记录 ${counts.pesticide_requisition ?? 0} 条、施药记录 ` +
          `${counts.pesticide_application ?? 0} 条，删除将一并清除且不可恢复，确认继续？`,
          '存在关联记录',
          { type: 'warning', confirmButtonText: '强制删除', cancelButtonText: '取消' },
        )
        await doDelete(true)
      } catch (confirmError) {
        if (confirmError === 'cancel' || confirmError === 'close') return
      }
    }
  }
}
</script>

<style scoped>
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}

.interval-text {
  font-weight: 600;
  color: #e6a23c;
}

.stock-empty {
  color: #f56c6c;
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
