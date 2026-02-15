import json
import logging
import random
import os
import re
import threading
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError
from pathlib import Path

import pytz
from PIL import Image, ImageDraw, ImageFont
from plugins.base_plugin.base_plugin import BasePlugin
from utils.app_utils import get_font

logger = logging.getLogger(__name__)

# (display name, bolls.life book ID, max chapters)
BOOKS = [
    ("Genesis", 1, 50), ("Exodus", 2, 40),
    ("Leviticus", 3, 27), ("Numbers", 4, 36),
    ("Deuteronomy", 5, 34), ("Joshua", 6, 24),
    ("Judges", 7, 21), ("Ruth", 8, 4),
    ("1 Samuel", 9, 31), ("2 Samuel", 10, 24),
    ("1 Kings", 11, 22), ("2 Kings", 12, 25),
    ("1 Chronicles", 13, 29), ("2 Chronicles", 14, 36),
    ("Ezra", 15, 10), ("Nehemiah", 16, 13),
    ("Esther", 17, 10), ("Job", 18, 42),
    ("Psalm", 19, 150), ("Proverbs", 20, 31),
    ("Ecclesiastes", 21, 12), ("Song of Solomon", 22, 8),
    ("Isaiah", 23, 66), ("Jeremiah", 24, 52),
    ("Lamentations", 25, 5), ("Ezekiel", 26, 48),
    ("Daniel", 27, 12), ("Hosea", 28, 14),
    ("Joel", 29, 3), ("Amos", 30, 9),
    ("Obadiah", 31, 1), ("Jonah", 32, 4),
    ("Micah", 33, 7), ("Nahum", 34, 3),
    ("Habakkuk", 35, 3), ("Zephaniah", 36, 3),
    ("Haggai", 37, 2), ("Zechariah", 38, 14),
    ("Malachi", 39, 4),
    ("Matthew", 40, 28), ("Mark", 41, 16),
    ("Luke", 42, 24), ("John", 43, 21),
    ("Acts", 44, 28), ("Romans", 45, 16),
    ("1 Corinthians", 46, 16), ("2 Corinthians", 47, 13),
    ("Galatians", 48, 6), ("Ephesians", 49, 6),
    ("Philippians", 50, 4), ("Colossians", 51, 4),
    ("1 Thessalonians", 52, 5), ("2 Thessalonians", 53, 3),
    ("1 Timothy", 54, 6), ("2 Timothy", 55, 4),
    ("Titus", 56, 3), ("Philemon", 57, 1),
    ("Hebrews", 58, 13), ("James", 59, 5),
    ("1 Peter", 60, 5), ("2 Peter", 61, 3),
    ("1 John", 62, 5), ("2 John", 63, 1),
    ("3 John", 64, 1), ("Jude", 65, 1),
    ("Revelation", 66, 22),
]

# Supported translations
TRANSLATIONS = {
    "NASB": "https://bolls.life/get-verse/NASB",
    "KJV": "https://bolls.life/get-verse/KJV",
    "NIV": "https://bolls.life/get-verse/NIV",
    "ESV": "https://bolls.life/get-verse/ESV",
    "NKJV": "https://bolls.life/get-verse/NKJV",
    "NLT": "https://bolls.life/get-verse/NLT",
    "CSB": "https://bolls.life/get-verse/CSB",
}

DEFAULT_TIMEZONE = "US/Eastern"


class BibleCache:
    """Manages offline Bible verse storage."""
    
    def __init__(self, cache_dir):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.download_status_file = self.cache_dir / "download_status.json"
        
    def get_cache_file(self, translation):
        """Get the cache file path for a translation."""
        return self.cache_dir / f"{translation}.json"
    
    def load_cache(self, translation):
        """Load cached Bible data for a translation."""
        cache_file = self.get_cache_file(translation)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading cache for {translation}: {e}")
        return {}
    
    def save_cache(self, translation, data):
        """Save Bible data to cache."""
        cache_file = self.get_cache_file(translation)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved cache for {translation}")
        except IOError as e:
            logger.error(f"Error saving cache for {translation}: {e}")
    
    def get_verse_from_cache(self, translation, book_id, chapter, verse):
        """Get a verse from cache."""
        cache = self.load_cache(translation)
        key = f"{book_id}_{chapter}_{verse}"
        return cache.get(key)
    
    def save_verse_to_cache(self, translation, book_id, chapter, verse, text):
        """Save a verse to cache."""
        cache = self.load_cache(translation)
        key = f"{book_id}_{chapter}_{verse}"
        cache[key] = text
        self.save_cache(translation, cache)
    
    def get_download_status(self):
        """Get the current download status."""
        if self.download_status_file.exists():
            try:
                with open(self.download_status_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"status": "not_started", "progress": 0}
    
    def set_download_status(self, status, progress=0, message=""):
        """Set the download status."""
        try:
            with open(self.download_status_file, 'w') as f:
                json.dump({
                    "status": status,
                    "progress": progress,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                }, f)
        except IOError as e:
            logger.error(f"Error saving download status: {e}")


