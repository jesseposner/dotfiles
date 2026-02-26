import { readFileSync, readdirSync } from "fs";
import { dirname, resolve } from "path";
import { parseArgs } from "node:util";
import { marked } from "marked";
import puppeteer from "puppeteer";

const scriptDir = dirname(new URL(import.meta.url).pathname);
const themesDir = resolve(scriptDir, "themes");

const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    theme:  { type: "string", short: "t" },
    css:    { type: "string", short: "c" },
    output: { type: "string", short: "o" },
    themes: { type: "boolean" },
    help:   { type: "boolean", short: "h" },
  },
});

if (values.themes) {
  const themes = readdirSync(themesDir)
    .filter(f => f.endsWith(".css"))
    .map(f => f.replace(/\.css$/, ""));
  console.log("Available themes:");
  for (const t of themes) {
    console.log(`  ${t}${t === "github" ? " (default)" : ""}`);
  }
  process.exit(0);
}

if (values.help || positionals.length === 0) {
  console.log(`Usage: mdpdf <input.md> [options]

Options:
  -t, --theme <name>   Use a built-in theme (default: github)
  -c, --css <file>     Use a custom CSS file
  -o, --output <file>  Output PDF path (default: input.pdf)
      --themes         List available themes
  -h, --help           Show this help`);
  process.exit(0);
}

const mdFile = positionals[0];

let cssFile;
if (values.css) {
  cssFile = resolve(values.css);
} else {
  const theme = values.theme || "github";
  cssFile = resolve(themesDir, `${theme}.css`);
}

const outFile = values.output || mdFile.replace(/\.md$/, ".pdf");

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
