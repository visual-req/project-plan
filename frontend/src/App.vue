<template>
  <a-layout class="layout">
    <a-layout-header class="header">
      <div class="header-left">{{ t("appTitle") }}</div>
      <div class="header-right">
        <a-space>
          <a-select
            :value="ui.lang"
            @change="setLang"
            size="small"
            style="width: 110px;"
          >
            <a-select-option value="zh-CN">中文</a-select-option>
            <a-select-option value="ja-JP">日本語</a-select-option>
            <a-select-option value="en-US">English</a-select-option>
          </a-select>
        </a-space>
      </div>
    </a-layout-header>

    <a-layout-content class="content">
      <div class="page">
        <a-card>
          <Toolbar
            :uploading="state.uploading"
            :canRun="canRun"
            :runningDecompose="state.running.decompose"
            :runningSchedule="state.running.schedule"
            :runningEstimate="state.running.estimate"
            :t="t"
            @upload="handleUpload"
            @decompose="runDecompose"
            @schedule="runSchedule"
            @estimate="runEstimate"
          />

          <div v-if="state.doc.id" class="meta">
            <a-tag color="blue">doc_id: {{ state.doc.id }}</a-tag>
            <a-tag>{{ state.doc.filename }}</a-tag>
          </div>

          <a-alert
            v-if="state.error"
            type="error"
            show-icon
            :message="state.error"
            style="margin-top: 12px;"
          />

          <Artifacts v-if="state.doc.id" :docId="state.doc.id" :lang="ui.lang" :t="t" />
        </a-card>

        <a-tabs v-model:activeKey="ui.activeTab" style="margin-top: 16px;" type="card">
          <a-tab-pane key="decompose" :tab="t('decompose')">
            <DecomposeView :stories="stories" :t="t" />
          </a-tab-pane>

          <a-tab-pane key="schedule" :tab="t('scheduleMap')">
            <ScheduleView :schedule="state.schedule" :t="t" />
          </a-tab-pane>

          <a-tab-pane key="estimate" :tab="t('estimate')">
            <EstimateView :rows="estimateRows" :t="t" />
          </a-tab-pane>
        </a-tabs>
      </div>
    </a-layout-content>
  </a-layout>
</template>

<script>
const { computed, reactive } = window.Vue;

