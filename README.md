# Learning Activity Server

A Python server for developing and testing interactive learning activities with WebAssembly plugin support.

# Requirements

- Python 3.11+
- [extism-js](https://github.com/extism/js-pdk): for building JS plugins to WebAssembly (remember to also install [binaryen](https://github.com/WebAssembly/binaryen))

Install Python requirements with:

    pip install -r requirements/base.in

# Usage

## Running the server with an activity

```bash
python -m server activities/quiz-demo
# Open http://127.0.0.1:8000/ in your browser
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

## Building Plugins

```bash
./tools/build_plugin.py activities/my-activity/plugin.js
```

This produces `plugin.wasm` in the same directory.

# Project structure

## API endpoints

The server exposes several `/api/*` endpoints which are defined in [./server/app.py](./server/app.py).

## Host Functions

Plugins can call host functions which are defined in [./server/host_functions.py](./server/host_functions.py).

# Development

Install requirements with:

    pip install -r requirements/dev.in

## Running Tests

```bash
python ./tests/test_server.py
```