def fetch_verse(translation, book_id, chapter, verse, cache=None):
    """Fetch verse text from bolls.life API or cache."""
    if cache:
        cached_text = cache.get_verse_from_cache(translation, book_id, chapter, verse)
        if cached_text:
            return cached_text
    
    api_base = TRANSLATIONS.get(translation, TRANSLATIONS["NASB"])
    url = f"{api_base}/{book_id}/{chapter}/{verse}/"
    req = Request(url, headers={"User-Agent": "bible-clock/2.0"})
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if "text" in data:
                text = data["text"].strip()
                # Remove HTML/XML tags like <S>...</S>, <i>, </i>
                text = re.sub(r'<[^>]+>', '', text)
                # Clean up multiple spaces
                text = re.sub(r'\s+', ' ', text).strip()
                if cache:
                    cache.save_verse_to_cache(translation, book_id, chapter, verse, text)
                return text
    except (URLError, KeyError, json.JSONDecodeError) as e:
        logger.error(f"Error fetching verse: {e}")
        return None
    return None


def download_all_verses(cache, translations_to_download):
    """Download all time-based verses for selected translations."""
    try:
        cache.set_download_status("downloading", 0, "Starting download...")
        logger.info(f"Starting bulk download for translations: {translations_to_download}")
        
        total_combinations = 24 * 60 * len(translations_to_download)
        downloaded_verses = 0
        
        for translation in translations_to_download:
            logger.info(f"Downloading {translation}...")
            
            for chapter in range(1, 25):
                for verse in range(1, 61):
                    candidates = [(book_id,) for _, book_id, max_ch in BOOKS if max_ch >= chapter]
                    
                    if candidates:
                        book_id = candidates[0][0]
                        text = fetch_verse(translation, book_id, chapter, verse, cache)
                        
                        downloaded_verses += 1
                        progress = int((downloaded_verses / total_combinations) * 100)
                        
                        if downloaded_verses % 100 == 0:
                            cache.set_download_status(
                                "downloading",
                                progress,
                                f"{translation}: Downloaded {downloaded_verses}/{total_combinations}"
                            )
                            logger.info(f"Progress: {progress}%")
        
        cache.set_download_status("completed", 100, f"Downloaded all verses for {len(translations_to_download)} translation(s)!")
        logger.info(f"Download completed! Processed {downloaded_verses} verses")
        
    except Exception as e:
        logger.error(f"Error during bulk download: {e}")
        cache.set_download_status("error", 0, f"Error: {str(e)}")


def pick_book_and_fetch(translation, chapter, verse, cache=None):
    """Pick a random book that has the given chapter, fetch the verse text."""
    candidates = [(name, book_id) for name, book_id, max_ch in BOOKS if max_ch >= chapter]
    if not candidates:
        logger.warning(f"No book has chapter {chapter}, using Psalm 23:1")
        return ("Psalm", "The Lord is my shepherd; I shall not want.")
    random.shuffle(candidates)
    for name, book_id in candidates:
        text = fetch_verse(translation, book_id, chapter, verse, cache)
        if text:
            return (name, text)
    logger.warning(f"Could not find {chapter}:{verse}, using Psalm 23:1")
    return ("Psalm", "The Lord is my shepherd; I shall not want.")


