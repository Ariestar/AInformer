import { rm } from "node:fs/promises";
import { defineConfig } from "astro/config";
import react from "@astrojs/react";

// Astro 会把 content layer 的构建元数据和缓存写进输出目录，它们不参与部署，
// 留在 out/ 里既浪费空间也会被 Cloudflare 一起发出去。
const STRIP = ["content-assets.mjs", "content-modules.mjs", "data-store.json", "settings.json"];
const stripBuildMetadata = {
  name: "strip-build-metadata",
  hooks: {
    "astro:build:done": async ({ dir }) => {
      for (const name of STRIP) {
        await rm(new URL(name, dir), { force: true });
      }
    },
  },
};

// 构建产物直接写进仓库根目录的 out/，与 build_feed.py 共用同一个部署目录。
// Astro 构建时会清空 out/，所以 feed.xml 必须在构建之后生成（publish.py 保证顺序）。
export default defineConfig({
  integrations: [react(), stripBuildMetadata],
  outDir: "../out",
  publicDir: "public",
  build: { assets: "assets" },
});
