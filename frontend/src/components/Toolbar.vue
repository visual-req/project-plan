<template>
  <div class="toolbar">
    <a-upload :customRequest="handleUpload" :showUploadList="false" accept=".docx">
      <a-button type="primary" :loading="uploading">{{ t("chooseDoc") }}</a-button>
    </a-upload>

    <div class="toolbar-right">
      <a-space>
        <a-button @click="$emit('decompose')" :disabled="!canRun" :loading="runningDecompose">{{ t("decompose") }}</a-button>
        <a-button @click="$emit('schedule')" :disabled="!canRun" :loading="runningSchedule">{{ t("schedule") }}</a-button>
        <a-button @click="$emit('estimate')" :disabled="!canRun" :loading="runningEstimate">{{ t("estimate") }}</a-button>
      </a-space>
    </div>
  </div>
</template>

<script>
export default {
  name: "Toolbar",
  props: {
    uploading: { type: Boolean, required: true },
    canRun: { type: Boolean, required: true },
    runningDecompose: { type: Boolean, required: true },
    runningSchedule: { type: Boolean, required: true },
    runningEstimate: { type: Boolean, required: true },
    t: { type: Function, required: true },
  },
  emits: ["upload", "decompose", "schedule", "estimate"],
  methods: {
    handleUpload(args) {
      this.$emit("upload", args);
    },
  },
};
</script>
