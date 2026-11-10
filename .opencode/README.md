# .opencode

## Superpowers plugin (not committed)

`opencode.json` in the repo root loads the plugin from:

```
./.opencode/superpowers
```

That directory is a **local vendored copy** of
[obra/superpowers](https://github.com/obra/superpowers) (v7.0.2) and is listed
in `.gitignore`, so it is **not part of this repository**. A fresh clone will
log `failed to load plugin` for it until you restore the copy.

### Restore on a new machine

Any one of these works:

```powershell
# Option A — clone the upstream repo straight into place
git clone https://github.com/obra/superpowers .opencode/superpowers

# Option B — let OpenCode install it from git instead of vendoring
# (then change opencode.json to: "plugins": ["superpowers@git+https://github.com/obra/superpowers.git"] )
```

Option A keeps the exact directory layout the plugin expects (`skills/`,
`.opencode/plugins/superpowers.js`, `index.js`). Do not copy only `skills/` —
the entrypoint and skill paths are relative to the package root.

### Remove entirely

Delete the `.opencode/superpowers` folder and the `plugins` entry in
`opencode.json`. Nothing else in this repo depends on it.
