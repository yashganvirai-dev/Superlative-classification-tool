// One-off static check: find JSX components used but never imported/declared.
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "src");

function walk(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(full));
    else if (/\.(jsx|js)$/.test(entry.name)) out.push(full);
  }
  return out;
}

const problems = [];
for (const file of walk(root)) {
  const src = fs.readFileSync(file, "utf8");

  const declared = new Set();

  // named imports: import { a, b as c } from "x";
  for (const m of src.matchAll(/import\s*\{([^}]+)\}\s*from/g)) {
    for (let part of m[1].split(",")) {
      part = part.trim();
      if (!part) continue;
      const asMatch = part.match(/^\S+\s+as\s+(\S+)$/);
      declared.add(asMatch ? asMatch[1] : part.split(/\s+/)[0]);
    }
  }
  // default + namespace imports
  for (const m of src.matchAll(/import\s+(\w+)\s+from/g)) declared.add(m[1]);
  for (const m of src.matchAll(/import\s*\*\s*as\s+(\w+)/g)) declared.add(m[1]);

  // local declarations (function/const/let/var/class)
  for (const m of src.matchAll(/(?:function|const|let|var|class)\s+([A-Z]\w*)/g)) {
    declared.add(m[1]);
  }
  // props destructure etc. won't be uppercase components typically

  // JSX usage: <Name or <Namespace.Name
  const used = new Set();
  for (const m of src.matchAll(/<([A-Z][\w.]*)/g)) used.add(m[1].split(".")[0]);

  for (const name of used) {
    if (!declared.has(name)) {
      problems.push(`${path.relative(root, file)}: <${name} /> used but not imported/declared`);
    }
  }
}

if (problems.length === 0) {
  console.log("OK: no missing JSX component imports found.");
} else {
  console.log("PROBLEMS:");
  for (const p of problems) console.log(" - " + p);
  process.exit(1);
}
