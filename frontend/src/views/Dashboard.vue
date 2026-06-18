<template>
  <div class="space-y-6 bg-background text-foreground min-h-screen">
    <!-- Top Action Navigation Bar -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border border-border rounded-lg p-4 bg-card text-card-foreground shadow-sm">
      <div class="space-y-1">
        <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Organization Workspace</p>
        <div class="flex items-center gap-2">
          <Select v-if="user?.organizations?.length > 0" class="w-48 font-semibold" :modelValue="activeOrganization?.id" @update:modelValue="switchOrganizationDirect">
            <option 
              v-for="org in user.organizations" 
              :key="org.id" 
              :value="org.id"
            >
              {{ org.brand_name || org.name }}
            </option>
          </Select>
          <h2 v-else class="text-sm font-semibold text-neutral-500">No Organization Selected</h2>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <div v-if="user" :class="[
          'px-2.5 py-1 rounded-full text-xs font-semibold border flex items-center gap-1.5',
          user.credits < 300 ? 'bg-amber-500/10 text-amber-500 border-amber-500/20' : 
          user.credits < 0 ? 'bg-red-500/10 text-red-500 border-red-500/20' : 'bg-secondary text-secondary-foreground border-border'
        ]">
          <span>🪙</span>
          <span>{{ user.credits }} Personal Credits</span>
        </div>
        <Button variant="outline" size="sm" @click="router.push('/billing')" v-if="user">
          Add Credits
        </Button>
        <Button size="sm" @click="applyFilters" v-if="activeOrganization">
          Refresh
        </Button>
      </div>
    </div>

    <!-- ZERO ORG STATE -->
    <Card v-if="user && user.organizations?.length === 0" class="border-red-500/20 bg-red-500/5">
      <CardHeader>
        <CardTitle class="text-lg">Welcome! Create your first Organization</CardTitle>
        <CardDescription>
          You currently hold {{ user.credits }} credits. Get started by establishing your brand.
        </CardDescription>
      </CardHeader>
      <CardContent class="grid gap-4 sm:grid-cols-3">
        <div class="grid gap-1.5">
          <label class="text-xs font-medium text-neutral-500">System Name</label>
          <Input v-model="newOrgForm.name" placeholder="acme_corp" />
        </div>
        <div class="grid gap-1.5">
          <label class="text-xs font-medium text-neutral-500">Brand Display Name</label>
          <Input v-model="newOrgForm.brand_name" placeholder="Acme" />
        </div>
        <div class="grid gap-1.5">
          <label class="text-xs font-medium text-neutral-500">Keywords (comma separated)</label>
          <Input v-model="newOrgForm.keywords" placeholder="Acme, battery, support" />
        </div>
      </CardContent>
      <CardFooter class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-t border-border pt-4 mt-2">
        <Button @click="createOrganization" :disabled="loading">Create Organization</Button>
        <p v-if="message" class="text-xs text-neutral-500">{{ message }}</p>
      </CardFooter>
    </Card>

    <!-- INCOMPLETE TENANT SETUP STATE -->
    <Card v-if="activeOrganization && (!activeOrganization.brand_name || !activeOrganization.keywords)" class="border-amber-500/20 bg-amber-500/5">
      <CardHeader>
        <CardTitle class="text-lg">Complete Profile Setup</CardTitle>
        <CardDescription>
          Set your brand identity and keyword watchlist before analytics can run.
        </CardDescription>
      </CardHeader>
      <CardContent class="grid gap-4 sm:grid-cols-2">
        <div class="grid gap-1.5">
          <label class="text-xs font-medium text-neutral-500">Brand Name</label>
          <Input v-model="tenantForm.brand_name" placeholder="Acme" />
        </div>
        <div class="grid gap-1.5">
          <label class="text-xs font-medium text-neutral-500">Keywords (comma separated)</label>
          <Input v-model="tenantForm.keywords" placeholder="Acme, refund, error" />
        </div>
      </CardContent>
      <CardFooter class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-t border-border pt-4 mt-2">
        <Button @click="updateTenantProfile" :disabled="loading">Save Profile</Button>
        <p v-if="message" class="text-xs text-neutral-500">{{ message }}</p>
      </CardFooter>
    </Card>

    <template v-if="activeOrganization && activeOrganization.brand_name && activeOrganization.is_active">
      <!-- AI Assistant Query Card -->
      <Card>
        <CardHeader class="flex flex-row items-start justify-between space-y-0 pb-3">
          <div class="space-y-1">
            <CardTitle class="text-lg flex items-center gap-2">
              <span>Ask the AI Assistant</span>
              <Badge variant="secondary" class="text-[10px]">Beta</Badge>
            </CardTitle>
            <CardDescription>Get customized chart and keyword analysis instantly.</CardDescription>
          </div>
          <Button variant="ghost" size="sm" @click="toggleAskLLM">
            {{ isAskLLMCollapsed ? 'Show Ask AI' : 'Hide Ask AI' }}
          </Button>
        </CardHeader>
        
        <CardContent v-show="!isAskLLMCollapsed" class="space-y-4">
          <div class="grid gap-4 sm:grid-cols-12">
            <div class="grid gap-1.5 sm:col-span-8">
              <label class="text-xs font-medium text-neutral-500">Your Question</label>
              <textarea
                v-model="queryText"
                rows="3"
                class="flex w-full rounded-md border border-input bg-background text-foreground px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                placeholder="What do customers think about customer support quality?"
              ></textarea>
            </div>
            <div class="grid gap-1.5 sm:col-span-4">
              <label class="text-xs font-medium text-neutral-500">Timeframe</label>
              <Select v-model="queryTimeframe">
                <option v-for="tf in timeframes" :key="`query-${String(tf.value)}`" :value="tf.value">
                  {{ tf.label }}
                </option>
              </Select>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <Button @click="runSentimentQuery" :disabled="queryLoading || !queryText.trim()">
              {{ queryLoading ? 'Analyzing...' : 'Analyze Question' }}
            </Button>
            <Button variant="ghost" @click="clearSentimentQuery" :disabled="queryLoading && !queryResult">
              Clear
            </Button>
          </div>

          <p v-if="queryError" class="text-xs text-red-600 bg-red-500/10 border border-red-500/20 rounded-md p-3">
            {{ queryError }}
          </p>
        </CardContent>
      </Card>

      <!-- AI Query Results Display -->
      <Card v-if="queryResult" class="border-border">
        <CardHeader>
          <div class="flex items-center justify-between">
            <CardTitle class="text-lg">Sentiment Insight</CardTitle>
            <Badge variant="outline">{{ queryResult.focus || queryResult.query }}</Badge>
          </div>
          <CardDescription class="pt-2 text-foreground leading-relaxed">
            {{ queryResult.summary_text }}
          </CardDescription>
        </CardHeader>
        
        <CardContent class="space-y-6">
          <!-- Tags list -->
          <div class="flex flex-wrap gap-1.5" v-if="queryResult.keywords?.length">
            <span 
              v-for="kw in queryResult.keywords" 
              :key="kw"
              class="inline-flex items-center rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground border border-border"
            >
              #{{ kw }}
            </span>
          </div>

          <!-- Mini Metrics -->
          <div class="grid gap-3 grid-cols-2 md:grid-cols-4">
            <div class="border border-border rounded-lg p-3 text-center bg-muted/50">
              <p class="text-[10px] uppercase font-bold text-neutral-500">Total</p>
              <p class="text-xl font-bold mt-1">{{ queryResult.summary?.total_mentions || 0 }}</p>
            </div>
            <div class="border border-green-500/20 rounded-lg p-3 text-center bg-green-500/5">
              <p class="text-[10px] uppercase font-bold text-green-700 dark:text-green-400">Positive</p>
              <p class="text-xl font-bold mt-1 text-green-700 dark:text-green-400">{{ queryResult.summary?.positive_pct || 0 }}%</p>
            </div>
            <div class="border border-red-500/20 rounded-lg p-3 text-center bg-red-500/5">
              <p class="text-[10px] uppercase font-bold text-red-700 dark:text-red-400">Negative</p>
              <p class="text-xl font-bold mt-1 text-red-700 dark:text-red-400">{{ queryResult.summary?.negative_pct || 0 }}%</p>
            </div>
            <div class="border border-border rounded-lg p-3 text-center bg-muted/50">
              <p class="text-[10px] uppercase font-bold text-neutral-600 dark:text-neutral-400">Neutral</p>
              <p class="text-xl font-bold mt-1 text-neutral-600 dark:text-neutral-400">{{ queryResult.summary?.neutral_pct || 0 }}%</p>
            </div>
          </div>

          <!-- Doughnut Chart -->
          <div class="h-60 flex items-center justify-center border border-border rounded-lg p-4">
            <Doughnut :data="queryDoughnutData" :options="queryDoughnutOptions" />
          </div>

          <!-- Top Products & Representative Posts split -->
          <div class="grid gap-4 md:grid-cols-2">
            <div class="border border-border rounded-lg p-4 space-y-3">
              <h4 class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Top Products</h4>
              <ul v-if="queryResult.top_products?.length" class="divide-y divide-border">
                <li v-for="item in queryResult.top_products" :key="item.product" class="py-2 flex justify-between text-sm">
                  <span class="font-medium">{{ item.product }}</span>
                  <span class="text-neutral-500">{{ item.mentions }} mentions</span>
                </li>
              </ul>
              <p v-else class="text-xs text-neutral-500">No product matches found.</p>
            </div>

            <div class="border border-border rounded-lg p-4 space-y-3">
              <h4 class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Representative Posts</h4>
              <ul v-if="queryResult.sample_posts?.length" class="space-y-3">
                <li v-for="post in queryResult.sample_posts" :key="post.id" class="text-xs bg-muted/30 p-2.5 rounded border border-border">
                  <div class="flex items-center gap-2 mb-1.5">
                    <Badge :variant="post.sentiment === 'POSITIVE' ? 'success' : post.sentiment === 'NEGATIVE' ? 'destructive' : 'secondary'">
                      {{ post.sentiment }}
                    </Badge>
                  </div>
                  <p class="text-muted-foreground leading-normal">{{ post.content }}</p>
                </li>
              </ul>
              <p v-else class="text-xs text-neutral-500">No matched posts to sample.</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Filters Panel -->
      <Card>
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-3">
          <div class="space-y-1">
            <CardTitle class="text-lg">Filters</CardTitle>
            <CardDescription>Adjust timeframe, keywords, search, and sorting.</CardDescription>
          </div>
          <Button variant="ghost" size="sm" @click="toggleFilters">
            {{ isFiltersCollapsed ? 'Show Filters' : 'Hide Filters' }}
          </Button>
        </CardHeader>
        
        <CardContent v-show="!isFiltersCollapsed" class="space-y-4">
          <div class="grid gap-4 sm:grid-cols-12">
            <div class="grid gap-1.5 sm:col-span-6">
              <label class="text-xs font-medium text-neutral-500">Search</label>
              <Input
                v-model="searchInput"
                @keyup.enter="applyFilters"
                placeholder="Search posts, products..."
              />
            </div>

            <div class="grid gap-1.5 sm:col-span-3">
              <label class="text-xs font-medium text-neutral-500">Timeframe</label>
              <Select v-model="selectedTimeframe">
                <option v-for="tf in timeframes" :key="String(tf.value)" :value="tf.value">{{ tf.label }}</option>
              </Select>
            </div>

            <div class="grid gap-1.5 sm:col-span-3">
              <label class="text-xs font-medium text-neutral-500">Sort By</label>
              <Select v-model="sortBy">
                <option value="time_desc">Latest First</option>
                <option value="time_asc">Oldest First</option>
                <option value="score_desc">Score High to Low</option>
                <option value="score_asc">Score Low to High</option>
                <option value="engagement_desc">Most Engagement</option>
              </Select>
            </div>
          </div>

          <!-- Custom Timeframe row -->
          <div class="grid gap-4 sm:grid-cols-2" v-if="selectedTimeframe === 'custom'">
            <div class="grid gap-1.5">
              <label class="text-xs font-medium text-neutral-500">From</label>
              <Input type="datetime-local" v-model="customStart" />
            </div>
            <div class="grid gap-1.5">
              <label class="text-xs font-medium text-neutral-500">To</label>
              <Input type="datetime-local" v-model="customEnd" />
            </div>
          </div>

          <!-- Keywords checklist -->
          <div class="space-y-2">
            <span class="text-xs font-medium text-neutral-500 block">Keywords filter</span>
            <div class="flex flex-wrap gap-2">
              <label 
                v-for="kw in tenantKeywordsList" 
                :key="kw"
                :class="[
                  'cursor-pointer select-none border rounded-full px-3 py-1 text-xs font-medium transition-colors flex items-center gap-1.5',
                  selectedKeywords.includes(kw) ? 'bg-primary text-primary-foreground border-primary' : 'bg-background text-foreground hover:bg-accent border-border'
                ]"
              >
                <input type="checkbox" :value="kw" v-model="selectedKeywords" class="sr-only" />
                <span>{{ kw }}</span>
              </label>
              <p v-if="tenantKeywordsList.length === 0" class="text-xs text-neutral-500">No keywords configured yet.</p>
            </div>
          </div>

          <div class="flex items-center gap-2 border-t border-border pt-4 mt-2">
            <Button size="sm" @click="applyFilters">Apply Filters</Button>
            <Button variant="ghost" size="sm" @click="resetFilters">Reset</Button>
          </div>
        </CardContent>
      </Card>

      <p v-if="!analyticsData" class="text-center py-12 text-sm text-neutral-400">Loading analytics...</p>

      <!-- Analytics Cards block -->
      <template v-if="analyticsData">
        <!-- KPI Metrics Grid -->
        <div class="grid gap-4 grid-cols-2 md:grid-cols-4">
          <Card>
            <CardHeader class="pb-1">
              <CardDescription class="text-[10px] uppercase font-bold tracking-wider">Total Mentions</CardDescription>
            </CardHeader>
            <CardContent>
              <p class="text-3xl font-extrabold">{{ analyticsData.summary.total_mentions }}</p>
            </CardContent>
          </Card>
          <Card class="border-green-500/20 bg-green-50/5">
            <CardHeader class="pb-1">
              <CardDescription class="text-[10px] uppercase font-bold tracking-wider text-green-700 dark:text-green-400">Positive</CardDescription>
            </CardHeader>
            <CardContent class="space-y-1">
              <p class="text-3xl font-extrabold text-green-700 dark:text-green-400">{{ analyticsData.summary.positive }}</p>
              <p class="text-xs text-green-600 dark:text-green-500">{{ analyticsData.summary.positive_pct }}%</p>
            </CardContent>
          </Card>
          <Card class="border-red-500/20 bg-red-50/5">
            <CardHeader class="pb-1">
              <CardDescription class="text-[10px] uppercase font-bold tracking-wider text-red-700 dark:text-red-400">Negative</CardDescription>
            </CardHeader>
            <CardContent class="space-y-1">
              <p class="text-3xl font-extrabold text-red-700 dark:text-red-400">{{ analyticsData.summary.negative }}</p>
              <p class="text-xs text-red-600 dark:text-red-500">{{ analyticsData.summary.negative_pct }}%</p>
            </CardContent>
          </Card>
          <Card class="border-border bg-muted/50">
            <CardHeader class="pb-1">
              <CardDescription class="text-[10px] uppercase font-bold tracking-wider text-neutral-600 dark:text-neutral-400">Neutral</CardDescription>
            </CardHeader>
            <CardContent class="space-y-1">
              <p class="text-3xl font-extrabold text-neutral-600 dark:text-neutral-400">{{ analyticsData.summary.neutral }}</p>
              <p class="text-xs text-neutral-500 dark:text-neutral-500">{{ analyticsData.summary.neutral_pct }}%</p>
            </CardContent>
          </Card>
        </div>

        <!-- Trend box -->
        <Card v-if="analyticsData.prediction?.majority" :class="[
          'border',
          analyticsData.prediction.trend === 'IMPROVING' ? 'border-green-500/20 bg-green-50/5' :
          analyticsData.prediction.trend === 'WORSENING' ? 'border-red-500/20 bg-red-50/5' : 'border-border'
        ]">
          <CardHeader>
            <CardDescription class="text-[10px] uppercase font-bold tracking-wider">Trend Signal</CardDescription>
            <CardTitle class="text-lg mt-1 font-bold">
              {{ analyticsData.prediction.trend }} {{ analyticsData.prediction.direction || '→' }}
            </CardTitle>
          </CardHeader>
          <CardContent class="text-sm">
            Majority sentiment: <strong class="font-semibold">{{ analyticsData.prediction.majority }}</strong>
            based on {{ analyticsData.summary.total_mentions }} mentions.
          </CardContent>
        </Card>

        <!-- Charts Grid -->
        <div class="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle class="text-sm">Sentiment Trend (Line)</CardTitle>
              <CardDescription>Temporal distribution by sentiment class.</CardDescription>
            </CardHeader>
            <CardContent>
              <div class="h-80">
                <Line :data="lineChartData" :options="lineChartOptions" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle class="text-sm">Sentiment Mix (Bar)</CardTitle>
              <CardDescription>Current ratio snapshot across categories.</CardDescription>
            </CardHeader>
            <CardContent>
              <div class="h-80">
                <Bar :data="barChartData" :options="barChartOptions" />
              </div>
            </CardContent>
          </Card>
        </div>

        <!-- Recent Mentions Table -->
        <Card>
          <CardHeader class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3">
            <div class="space-y-1">
              <CardTitle class="text-sm">Recent Mentions</CardTitle>
              <CardDescription>Sorted and filtered records for review.</CardDescription>
            </div>
            
            <div class="flex items-center gap-2 text-xs text-neutral-500">
              <Button variant="outline" size="sm" @click="changePage(-1)" :disabled="page <= 1">Previous</Button>
              <span>Page {{ page }} / {{ analyticsData.pagination?.total_pages || 1 }}</span>
              <Button variant="outline" size="sm" @click="changePage(1)" :disabled="page >= (analyticsData.pagination?.total_pages || 1)">Next</Button>
            </div>
          </CardHeader>
          
          <CardContent class="p-0 border-t border-border">
            <div class="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead class="w-32">Sentiment</TableHead>
                    <TableHead class="w-32">Product</TableHead>
                    <TableHead>Content</TableHead>
                    <TableHead class="w-24">Score</TableHead>
                    <TableHead class="w-28">Engagement</TableHead>
                    <TableHead class="w-44">Timestamp</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow v-for="mention in analyticsData.recent_mentions" :key="mention.id">
                    <TableCell>
                      <Badge :variant="mention.sentiment === 'POSITIVE' ? 'success' : mention.sentiment === 'NEGATIVE' ? 'destructive' : 'secondary'">
                        {{ mention.sentiment }}
                      </Badge>
                    </TableCell>
                    <TableCell class="font-medium text-foreground">{{ mention.product }}</TableCell>
                    <TableCell class="max-w-md text-muted-foreground leading-relaxed break-words py-3">{{ mention.content }}</TableCell>
                    <TableCell class="font-mono text-xs">{{ mention.overall_score?.toFixed(2) ?? 'N/A' }}</TableCell>
                    <TableCell>{{ mention.engagement ?? 0 }}</TableCell>
                    <TableCell class="text-neutral-500 text-xs">{{ mention.post_createdat ? new Date(mention.post_createdat).toLocaleString() : 'N/A' }}</TableCell>
                  </TableRow>
                  <TableRow v-if="analyticsData.recent_mentions.length === 0">
                    <TableCell colspan="6" class="text-center text-neutral-500 py-12">No posts match the current filters.</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </template>
    </template>

    <Separator />

    <footer class="text-center text-xs text-neutral-400 py-4">
      Made by Jayavighnesh B K
    </footer>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, computed, reactive, ref, watch } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useRouter } from 'vue-router';
