"""One-time MPFB setup (run with: blender --background --python setup_mpfb.py).

Installs the CC0 asset packs and registers the TalkingHead rig (CC0) as the
custom rig "talkinghead", the same result as the GUI steps in TalkingHead's
blender/MPFB/MPFB.md.
"""
import json
import os
import shutil

from bl_ext.user_default.mpfb.services import AssetService, LocationService

DL = os.environ.get("AVATAR_DOWNLOADS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "dl"))
user_data = LocationService.get_user_data()
print("MPFB user data:", user_data)

for pack in ("makehuman_system_assets_cc0.zip", "suits01_cc0.zip", "visemes02.zip", "faceunits01.zip"):
    path = os.path.join(DL, "packs", pack)
    problem = AssetService.check_asset_pack_zip(path)
    print("pack", pack, "check:", problem or "ok")
    err = AssetService.fix_and_extract_asset_pack_zip(path, user_data)
    if err:
        raise SystemExit(f"Failed to install {pack}: {err}")
AssetService.rescan_pack_metadata()
print("packs installed:", AssetService.get_pack_names())

rigs_dir = LocationService.get_user_data("rigs")
os.makedirs(rigs_dir, exist_ok=True)
with open(os.path.join(DL, "talkinghead", "talkinghead.mpfbskel"), encoding="utf-8") as f:
    rig = json.load(f)
rig["identifying_bones"] = ["LeftToe_End"]
with open(os.path.join(rigs_dir, "talkinghead.json"), "w", encoding="utf-8") as f:
    json.dump(rig, f, indent=4, sort_keys=True)
shutil.copyfile(os.path.join(DL, "talkinghead", "talkinghead.mhw"), os.path.join(rigs_dir, "weights.talkinghead.json"))
AssetService.invalidate_custom_rig_cache()
print("custom rigs:", [r["name"] for r in AssetService.get_custom_rigs()])
