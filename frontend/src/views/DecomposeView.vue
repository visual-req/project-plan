<template>
  <a-card>
    <a-table
      :columns="columns"
      :dataSource="stories"
      :pagination="{ pageSize: 10 }"
      rowKey="id"
      :expandRowByClick="true"
    >
      <template #expandedRowRender="{ record }">
        <div class="expanded">
          <a-typography-text strong>{{ t("ac") }}</a-typography-text>
          <ul class="list">
            <li v-for="(ac, idx) in (record.acceptance_criteria || [])" :key="idx">{{ ac }}</li>
          </ul>
          <div v-if="record.notes" class="notes">
            <a-typography-text strong>{{ t("notes") }}</a-typography-text>
            <a-typography-text>{{ record.notes }}</a-typography-text>
          </div>
        </div>
      </template>
    </a-table>
  </a-card>
</template>

<script>
export default {
  name: "DecomposeView",
  props: {
    stories: { type: Array, required: true },
    t: { type: Function, required: true },
  },
  computed: {
    columns() {
      return [
        { title: "ID", dataIndex: "id", key: "id", width: 90 },
        { title: this.t("module"), dataIndex: "module", key: "module", width: 140 },
        { title: this.t("feature"), dataIndex: "feature", key: "feature", width: 180 },
        { title: this.t("title"), dataIndex: "title", key: "title", width: 220 },
        { title: this.t("story"), dataIndex: "user_story", key: "user_story" },
        { title: this.t("priority"), dataIndex: "priority", key: "priority", width: 90 },
      ];
    },
  },
};
</script>
