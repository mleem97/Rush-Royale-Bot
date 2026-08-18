# ML data and Unity image pipeline

## Purpose

The canonical training domain is a rendered game frame or a crop derived from one. Optional
Unity textures and sprites may help bootstrap labels and templates, but they do not replace
screenshots that include real scaling, visual effects, animation, compression, localization
and device-specific rendering.

## Project boundary

Permitted inputs are visible-screen captures, screenshots voluntarily supplied by players
and image files exported offline from packages the operator is legally allowed to inspect.
The project remains a user-interface automation and computer-vision system. It does not
modify a running game, inspect private runtime state, alter network traffic or bypass access
controls. IL2CPP runtime analysis is not part of this pipeline.

## Repository data zones

The `.gitignore` defines private inputs that must stay outside Git history:

```text
data/raw/                 Original screenshots supplied or captured locally
data/private/             Consent records and source manifests
data/screenshots/         Working screenshots
extracted-assets/         Offline Unity export staging
machine_learning/raw_input/
*.apk, *.apks, *.aab, *.xapk, *.obb
```

Only derived artifacts that are legally redistributable and necessary for reproducibility
may enter the repository. Source packages and proprietary artwork remain local and must not
be redistributed.

## Screenshot intake

Every source session should receive a manifest containing at least:

```json
{
  "schema_version": 1,
  "source_id": "random-project-id",
  "source_type": "adb-capture | player-upload | test-fixture",
  "consent": true,
  "game_version": "operator supplied",
  "android_version": "optional",
  "device_class": "phone | tablet | emulator",
  "resolution": [1440, 3088],
  "locale": "de-DE",
  "captured_at": "RFC3339 timestamp",
  "notes": "optional"
}
```

Do not store player names, account identifiers, clan names, chat content, notification text,
precise locations or raw device serials. Prefer a random project-scoped source ID rather than
a persistent device identifier.

## Offline Unity image import

1. Place the authorized package or already exported asset directory in a private staging
   location outside the repository.
2. Record source, game version, SHA-256 digest and the operator's legal basis for use.
3. Use an offline Unity image-export tool only when the files are directly accessible and no
   access control must be circumvented.
4. Export selected image objects as lossless PNG plus a manifest containing the original
   container, object name, dimensions and digest.
5. Review the export manually and reject unrelated or player-specific content.
6. Copy selected references into the private preprocessing workspace.
7. Never commit the source package, full export tree or proprietary sprites.

The future importer accepts a directory of exported PNG files and manifests. It must validate
archive paths, file counts, dimensions and total size before processing untrusted uploads.

## Label schema

Use JSON Lines or Parquet with explicit coordinates and provenance rather than encoding all
labels in filenames. A detection record should include:

```json
{
  "image_id": "sha256:...",
  "split_group": "session-uuid",
  "task": "unit-detection",
  "label": "monk",
  "bbox_xyxy": [101, 844, 221, 964],
  "confidence": 1.0,
  "annotator": "human | assisted",
  "source": "screenshot",
  "review_state": "approved"
}
```

Separate schemas cover board cells, unit identity, merge rank, battle state, controls and
OCR. Labels remain versioned so game updates do not silently redefine old classes.

## Dataset splitting

Split by player/session/device capture group, not by individual crop. Randomly distributing
near-identical frames across train and validation sets creates data leakage and misleading
accuracy. Keep a final holdout set from devices, resolutions and game versions that never
appear in training.

## Training stages

1. Run the deterministic CV baseline against frozen screenshots.
2. Audit class counts, duplicates, corrupt files and source leakage.
3. Train detection or segmentation for board cells, units and controls.
4. Train classification heads for unit, rank and state from normalized crops.
5. Combine consecutive frames with temporal smoothing.
6. Test decisions against recorded state sequences without a connected device.
7. Run shadow mode on a live device and log suggested actions without sending input.
8. Enable limited live mode only after confidence, cooldown and safety gates pass.

## Model artifact rules

Every released model requires:

- a model card and training-code revision;
- dataset schema version and non-sensitive aggregate statistics;
- deterministic preprocessing definition;
- supported resolutions, game versions and locales;
- confidence calibration and known failure modes;
- a version-neutral format such as ONNX or a documented numerical artifact;
- no automatic loading of untrusted serialized Python objects.
