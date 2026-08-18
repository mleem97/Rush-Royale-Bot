# Unity image ingestion for ML preparation

## Boundary

This pipeline is for offline preparation of visible image classes such as sprites, icons,
textures and rendered screenshots. It does not patch the Android application, attach to a
running process, inspect live memory, alter network traffic, bypass anti-cheat controls or
modify game behavior.

The operator must be authorized to inspect every source package. Original packages, extracted
proprietary assets and player screenshots remain outside Git history and are not redistributed
from this repository.

## IL2CPP classification

Do not assume the application uses IL2CPP. Record evidence from an authorized local package,
for example the presence of architecture-specific `libil2cpp.so` and Unity metadata, as a
package characteristic. This classification is not needed merely to export serialized Unity
images: image assets normally reside in Unity data files, asset bundles or Android expansion
files independently of the compiled gameplay code.

RushBot must not add an IL2CPP runtime hook or code-injection component. Any future importer is
an offline file reader with bounded input size, path traversal protection and no execution of
code found in the package.

## Import stages

1. **Private intake** — store the authorized APK/APKS/XAPK/OBB or exported directory outside
   the repository and calculate SHA-256 hashes.
2. **Package inventory** — record package/version identifiers, Unity version when available,
   architectures and container file names without copying account data.
3. **Image export** — export only selected texture/sprite objects to lossless PNG plus a JSONL
   manifest containing source hash, container path, object name, dimensions and export hash.
4. **Manual review** — remove unrelated artwork, player-specific information, chat, names,
   notifications and duplicate frames.
5. **Private reference store** — keep selected images under ignored local paths such as
   `extracted-assets/` or `data/private/`.
6. **Derived training records** — create labels and crops with stable class identifiers; keep
   provenance linked by hashes rather than filenames containing personal data.
7. **Domain validation** — compare asset-derived references against real rendered screenshots.
   Scaling, animation, shaders, localization, compression and effects create a domain gap.

## Preferred training hierarchy

Use data in this order:

1. consented or locally captured rendered screenshots;
2. labeled crops from those screenshots;
3. synthetic compositions built from authorized references;
4. exported sprites/textures as auxiliary templates or pretraining data.

A model trained only on pristine sprites is not considered validated for live gameplay.

## Dataset controls

- group train/validation/test splits by capture session, player source and device;
- keep a protected holdout from unseen resolutions and game versions;
- use perceptual hashes to prevent near-duplicate leakage;
- version labels separately from the model;
- never load untrusted Python pickle/joblib artifacts;
- release models with a model card, preprocessing contract and supported-version matrix;
- add an explicit consent and deletion record for player-supplied screenshots.