import api from '../api/api';
import Card from '../components/ui/Card.vue';
import CardHeader from '../components/ui/CardHeader.vue';
import CardTitle from '../components/ui/CardTitle.vue';
import CardDescription from '../components/ui/CardDescription.vue';
import CardContent from '../components/ui/CardContent.vue';
import CardFooter from '../components/ui/CardFooter.vue';
import Button from '../components/ui/Button.vue';
import Input from '../components/ui/Input.vue';
import Select from '../components/ui/Select.vue';
import Badge from '../components/ui/Badge.vue';
import Separator from '../components/ui/Separator.vue';
import Table from '../components/ui/Table.vue';
import TableHeader from '../components/ui/TableHeader.vue';
import TableBody from '../components/ui/TableBody.vue';
import TableRow from '../components/ui/TableRow.vue';
import TableHead from '../components/ui/TableHead.vue';
import TableCell from '../components/ui/TableCell.vue';

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar, Doughnut } from 'vue-chartjs';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Title, Tooltip, Legend, Filler);

const auth = useAuthStore();
const router = useRouter();
const user = computed(() => auth.user);

const isFiltersCollapsed = ref(true);
const isAskLLMCollapsed = ref(true);
const tenantForm = reactive({ brand_name: '', keywords: '' });
const newOrgForm = reactive({ name: '', brand_name: '', keywords: '' });
const loading = ref(false);
const message = ref('');

