import { defineStore } from "pinia";
import api from "../api/api";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null, // this will hold the response from /me
    token: localStorage.getItem("token") || "",
    activeTenantId: localStorage.getItem("activeTenantId") || null,
    theme: localStorage.getItem("theme") || "dark",
  }),

  actions: {
    setTheme(theme) {
      this.theme = theme;
      localStorage.setItem("theme", theme);
      if (theme === "dark") {
        document.documentElement.classList.add("dark");
      } else {
        document.documentElement.classList.remove("dark");
      }
    },

    async login(payload) {
      const res = await api.post("/login", payload);

      this.token = res.data.access_token;
      localStorage.setItem("token", this.token);
      await this.fetchMe();
    },

    async register(payload) {
      await api.post("/register", payload);
    },

    logout() {
      this.user = null;
      this.token = "";
      this.activeTenantId = null;
      localStorage.removeItem("token");
      localStorage.removeItem("activeTenantId");
    },

    setActiveTenant(tenantId) {
      this.activeTenantId = Number(tenantId);
      localStorage.setItem("activeTenantId", String(tenantId));
    },

    async fetchMe() {
      const res = await api.get("/me", {
        headers: {
          "X-Skip-Tenant": "1",
        },
      });
      this.user = res.data;

      const stillExists = this.user.organizations?.some((org) => org.id === Number(this.activeTenantId));
      if (!stillExists) {
        this.activeTenantId = null;
        localStorage.removeItem("activeTenantId");
      }
      
      // Auto-select first organization if none is selected
      if (!this.activeTenantId && this.user.organizations?.length > 0) {
        this.activeTenantId = this.user.organizations[0].id;
        localStorage.setItem("activeTenantId", this.activeTenantId);
      }
    },
  },
});