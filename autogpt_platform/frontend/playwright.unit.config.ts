import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./src/tests",
  testMatch: "**/security-headers.spec.ts",
  reporter: [["list"]],
  workers: 1,
  use: {
    browserName: "chromium",
    headless: true,
  },
});
