const { loadModule } = window["vue3-sfc-loader"];

const options = {
  moduleCache: {
    vue: window.Vue,
  },
  async getFile(url) {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) {
      throw new Error(`Failed to load ${url}: ${res.status} ${res.statusText}`);
    }
    const text = await res.text();
    return {
      getContentData: () => text,
    };
  },
  addStyle(textContent) {
    const style = document.createElement("style");
    style.textContent = textContent;
    document.head.appendChild(style);
  },
};

const App = await loadModule("/src/App.vue", options);
const Toolbar = await loadModule("/src/components/Toolbar.vue", options);
const Artifacts = await loadModule("/src/components/Artifacts.vue", options);
const DecomposeView = await loadModule("/src/views/DecomposeView.vue", options);
const ScheduleView = await loadModule("/src/views/ScheduleView.vue", options);
const EstimateView = await loadModule("/src/views/EstimateView.vue", options);

const app = window.Vue.createApp(App);
app.use(window.antd);
app.component("Toolbar", Toolbar);
app.component("Artifacts", Artifacts);
app.component("DecomposeView", DecomposeView);
app.component("ScheduleView", ScheduleView);
app.component("EstimateView", EstimateView);
app.mount("#app");
