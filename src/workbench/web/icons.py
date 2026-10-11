"""SVG paths for the icon() macro: 24×24 viewBox, stroked with currentColor."""

ICON_PATHS: dict[str, str] = {
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "x": '<path d="M6 6l12 12M18 6L6 18"/>',
    "file": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
    "upload": '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M5 20h14"/>',
    "download": '<path d="M12 4v12M7 11l5 5 5-5"/><path d="M5 20h14"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    "warn": '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17h.01"/>',
    "plug": '<path d="M9 3v5M15 3v5M7 8h10v3a5 5 0 0 1-10 0zM12 16v5"/>',
    "play": '<path d="M8 5v14l11-7z"/>',
    "refresh": '<path d="M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5"/>',
    "chevron-down": '<path d="M6 9l6 6 6-6"/>',
    "chevron-right": '<path d="M9 6l6 6-6 6"/>',
    "code": '<path d="M9 8l-4 4 4 4M15 8l4 4-4 4"/>',
    "copy": '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
    "spinner": '<path class="spin" style="transform-origin:12px 12px" d="M21 12a9 9 0 1 1-9-9"/>',
    "circle-dashed": '<circle cx="12" cy="12" r="9" stroke-dasharray="3 3"/>',
    "video": '<rect x="3" y="6" width="13" height="12" rx="2"/><path d="M16 10l5-3v10l-5-3"/>',
}
