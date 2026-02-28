// Activity script for Python coding exercises
// Supports author view (configure instructions, starter code, tests)
// and student view (write code, run with Pyodide, check against tests)

import { EditorView, basicSetup } from "codemirror";
import { python } from "@codemirror/lang-python";

const TIMEOUT_MS = 5000;

function makeWorkerSrc(pyodideUrl) {
  return `
const TEST_RUNNER = \`
import json as __json
__results = []
__test_functions = [
    (__name, __func) for (__name, __func) in globals().items()
    if __name.startswith("test_") and callable(__func)
]
for __name, __func in __test_functions:
    __doc = (__func.__doc__ or __name).strip()
    try:
        __func()
        __results.append({"name": __name, "description": __doc, "passed": True})
    except AssertionError as __e:
        __results.append({"name": __name, "description": __doc, "passed": False, "error": str(__e) or "Assertion failed"})
    except Exception as __e:
        __results.append({"name": __name, "description": __doc, "passed": False, "error": f"{type(__e).__name__}: {__e}"})
print(__json.dumps(__results))
\`;

let pyodide = null;

async function ensurePyodide() {
  if (!pyodide) {
    // Pyodide WASM runtime (~20MB) must be fetched at runtime; it cannot be bundled.
    const mod = await import("${pyodideUrl}");
    pyodide = await mod.loadPyodide();
  }
  return pyodide;
}

self.onmessage = async (e) => {
  const { id, type, code, testCode } = e.data;
  try {
    const py = await ensurePyodide();
    self.postMessage({ id, kind: "loaded" });

    let stdout = "";
    let stderr = "";
    py.setStdout({ batched: (s) => (stdout += s + "\\n") });
    py.setStderr({ batched: (s) => (stderr += s + "\\n") });

    const script = type === "check" ? code + "\\n" + testCode + "\\n" + TEST_RUNNER : code;
    try {
      py.runPython(script);
    } catch (err) {
      stderr += err.message + "\\n";
    }
    self.postMessage({ id, kind: "done", stdout, stderr });
  } catch (err) {
    self.postMessage({ id, kind: "error", error: err.message });
  }
};
`;
}

function createEditor(parent, doc, root) {
  return new EditorView({
    doc,
    extensions: [basicSetup, python()],
    parent,
    root,
  });
}

