import { rm } from "node:fs/promises";
import { resolve } from "node:path";
import react from "@astrojs/react";
import { defineConfig } from "astro/config";
import { loadEnv } from "vite";

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

// .env 在仓库根，和 Python 脚本共用一份。第三个参数是空前缀，
// 表示不限于 PUBLIC_，构建期需要什么就取什么。
const env = loadEnv(process.env.NODE_ENV ?? "production", resolve(".."), "");

// 构建产物直接写进仓库根目录的 out/，与 build_feed.py 共用同一个部署目录。
// Astro 构建时会清空 out/，所以 feed.xml 必须在构建之后生成（publish.py 保证顺序）。
export default defineConfig({
  integrations: [react(), stripBuildMetadata],
  outDir: "../out",
  publicDir: "public",
  build: { assets: "assets" },
  vite: {
    define: {
      __SITE_NAME__: JSON.stringify(env.AINFORMER_SITE_NAME || "AI 情报池"),
    },
  },
});
