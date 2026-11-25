#!/usr/bin/env node
// npx @kindlingai/recipe <id> [dir]: one recipe from kindlingai/recipes in a folder of its own, ready to run.
// Needs git. Reads the repo's index.json to find the recipe, then fetches only that folder (a shallow, blobless,
// sparse clone), or with --history the recipe's own history re-rooted to the folder (git filter-branch).

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const REPO = "https://github.com/kindlingai/recipes.git";
const USAGE = `Usage: npx @kindlingai/recipe <id|path> [dir] [options]
       npx @kindlingai/recipe --list

Writes [dir] (default ./<id>) with only that recipe from kindlingai/recipes, and copies .env.example to .env.

Options:
  --list          list every recipe: id, hardware, status, path
  --engine        also check out the engine source the recipe builds (kindling.json engine.commit) into <dir>/gr8,
                  for recipes whose Dockerfile compiles it (docker compose build)
  --history       make <dir> a git repo holding the recipe's own history, the folder as its root
  --ref <ref>     a branch, tag or commit of kindlingai/recipes (default: its default branch)
  --repo <url>    another clone or fork of kindlingai/recipes (a URL or a local path)
  -h, --help      this help
  -v, --version   the CLI's version`;

class Fail extends Error {}

function parseArgs(argv) {
  const opts = { positional: [], list: false, engine: false, history: false, ref: null, repo: REPO };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const value = () => {
      const v = a.includes("=") ? a.slice(a.indexOf("=") + 1) : argv[++i];
      if (!v) throw new Fail(`${a.split("=")[0]} needs a value`);
      return v;
    };
    if (a === "-h" || a === "--help") opts.help = true;
    else if (a === "-v" || a === "--version") opts.version = true;
    else if (a === "--list") opts.list = true;
    else if (a === "--engine") opts.engine = true;
    else if (a === "--history") opts.history = true;
    else if (a === "--ref" || a.startsWith("--ref=")) opts.ref = value();
    else if (a === "--repo" || a.startsWith("--repo=")) opts.repo = value();
    else if (a.startsWith("-")) throw new Fail(`unknown option ${a}`);
    else opts.positional.push(a);
  }
  // A local path works as a repo; git needs a file:// URL for --filter and --depth to apply.
  if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(opts.repo) && !/^[^/]+@[^/]+:/.test(opts.repo) && fs.existsSync(opts.repo)) {
    opts.repo = pathToFileURL(path.resolve(opts.repo)).href;
  }
  return opts;
}

function git(args, { cwd, env, input } = {}) {
  const r = spawnSync("git", args, { cwd, input, encoding: "utf8", env: { ...process.env, ...env }, maxBuffer: 1 << 28 });
  if (r.error?.code === "ENOENT") throw new Fail("git is not installed: https://git-scm.com/downloads");
  if (r.error) throw r.error;
  if (r.status !== 0) throw new Fail(`git ${args.join(" ")} failed:\n${(r.stderr || r.stdout).trim()}`);
  return r.stdout;
}

function say(msg) {
  process.stderr.write(`${msg}\n`);
}

// A shallow, blobless clone with nothing checked out: commits and trees of one revision, files fetched on demand.
function shallowClone(repo, ref, dir) {
  git(["clone", "--quiet", "--depth", "1", "--filter=blob:none", "--no-checkout", repo, dir]);
  if (!ref) return "HEAD";
  git(["fetch", "--quiet", "--depth", "1", "--filter=blob:none", "origin", ref], { cwd: dir });
  return git(["rev-parse", "FETCH_HEAD"], { cwd: dir }).trim();
}

function readIndex(dir, rev) {
  let text;
  try {
    text = git(["show", `${rev}:index.json`], { cwd: dir });
  } catch {
    throw new Fail("this revision of the recipes repo has no index.json");
  }
  const index = JSON.parse(text);
  if (index.version !== 1 || !Array.isArray(index.recipes)) throw new Fail(`index.json version ${index.version} is not supported: update the CLI`);
  return index;
}

function find(index, want) {
  const key = want.replace(/\/+$/, "");
  const hit = index.recipes.find((r) => r.id === key || r.path === key);
  if (hit) return hit;
  const q = key.toLowerCase();
  const near = index.recipes.filter((r) => r.id.includes(q) || r.path.includes(q) || q.includes(r.model));
  throw new Fail(
    `no recipe ${want}` +
      (near.length ? `. Close:\n${near.map((r) => `  ${r.id}`).join("\n")}` : "") +
      "\nnpx @kindlingai/recipe --list shows them all",
  );
}