const analyticsData = ref(null);
const queryText = ref('');
const queryTimeframe = ref(null);
const queryLoading = ref(false);
const queryError = ref('');
const queryResult = ref(null);
const page = ref(1);
const limit = ref(10);

const searchInput = ref('');
const selectedKeywords = ref([]);
const selectedTimeframe = ref(null);
const customStart = ref('');
const customEnd = ref('');
const sortBy = ref('time_desc');

let pollInterval = null;

const timeframes = [
  { label: 'All', value: null },
  { label: '1h', value: '1h' },
  { label: '12h', value: '12h' },
  { label: '24h', value: '24h' },
  { label: 'Custom', value: 'custom' },
];

const activeOrganization = computed(() => {
  if (!user.value || !user.value.organizations) return null;
  return user.value.organizations.find(o => o.id === auth.activeTenantId) || user.value.organizations[0];
});

const syncActiveOrganization = async () => {
  if (!activeOrganization.value) {
    analyticsData.value = null;
    return;
  }

  tenantForm.brand_name = activeOrganization.value.brand_name || '';
  tenantForm.keywords = activeOrganization.value.keywords || '';
  selectedKeywords.value = [];
  page.value = 1;
  analyticsData.value = null;
  await fetchAnalytics();
};

const switchOrganizationDirect = (val) => {
  const newTenantId = parseInt(val);
  auth.setActiveTenant(newTenantId);
};

