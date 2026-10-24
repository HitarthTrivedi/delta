# Interviewer avatar ("Aria")

`frontend/public/avatars/interviewer.glb` is built from these scripts. The model is a
woman in her early 30s with long dark hair, in a charcoal pinstripe skirt suit with a
white shirt. It has the TalkingHead rig, 15 Oculus visemes and 52 ARKit face units
(teeth, tongue, brows and lashes included), so lip-sync and expressions work.

## Licences (all CC0, commercial use, no attribution required)
| Part | Source |
|---|---|
| Base mesh, skin `young_asian_female`, hair `long01`, eyes, brows, lashes, teeth, tongue | MakeHuman system assets (MPFB) |
| Suit `toigo_female_suit` | "Suits 01" asset pack by Margaret Toigo |
| Rig + weights | TalkingHead `blender/MPFB/talkinghead.mpfbskel` / `.mhw` (v1.8.0) |
| Visemes / face units | "Visemes 02" and "Faceunits 01" asset packs by Mika Suominen |

Tools: Blender 4.5 LTS and MPFB 2.0.18 (both GPL; used as tools only, nothing of them ships in the GLB).

## Rebuild
1. Download into `dl/` (or point `AVATAR_DOWNLOADS` at the folder):
   - Blender 4.5 LTS (portable zip; create an empty `portable/` folder next to `blender.exe` so its settings stay local).
   - MPFB 2.0.18 from extensions.blender.org, then `blender --command extension install-file --repo user_default --enable <mpfb zip>`.
   - Asset packs into `dl/packs/` from `https://files.makehumancommunity.org/` (the `files2` mirror is very slow): `asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip`, `asset_packs/suits01/suits01_cc0.zip`, `functional/visemes02.zip`, `functional/faceunits01.zip`.
   - `talkinghead.mpfbskel` and `talkinghead.mhw` from the TalkingHead repo (tag v1.8.0) into `dl/talkinghead/`.
2. `blender --background --python setup_mpfb.py` installs the packs and registers the rig (once).
3. `blender --background --python build_avatar.py -- aria.glb [skin] [hair] [suit]` builds the GLB and renders `aria_face.png` / `aria_upper.png` previews.
4. `node postprocess.mjs aria.glb interviewer.glb` (needs `@gltf-transform/core`, `@gltf-transform/extensions`, `@gltf-transform/functions`, `meshoptimizer`, `sharp`). It sets alpha modes (eyes, hair, brows and lashes are cut out; everything else is opaque), applies the warm skin and dark hair tint, converts textures to WebP and applies Meshopt compression (about 2.3 MB).
5. Copy the result to `frontend/public/avatars/interviewer.glb` and check it in the interview page.

Hair options that keep both eyes visible: `long01` (used), `ponytail01`. `bob01`, `bob02`, `short03` and `braid01` put hair over one eye.
