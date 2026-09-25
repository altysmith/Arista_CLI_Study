# L1 study-blade sandbox

This is an isolated working copy for rebuilding the L1 study experience. It starts at the deployed baseline commit `4d0a0b5` on branch `sandbox/l1-study-blade`.

## Start it

On Windows, double-click `run_l1_sandbox.bat` in this folder. It opens the browser app at:

`http://127.0.0.1:8767`

Keep the terminal window open while working. Press `Ctrl+C` in that window when finished.

The sandbox saves its own progress only in `user_data/l1-sandbox-progress.sqlite3`. That path is ignored by Git and is separate from the maintained checkout, the live Pi database, and the deployed app.

## Work agreement

- Make L1 study-blade experiments only in this folder and branch.
- Do not deploy or push the sandbox while its structure is still being designed.
- Keep the existing terminal and individual labs working; evolve the study UI around them rather than replacing working simulator behavior.
- When a section design is ready, run the test suite before asking to merge or deploy it:

```powershell
$env:PYTHONPATH = "src"
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest discover -s tests -v
Remove-Item Env:PYTHONPATH
node --check src\arista_sim\web_assets\app.js
```

## First design target

Use **Network Engineering Fundamentals** as the template section. Decide its page flow before building the other four domains: relevance, session priorities, concepts and terms, recall, guided practice, scenario work, and section review. Once that structure feels right, it can be repeated for EOS, Layer 2, Layer 3, and Advanced Concepts.