const switchOrganization = (event) => {
  const newTenantId = parseInt(event.target.value);
  auth.setActiveTenant(newTenantId);
};

const tenantKeywordsList = computed(() => {
  const kwStr = activeOrganization.value?.keywords || '';
  if (!kwStr) return [];
  return kwStr.split(',').map((k) => k.trim()).filter(Boolean);
});

const pickBucketMs = (timestamps) => {
  if (!timestamps.length) return 60 * 60 * 1000;
  const minTs = Math.min(...timestamps);
  const maxTs = Math.max(...timestamps);
  const spanMs = Math.max(0, maxTs - minTs);

  if (spanMs <= 2 * 60 * 60 * 1000) return 5 * 60 * 1000;
  if (spanMs <= 24 * 60 * 60 * 1000) return 60 * 60 * 1000;
  if (spanMs <= 7 * 24 * 60 * 60 * 1000) return 6 * 60 * 60 * 1000;
  if (spanMs <= 31 * 24 * 60 * 60 * 1000) return 24 * 60 * 60 * 1000;
  return 7 * 24 * 60 * 60 * 1000;
};

const formatBucketLabel = (bucketStartMs, bucketMs) => {
  const dt = new Date(bucketStartMs);
  if (bucketMs < 24 * 60 * 60 * 1000) {
    return dt.toLocaleString([], {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  return dt.toLocaleDateString([], {
    month: 'short',
    day: '2-digit',
  });
};

const lineChartData = computed(() => {
  const cd = analyticsData.value?.chart_data;
  if (!cd || cd.length === 0) {
    return { labels: [], datasets: [] };
  }

  const timestamps = cd
    .map((item) => Date.parse(item.t))
    .filter((ts) => Number.isFinite(ts));
  const bucketMs = pickBucketMs(timestamps);

  const buckets = new Map();
  cd.forEach((item) => {
    if (!item.t) {
      return;
    }

    const parsedTs = Date.parse(item.t);
    if (!Number.isFinite(parsedTs)) {
      return;
    }

    const bucketStartMs = Math.floor(parsedTs / bucketMs) * bucketMs;
    if (!buckets.has(bucketStartMs)) {
      buckets.set(bucketStartMs, { POSITIVE: 0, NEGATIVE: 0, NEUTRAL: 0, MIXED: 0 });
    }

    const bucket = buckets.get(bucketStartMs);
    if (bucket[item.s] !== undefined) {
      bucket[item.s] += 1;
    }
  });

  const sortedBucketTimes = Array.from(buckets.keys()).sort((a, b) => a - b);
  const labels = sortedBucketTimes.map((ts) => formatBucketLabel(ts, bucketMs));

  return {
    labels,
    datasets: [
      {
        label: 'Positive',
        borderColor: '#10b981',
        backgroundColor: 'rgba(16,185,129,0.08)',
        data: sortedBucketTimes.map((ts) => buckets.get(ts).POSITIVE),
        fill: true,
        tension: 0.3,
      },
      {
        label: 'Negative',
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239,68,68,0.06)',
        data: sortedBucketTimes.map((ts) => buckets.get(ts).NEGATIVE),
        fill: true,
        tension: 0.3,
      },
      {
        label: 'Neutral',
        borderColor: '#737373',
        backgroundColor: 'rgba(115,115,115,0.06)',
        data: sortedBucketTimes.map((ts) => buckets.get(ts).NEUTRAL),
        fill: true,
        tension: 0.3,
      },
    ],
  };
});

const barChartData = computed(() => ({
  labels: ['Positive', 'Negative', 'Neutral'],
  datasets: [
    {
      label: 'Mentions',
      data: [
        analyticsData.value?.summary?.positive || 0,
        analyticsData.value?.summary?.negative || 0,
        analyticsData.value?.summary?.neutral || 0,
      ],
      backgroundColor: ['#10b981', '#ef4444', '#737373'],
      borderRadius: 4,
      barThickness: 24,
    },
  ],
}));

const isDarkTheme = computed(() => auth.theme === 'dark');

const sharedChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { labels: { color: isDarkTheme.value ? '#ffffff' : '#000000' } },
  },
  scales: {
    x: {
      ticks: { color: isDarkTheme.value ? '#a3a3a3' : '#666666' },
      grid: { color: isDarkTheme.value ? '#262626' : '#E5E5E5' },
    },
    y: {
      ticks: { color: isDarkTheme.value ? '#a3a3a3' : '#666666' },
      grid: { color: isDarkTheme.value ? '#262626' : '#E5E5E5' },
      beginAtZero: true,
    },
  },
}));