export function setup(activity) {
  const element = activity.element;
  const permission = activity.permission;
  const root = element.getRootNode();

  const pyodideUrl = activity.getAssetUrl("static/pyodide/pyodide.mjs");
  const workerBlob = new Blob([makeWorkerSrc(pyodideUrl)], { type: "application/javascript" });
  const workerUrl = URL.createObjectURL(workerBlob);

  let worker = null;
  let messageId = 0;

  function getWorker() {
    if (!worker) {
      worker = new Worker(workerUrl, { type: "module" });
    }
    return worker;
  }

  function killWorker() {
    if (worker) {
      worker.terminate();
      worker = null;
    }
  }

  function runInWorker(msg, onLoaded) {
    return new Promise((resolve, reject) => {
      const id = ++messageId;
      const w = getWorker();
      let settled = false;

      const timer = setTimeout(() => {
        if (!settled) {
          settled = true;
          killWorker();
          reject(new Error("Execution timed out (5s limit)"));
        }
      }, TIMEOUT_MS);

      function onMessage(e) {
        if (e.data.id !== id) return;
        if (e.data.kind === "loaded") {
          if (onLoaded) onLoaded();
          return;
        }
        settled = true;
        clearTimeout(timer);
        w.removeEventListener("message", onMessage);
        if (e.data.kind === "error") {
          reject(new Error(e.data.error));
        } else {
          resolve(e.data);
        }
      }

      w.addEventListener("message", onMessage);
      w.postMessage({ id, ...msg });
    });
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  activity.onEvent = (name, value) => {
    if (name === "fields.change.user_code") {
      activity.state.user_code = value;
    } else if (name === "fields.change.instructions") {
      activity.state.instructions = value;
    } else if (name === "fields.change.test_code") {
      activity.state.test_code = value;
    } else if (name === "fields.change.starter_code") {
      activity.state.starter_code = value;
    }
  };

  function render() {
    if (permission === "edit") {
      renderEditView();
    } else {
      renderPlayView();
    }
  }

  function renderEditView() {
    const instructions = activity.state.instructions || "";
    const starterCode = activity.state.starter_code || "";
    const testCode = activity.state.test_code || "";

    element.innerHTML = `
      <style>
        .py-container { font-family: sans-serif; max-width: 800px; }
        .py-container label { display: block; font-weight: bold; margin-top: 1rem; }
        .py-container textarea { width: 100%; min-height: 80px; font-family: sans-serif; padding: 0.5rem; box-sizing: border-box; }
        .cm-wrap { border: 1px solid #ccc; margin-top: 0.25rem; }
        .cm-wrap .cm-editor { max-height: 300px; overflow: auto; }
        .save-btn { margin-top: 1rem; padding: 0.5rem 1rem; cursor: pointer; }
        .feedback { margin-top: 0.5rem; padding: 0.5rem; border-radius: 4px; }
        .feedback.success { background: #d4edda; color: #155724; }
        .feedback.error { background: #f8d7da; color: #721c24; }
      </style>
      <div class="py-container">
        <h3>Configure Python Exercise</h3>

        <label for="instructions-input">Instructions</label>
        <textarea id="instructions-input">${escapeHtml(instructions)}</textarea>

        <label>Starter Code</label>
        <div class="cm-wrap" id="starter-editor"></div>

        <label>Test Code</label>
        <div class="cm-wrap" id="test-editor"></div>

        <button type="button" class="save-btn" id="save-btn">Save</button>
        <div id="save-feedback"></div>
      </div>
    `;

    const starterEditor = createEditor(
      element.querySelector("#starter-editor"),
      starterCode,
      root,
    );
    const testEditor = createEditor(
      element.querySelector("#test-editor"),
      testCode,
      root,
    );

    element.querySelector("#save-btn").addEventListener("click", async () => {
      const feedbackEl = element.querySelector("#save-feedback");
      try {
        const value = {
          instructions: element.querySelector("#instructions-input").value,
          starter_code: starterEditor.state.doc.toString(),
          test_code: testEditor.state.doc.toString(),
        };
        await activity.sendAction("config.save", value);
        feedbackEl.innerHTML = '<div class="feedback success">Saved!</div>';
      } catch (err) {
        feedbackEl.innerHTML =
          '<div class="feedback error">Error: ' +
          escapeHtml(err.message) +
          "</div>";
      }
    });
  }

  function renderPlayView() {
    const instructions = activity.state.instructions || "";
    const initialCode = activity.state.user_code || activity.state.starter_code || "";

    element.innerHTML = `
      <style>
        .py-container { font-family: sans-serif; max-width: 800px; }
        .py-instructions { margin-bottom: 1rem; }
        .cm-wrap { border: 1px solid #ccc; }
        .cm-wrap .cm-editor { max-height: 400px; overflow: auto; }
        .py-buttons { display: flex; gap: 0.5rem; margin-top: 0.5rem; }
        .py-buttons button { padding: 0.5rem 1rem; cursor: pointer; }
        .py-output { margin-top: 1rem; }
        .py-output pre { background: #1e1e1e; color: #d4d4d4; padding: 0.75rem; border-radius: 4px; overflow-x: auto; white-space: pre-wrap; min-height: 1.5em; }
        .py-results { margin-top: 1rem; }
        .py-result-item { display: flex; align-items: baseline; gap: 0.5rem; padding: 0.25rem 0; }
        .py-pass { color: #155724; }
        .py-fail { color: #721c24; }
        .py-error-detail { font-size: 0.85em; color: #666; margin-left: 1.5rem; }
        .no-content { color: #666; font-style: italic; }
        .py-status { margin-top: 1rem; color: #666; font-style: italic; display: none; }
        .py-output, .py-results { display: none; }
        .state-loading .py-status { display: block; }
        .state-running .py-output { display: block; }
        .state-checking .py-results { display: block; }
      </style>
      <div class="py-container">
        <div class="py-instructions">${instructions ? escapeHtml(instructions) : '<span class="no-content">No instructions configured yet.</span>'}</div>

        <div class="cm-wrap" id="code-editor"></div>

        <div class="py-buttons">
          <button type="button" id="run-btn">Run</button>
          <button type="button" id="check-btn">Check</button>
        </div>

        <div class="py-status">Loading Python runtime...</div>

        <div class="py-output" id="output-panel">
          <strong>Output</strong>
          <pre id="output-content"></pre>
        </div>

        <div class="py-results" id="results-panel">
          <strong>Test Results</strong>
          <div id="results-content"></div>
        </div>
      </div>
    `;

    const codeEditor = createEditor(
      element.querySelector("#code-editor"),
      initialCode,
      root,
    );

    const container = element.querySelector(".py-container");
    const outputContent = element.querySelector("#output-content");
    const resultsContent = element.querySelector("#results-content");

    element.querySelector("#run-btn").addEventListener("click", async () => {
      container.className = "py-container state-loading";

      const code = codeEditor.state.doc.toString();
      activity.sendAction("code.run", { code });

      try {
        const { stdout, stderr } = await runInWorker(
          { type: "run", code },
          () => { container.className = "py-container state-running"; },
        );
        outputContent.textContent = (stdout + stderr).trimEnd() || "(no output)";
      } catch (err) {
        container.className = "py-container state-running";
        outputContent.textContent = err.message;
      }
    });

    element.querySelector("#check-btn").addEventListener("click", async () => {
      container.className = "py-container state-loading";

      const studentCode = codeEditor.state.doc.toString();
      activity.sendAction("code.check", { code: studentCode });

      const testCode = activity.state.test_code || "";
      if (!testCode) {
        container.className = "py-container state-checking";
        resultsContent.innerHTML = '<div class="no-content">No tests configured for this exercise.</div>';
        return;
      }

      let stdout, stderr;
      try {
        ({ stdout, stderr } = await runInWorker(
          { type: "check", code: studentCode, testCode },
          () => { container.className = "py-container state-checking"; },
        ));
      } catch (err) {
        container.className = "py-container state-checking";
        resultsContent.innerHTML = '<div class="py-fail">' + escapeHtml(err.message) + "</div>";
        return;
      }

      // Parse JSON results from stdout (last non-empty line)
      const lines = stdout.trimEnd().split("\n");
      const lastLine = lines[lines.length - 1] || "";
      let results;
      try {
        results = JSON.parse(lastLine);
      } catch {
        resultsContent.innerHTML =
          "<pre>" + escapeHtml(stdout + stderr) + "</pre>";
        return;
      }

      resultsContent.innerHTML = results
        .map((r) => {
          const icon = r.passed ? "&#10003;" : "&#10007;";
          const cls = r.passed ? "py-pass" : "py-fail";
          let html = `<div class="py-result-item"><span class="${cls}">${icon}</span> <span>${escapeHtml(r.description)}</span></div>`;
          if (!r.passed && r.error) {
            html += `<div class="py-error-detail">${escapeHtml(r.error)}</div>`;
          }
          return html;
        })
        .join("");
    });
  }

  render();
}