def wrap_text(text, font, draw, max_width):
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    if hex_color.startswith('#'):
        hex_color = hex_color[1:]
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
class BibleVerse(BasePlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        plugin_dir = Path(__file__).parent
        cache_dir = plugin_dir / "bible_cache"
        self.cache = BibleCache(cache_dir)
        self.download_thread = None
    
    def start_bulk_download(self, translations):
        """Start downloading all verses in background."""
        if self.download_thread and self.download_thread.is_alive():
            logger.info("Download already in progress")
            return
        
        self.download_thread = threading.Thread(
            target=download_all_verses,
            args=(self.cache, translations),
            daemon=True
        )
        self.download_thread.start()
        logger.info(f"Started bulk download for: {translations}")
    
    def generate_image(self, settings, device_config):
        # Check if download was triggered
        if settings.get("triggerDownload") == "yes":
            download_trans = settings.get("downloadTranslations", [])
            if isinstance(download_trans, str):
                download_trans = [download_trans] if download_trans else []
            if download_trans:
                self.start_bulk_download(download_trans)
        
        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        w, h = dimensions

        timezone_name = device_config.get_config("timezone") or DEFAULT_TIMEZONE
        tz = pytz.timezone(timezone_name)
        now = datetime.now(tz)
        
        # Handle DST override
        dst_override = settings.get("dstOverride")
        if dst_override == "always_dst":
            if not now.dst():
                from datetime import timedelta
                now = now + timedelta(hours=1)
        elif dst_override == "never_dst":
            if now.dst():
                from datetime import timedelta
                now = now - timedelta(hours=1)

        chapter = now.hour if now.hour != 0 else 24
        verse = now.minute if now.minute != 0 else 1

        # Get settings
        translation = settings.get("translation", "NASB")
        layout_style = settings.get("layoutStyle", "corner")
        size_preset = settings.get("sizePreset", "medium")
        logger.info(f"SIZE PRESET RECEIVED: {size_preset}")
        border_style = settings.get("borderStyle", "none")
        border_width = int(settings.get("borderWidth", 3))
        font_name = settings.get("fontName", "Caladea")
        
        # Get colors
        bg_color = settings.get("bgColor", "#f8f4e8")
        verse_color = settings.get("verseColor", "#2c3e50")
        ref_color = settings.get("refColor", "#34495e")
        trans_color = settings.get("transColor", "#7f8c8d")
        border_color = settings.get("borderColor", "#2c3e50")
        
        # Fetch verse
        book, text = pick_book_and_fetch(translation, chapter, verse, self.cache)
        reference = f"{book} {chapter}:{verse}" if book else ""
        
        # Create image
        img = Image.new("RGB", (w, h), hex_to_rgb(bg_color))
        draw = ImageDraw.Draw(img)

        # Equal margins
        margin = int(min(w, h) * 0.05)
        content_width = w - (margin * 2)
        content_height = h - (margin * 2)
        
        # FIXED FONT SIZING - Different multiplier for each preset
        if size_preset == "small":
            verse_multiplier = 0.054
            ref_multiplier = 0.035
            trans_multiplier = 0.030
        elif size_preset == "medium":
            verse_multiplier = 0.075
            ref_multiplier = 0.042
            trans_multiplier = 0.0375
        else:
            verse_multiplier = 0.096
            ref_multiplier = 0.054
            trans_multiplier = 0.048
        
        verse_font_size = int(min(w, h) * verse_multiplier)
        ref_font_size = int(min(w, h) * ref_multiplier)
        trans_font_size = int(min(w, h) * trans_multiplier)
        logger.info(f"CALCULATED SIZES: verse={verse_font_size}px, ref={ref_font_size}px, trans={trans_font_size}px")
        
        # Get fonts
        verse_font = get_font(font_name, verse_font_size)
        ref_font = get_font(font_name, ref_font_size)
        trans_font = get_font(font_name, trans_font_size)
        
        # Wrap verse text
        verse_text = f'"{text}"'
        verse_lines = wrap_text(verse_text, verse_font, draw, content_width)
       
        # Adjust line spacing based on font
        if font_name == "Napoli":
            line_spacing_multiplier = 1.5
        elif font_name == "Dogica":
            line_spacing_multiplier = 1.6
        elif font_name == "Jost":
            line_spacing_multiplier = 1.2
        else:
            line_spacing_multiplier = 1.4
       
         # Calculate verse block height
        line_height = int(draw.textbbox((0, 0), "Ay", font=verse_font)[3] * line_spacing_multiplier)
        verse_block_height = line_height * len(verse_lines)
        
        # Calculate reference and translation dimensions
        ref_bbox = draw.textbbox((0, 0), reference, font=ref_font)
        ref_width = ref_bbox[2] - ref_bbox[0]
        ref_height = ref_bbox[3] - ref_bbox[1]
        
        trans_bbox = draw.textbbox((0, 0), translation, font=trans_font)
        trans_width = trans_bbox[2] - trans_bbox[0]
        trans_height = trans_bbox[3] - trans_bbox[1]
        
        # Draw border if selected
        if border_style != "none":
            border_rect = [0, 0, w, h]
            
            if border_style == "solid":
                draw.rectangle(border_rect, outline=hex_to_rgb(border_color), width=border_width)
            elif border_style == "dashed":
                dash_length = 10
                gap_length = 5
                # Top
                x = 0
                while x < w:
                    draw.line([(x, 0), (min(x + dash_length, w), 0)], fill=hex_to_rgb(border_color), width=border_width)
                    x += dash_length + gap_length
                # Bottom
                x = 0
                while x < w:
                    draw.line([(x, h), (min(x + dash_length, w), h)], fill=hex_to_rgb(border_color), width=border_width)
                    x += dash_length + gap_length
                # Left
                y = 0
                while y < h:
                    draw.line([(0, y), (0, min(y + dash_length, h))], fill=hex_to_rgb(border_color), width=border_width)
                    y += dash_length + gap_length
                # Right
                y = 0
                while y < h:
                    draw.line([(w, y), (w, min(y + dash_length, h))], fill=hex_to_rgb(border_color), width=border_width)
                    y += dash_length + gap_length
            elif border_style == "dotted":
                dot_spacing = 8
                # Top & Bottom
                for x in range(0, w, dot_spacing):
                    draw.ellipse([x, -border_width//2, x + border_width, border_width//2], fill=hex_to_rgb(border_color))
                    draw.ellipse([x, h - border_width//2, x + border_width, h + border_width//2], fill=hex_to_rgb(border_color))
                # Left & Right
                for y in range(0, h, dot_spacing):
                    draw.ellipse([-border_width//2, y, border_width//2, y + border_width], fill=hex_to_rgb(border_color))
                    draw.ellipse([w - border_width//2, y, w + border_width//2, y + border_width], fill=hex_to_rgb(border_color))
            elif border_style == "double":
                inner_offset = border_width + 2
                draw.rectangle(border_rect, outline=hex_to_rgb(border_color), width=2)
                draw.rectangle([inner_offset, inner_offset, w - inner_offset, h - inner_offset], outline=hex_to_rgb(border_color), width=2)
        # Position elements based on layout style
        if layout_style == "corner":
            # Verse top-left
            y_verse = margin + 10
            for line in verse_lines:
                draw.text((margin, y_verse), line, fill=hex_to_rgb(verse_color), font=verse_font)
                y_verse += line_height
            
            # Translation bottom-left
            trans_y = h - margin - trans_height
            draw.text((margin, trans_y), translation, fill=hex_to_rgb(trans_color), font=trans_font)
            
            # Reference bottom-right
            ref_x = w - margin - ref_width
            ref_y = h - margin - ref_height
            draw.text((ref_x, ref_y), reference, fill=hex_to_rgb(ref_color), font=ref_font)
            
        elif layout_style == "center":
            # Verse centered top
            y_verse = margin + 10
            for line in verse_lines:
                line_bbox = draw.textbbox((0, 0), line, font=verse_font)
                line_width = line_bbox[2] - line_bbox[0]
                x_centered = (w - line_width) // 2
                draw.text((x_centered, y_verse), line, fill=hex_to_rgb(verse_color), font=verse_font)
                y_verse += line_height
            
            # Translation and reference centered at bottom
            trans_x = margin + (content_width // 4) - (trans_width // 2)
            trans_y = h - margin - trans_height
            draw.text((trans_x, trans_y), translation, fill=hex_to_rgb(trans_color), font=trans_font)
            
            ref_x = w - margin - (content_width // 4) - (ref_width // 2)
            ref_y = h - margin - ref_height
            draw.text((ref_x, ref_y), reference, fill=hex_to_rgb(ref_color), font=ref_font)
            
        elif layout_style == "left":
            # All left-aligned
            y_verse = margin + 10
            for line in verse_lines:
                draw.text((margin, y_verse), line, fill=hex_to_rgb(verse_color), font=verse_font)
                y_verse += line_height
            
            trans_y = h - margin - trans_height - ref_height - 10
            draw.text((margin, trans_y), translation, fill=hex_to_rgb(trans_color), font=trans_font)
            
            ref_y = h - margin - ref_height
            draw.text((margin, ref_y), reference, fill=hex_to_rgb(ref_color), font=ref_font)
            
        elif layout_style == "right":
            # All right-aligned
            y_verse = margin + 10
            for line in verse_lines:
                line_bbox = draw.textbbox((0, 0), line, font=verse_font)
                line_width = line_bbox[2] - line_bbox[0]
                x_right = w - margin - line_width
                draw.text((x_right, y_verse), line, fill=hex_to_rgb(verse_color), font=verse_font)
                y_verse += line_height
            
            trans_x = w - margin - trans_width
            trans_y = h - margin - trans_height - ref_height - 10
            draw.text((trans_x, trans_y), translation, fill=hex_to_rgb(trans_color), font=trans_font)
            
            ref_x = w - margin - ref_width
            ref_y = h - margin - ref_height
            draw.text((ref_x, ref_y), reference, fill=hex_to_rgb(ref_color), font=ref_font)

        return img