const lineChartOptions = computed(() => ({
  ...sharedChartOptions.value,
}));

const barChartOptions = computed(() => ({
  ...sharedChartOptions.value,
  plugins: {
    legend: { display: false },
  },
}));

const queryDoughnutData = computed(() => ({
  labels: ['Positive', 'Negative', 'Neutral'],
  datasets: [
    {
      data: [
        queryResult.value?.summary?.positive || 0,
        queryResult.value?.summary?.negative || 0,
        queryResult.value?.summary?.neutral || 0,
      ],
      backgroundColor: ['#10b981', '#ef4444', '#737373'],
      borderWidth: 0,
    },
  ],
}));

const queryDoughnutOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom',
      labels: { color: isDarkTheme.value ? '#ffffff' : '#000000' },
    },
  },
}));

const buildParams = () => {
  const params = new URLSearchParams({
    page: page.value.toString(),
    limit: limit.value.toString(),
    sort_by: sortBy.value,
  });

  if (selectedKeywords.value.length) params.append('keywords', selectedKeywords.value.join(','));
  if (searchInput.value.trim()) params.append('search', searchInput.value.trim());

  if (selectedTimeframe.value) {
    params.append('timeframe', selectedTimeframe.value);
    if (selectedTimeframe.value === 'custom' && customStart.value && customEnd.value) {
      params.append('start_time', new Date(customStart.value).toISOString());
      params.append('end_time', new Date(customEnd.value).toISOString());
    }
  }

  return params;
};