export default {
  name: "App",
  setup() {
    const dict = {
      "zh-CN": {
        appTitle: "项目计划分析器",
        id: "ID",
        chooseDoc: "选择 Word(.docx)",
        decompose: "分解",
        schedule: "排期",
        estimate: "估算",
        artifacts: "过程数据（落盘 JSON / txt）：",
        scheduleHint: "点击“排期”生成用户故事地图。",
        scheduleInvalid: "排期数据结构不符合迭代泳道格式，请重新点击“排期”。",
        module: "模块",
        feature: "功能",
        title: "标题",
        story: "用户故事",
        priority: "优先级",
        ac: "验收标准（AC）",
        notes: "备注：",
        assumptions: "假设：",
        typeLabel: "类型：",
        storyId: "故事",
        complexity: "复杂度",
        devDays: "开发(天)",
        testDays: "测试(天)",
        pmDays: "产品/交付(天)",
        risk: "风险",
        scheduleMap: "排期（故事地图）",
        maintainStandards: "维护标准估算",
        standardsTitle: "标准估算值（work/meta/estimation_standards.json）",
        save: "保存",
        refresh: "刷新",
        llmConnFailed: "服务不可用：无法连接后端或大模型",
        needDecomposeBeforeSchedule: "需要先分解，才能排期",
        needDecomposeBeforeEstimate: "需要先分解，才能估算",
      },
      "ja-JP": {
        appTitle: "プロジェクト計画アナライザー",
        id: "ID",
        chooseDoc: "Word(.docx) を選択",
        decompose: "分解",
        schedule: "計画",
        estimate: "見積",
        artifacts: "生成データ（JSON / txt）：",
        scheduleHint: "「計画」をクリックしてユーザーストーリーマップを生成します。",
        scheduleInvalid: "計画データの形式が想定と異なります。もう一度「計画」をクリックしてください。",
        module: "モジュール",
        feature: "機能",
        title: "タイトル",
        story: "ユーザーストーリー",
        priority: "優先度",
        ac: "受入条件（AC）",
        notes: "備考：",
        assumptions: "前提：",
        typeLabel: "タイプ：",
        storyId: "ストーリー",
        complexity: "複雑度",
        devDays: "開発(日)",
        testDays: "テスト(日)",
        pmDays: "PM(日)",
        risk: "リスク",
        scheduleMap: "計画（ストーリーマップ）",
        maintainStandards: "標準見積を編集",
        standardsTitle: "標準見積（work/meta/estimation_standards.json）",
        save: "保存",
        refresh: "更新",
        llmConnFailed: "サービスが利用できません：バックエンドまたはLLMに接続できません",
        needDecomposeBeforeSchedule: "先に分解してください。分解後に計画できます",
        needDecomposeBeforeEstimate: "先に分解してください。分解後に見積できます",
      },
      "en-US": {
        appTitle: "Project Plan Analyzer",
        id: "ID",
        chooseDoc: "Choose Word(.docx)",
        decompose: "Decompose",
        schedule: "Schedule",
        estimate: "Estimate",
        artifacts: "Artifacts (JSON / txt):",
        scheduleHint: 'Click "Schedule" to generate the story map.',
        scheduleInvalid: 'Schedule output format is invalid. Please click "Schedule" again.',
        module: "Module",
        feature: "Feature",
        title: "Title",
        story: "User Story",
        priority: "Priority",
        ac: "Acceptance Criteria",
        notes: "Notes:",
        assumptions: "Assumptions:",
        typeLabel: "Type:",
        storyId: "Story",
        complexity: "Complexity",
        devDays: "Dev (days)",
        testDays: "Test (days)",
        pmDays: "PM (days)",
        risk: "Risk",
        scheduleMap: "Schedule (Story Map)",
        maintainStandards: "Edit Standards",
        standardsTitle: "Estimation Standards (work/meta/estimation_standards.json)",
        save: "Save",
        refresh: "Refresh",
        llmConnFailed: "Service unavailable: cannot reach backend or LLM",
        needDecomposeBeforeSchedule: "Please decompose first, then schedule",
        needDecomposeBeforeEstimate: "Please decompose first, then estimate",
      },
    };

    const ui = reactive({
      lang: window.localStorage.getItem("lang") || "zh-CN",
      activeTab: "decompose",
    });

    const state = reactive({
      uploading: false,
      running: {
        decompose: false,
        schedule: false,
        estimate: false,
      },
      doc: {
        id: "",
        filename: "",
      },
      error: "",
      decompose: null,
      schedule: null,
      estimate: null,
    });

    const canRun = computed(() => !!state.doc.id && !state.uploading);
    const stories = computed(() => {
      const s = state.decompose?.stories;
      return Array.isArray(s) ? s : [];
    });
    const estimateRows = computed(() => {
      const r = state.estimate?.rows;
      return Array.isArray(r) ? r : [];
    });

    function t(key) {
      const lang = dict[ui.lang] ? ui.lang : "zh-CN";
      return dict[lang][key] || key;
    }

    function setLang(value) {
      ui.lang = value;
      window.localStorage.setItem("lang", value);
    }

    function normalizeError(err) {
      if (err instanceof Error) return err.message;
      if (typeof err === "string") return err;
      try {
        return JSON.stringify(err);
      } catch {
        return String(err);
      }
    }

    async function postJson(url, body) {
      let resp;
      try {
        resp = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
      } catch {
        throw new Error(t("llmConnFailed"));
      }

      const text = await resp.text();
      if (!resp.ok) {
        try {
          const payload = text ? JSON.parse(text) : null;
          if (payload && typeof payload.detail === "string") {
            throw new Error(payload.detail);
          }
        } catch {}
        throw new Error(text || `HTTP ${resp.status}`);
      }
      return text ? JSON.parse(text) : {};
    }

    async function uploadDocx(file) {
      const form = new FormData();
      form.append("file", file);
      const resp = await fetch("/api/upload", { method: "POST", body: form });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `HTTP ${resp.status}`);
      }
      return await resp.json();
    }

    async function handleUpload({ file, onSuccess, onError }) {
      state.error = "";
      state.uploading = true;
      state.doc.id = "";
      state.doc.filename = "";
      state.decompose = null;
      state.schedule = null;
      state.estimate = null;
      try {
        const res = await uploadDocx(file);
        state.doc.id = res.doc_id;
        state.doc.filename = res.filename || file.name;
        onSuccess?.(res, file);
      } catch (e) {
        state.error = normalizeError(e);
        onError?.(e);
      } finally {
        state.uploading = false;
      }
    }

    async function runDecompose() {
      state.error = "";
      state.running.decompose = true;
      try {
        state.decompose = await postJson("/api/decompose", { doc_id: state.doc.id, lang: ui.lang });
        ui.activeTab = "decompose";
      } catch (e) {
        state.error = normalizeError(e);
      } finally {
        state.running.decompose = false;
      }
    }

    async function runSchedule() {
      state.error = "";
      if (!state.decompose || !Array.isArray(state.decompose.stories) || state.decompose.stories.length === 0) {
        state.error = t("needDecomposeBeforeSchedule");
        ui.activeTab = "decompose";
        return;
      }
      state.running.schedule = true;
      try {
        state.schedule = await postJson("/api/schedule", { doc_id: state.doc.id, lang: ui.lang });
        ui.activeTab = "schedule";
      } catch (e) {
        state.error = normalizeError(e);
      } finally {
        state.running.schedule = false;
      }
    }

    async function runEstimate() {
      state.error = "";
      if (!state.decompose || !Array.isArray(state.decompose.stories) || state.decompose.stories.length === 0) {
        state.error = t("needDecomposeBeforeEstimate");
        ui.activeTab = "decompose";
        return;
      }
      state.running.estimate = true;
      try {
        state.estimate = await postJson("/api/estimate", { doc_id: state.doc.id, lang: ui.lang });
        ui.activeTab = "estimate";
      } catch (e) {
        state.error = normalizeError(e);
      } finally {
        state.running.estimate = false;
      }
    }

    return {
      ui,
      state,
      canRun,
      stories,
      estimateRows,
      t,
      setLang,
      handleUpload,
      runDecompose,
      runSchedule,
      runEstimate,
    };
  },
};
</script>
