/// <reference types="astro/client" />

// 由 astro.config.mjs 的 vite.define 注入，值来自仓库根的 .env 或 CI 环境变量
declare const __SITE_NAME__: string;
