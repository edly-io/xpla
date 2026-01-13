# Learning Activity Server

A Python server for developing and testing interactive learning activities with WebAssembly plugin support.

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (for running the server)
- [extism-js](https://github.com/extism/js-pdk) (optional, for building JS plugins)
- [binaryen](https://github.com/WebAssembly/binaryen) (optional, required by extism-js)

## Quick Start

```bash
# Run the server with an activity
./server.py activities/quiz-demo

# Open http://127.0.0.1:8000/ in your browser
```

## Project Structure

```
learning-activity/
  server.py              # Main server (run with ./server.py <activity_dir>)
  runtime.py             # Extism plugin wrapper
  host_functions.py      # Host functions (kv, http)
  build_plugin.py        # Compile JS to WASM
  learningactivity.js    # Web component library
  activities/
    quiz-demo/           # Example activity
      manifest.json      # Activity metadata
      index.html         # Activity page
      activity.js        # Frontend interactivity
      plugin.wasm        # Backend logic (optional)
```

## Creating an Activity

1. Create a directory under `activities/`:
   ```
   activities/my-activity/
     manifest.json
     index.html
     activity.js
   ```

2. Add a `manifest.json`:
   ```json
   {
     "name": "my-activity",
     "version": "1.0.0",
     "title": "My Activity",
     "capabilities": {}
   }
   ```

3. Create `index.html` using the web component:
   ```html
   <!DOCTYPE html>
   <html>
   <head><title>My Activity</title></head>
   <body>
     <script type="module" src="/lib/learningactivity.js"></script>
     <learning-activity src="/activity.js">
       <activity-title>My Activity</activity-title>
       <activity-content>
         <!-- Your content here -->
       </activity-content>
     </learning-activity>
   </body>
   </html>
   ```

4. Add interactivity in `activity.js`:
   ```javascript
   export function setup(activity) {
     // activity is the <learning-activity> DOM element
     const form = activity.querySelector("form");
     form.addEventListener("submit", (e) => {
       e.preventDefault();
       // Handle submission
     });
   }
   ```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/manifest` | GET | Activity manifest |
| `/api/plugin/{fn}` | POST | Call plugin function |
| `/api/kv` | GET | List all KV keys |
| `/api/kv/{key}` | GET | Get value |
| `/api/kv/{key}` | PUT | Set value |
| `/api/kv/{key}` | DELETE | Delete key |
| `/api/lms/user` | GET | Current user info |
| `/api/lms/grade` | POST | Submit grade `{"score": 85}` |
| `/api/lms/grades` | GET | All grades for activity |
| `/api/lms/grades/best` | GET | Best grade for user |

## Building Plugins

To compile JavaScript to WebAssembly, you need to install `extism-js` and `binaryen`.

### Installing extism-js

```bash
curl -O https://raw.githubusercontent.com/extism/js-pdk/main/install.sh
bash install.sh
```

Verify installation:
```bash
extism-js --version
```

### Installing binaryen

The `extism-js` compiler requires `wasm-merge` and `wasm-opt` from binaryen.

**macOS:**
```bash
brew install binaryen
```

**Fedora/RHEL:**
```bash
sudo dnf install binaryen
```

**Debian/Ubuntu:**
```bash
sudo apt install binaryen
```

**From source:** See [binaryen releases](https://github.com/WebAssembly/binaryen/releases)

### Building a plugin

```bash
./build_plugin.py activities/my-activity/plugin.js
```

This produces `plugin.wasm` in the same directory.

## Host Functions

Plugins can call these host functions:

| Function | Input | Output | Description |
|----------|-------|--------|-------------|
| `kv_get` | key (string) | value (string) | Get value from store |
| `kv_set` | `{"key": "...", "value": "..."}` | "ok" | Set key-value pair |
| `kv_delete` | key (string) | "deleted" or "not_found" | Delete key |
| `kv_keys` | any | JSON array of keys | List all keys |
| `http_request` | `{"method": "...", "url": "...", "headers": {...}, "body": "..."}` | response body | Make HTTP request |
| `lms_get_user` | any | JSON user object | Get current user |
| `lms_submit_grade` | `{"score": 85, "max_score": 100}` | JSON status | Submit grade |

## Running Tests

```bash
./test_server.py
```
