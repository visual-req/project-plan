<template>
  <a-card>
    <template #title>
      <a-space>
        <a-typography-text>{{ t("estimate") }}</a-typography-text>
        <a-button size="small" @click="openStandards">{{ t("maintainStandards") }}</a-button>
      </a-space>
    </template>

    <a-table
      :columns="columns"
      :dataSource="rows"
      :pagination="{ pageSize: 10 }"
      rowKey="story_id"
      :expandRowByClick="true"
    >
      <template #expandedRowRender="{ record }">
        <div class="expanded">
          <a-typography-text strong>{{ t("assumptions") }}</a-typography-text>
          <ul class="list">
            <li v-for="(a, idx) in (record.assumptions || [])" :key="idx">{{ a }}</li>
          </ul>
        </div>
      </template>
    </a-table>

    <a-drawer
      :open="standardsVisible"
      :title="t('standardsTitle')"
      placement="right"
      width="520"
      @close="standardsVisible = false"
    >
      <a-alert
        v-if="standardsError"
        type="error"
        show-icon
        :message="standardsError"
        style="margin-bottom: 12px;"
      />

      <a-spin :spinning="standardsLoading || standardsSaving">
        <a-space v-if="standards && standards.types && standards.types.length" style="margin-bottom: 12px;">
          <a-typography-text>类型：</a-typography-text>
          <a-select
            style="width: 240px;"
            :value="selectedType"
            @change="selectedType = $event"
          >
            <a-select-option
              v-for="tItem in standards.types"
              :key="tItem.key"
              :value="tItem.key"
            >
              {{ tItem.label }}
            </a-select-option>
          </a-select>
        </a-space>

        <a-table
          v-if="standards && standards.matrix && selectedType && standards.matrix[selectedType]"
          :dataSource="standards.matrix[selectedType]"
          :pagination="false"
          rowKey="key"
          size="small"
        >
          <a-table-column title="Key" dataIndex="key" key="key" width="70" />
          <a-table-column title="Dev" key="dev_days" width="120">
            <template #default="{ record }">
              <a-input-number v-model:value="record.dev_days" :min="0" :step="0.5" style="width: 100%;" />
            </template>
          </a-table-column>
          <a-table-column title="Test" key="test_days" width="120">
            <template #default="{ record }">
              <a-input-number v-model:value="record.test_days" :min="0" :step="0.5" style="width: 100%;" />
            </template>
          </a-table-column>
          <a-table-column title="PM" key="pm_days" width="120">
            <template #default="{ record }">
              <a-input-number v-model:value="record.pm_days" :min="0" :step="0.5" style="width: 100%;" />
            </template>
          </a-table-column>
        </a-table>

        <div style="margin-top: 12px;">
          <a-space>
            <a-button type="primary" @click="saveStandards">{{ t("save") }}</a-button>
            <a-button type="primary" @click="reloadStandards">{{ t("refresh") }}</a-button>
          </a-space>
        </div>
      </a-spin>
    </a-drawer>
  </a-card>
</template>

<script>
export default {
  name: "EstimateView",
  props: {
    rows: { type: Array, required: true },
    t: { type: Function, required: true },
  },
  data() {
    return {
      standardsVisible: false,
      standardsLoading: false,
      standardsSaving: false,
      standardsError: "",
      standards: null,
      selectedType: "",
    };
  },
  computed: {
    columns() {
      return [
        { title: this.t("module"), dataIndex: "module", key: "module", width: 140 },
        { title: this.t("feature"), dataIndex: "feature", key: "feature", width: 180 },
        { title: this.t("complexity"), dataIndex: "complexity", key: "complexity", width: 90 },
        { title: this.t("devDays"), dataIndex: "dev_days", key: "dev_days", width: 100 },
        { title: this.t("testDays"), dataIndex: "test_days", key: "test_days", width: 100 },
        { title: this.t("pmDays"), dataIndex: "pm_days", key: "pm_days", width: 120 },
      ];
    },
  },
  methods: {
    async reloadStandards() {
      this.standardsError = "";
      this.standardsLoading = true;
      try {
        const resp = await fetch("/api/meta/estimation-standards", { cache: "no-store" });
        if (!resp.ok) throw new Error(await resp.text());
        this.standards = await resp.json();
        if (!this.selectedType && this.standards && Array.isArray(this.standards.types) && this.standards.types.length) {
          this.selectedType = this.standards.types[0].key;
        }
      } catch (e) {
        this.standardsError = e instanceof Error ? e.message : String(e);
      } finally {
        this.standardsLoading = false;
      }
    },
    async saveStandards() {
      if (!this.standards) return;
      this.standardsError = "";
      this.standardsSaving = true;
      try {
        const resp = await fetch("/api/meta/estimation-standards", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(this.standards),
        });
        if (!resp.ok) throw new Error(await resp.text());
        this.standards = await resp.json();
      } catch (e) {
        this.standardsError = e instanceof Error ? e.message : String(e);
      } finally {
        this.standardsSaving = false;
      }
    },
    async openStandards() {
      this.standardsVisible = true;
      if (!this.standards) {
        await this.reloadStandards();
      }
    },
  },
};
</script>
