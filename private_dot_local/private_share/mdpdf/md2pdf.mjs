import { readFileSync } from "fs";
import { dirname, resolve } from "path";
import { marked } from "marked";
import puppeteer from "puppeteer";

const mdFile = process.argv[2];
const cssFile = process.argv[3] || resolve(dirname(new URL(import.meta.url).pathname), "splendor.css");
const outFile = process.argv[4] || mdFile.replace(/\.md$/, ".pdf");

if (!mdFile) {
  console.error("Usage: mdpdf <input.md> [style.css] [output.pdf]");
  process.exit(1);
}

const md = readFileSync(mdFile, "utf-8");
const css = readFileSync(cssFile, "utf-8");
const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>${css}</style></head>
<body>${marked(md)}</body></html>`;

const browser = await puppeteer.launch();
const page = await browser.newPage();
await page.setContent(html, { waitUntil: "networkidle0" });
await page.pdf({ path: outFile, format: "Letter", margin: { top: "20mm", bottom: "20mm", left: "20mm", right: "20mm" } });
await browser.close();
console.log(`wrote ${outFile}`);
