import re


def parse_body_materials(specifications_dict):
    def fa_to_en(text):
        if not text:
            return ""
        return str(text).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

    # Extract target field safely
    general_specs = specifications_dict.get("مشخصات کلی", {})
    raw_body = general_specs.get("توضیحات بدنه", "")

    if not raw_body:
        return "Unknown", "Unknown"

    # Normalize digits and strip problematic quotes/commas
    text = fa_to_en(raw_body).lower()
    text = re.sub(r"[\"\',]", " ", text)

    back_materials = set()
    frame_materials = set()

    # Split the description by natural segment break points
    segments = re.split(r"[/\n\-\|]", text)

    for seg in segments:
        seg = seg.strip()
        is_frame_seg = any(
            k in seg for k in ["فریم", "قاب دور", "قاب کناری", "شاسی"]
        )
        is_back_seg = any(
            k in seg for k in ["پشت", "پشتی", "پنل پشت", "قسمت پشتی"]
        )

        # Skip explicit front glass declarations unless they share back/frame contexts
        if "جلو" in seg and not is_back_seg and not is_frame_seg:
            continue

        # 1. Evaluate Explicit Frame Segments
        if is_frame_seg:
            if "آلومینیوم" in seg or "aluminum" in seg:
                frame_materials.add("Aluminum")
            if "تیتانیوم" in seg or "titanium" in seg:
                frame_materials.add("Titanium")
            if any(k in seg for k in ["فولاد", "استیل", "steel"]):
                frame_materials.add("Stainless Steel")
            if "منیزیم" in seg or "magnesium" in seg:
                frame_materials.add("Magnesium")
            if "پلاستیک" in seg or "plastic" in seg:
                frame_materials.add("Plastic")

        # 2. Evaluate Explicit Back Panel Segments
        if is_back_seg:
            if "شیشه" in seg or "glass" in seg:
                back_materials.add("Glass")
            if "پلاستیک" in seg or "plastic" in seg:
                back_materials.add("Plastic")
            if any(
                k in seg
                for k in [
                    "چرم",
                    "سیلیکون پلیمر",
                    "سیلیکون پلمیر",
                    "leather",
                    "faux",
                ]
            ):
                back_materials.add("Eco-Leather")
            if "سرامیک" in seg or "ceramic" in seg:
                back_materials.add("Ceramic")
            if "فلز" in seg or "metal" in seg:
                back_materials.add("Metal")
            if any(k in seg for k in ["الیاف", "aramid", "fiber"]):
                back_materials.add("Aramid Fiber")
            if "چوب" in seg or "wood" in seg:
                back_materials.add("Wood")

    # ---------------------------------------------
    # GLOBAL FALLBACKS (If contextual sets are empty)
    # ---------------------------------------------
    if not frame_materials:
        if "تیتانیوم" in text or "titanium" in text:
            frame_materials.add("Titanium")
        if "منیزیم" in text or "magnesium" in text:
            frame_materials.add("Magnesium")
        if any(k in text for k in ["فولاد ضدزنگ", "فولاد", "steel"]):
            frame_materials.add("Stainless Steel")
        if "آلومینیوم" in text or "aluminum" in text:
            frame_materials.add("Aluminum")
        if any(
            k in text for k in ["فریم پلاستیکی", "بدنه پلاستیکی", "فریم و قاب"]
        ):
            frame_materials.add("Plastic")

    if not back_materials:
        if any(
            k in text for k in ["پشت شیشه", "پشت از جنس شیشه", "پشت شیشه‌ای"]
        ):
            back_materials.add("Glass")
        if any(
            k in text
            for k in [
                "قاب پشتی از جنس پلاستیک",
                "قاب پشت از جنس پلاستیک",
                "پشت و فریم از نوع پلاستیک",
            ]
        ):
            back_materials.add("Plastic")
        if any(
            k in text
            for k in [
                "چرم مصنوعی",
                "چرم گیاهی",
                "سیلیکون پلیمر",
                "eco leather",
                "faux",
            ]
        ):
            back_materials.add("Eco-Leather")
        if "سرامیک" in text:
            back_materials.add("Ceramic")
        if "الیاف شیشه‌" in text or "glass fiber" in text:
            back_materials.add("Aramid Fiber")

        # Structural phrase fallbacks (e.g., "شیشه و پلاستیک" with no key sections)
        if not back_materials:
            if "فلز و شیشه" in text:
                back_materials.add("Glass")
            elif "شیشه و پلاستیک" in text:
                back_materials.add("Plastic")
                frame_materials.add("Plastic")

    # Handle unibody/integrated structures
    if "یکپارچه از جنس آلومینیوم" in text:
        back_materials.add("Metal")
        frame_materials.add("Aluminum")

    # ---------------------------------------------
    # WHITELIST RESOLUTION & MAPPING
    # ---------------------------------------------
    # Resolve Chassis / Frame Material
    if "Aluminum" in frame_materials and "Titanium" in frame_materials:
        chassis_frame_material = "Aluminum, Titanium"
    elif "Aluminum" in frame_materials:
        chassis_frame_material = "Aluminum"
    elif "Titanium" in frame_materials:
        chassis_frame_material = "Titanium"
    elif "Stainless Steel" in frame_materials:
        chassis_frame_material = "Stainless Steel"
    elif "Magnesium" in frame_materials:
        chassis_frame_material = "Magnesium"
    elif "Plastic" in frame_materials:
        chassis_frame_material = "Plastic"
    else:
        chassis_frame_material = "Unknown"

    # Resolve Back Panel Material Combinations
    back_panel_material = "Unknown"
    if back_materials:
        if "Eco-Leather" in back_materials and "Glass" in back_materials:
            back_panel_material = "Eco-Leather, Glass"
        elif "Eco-Leather" in back_materials and "Plastic" in back_materials:
            back_panel_material = "Eco-Leather, Plastic"
        elif "Eco-Leather" in back_materials and "Metal" in back_materials:
            back_panel_material = "Eco-Leather, Metal"
        elif "Eco-Leather" in back_materials and "Wood" in back_materials:
            back_panel_material = "Eco-Leather, Wood"
        elif "Eco-Leather" in back_materials and "Ceramic" in back_materials:
            back_panel_material = "Eco-Leather, Ceramic"
        elif (
            "Glass" in back_materials
            and "Ceramic" in back_materials
            and "Metal" in back_materials
        ):
            back_panel_material = "Glass, Ceramic, Metal"
        elif "Glass" in back_materials and "Ceramic" in back_materials:
            back_panel_material = "Glass, Ceramic"
        elif "Glass" in back_materials and "Metal" in back_materials:
            back_panel_material = "Glass, Metal"
        elif "Glass" in back_materials and "Aramid Fiber" in back_materials:
            back_panel_material = "Glass, Aramid Fiber"
        elif "Plastic" in back_materials and "Ceramic" in back_materials:
            back_panel_material = "Plastic, Ceramic"
        elif "Glass" in back_materials:
            back_panel_material = "Glass"
        elif "Plastic" in back_materials:
            back_panel_material = "Plastic"
        elif "Eco-Leather" in back_materials:
            back_panel_material = "Eco-Leather"
        elif "Metal" in back_materials:
            back_panel_material = "Metal"
        elif "Ceramic" in back_materials:
            back_panel_material = "Ceramic"
        elif "Aramid Fiber" in back_materials:
            back_panel_material = "Aramid Fiber"

    return back_panel_material, chassis_frame_material