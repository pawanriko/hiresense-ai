import type { MetadataRoute } from "next";

const BASE = "https://hiresense-ai-nine.vercel.app";

export default function sitemap(): MetadataRoute.Sitemap {
  const pages = ["", "/login", "/dashboard", "/resume-lab", "/jd-match", "/interview"];
  return pages.map((page) => ({
    url: `${BASE}${page}`,
    lastModified: new Date(),
    changeFrequency: "weekly",
    priority: page === "" ? 1 : 0.8,
  }));
}