function list(index) {
  const rows = index.recipes
    .filter((r) => r.status !== "retired")
    .map((r) => [r.id, `${r.count}x ${r.hardware_name}`, r.status, r.path]);
  const w = [0, 1, 2].map((i) => Math.max(...rows.map((row) => row[i].length)));
  for (const row of rows) process.stdout.write(`${row.map((c, i) => (i < 3 ? c.padEnd(w[i]) : c)).join("  ")}\n`);
}

function emptyTarget(dest) {
  if (fs.existsSync(dest) && fs.readdirSync(dest).length) throw new Fail(`${dest} exists and is not empty`);
}

// The recipe folder alone, no git: sparse-checkout one folder of the shallow clone and move it out.
function fetchFolder(tmp, rev, recipe, dest) {
  git(["sparse-checkout", "set", "--no-cone", `/${recipe.path}/`], { cwd: tmp });
  git(["checkout", "--quiet", rev], { cwd: tmp });
  fs.rmSync(dest, { recursive: true, force: true });
  fs.renameSync(path.join(tmp, recipe.path), dest);
}

// A git repo of the recipe's own history with the folder as its root. git filter-branch --subdirectory-filter keeps
// the commits that touch the folder. A recipe adopted from its own repo (tools/adopt.sh) starts at a commit "Move
// <repo> into <path>/" whose parent is that repo's head, files at the root: the filtered history is grafted onto it,
// so the repo's earlier commits come along.
function fetchHistory(repo, ref, recipe, tmp, dest) {
  // bare: filter-branch refuses a clone whose (empty) index differs from HEAD, and needs no work tree
  git(["clone", "--quiet", "--bare", repo, tmp]);
  let rev = "HEAD";
  if (ref) {
    git(["fetch", "--quiet", "origin", ref], { cwd: tmp });
    rev = "FETCH_HEAD";
  }
  git(["branch", "--quiet", "--force", "recipe", rev], { cwd: tmp });
  const moved = git(["log", "--format=%H %P%x09%s", "recipe", "--", recipe.path], { cwd: tmp })
    .split("\n")
    .map((l) => l.split("\t"))
    .find(([, subject]) => subject && subject.endsWith(` into ${recipe.path}/`) && subject.startsWith("Move "));
  const env = { FILTER_BRANCH_SQUELCH_WARNING: "1" };
  git(["filter-branch", "--subdirectory-filter", recipe.path, "--", "recipe"], { cwd: tmp, env });
  if (moved) {
    const [, parent] = moved[0].split(" ");
    const roots = git(["rev-list", "--max-parents=0", "recipe"], { cwd: tmp }).trim().split("\n");
    if (roots.length === 1 && parent) {
      git(["replace", "--graft", roots[0], parent], { cwd: tmp });
      // bake the graft into the move commit and its descendants only: the old repo's commits keep their ids (and
      // their signatures, which a rewrite would drop)
      git(["filter-branch", "--force", "--", "recipe", `^${parent}`], { cwd: tmp, env });
    }
  }
  // --no-local packs only what the branch reaches, not every recipe's objects
  git(["clone", "--quiet", "--no-local", "--single-branch", "--branch", "recipe", tmp, dest]);
  git(["branch", "--quiet", "-m", "recipe", "main"], { cwd: dest });
  git(["remote", "remove", "origin"], { cwd: dest });
  // the clone brought the tags on this history, which tools/adopt.sh named <id>/<name>: give them their names back
  const prefix = `refs/tags/${recipe.id}/`;
  for (const line of git(["for-each-ref", "--format=%(objectname) %(refname)", prefix], { cwd: dest }).split("\n")) {
    const [sha, ref] = line.split(" ");
    if (!ref) continue;
    git(["update-ref", `refs/tags/${ref.slice(prefix.length)}`, sha], { cwd: dest });
    git(["update-ref", "-d", ref], { cwd: dest });
  }
  fs.appendFileSync(path.join(dest, ".git", "info", "exclude"), ".env\ngr8/\n");
}

