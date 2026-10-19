export default defineNuxtConfig({
  modules: ["@pinia/nuxt", "@vueuse/nuxt", "@nuxt/eslint"],
  runtimeConfig: {
    public: {
      apiBase: "",
    },
  },
  typescript: { strict: true },
})