const fetchAnalytics = async (silent = false) => {
  try {
    const res = await api.get(`/analytics?${buildParams().toString()}`);
    analyticsData.value = res.data;
  } catch (error) {
    if (!silent) console.error('Failed to fetch analytics:', error);
  }
};

const runSentimentQuery = async () => {
  const trimmedQuery = queryText.value.trim();
  if (!trimmedQuery) {
    queryError.value = 'Enter a question first.';
    return;
  }

  queryLoading.value = true;
  queryError.value = '';

  try {
    const res = await api.post('/admin/sentiment-query', {
      query: trimmedQuery,
      timeframe: queryTimeframe.value,
    });
    queryResult.value = res.data;
  } catch (error) {
    queryResult.value = null;
    queryError.value = error.response?.data?.detail || 'Failed to analyze the question.';
  } finally {
    queryLoading.value = false;
  }
};

const clearSentimentQuery = () => {
  queryText.value = '';
  queryTimeframe.value = null;
  queryError.value = '';
  queryResult.value = null;
};

const applyFilters = () => {
  page.value = 1;
  fetchAnalytics();
};

const resetFilters = () => {
  searchInput.value = '';
  selectedKeywords.value = [];
  selectedTimeframe.value = null;
  customStart.value = '';
  customEnd.value = '';
  sortBy.value = 'time_desc';
  applyFilters();
};

