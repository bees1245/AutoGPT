import { promises as fs } from "fs";
import path from "path";

interface Metrics {
  files: number;
  directories: number;
  lines: number;
  characters: number;
}

const SKIP_DIRECTORIES = new Set([
  ".next",
  "node_modules",
  "storybook-static",
]);

async function collectMetrics(basePath: string): Promise<Metrics> {
  const stack: string[] = [basePath];
  const totals: Metrics = { files: 0, directories: 0, lines: 0, characters: 0 };

  while (stack.length > 0) {
    const current = stack.pop()!;
    const entries = await fs.readdir(current, { withFileTypes: true });

    for (const entry of entries) {
      if (entry.name.startsWith(".")) {
        continue;
      }

      const entryPath = path.join(current, entry.name);

      if (entry.isDirectory()) {
        if (SKIP_DIRECTORIES.has(entry.name)) {
          continue;
        }

        totals.directories += 1;
        stack.push(entryPath);
        continue;
      }

      if (!entry.isFile()) {
        continue;
      }

      totals.files += 1;
      const fileContent = await fs.readFile(entryPath, "utf8");
      totals.lines += fileContent.split(/\r?\n/).length;
      totals.characters += fileContent.length;
    }
  }

  return totals;
}

async function main() {
  const basePath = process.argv[2] ? path.resolve(process.argv[2]) : process.cwd();
  const metrics = await collectMetrics(basePath);

  const summary = {
    basePath,
    ...metrics,
  };

  console.log(JSON.stringify(summary, null, 2));
}

main().catch((error) => {
  console.error("Failed to collect repository metrics:", error);
  process.exitCode = 1;
});
