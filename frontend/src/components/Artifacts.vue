<template>
  <div v-if="items.length" class="artifacts">
    <a-typography-text>{{ t("artifacts") }}</a-typography-text>
    <a-space wrap>
      <a
        v-for="a in items"
        :key="a.name"
        class="artifact-link"
        :href="a.url"
        target="_blank"
        rel="noreferrer"
      >
        {{ a.name }}
      </a>
    </a-space>
  </div>
</template>

<script>
export default {
  name: "Artifacts",
  props: {
    docId: { type: String, required: true },
    lang: { type: String, required: true },
    t: { type: Function, required: true },
  },
  computed: {
    items() {
      if (!this.docId) return [];
      const base = `/api/artifacts/${this.docId}`;
      const q = `?lang=${encodeURIComponent(this.lang)}`;
      return [
        { name: "requirement.txt", url: `${base}/requirement.txt${q}` },
        { name: "decompose.json", url: `${base}/decompose.json${q}` },
        { name: "schedule.json", url: `${base}/schedule.json${q}` },
        { name: "estimate.json", url: `${base}/estimate.json${q}` },
      ];
    },
  },
};
</script>
