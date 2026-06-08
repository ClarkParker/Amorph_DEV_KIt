# Templates (roadmap)

This folder will hold a minimal **copy-to-start** plugin: three files you duplicate
and rename to begin a new plugin.

```
Plugin/
  Plugin.cmajorpatch    Manifest (generic placeholders).
  PluginDSP.cmajor      Minimal stereo effect: drive / tone / mix / output / bypass + meter.
  PluginUI.js           Single-file UI: a few knobs, bypass, meter, zoom scaling, cleanup.
```

Until it lands, build from the verified patterns in [`../docs`](../docs):

- DSP skeleton, parameters, building blocks → [`../docs/02_DSP_CMAJOR.md`](../docs/02_DSP_CMAJOR.md)
- UI skeleton, bridge, lifecycle → [`../docs/03_UI_WEBCOMPONENT.md`](../docs/03_UI_WEBCOMPONENT.md)
- Manifest shape → [`../docs/01_ARCHITECTURE.md`](../docs/01_ARCHITECTURE.md)
- Scaling block → [`../docs/07_SCALING.md`](../docs/07_SCALING.md)

The template's design size must match `view.width`/`height` in the manifest and the
fixed `.chassis` size in the UI.

Want to help? See [`../CONTRIBUTING.md`](../CONTRIBUTING.md).
