<template>
  <a-card>
    <div v-if="!schedule" class="empty">
      <a-typography-text>{{ t("scheduleHint") }}</a-typography-text>
    </div>

    <div v-else class="story-map-grid">
      <div v-if="hasGrid" class="usm-grid">
        <div class="usm-header">
          <div class="usm-corner"></div>
          <div class="usm-columns" :style="{ '--usm-cols': modules.length }">
            <div v-for="m in modules" :key="m" class="usm-col-header">{{ m }}</div>
          </div>
        </div>

        <div v-for="it in iterations" :key="it.name" class="usm-row">
          <div class="usm-row-header">{{ it.name }}</div>
          <div class="usm-columns" :style="{ '--usm-cols': modules.length }">
            <div v-for="m in modules" :key="m" class="usm-cell">
              <div class="usm-cards">
                <a-card
                  v-for="s in laneStories(it, m)"
                  :key="s.id + '-' + m"
                  size="small"
                  class="usm-card"
                  :title="s.feature || ''"
                >
                  <div class="usm-card-title">{{ s.title }}</div>
                  <div class="usm-card-id">{{ s.id }}</div>
                </a-card>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="empty">
        <a-typography-text>排期数据结构不符合迭代泳道格式，请重新点击“排期”。</a-typography-text>
      </div>
    </div>
  </a-card>
</template>

<script>
export default {
  name: "ScheduleView",
  props: {
    schedule: { type: Object, required: false, default: null },
    t: { type: Function, required: true },
  },
  computed: {
    hasGrid() {
      return !!(this.schedule && Array.isArray(this.schedule.modules) && Array.isArray(this.schedule.iterations));
    },
    modules() {
      return this.hasGrid ? this.schedule.modules : [];
    },
    iterations() {
      return this.hasGrid ? this.schedule.iterations : [];
    },
  },
  methods: {
    laneStories(iteration, moduleName) {
      const lanes = Array.isArray(iteration?.lanes) ? iteration.lanes : [];
      const lane = lanes.find((x) => x && x.module === moduleName);
      const stories = Array.isArray(lane?.stories) ? lane.stories : [];
      return stories;
    },
  },
};
</script>
