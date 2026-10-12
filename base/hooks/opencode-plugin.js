// AIKit hooks for OpenCode — managed by the AIKit installer, edits are overwritten on update.
//
// OpenCode has no hook config, only plugins. This plugin translates OpenCode tool events into the
// Claude Code / Codex hook input and calls the shared script .aikit/hooks/aikit_hook.py:
//   tool.execute.before → PreToolUse  (a blocked call throws, OpenCode shows the reason to the agent)
//   tool.execute.after  → PostToolUse (lint problems are appended to the tool output)
//   session.idle        → Stop        (failed tests are sent back to the session as a new message)
// Memory and PRODUCT.md come into the session through "instructions" in opencode.json.

import { spawn } from "node:child_process"
import path from "node:path"

const BLOCK_EXIT_CODE = 2
const PYTHON_CANDIDATES = process.platform === "win32" ? ["python3", "python", "py"] : ["python3", "python"]
const PYTHON_CHECK = "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"
const TOOL_NAMES = { bash: "Bash", write: "Write", edit: "Edit", apply_patch: "apply_patch" }

function runOnce(python, args, input, cwd) {
  return new Promise((resolve) => {
    const child = spawn(python, args, { cwd, windowsHide: true })
    let stdout = ""
    let stderr = ""
    child.stdout.on("data", (chunk) => (stdout += chunk))
    child.stderr.on("data", (chunk) => (stderr += chunk))
    child.on("error", () => resolve(null))
    child.on("close", (code) => resolve({ code, stdout, stderr }))
    child.stdin.end(JSON.stringify(input))
  })
}

// The first interpreter that is Python 3.9+: on Windows "python" may be Python 2 or the Store stub
let pythonLookup
function findPython(directory) {
  pythonLookup ??= (async () => {
    for (const python of PYTHON_CANDIDATES) {
      const result = await runOnce(python, ["-c", PYTHON_CHECK], {}, directory)
      if (result?.code === 0) return python
    }
    return null
  })()
  return pythonLookup
}

async function runHook(directory, input) {
  const python = await findPython(directory)
  const script = path.join(directory, ".aikit", "hooks", "aikit_hook.py")
  const result = python && (await runOnce(python, [script], { cwd: directory, ...input }, directory))
  return result || { code: 0, stdout: "", stderr: "" }
}

function parseOutput(stdout) {
  try {
    return JSON.parse(stdout || "{}")
  } catch {
    return {}
  }
}

function toolInput(tool, args) {
  if (tool === "bash") return { command: args.command }
  if (tool === "apply_patch") return { command: args.patchText }
  return { file_path: args.filePath, content: args.content, new_string: args.newString }
}

export const AikitHooks = async ({ client, directory }) => {
  const pendingArgs = new Map()
  const continuedSessions = new Set()

  async function hook(event, sessionID, extra) {
    return runHook(directory, { hook_event_name: event, session_id: sessionID, ...extra })
  }

  return {
    "tool.execute.before": async (input, output) => {
      const name = TOOL_NAMES[input.tool]
      if (!name) return
      pendingArgs.set(input.callID, output.args)
      const result = await hook("PreToolUse", input.sessionID, { tool_name: name, tool_input: toolInput(input.tool, output.args) })
      if (result.code === BLOCK_EXIT_CODE) {
        pendingArgs.delete(input.callID)
        throw new Error(result.stderr.trim() || "AIKit: действие заблокировано")
      }
    },

    "tool.execute.after": async (input, output) => {
      const args = pendingArgs.get(input.callID)
      pendingArgs.delete(input.callID)
      const name = TOOL_NAMES[input.tool]
      if (!name || name === "Bash" || !args) return
      const result = await hook("PostToolUse", input.sessionID, { tool_name: name, tool_input: toolInput(input.tool, args) })
      const context = parseOutput(result.stdout).hookSpecificOutput?.additionalContext
      if (context && typeof output.output === "string") output.output += `\n\n${context}`
    },

    event: async ({ event }) => {
      if (event.type !== "session.idle") return
      const sessionID = event.properties?.sessionID
      if (!sessionID) return
      const stopHookActive = continuedSessions.delete(sessionID)
      const result = await hook("Stop", sessionID, { stop_hook_active: stopHookActive })
      const decision = parseOutput(result.stdout)
      try {
        if (decision.systemMessage) {
          await client.tui.showToast({ body: { message: decision.systemMessage, variant: "info" } })
        }
        if (decision.decision === "block" && decision.reason) {
          continuedSessions.add(sessionID)
          await client.session.prompt({ path: { id: sessionID }, body: { parts: [{ type: "text", text: decision.reason }] } })
        }
      } catch {
        // An older OpenCode without these client methods: the hook stays silent instead of failing the session
      }
    },
  }
}
