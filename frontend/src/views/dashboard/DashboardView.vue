<template>
  <div class="page" v-loading="loading">
    <PageHeader title="养护总览" description="绿地台账、养护任务、养护记录、绿植更换与药剂安全管控的整体运行情况">
      <template #actions>
        <el-button :icon="'Refresh'" @click="load">刷新数据</el-button>
      </template>
    </PageHeader>

    <div class="stat-grid">
      <StatCard
        label="在册绿地"
        :value="formatNumber(overview.green_space.total)"
        unit="处"
        :hint="`总面积 ${formatArea(overview.green_space.total_area)}`"
        icon="MapLocation"
      />
      <StatCard
        label="未完成养护任务"
        :value="formatNumber(overview.task.open_count)"
        unit="项"
        :hint="`其中逾期 ${overview.task.overdue_count} 项，7 天内到期 ${overview.task.due_soon_count} 项`"
        :tone="overview.task.overdue_count ? 'danger' : 'default'"
        icon="Tickets"
      />
      <StatCard
        label="任务完成率"
        :value="formatPercent(overview.task.completion_rate)"
        :hint="`已完成 ${overview.task.by_status.completed} / 共 ${overview.task.total} 项`"
        tone="info"
        icon="CircleCheck"
      />
      <StatCard
        label="本月养护记录"
        :value="formatNumber(overview.record.month_count)"
        unit="条"
        :hint="`本月工时 ${formatHours(overview.record.month_work_hours)}，累计 ${formatNumber(overview.record.total)} 条`"
        icon="Notebook"
      />
      <StatCard
        label="本月绿植更换"
        :value="formatNumber(overview.replacement.month_quantity)"
        unit="株/㎡"
        :hint="`金额 ${formatCurrency(overview.replacement.month_amount)}`"
        icon="Cherry"
      />
      <StatCard
        label="累计更换投入"
        :value="formatCurrency(overview.replacement.total_amount)"
        :hint="`今年 ${formatCurrency(overview.replacement.year_amount)}，共 ${formatNumber(overview.replacement.total)} 次`"
        tone="info"
        icon="Money"
      />
      <StatCard
        label="在档药剂"
        :value="formatNumber(overview.pesticide.total)"
        unit="种"
        :hint="`累计施药 ${formatNumber(overview.pesticide.application_total)} 次，本月 ${formatNumber(overview.pesticide.month_application_count)} 次`"
        icon="Box"
      />
      <StatCard
        label="间隔期内区域"
        :value="formatNumber(overview.pesticide.active_interval_count)"
        unit="处"
        :hint="overview.pesticide.active_interval_count
          ? '暂不可进入，禁止安排人员作业'
          : '当前无处于安全间隔期内的区域'"
        :tone="overview.pesticide.active_interval_count ? 'danger' : 'default'"
        icon="WarningFilled"
      />
    </div>

    <div class="chart-grid">
      <ChartPanel title="近半年养护记录与工时" hint="柱：记录条数，折线：工时" :option="trendChart" />
      <ChartPanel title="绿地类型分布" hint="按绿地处数" :option="typeChart" />
      <ChartPanel title="养护任务类型分布" hint="按任务条数" :option="taskTypeChart" />
      <ChartPanel title="绿植更换原因分布" hint="按更换数量" :option="reasonChart" />
    </div>

    <div class="dashboard-columns">
      <div class="panel">
        <div class="table-toolbar">
          <span class="panel-title">逾期未完成的养护任务</span>
          <el-link type="primary" :underline="false" @click="router.push('/tasks')">
            查看全部任务
          </el-link>
        </div>
        <el-table :data="dashboard.overdue_tasks" size="small" empty-text="暂无逾期任务">
          <el-table-column prop="task_no" label="任务编号" width="150" />
          <el-table-column label="绿地" min-width="140">
            <template #default="{ row }">{{ row.green_space?.name || '-' }}</template>
          </el-table-column>
          <el-table-column prop="title" label="任务名称" min-width="150" show-overflow-tooltip />
          <el-table-column prop="plan_date" label="计划日期" width="110" />
          <el-table-column label="逾期" width="80">
            <template #default="{ row }">
              <span class="overdue-days">{{ overdueDays(row.plan_date) }} 天</span>
            </template>
          </el-table-column>
          <el-table-column prop="executor" label="执行班组" width="110">
            <template #default="{ row }">{{ row.executor || '-' }}</template>
          </el-table-column>
        </el-table>
      </div>

      <div class="panel">
        <div class="table-toolbar">
          <span class="panel-title">养护工作量排名</span>
          <span class="summary-text">按累计养护记录条数</span>
        </div>
        <el-table :data="dashboard.ranking" size="small" empty-text="暂无养护记录">
          <el-table-column type="index" label="#" width="48" />
          <el-table-column prop="name" label="绿地名称" min-width="150" show-overflow-tooltip />
          <el-table-column prop="district" label="行政区" width="90" />
          <el-table-column prop="record_count" label="养护次数" width="90" />
          <el-table-column label="累计工时" width="100">
            <template #default="{ row }">{{ formatHours(row.total_work_hours) }}</template>
          </el-table-column>
          <el-table-column label="更换量" width="100">
            <template #default="{ row }">{{ formatNumber(row.replacement_quantity) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <div class="dashboard-columns">
      <div class="panel">
        <div class="table-toolbar">
          <span class="panel-title">安全间隔期内的施药区域</span>
          <el-link type="primary" :underline="false" @click="router.push('/pesticide-applications')">
            进入施药记录
          </el-link>
        </div>
        <el-table :data="dashboard.pesticide_reminders.active_intervals" size="small"
                  empty-text="当前无处于间隔期内的区域">
          <el-table-column label="施药区域" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">{{ row.green_space?.name || '-' }}</template>
          </el-table-column>
          <el-table-column prop="pesticide_name" label="药剂" min-width="130" show-overflow-tooltip />
          <el-table-column prop="applied_at" label="施药时间" width="120" />
          <el-table-column label="最早可进入" width="135">
            <template #default="{ row }">
              <span class="reentry-locked">{{ row.earliest_reentry_at }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="panel">
        <div class="table-toolbar">
          <span class="panel-title">药剂库存预警</span>
          <el-link type="primary" :underline="false" @click="router.push('/pesticides')">
            进入药剂档案
          </el-link>
        </div>
        <el-table :data="dashboard.pesticide_reminders.low_stock" size="small" empty-text="暂无库存预警">
          <el-table-column prop="code" label="编号" width="120" />
          <el-table-column prop="name" label="药剂名称" min-width="150" show-overflow-tooltip />
          <el-table-column label="当前库存" width="130" align="right">
            <template #default="{ row }">
              <span class="reentry-locked">
                {{ formatNumber(row.stock_quantity) }} {{ row.unit_label }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="预警阈值" width="110" align="right">
            <template #default="{ row }">{{ formatNumber(row.stock_low_threshold) }} {{ row.unit_label }}</template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <div class="dashboard-columns">
      <div class="panel">
        <div class="table-toolbar">
          <span class="panel-title">最近养护记录</span>
          <el-link type="primary" :underline="false" @click="router.push('/records')">进入养护记录</el-link>
        </div>
        <el-table :data="dashboard.recent_activity.records" size="small" empty-text="暂无养护记录">
          <el-table-column prop="record_no" label="记录编号" width="150" />
          <el-table-column label="绿地" min-width="140">
            <template #default="{ row }">{{ row.green_space?.name || '-' }}</template>
          </el-table-column>
          <el-table-column prop="record_date" label="养护日期" width="110" />
          <el-table-column prop="work_content" label="作业内容" min-width="180" show-overflow-tooltip />
          <el-table-column label="质量评定" width="100">
            <template #default="{ row }">
              <EnumTag group="quality_result" :value="row.quality_result" />
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="panel">
        <div class="table-toolbar">
          <span class="panel-title">最近绿植更换</span>
          <el-link type="primary" :underline="false" @click="router.push('/replacements')">
            进入更换记录
          </el-link>
        </div>
        <el-table :data="dashboard.recent_activity.replacements" size="small" empty-text="暂无更换记录">
          <el-table-column prop="replacement_no" label="编号" width="150" />
          <el-table-column label="绿地" min-width="130">
            <template #default="{ row }">{{ row.green_space?.name || '-' }}</template>
          </el-table-column>
          <el-table-column prop="plant_name" label="植株" width="110" />
          <el-table-column label="数量" width="110">
            <template #default="{ row }">
              {{ formatNumber(row.quantity) }} {{ row.unit_label }}
            </template>
          </el-table-column>
          <el-table-column label="金额" width="120">
            <template #default="{ row }">{{ formatCurrency(row.amount) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { statisticsApi } from '@/api'
import ChartPanel from '@/components/common/ChartPanel.vue'
import EnumTag from '@/components/common/EnumTag.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import { formatArea, formatCurrency, formatHours, formatNumber, formatPercent, today } from '@/utils/format'

import { barOption, pieOption, trendOption } from './chartOptions'

const router = useRouter()
const loading = ref(false)
const dashboard = ref(emptyDashboard())

function emptyDashboard() {
  return {
    overview: {
      green_space: { total: 0, total_area: 0, by_status: {} },
      task: { total: 0, open_count: 0, overdue_count: 0, due_soon_count: 0, completion_rate: 0, by_status: {} },
      record: { total: 0, month_count: 0, month_work_hours: 0, total_work_hours: 0 },
      replacement: { total: 0, month_count: 0, month_quantity: 0, month_amount: 0, year_amount: 0, total_amount: 0 },
      pesticide: { total: 0, low_stock_count: 0, application_total: 0,
                   month_application_count: 0, active_interval_count: 0 },
    },
    distributions: {
      green_space_by_type: [],
      task_by_type: [],
      replacement_by_reason: [],
      replacement_by_category: [],
    },
    trends: [],
    ranking: [],
    overdue_tasks: [],
    upcoming_tasks: [],
    pesticide_reminders: { low_stock: [], active_intervals: [] },
    recent_activity: { records: [], replacements: [] },
  }
}

const overview = computed(() => dashboard.value.overview)

const trendChart = computed(() => trendOption(dashboard.value.trends || []))

const typeChart = computed(() =>
  pieOption(
    (dashboard.value.distributions.green_space_by_type || []).map((item) => ({
      name: item.label,
      value: item.count,
    })),
    { unit: '处' },
  ),
)

const taskTypeChart = computed(() =>
  barOption(
    (dashboard.value.distributions.task_by_type || []).map((item) => ({
      name: item.label,
      value: item.count,
    })),
    { unit: '项', horizontal: true },
  ),
)

const reasonChart = computed(() =>
  pieOption(
    (dashboard.value.distributions.replacement_by_reason || []).map((item) => ({
      name: item.label,
      value: item.quantity,
    })),
    { unit: '株/㎡' },
  ),
)

function overdueDays(planDate) {
  if (!planDate) return 0
  const diff = new Date(today()) - new Date(planDate)
  return Math.max(Math.round(diff / 86400000), 0)
}

async function load() {
  loading.value = true
  try {
    dashboard.value = await statisticsApi.dashboard({ months: 6 })
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.dashboard-columns {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 16px;
}

.panel-title {
  font-weight: 600;
}

.overdue-days {
  color: #f56c6c;
  font-weight: 600;
}

.reentry-locked {
  color: #f56c6c;
  font-weight: 600;
}
</style>
