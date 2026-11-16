def tray_picture():
    """The toolbox's icon next to the clock: a round teal icon with a T, drawn here (the toolbox has no picture
    file for it). Used by the starter's tray and the toolbox's own (ToolboxTray)."""
    from PIL import Image, ImageDraw
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((2, 2, 62, 62), fill=(38, 166, 154, 255))
    draw.rectangle((16, 16, 48, 24), fill="white")
    draw.rectangle((28, 16, 36, 50), fill="white")
    return image
