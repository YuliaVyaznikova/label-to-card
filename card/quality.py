import cv2
import numpy as np

from .normalize import norm


def read_image(path):
    data = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def fit(image, max_pixels):
    height, width = image.shape[:2]
    scale = min(1.0, (max_pixels / (height * width)) ** 0.5)
    if scale < 1.0:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return image, scale


def photo_quality(path, settings):
    image = read_image(path)
    if image is None:
        return {"readable": False, "size": False, "sharp": False, "light": False}
    height, width = image.shape[:2]
    short = min(height, width)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    scale = 800 / short if short > 800 else 1.0
    small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else gray
    sharpness = float(cv2.Laplacian(small, cv2.CV_64F).var())
    brightness = float(gray.mean())
    return {
        "readable": True,
        "width": width, "height": height,
        "sharpness": round(sharpness, 1), "brightness": round(brightness, 1),
        "size": width * height >= settings["min_pixels"],
        "sharp": sharpness >= settings["sharpness"],
        "light": settings["dark"] <= brightness <= settings["bright"],
    }


def photo_checks(qualities, lines, fields):
    has_composition = fields.get("composition", {}).get("source") == "photo" or any("состав" in norm(line["text"]) for line in lines.values())
    checks = [
        {"name": "two_photos", "passed": len(qualities) >= 2, "message": "Добавьте ещё одно фото, нужны и лицевая сторона, и этикетка"},
        {"name": "composition_photo", "field": "composition", "passed": has_composition, "message": "Сфотографируйте часть этикетки, где написан состав"},
    ]
    for number, quality in enumerate(qualities, 1):
        checks.append({"name": f"photo_{number}_size", "passed": quality["size"],
                       "message": f"Фото {number} слишком маленькое, снимите ближе или в большем разрешении"})
        checks.append({"name": f"photo_{number}_sharp", "passed": quality["sharp"],
                       "message": f"Фото {number} размыто, снимите ещё раз, держа телефон неподвижно"})
        checks.append({"name": f"photo_{number}_light", "passed": quality["light"],
                       "message": f"Фото {number} слишком тёмное или пересвеченное"})
    return checks