// What tools/engine.sh does in a full clone: the engine at engine.commit, in <dir>/<engine repo name>.
function fetchEngine(dest) {
  const k = JSON.parse(fs.readFileSync(path.join(dest, "kindling.json"), "utf8"));
  const e = k.engine;
  if (!e || e.pin !== "source" || !e.commit) {
    say(`--engine: ${k.id} runs a published engine image (engine.pin ${e?.pin ?? "none"}); there is no source to fetch`);
    return;
  }
  const dir = path.join(dest, e.repo.split("/").pop());
  say(`Fetching ${e.repo} at ${e.commit.slice(0, 7)} into ${path.relative(process.cwd(), dir) || dir}`);
  git(["init", "--quiet", dir]);
  git(["fetch", "--quiet", "--depth", "1", `https://github.com/${e.repo}.git`, e.commit], { cwd: dir });
  git(["checkout", "--quiet", "--detach", "FETCH_HEAD"], { cwd: dir });
}

function prepare(dest) {
  const example = path.join(dest, ".env.example");
  const env = path.join(dest, ".env");
  if (fs.existsSync(example) && !fs.existsSync(env)) {
    fs.copyFileSync(example, env);
    return true;
  }
  return false;
}

function main(argv) {
  const opts = parseArgs(argv);
  if (opts.help) return void process.stdout.write(`${USAGE}\n`);
  if (opts.version) {
    const pkg = JSON.parse(fs.readFileSync(new URL("../package.json", import.meta.url), "utf8"));
    return void process.stdout.write(`${pkg.version}\n`);
  }
  if (!opts.list && opts.positional.length === 0) throw new Fail(USAGE);
  if (opts.positional.length > 2) throw new Fail(`too many arguments: ${opts.positional.slice(2).join(" ")}`);

  const want = opts.positional[0];
  const destArg = opts.positional[1];
  const parent = path.resolve(destArg ? path.dirname(destArg) : ".");
  fs.mkdirSync(parent, { recursive: true });
  // the scratch clone sits next to the target so the final move is a rename on one filesystem
  const tmp = fs.mkdtempSync(path.join(opts.list ? fs.realpathSync(process.env.TMPDIR || "/tmp") : parent, ".kindling-recipe-"));
  try {
    say(`Reading the recipe index from ${opts.repo}${opts.ref ? ` at ${opts.ref}` : ""}`);
    const rev = shallowClone(opts.repo, opts.ref, path.join(tmp, "index"));
    const index = readIndex(path.join(tmp, "index"), rev);
    if (opts.list) return list(index);

    const recipe = find(index, want);
    const dest = path.resolve(destArg ?? recipe.id);
    emptyTarget(dest);
    if (recipe.status === "retired") say(`${recipe.id} is retired: it is kept for reference and no longer maintained`);

    if (recipe.status === "external") {
      const src = recipe.kindling.source;
      say(`${recipe.id} lives in its own repo, ${src.repo}: cloning it`);
      const args = ["clone", "--quiet", "--recurse-submodules"];
      if (!opts.history) args.push("--depth", "1", "--shallow-submodules");
      if (src.ref) args.push("--branch", src.ref);
      git([...args, `https://github.com/${src.repo}.git`, dest]);
    } else if (opts.history) {
      say(`Fetching ${recipe.path} with its history`);
      fetchHistory(opts.repo, opts.ref, recipe, path.join(tmp, "history"), dest);
    } else {
      say(`Fetching ${recipe.path}`);
      fetchFolder(path.join(tmp, "index"), rev, recipe, dest);
    }
    if (opts.engine) fetchEngine(dest);
    const madeEnv = prepare(dest);

    const rel = path.relative(process.cwd(), dest) || ".";
    const out = [
      "",
      `${recipe.id}: ${recipe.kindling.title}${recipe.kindling.variant ? `, ${recipe.kindling.variant}` : ""}`,
      `on ${recipe.count}x ${recipe.hardware_name} (${recipe.status})`,
      "",
      `  cd ${rel}`,
    ];
    if (madeEnv) out.push("  $EDITOR .env               # .env is a copy of .env.example: set it for your boxes");
    out.push(
      `  less README.md             # the quickstart: what you need, then the commands`,
      "",
      `Browse it at ${recipe.url}`,
    );
    process.stdout.write(`${out.join("\n")}\n`);
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

try {
  main(process.argv.slice(2));
} catch (err) {
  if (!(err instanceof Fail)) throw err;
  say(err.message.startsWith("Usage:") ? err.message : `kindling-recipe: ${err.message}`);
  process.exit(1);
}