watch(page, () => fetchAnalytics());

watch(
  () => auth.activeTenantId,
  async (newTenantId, oldTenantId) => {
    if (!newTenantId || newTenantId === oldTenantId) return;
    await syncActiveOrganization();
  }
);

const changePage = (offset) => {
  page.value += offset;
};

const toggleFilters = () => {
  isFiltersCollapsed.value = !isFiltersCollapsed.value;
};

const toggleAskLLM = () => {
  isAskLLMCollapsed.value = !isAskLLMCollapsed.value;
};

onMounted(async () => {
  if (!auth.user) await auth.fetchMe();

  if (activeOrganization.value) {
    await syncActiveOrganization();
    pollInterval = setInterval(() => fetchAnalytics(true), 5000);
  }
});

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval);
});

const updateTenantProfile = async () => {
  loading.value = true;
  try {
    const res = await api.patch('/tenant', tenantForm);
    message.value = res.data.msg;
    await auth.fetchMe();
    await fetchAnalytics();
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
};

const createOrganization = async () => {
  if (!newOrgForm.name) {
    message.value = 'Organization System Name is required.';
    return;
  }
  loading.value = true;
  try {
    const res = await api.post('/organization', newOrgForm);
    message.value = res.data.msg;
    await auth.fetchMe();
    auth.setActiveTenant(res.data.tenant_id);
  } catch (error) {
    message.value = error.response?.data?.detail || 'Failed to create organization';
    console.error(error);
  } finally {
    loading.value = false;
  }
};
</script>
