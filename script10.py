import re


def parse_video_features(specifications_dict):
    def fa_to_en(text):
        if not text:
            return ""
        return str(text).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

    # Safely extract sub-dictionary category
    specs_camera = specifications_dict.get("دوربین", {})

    raw_res = specs_camera.get("رزولوشن فیلمبرداری", "")
    raw_specs_video = specs_camera.get("سایر مشخصات فیلمبرداری", "")

    # Clean strings for processing
    clean_res = fa_to_en(raw_res).lower()
    clean_specs = fa_to_en(raw_specs_video).lower()

    # ---------------------------------------------
    # 1. PROCESS VIDEO RESOLUTION OPTIONS
    # ---------------------------------------------
    video_resolution_options = ""

    def detect_highest_resolution(text_pool):
        # Resolution tier checklist (highest to lowest vertical pixel matching)
        if any(kw in text_pool for kw in ["8k", "4320", "7680"]):
            return 4320
        if any(kw in text_pool for kw in ["4k", "2160", "3840", "4096"]):
            return 2160
        if any(kw in text_pool for kw in ["1440", "2560", "2k", "1140"]):
            return 1440
        if "1152" in text_pool:
            return 1152
        if any(kw in text_pool for kw in ["1080", "1920"]):
            return 1080
        if any(kw in text_pool for kw in ["720", "1280"]):
            return 720
        return ""

    # Primary check on the resolution field
    if clean_res:
        video_resolution_options = detect_highest_resolution(clean_res)

    # Fallback check on specifications field if primary was missing or empty
    if not video_resolution_options and clean_specs:
        video_resolution_options = detect_highest_resolution(clean_specs)

    # ---------------------------------------------
    # 2. PROCESS FRAMERATE (fps1)
    # ---------------------------------------------
    fps1 = ""

    if clean_specs:
        # Step A: Define search aliases based on the highest resolution detected
        aliases = []
        if video_resolution_options == 4320:
            aliases = ["8k", "4320", "7680"]
        elif video_resolution_options == 2160:
            aliases = ["4k", "2160", "3840", "4096"]
        elif video_resolution_options == 1440:
            aliases = ["1440", "2560", "2k", "1140"]
        elif video_resolution_options == 1152:
            aliases = ["1152"]
        elif video_resolution_options == 1080:
            aliases = ["1080", "1920"]

        # Step B: Look for target resolution specific '@' format (e.g., 1080p@480FPS)
        at_format_found = False
        if aliases:
            # Matches any of the aliases followed by optional 'p' and '@', grabbing the first digits
            at_pattern = r"(?:ExactMatch)p?@\s*(\d+)".replace(
                "ExactMatch", "|".join(aliases)
            )
            at_match = re.search(at_pattern, clean_specs)
            if at_match:
                fps1 = int(at_match.group(1))
                at_format_found = True

        # Step C: Fallback parsing sequentially from the start for context keys
        if not at_format_found:
            # Look for explicit framing contexts (speed, rate, frames, or trailing @ tokens)
            fallback_match = re.search(
                r"(?:سرعت|نرخ)\s*(\d+)|(\d+)\s*فریم|@\s*(\d+)", clean_specs
            )
            if fallback_match:
                # Extract whichever regex alternative captured the digit group first
                fps_val = next(
                    (g for g in fallback_match.groups() if g is not None), None
                )
                if fps_val:
                    fps1 = int(fps_val)

    return video_resolution_options, fps1