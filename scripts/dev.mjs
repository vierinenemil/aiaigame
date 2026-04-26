import { execSync, spawn } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import path from "node:path";
import process from "node:process";

const rootDir = process.cwd();
const backendDir = path.join(rootDir, "backend");
const frontendDir = path.join(rootDir, "frontend");
const venvDir = path.join(backendDir, ".venv");
const requirementsFile = path.join(backendDir, "requirements.txt");
const requirementsStamp = path.join(venvDir, ".requirements-installed");
const envFile = path.join(rootDir, ".env");

function parseEnvFile(filePath) {
  if (!existsSync(filePath)) return {};
  const parsed = {};
  const lines = readFileSync(filePath, "utf8").split(/\r?\n/);
  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq <= 0) continue;
    const key = line.slice(0, eq).trim();
    const value = line.slice(eq + 1).trim().replace(/^["']|["']$/g, "");
    parsed[key] = value;
  }
  return parsed;
}

const runtimeEnv = {
  ...parseEnvFile(envFile),
  ...process.env,
};

function run(cmd, cwd = rootDir) {
  execSync(cmd, {
    cwd,
    stdio: "inherit",
    shell: "/bin/zsh",
  });
}

function output(cmd, cwd = rootDir) {
  try {
    return execSync(cmd, {
      cwd,
      stdio: ["ignore", "pipe", "ignore"],
      encoding: "utf8",
      shell: "/bin/zsh",
    }).trim();
  } catch {
    return "";
  }
}

function killPort(port) {
  const pids = output(`lsof -ti tcp:${port} -sTCP:LISTEN`);
  if (!pids) return;
  for (const pid of pids.split("\n").filter(Boolean)) {
    try {
      process.kill(Number(pid), "SIGTERM");
    } catch {
      // Ignore stale pids.
    }
  }
}

function ensureBackendReady() {
  if (!existsSync(venvDir)) {
    run("python3 -m venv .venv", backendDir);
  }

  const reqMtime = statSync(requirementsFile).mtimeMs;
  const stampMtime = existsSync(requirementsStamp) ? statSync(requirementsStamp).mtimeMs : 0;
  if (stampMtime < reqMtime) {
    run("source .venv/bin/activate && pip install -r requirements.txt", backendDir);
    writeFileSync(requirementsStamp, String(Date.now()));
  }
}

function ensureFrontendReady() {
  const nodeModulesDir = path.join(frontendDir, "node_modules");
  if (!existsSync(nodeModulesDir)) {
    run("npm install", frontendDir);
  }
}

function startProcess(name, cmd, cwd) {
  const child = spawn("/bin/zsh", ["-lc", cmd], {
    cwd,
    stdio: "inherit",
    env: runtimeEnv,
  });

  child.on("exit", (code, signal) => {
    if (shuttingDown) return;
    shuttingDown = true;
    shutdownChildren();
    const reason = signal ? `signal ${signal}` : `code ${code ?? 0}`;
    console.error(`${name} exited with ${reason}`);
    process.exit(code ?? 1);
  });

  children.push(child);
  return child;
}

const children = [];
let shuttingDown = false;

function shutdownChildren() {
  for (const child of children) {
    if (!child.killed) {
      child.kill("SIGTERM");
    }
  }
}

function main() {
  if (!existsSync(path.join(rootDir, "scripts"))) {
    mkdirSync(path.join(rootDir, "scripts"), { recursive: true });
  }

  killPort(3000);
  killPort(8000);
  ensureBackendReady();
  ensureFrontendReady();

  startProcess(
    "backend",
    "source .venv/bin/activate && uvicorn main:app --host 127.0.0.1 --port 8000",
    backendDir,
  );
  startProcess("frontend", "npm run dev", frontendDir);

  process.on("SIGINT", () => {
    shuttingDown = true;
    shutdownChildren();
    process.exit(0);
  });

  process.on("SIGTERM", () => {
    shuttingDown = true;
    shutdownChildren();
    process.exit(0);
  });
}

main();
