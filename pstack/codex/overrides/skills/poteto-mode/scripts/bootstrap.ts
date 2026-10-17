import { createHash } from "node:crypto";
import {
  existsSync,
  chmodSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  realpathSync,
  renameSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";

const scriptsDirectory = realpathSync(import.meta.dir);
const runtimeMarker = ".pstack-runtime-key";

function isWithin(directory: string, candidate: string): boolean {
  const path = relative(directory, candidate);
  return path === "" || (!path.startsWith(`..${sep}`) && path !== ".." && !isAbsolute(path));
}

function canonicalPath(path: string): string {
  if (existsSync(path)) return realpathSync(path);
  return join(canonicalPath(dirname(path)), relative(dirname(path), path));
}

function readBundle(directory: string): { path: string; data: Buffer; mode: number }[] {
  return readdirSync(directory).sort().flatMap((name) => {
    if (name === "node_modules" || name === ".git" || name === runtimeMarker) return [];
    const path = join(directory, name);
    const stat = lstatSync(path);
    if (stat.isDirectory()) return readBundle(path);
    if (!stat.isFile()) throw new Error(`Unsupported tools bundle entry: ${path}`);
    return [{ path: relative(scriptsDirectory, path), data: readFileSync(path), mode: stat.mode & 0o777 }];
  });
}

function isReady(directory: string, key: string): boolean {
  const marker = join(directory, runtimeMarker);
  return existsSync(join(directory, "node_modules", "commander", "package.json")) &&
    existsSync(marker) && readFileSync(marker, "utf8").trim() === key;
}

export function ensureDependenciesInstalled(): void {
  const configured = process.env.PSTACK_TOOLS_DIR ||
    (process.env.PSTACK_RUN_DIR ? join(process.env.PSTACK_RUN_DIR, "tools") : undefined);
  if (!configured || !isAbsolute(configured)) {
    throw new Error("Set PSTACK_TOOLS_DIR to an absolute writable directory dedicated to this run, or set PSTACK_RUN_DIR to the absolute writable run directory. Bun dependencies are installed there, never in the plugin package.");
  }
  const toolsDirectory = canonicalPath(resolve(configured));
  const files = readBundle(scriptsDirectory);
  const hash = createHash("sha256");
  for (const file of files) {
    hash.update(file.path).update("\0").update(String(file.mode)).update("\0").update(file.data).update("\0");
  }
  const key = hash.digest("hex");
  const runtimeDirectory = join(toolsDirectory, key);
  if (dirname(scriptsDirectory) === toolsDirectory && existsSync(join(scriptsDirectory, runtimeMarker))) {
    if (scriptsDirectory !== runtimeDirectory || !isReady(runtimeDirectory, key)) {
      throw new Error(`Incomplete pstack tools runtime at ${scriptsDirectory}. Remove this run's tools copy and retry from the installed entrypoint.`);
    }
    return;
  }

  const packageDirectory = resolve(scriptsDirectory, "../../..");
  if (isWithin(scriptsDirectory, toolsDirectory) ||
      (existsSync(join(packageDirectory, ".codex-plugin", "plugin.json")) && isWithin(packageDirectory, toolsDirectory))) {
    throw new Error("PSTACK_TOOLS_DIR must be outside the installed plugin package. Choose an absolute writable directory dedicated to this run.");
  }
  const entrypoint = process.argv[1] && realpathSync(resolve(process.argv[1]));
  if (!entrypoint || !isWithin(scriptsDirectory, entrypoint)) {
    throw new Error("Invoke the bundled orch/orch.ts or watch-pr/watch-pr entrypoint directly so pstack can relocate it.");
  }

  if (!isReady(runtimeDirectory, key)) {
    let staging: string;
    try {
      mkdirSync(toolsDirectory, { recursive: true });
      staging = mkdtempSync(join(toolsDirectory, ".pstack-stage-"));
    } catch (error) {
      throw new Error(`Cannot write pstack tools to ${toolsDirectory}. Set PSTACK_TOOLS_DIR to an absolute writable directory dedicated to this run. ${error}`);
    }
    try {
      for (const file of files) {
        const destination = join(staging, file.path);
        mkdirSync(dirname(destination), { recursive: true });
        writeFileSync(destination, file.data, { mode: file.mode });
        chmodSync(destination, file.mode);
      }
      const installed = Bun.spawnSync([process.execPath, "install", "--frozen-lockfile"], {
        cwd: staging,
        env: process.env,
        stdin: "inherit",
        stdout: "pipe",
        stderr: "pipe",
      });
      if (installed.exitCode !== 0) {
        process.stderr.write(installed.stdout);
        process.stderr.write(installed.stderr);
        throw new Error(`bun install --frozen-lockfile exited with status ${installed.exitCode}`);
      }
      if (!existsSync(join(staging, "node_modules", "commander", "package.json"))) {
        throw new Error("bun install --frozen-lockfile completed without installing commander");
      }
      writeFileSync(join(staging, runtimeMarker), `${key}\n`);
      try {
        renameSync(staging, runtimeDirectory);
      } catch (error) {
        if (!isReady(runtimeDirectory, key)) throw error;
      }
    } finally {
      rmSync(staging, { recursive: true, force: true });
    }
  }

  const restarted = Bun.spawnSync([
    process.execPath,
    ...process.execArgv,
    join(runtimeDirectory, relative(scriptsDirectory, entrypoint)),
    ...process.argv.slice(2),
  ], {
    cwd: process.cwd(),
    env: process.env,
    stdin: "inherit",
    stdout: "inherit",
    stderr: "inherit",
  });
  process.exit(restarted.exitCode ?? 1);
}
