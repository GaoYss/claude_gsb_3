<template>
  <div class="page">
    <PageHeader title="药剂档案与领用"
               description="建立药剂台账与库存，登记入库与领用，并记录施用区域、防治对象、浓度与用药量；按安全间隔期管控进入时间">
      <template #actions>
        <el-button type="warning" plain :icon="'Bottom'" @click="movementDialog.open({ movement_type: 'out' })">
          领用出库
        </el-button>
        <el-button type="success" plain :icon="'Top'" @click="movementDialog.open({ movement_type: 'in' })">
          入库补货
        </el-button>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">新建药剂档案</el-button>
      </template>
    </PageHeader>

    <el-tabs v-model="activeTab" class="panel-tabs">
      <el-tab-pane label="药剂档案" name="pesticides">
        <div class="panel">
          <div class="filter-bar">
            <el-input v-model="filters.keyword" placeholder="名称 / 编号 / 登记证号 / 有效成分" clearable
                      :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
            <el-select v-model="filters.pesticide_type" placeholder="药剂类别" clearable @change="search">
              <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
            <el-select v-model="filters.toxicity" placeholder="毒性" clearable @change="search">
              <el-option v-for="item in toxicityOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
            <el-checkbox v-model="lowStockOnly" @change="onLowStockChange">仅看库存预警</el-checkbox>
            <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
            <el-button :icon="'RefreshLeft'" @click="reset">重置</el-button>
          </div>
        </div>

        <div class="stat-grid">
          <StatCard label="药剂种类" :value="formatNumber(summary?.total_count ?? 0)" unit="种"
                    hint="已建档的药剂数量" icon="Box" />
          <StatCard label="库存预警" :value="formatNumber(summary?.low_stock_count ?? 0)" unit="种"
                    :hint="lowStockHint" tone="danger" icon="WarningFilled" />
          <StatCard label="安全间隔期" value="按天管控"
                    hint="施药后自动推算最早可进入时间" tone="info" icon="Timer" />
          <StatCard label="领用与入库" value="可追溯"
                    hint="出入库流水自动维护库存余额" icon="SortDown" />
        </div>

        <div class="panel">
          <div class="table-toolbar">
            <span class="summary-text">共 <strong>{{ meta.total }}</strong> 种药剂</span>
            <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
          </div>
          <el-table :data="items" v-loading="loading" border stripe>
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="expand-detail">
                  <span><b>剂型：</b>{{ row.form_label }}</span>
                  <span><b>有效成分：</b>{{ row.active_ingredient || '-' }}</span>
                  <span><b>登记证号：</b>{{ row.registration_no || '-' }}</span>
                  <span><b>生产企业：</b>{{ row.manufacturer || '-' }}</span>
                  <span><b>防治对象：</b>{{ row.target_pests || '-' }}</span>
                  <span><b>储存条件：</b>{{ row.storage_condition || '-' }}</span>
                  <span v-if="row.remark"><b>备注：</b>{{ row.remark }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="code" label="编号" width="130" />
            <el-table-column label="药剂名称" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">
                <div class="name-cell">{{ row.name }}</div>
                <EnumTag group="pesticide_type" :value="row.pesticide_type"
                         :label="row.pesticide_type_label" />
              </template>
            </el-table-column>
            <el-table-column label="毒性" width="90">
              <template #default="{ row }">
                <EnumTag group="pesticide_toxicity" :value="row.toxicity" :label="row.toxicity_label" />
              </template>
            </el-table-column>
            <el-table-column label="当前库存" width="150" align="right">
              <template #default="{ row }">
                <span :class="{ 'stock-low': row.is_low_stock, 'stock-num': true }">
                  {{ formatNumber(row.stock_quantity) }} {{ row.unit_label }}
                </span>
                <div v-if="row.is_low_stock" class="low-flag">低于预警值 {{ formatNumber(row.stock_low_threshold) }}</div>
              </template>
            </el-table-column>
            <el-table-column label="安全间隔期" width="110" align="center">
              <template #default="{ row }">
                <el-tag type="warning" effect="plain">{{ row.safety_interval_days }} 天</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="230" fixed="right">
              <template #default="{ row }">
                <el-button link type="success" @click="movementDialog.open({ pesticide: presetOf(row), movement_type: 'in' })">
                  入库
                </el-button>
                <el-button link type="warning" @click="movementDialog.open({ pesticide: presetOf(row), movement_type: 'out' })">
                  领用
                </el-button>
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
      </el-tab-pane>

      <el-tab-pane label="出入库流水" name="movements" lazy>
        <StockMovementsPanel ref="movementsPanel" />
      </el-tab-pane>
    </el-tabs>

    <PesticideFormDialog ref="formDialog" @saved="load" />
    <StockMovementDialog ref="movementDialog" @saved="onMovementSaved" />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { pesticideApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'
import { formatNumber } from '@/utils/format'

import PesticideFormDialog from './PesticideFormDialog.vue'
import StockMovementDialog from './StockMovementDialog.vue'
import StockMovementsPanel from './StockMovementsPanel.vue'

const activeTab = ref('pesticides')
const formDialog = ref(null)
const movementDialog = ref(null)
const movementsPanel = ref(null)
const lowStockOnly = ref(false)

const { options: typeOptions } = useEnumOptions('pesticide_type')
const { options: toxicityOptions } = useEnumOptions('pesticide_toxicity')

const { filters, meta, items, summary, loading, load, search, resetFilters,
        handlePageChange, handleSizeChange } = useListQuery(pesticideApi.list, {
  initialFilters: {
    keyword: '',
    pesticide_type: '',
    toxicity: '',
    low_stock: null,
  },
})

const lowStockHint = computed(() => {
  const count = summary.value?.low_stock_count ?? 0
  return count > 0 ? `${count} 种药剂库存已低于预警值，请及时补货` : '暂无库存预警'
})

function onLowStockChange(value) {
  filters.low_stock = value ? true : null
  search()
}

function reset() {
  lowStockOnly.value = false
  resetFilters()
}

function presetOf(row) {
  return {
    id: row.id,
    code: row.code,
    name: row.name,
    stock_quantity: row.stock_quantity,
    unit_label: row.unit_label,
    safety_interval_days: row.safety_interval_days,
    is_low_stock: row.is_low_stock,
  }
}

function onMovementSaved() {
  load()
  movementsPanel.value?.load?.()
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除药剂档案「${row.name}」吗？若已有出入库或施药记录，需要二次确认。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch (error) {
    return
  }
  try {
    await pesticideApi.remove(row.id)
    ElMessage.success('药剂档案已删除')
    await load()
  } catch (error) {
    if (error?.status === 409) {
      try {
        await ElMessageBox.confirm(
          `${error.message}。确认强制删除吗？`,
          '存在关联记录，需强制删除',
          { type: 'warning', confirmButtonText: '强制删除', cancelButtonText: '取消' },
        )
        await pesticideApi.remove(row.id, { force: 'true' })
        ElMessage.success('药剂档案及出入库流水已删除')
        await load()
      } catch (confirmError) {
        // 用户取消强制删除
      }
    }
  }
}
</script>

<style scoped>
.panel-tabs {
  margin-top: 4px;
}

.name-cell {
  font-weight: 600;
  margin-bottom: 2px;
}

.stock-num {
  font-weight: 600;
}

.stock-low {
  color: #f56c6c;
}

.low-flag {
  color: #f56c6c;
  font-size: 12px;
}

.expand-detail {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 6px 16px;
  padding: 4px 12px;
  color: #606266;
  font-size: 13px;
}
</style>
