import yt_dlp
import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import tempfile
import json
from datetime import datetime
import requests
import re


logger = logging.getLogger(__name__)


def _get_proxy_config() -> Optional[str]:
    """
    Get proxy configuration from environment variable.

    Returns:
        Proxy URL string if set, None otherwise
    """
    proxy_url = os.getenv("PROXY_URL", "").strip()
    if proxy_url:
        logger.info(f"Using proxy: {proxy_url}")
        return proxy_url
    return None


def _get_base_ydl_opts() -> Dict[str, Any]:
    """
    Get base yt-dlp options including proxy configuration if available.

    Returns:
        Dictionary with base yt-dlp options
    """
    opts = {}

    # Add proxy if configured
    proxy_url = _get_proxy_config()
    if proxy_url:
        opts["proxy"] = proxy_url

    return opts


class DownloadProgressHook:
    """Progress hook for yt-dlp downloads"""

    def __init__(self, download_id: str = None):
        self.download_id = download_id
        self.last_progress = 0.0

    def __call__(self, d: Dict[str, Any]):
        """Progress hook callback"""
        if d["status"] == "downloading":
            if "total_bytes" in d and d["total_bytes"] is not None:
                progress = (d["downloaded_bytes"] / d["total_bytes"]) * 100
                if progress - self.last_progress > 1:  # Log every 1% change
                    logger.info(f"Download progress: {progress:.1f}%")
                    self.last_progress = progress
        elif d["status"] == "finished":
            logger.info(f"Download finished: {d['filename']}")


async def extract_video_info(url: str) -> Dict[str, Any]:
    """
    Extract video information without downloading

    Args:
        url: YouTube video URL

    Returns:
        Dictionary containing video metadata
    """
    try:
        ydl_opts = {
            **_get_base_ydl_opts(),
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "writeinfojson": False,  # We'll extract info programmatically
        }

        def _extract_info():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _extract_info)

        # Extract detailed subtitle information
        subtitles_info = {}
        if info.get("subtitles"):
            for lang, subs in info.get("subtitles", {}).items():
                if subs:  # Check if subtitle list is not empty
                    subtitle_data = {"language": lang, "formats": []}
                    for sub in subs:
                        subtitle_data["formats"].append(
                            {
                                "ext": sub.get("ext", ""),
                                "url": sub.get("url", ""),
                                "name": sub.get("name", ""),
                            }
                        )
                    subtitles_info[lang] = subtitle_data

        # Extract automatic captions if available
        automatic_captions_info = {}
        if info.get("automatic_captions"):
            for lang, captions in info.get("automatic_captions", {}).items():
                if captions:  # Check if caption list is not empty
                    caption_data = {"language": lang, "formats": []}
                    for cap in captions:
                        caption_data["formats"].append(
                            {
                                "ext": cap.get("ext", ""),
                                "url": cap.get("url", ""),
                                "name": cap.get("name", ""),
                            }
                        )
                    automatic_captions_info[lang] = caption_data

        # Extract relevant information
        video_info = {
            "title": info.get("title", "Unknown"),
            "uploader": info.get("uploader", "Unknown"),
            "uploader_id": info.get("uploader_id", ""),
            "uploader_url": info.get("uploader_url", ""),
            "duration": info.get("duration", 0),
            "view_count": info.get("view_count", 0),
            "like_count": info.get("like_count", 0),
            "dislike_count": info.get("dislike_count", 0),
            "description": info.get("description", ""),
            "upload_date": info.get("upload_date", ""),
            "thumbnail": info.get("thumbnail", ""),
            "webpage_url": info.get("webpage_url", url),
            "formats": [],
            "subtitles": subtitles_info,
            "automatic_captions": automatic_captions_info,
            "available_subtitle_languages": list(subtitles_info.keys()),
            "available_caption_languages": list(automatic_captions_info.keys()),
            "categories": info.get("categories", []),
            "tags": info.get("tags", []),
            "age_limit": info.get("age_limit", 0),
            "availability": info.get("availability", ""),
            "live_status": info.get("live_status", ""),
            "release_timestamp": info.get("release_timestamp", 0),
            "original_url": info.get("original_url", url),
        }

        # Extract format information
        if "formats" in info:
            for fmt in info["formats"]:
                format_info = {
                    "format_id": fmt.get("format_id", ""),
                    "ext": fmt.get("ext", ""),
                    "resolution": fmt.get(
                        "resolution",
                        "audio only" if fmt.get("vcodec") == "none" else "unknown",
                    ),
                    "filesize": fmt.get("filesize", 0),
                    "fps": fmt.get("fps", 0),
                    "vcodec": fmt.get("vcodec", "none"),
                    "acodec": fmt.get("acodec", "none"),
                    "quality": fmt.get("quality", 0),
                    "format_note": fmt.get("format_note", ""),
                    "container": fmt.get("container", ""),
                }
                video_info["formats"].append(format_info)

        return video_info

    except Exception as e:
        logger.error(f"Error extracting video info: {e}")
        raise Exception(f"Failed to extract video information: {str(e)}")


async def download_youtube_video(
    url: str,
    output_dir: str,
    filename_prefix: str = "download",
    format_type: str = "video",
    video_quality: str = "best",
    audio_quality: str = "best",
    include_subtitles: bool = False,
    subtitle_languages: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Download YouTube video using yt-dlp

    Args:
        url: YouTube video URL
        output_dir: Directory to save the downloaded file
        filename_prefix: Prefix for the output filename
        format_type: Type of download ('video', 'audio', 'both')
        video_quality: Video quality preference
        audio_quality: Audio quality preference
        include_subtitles: Whether to download subtitles
        subtitle_languages: List of subtitle language codes

    Returns:
        Dictionary containing download result information
    """
    try:
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Base yt-dlp options
        ydl_opts = {
            **_get_base_ydl_opts(),
            "outtmpl": os.path.join(output_dir, f"{filename_prefix}.%(ext)s"),
            "progress_hooks": [DownloadProgressHook()],
            "no_warnings": False,
            "extract_flat": False,
        }

        # Configure format selection based on type and quality
        if format_type == "audio":
            if audio_quality == "mp3":
                ydl_opts.update(
                    {
                        "format": "bestaudio/best",
                        "postprocessors": [
                            {
                                "key": "FFmpegExtractAudio",
                                "preferredcodec": "mp3",
                                "preferredquality": "192",
                            }
                        ],
                    }
                )
            elif audio_quality == "m4a":
                ydl_opts.update(
                    {
                        "format": "bestaudio[ext=m4a]/bestaudio/best",
                    }
                )
            else:
                ydl_opts["format"] = "bestaudio/best"

        elif format_type == "video":
            if video_quality == "best":
                ydl_opts["format"] = "best[ext=mp4]/best"
            elif video_quality == "worst":
                ydl_opts["format"] = "worst[ext=mp4]/worst"
            elif video_quality in ["720p", "1080p", "1440p", "2160p"]:
                height = video_quality.replace("p", "")
                ydl_opts["format"] = (
                    f"best[height<={height}][ext=mp4]/best[height<={height}]/best[ext=mp4]/best"
                )
            else:
                ydl_opts["format"] = "best[ext=mp4]/best"

        elif format_type == "both":
            # Download both video and audio separately
            ydl_opts["format"] = "best[ext=mp4]/best"

        # Configure subtitles
        if include_subtitles:
            ydl_opts.update(
                {
                    "writesubtitles": True,
                    "writeautomaticsub": True,
                    "subtitleslangs": subtitle_languages or ["en"],
                }
            )

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # First extract info to get the actual filename
                info = ydl.extract_info(url, download=False)

                # Download the video
                ydl.download([url])

                return info

        # Run download in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _download)

        # Find the downloaded file
        downloaded_files = []
        for file in os.listdir(output_dir):
            if file.startswith(filename_prefix):
                downloaded_files.append(os.path.join(output_dir, file))

        if not downloaded_files:
            raise Exception("Downloaded file not found")

        # Get the main video/audio file (largest file)
        main_file = max(downloaded_files, key=os.path.getsize)

        # Extract video info for response
        video_info = {
            "title": info.get("title", "Unknown"),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", "Unknown"),
            "view_count": info.get("view_count", 0),
            "upload_date": info.get("upload_date", ""),
        }

        return {
            "success": True,
            "file_path": main_file,
            "filename": os.path.basename(main_file),
            "file_size": os.path.getsize(main_file),
            "video_info": video_info,
            "downloaded_files": downloaded_files,
        }

    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return {
            "success": False,
            "error": str(e),
            "file_path": None,
            "filename": None,
        }


async def get_available_formats(url: str) -> Dict[str, Any]:
    """
    Get available formats for a YouTube video

    Args:
        url: YouTube video URL

    Returns:
        Dictionary containing available formats
    """
    try:
        info = await extract_video_info(url)

        video_formats = []
        audio_formats = []

        for fmt in info.get("formats", []):
            if fmt["vcodec"] != "none" and fmt["acodec"] != "none":
                # Video + Audio format
                video_formats.append(
                    {
                        "format_id": fmt["format_id"],
                        "resolution": fmt["resolution"],
                        "ext": fmt["ext"],
                        "filesize": fmt["filesize"],
                        "fps": fmt["fps"],
                    }
                )
            elif fmt["vcodec"] == "none" and fmt["acodec"] != "none":
                # Audio only format
                audio_formats.append(
                    {
                        "format_id": fmt["format_id"],
                        "ext": fmt["ext"],
                        "filesize": fmt["filesize"],
                        "acodec": fmt["acodec"],
                    }
                )

        return {
            "video_formats": video_formats,
            "audio_formats": audio_formats,
            "subtitles": info.get("subtitles", []),
        }

    except Exception as e:
        logger.error(f"Error getting available formats: {e}")
        raise Exception(f"Failed to get available formats: {str(e)}")


async def download_playlist(
    url: str,
    output_dir: str,
    max_downloads: int = 10,
    format_type: str = "video",
    video_quality: str = "best",
) -> Dict[str, Any]:
    """
    Download YouTube playlist (limited functionality)

    Args:
        url: YouTube playlist URL
        output_dir: Directory to save downloaded files
        max_downloads: Maximum number of videos to download
        format_type: Type of download ('video', 'audio')
        video_quality: Video quality preference

    Returns:
        Dictionary containing download results
    """
    try:
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        ydl_opts = {
            **_get_base_ydl_opts(),
            "outtmpl": os.path.join(
                output_dir, "%(playlist_index)s - %(title)s.%(ext)s"
            ),
            "playlistend": max_downloads,
            "progress_hooks": [DownloadProgressHook()],
        }

        # Configure format
        if format_type == "audio":
            ydl_opts["format"] = "bestaudio/best"
        else:
            if video_quality == "best":
                ydl_opts["format"] = "best[ext=mp4]/best"
            else:
                ydl_opts["format"] = (
                    f'best[height<={video_quality.replace("p", "")}][ext=mp4]/best'
                )

        def _download_playlist():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                ydl.download([url])
                return info

        # Run in thread pool
        loop = asyncio.get_event_loop()
        playlist_info = await loop.run_in_executor(None, _download_playlist)

        # Get downloaded files
        downloaded_files = []
        for file in os.listdir(output_dir):
            if os.path.isfile(os.path.join(output_dir, file)):
                downloaded_files.append(file)

        return {
            "success": True,
            "playlist_title": playlist_info.get("title", "Unknown Playlist"),
            "total_videos": len(playlist_info.get("entries", [])),
            "downloaded_count": len(downloaded_files),
            "downloaded_files": downloaded_files,
        }

    except Exception as e:
        logger.error(f"Error downloading playlist: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def parse_subtitle_content(subtitle_text: str, format_type: str = "vtt") -> str:
    """
    Parse subtitle content and extract clean text

    Args:
        subtitle_text: Raw subtitle content
        format_type: Format of the subtitle (vtt, srt, etc.)

    Returns:
        Clean text content from subtitles
    """
    try:
        if format_type.lower() == "vtt":
            # Remove VTT headers and timing information
            lines = subtitle_text.split("\n")
            text_lines = []

            for line in lines:
                line = line.strip()
                # Skip empty lines, headers, and timing lines
                if (
                    not line
                    or line.startswith("WEBVTT")
                    or line.startswith("NOTE")
                    or "-->" in line
                    or re.match(r"^\d+$", line)
                ):
                    continue

                # Remove HTML tags and styling
                line = re.sub(r"<[^>]+>", "", line)
                line = re.sub(r"&\w+;", "", line)  # Remove HTML entities

                if line:
                    text_lines.append(line)

            return "\n".join(text_lines)

        elif format_type.lower() == "srt":
            # Remove SRT timing and numbering
            lines = subtitle_text.split("\n")
            text_lines = []

            for line in lines:
                line = line.strip()
                # Skip empty lines, numbers, and timing lines
                if not line or re.match(r"^\d+$", line) or "-->" in line:
                    continue

                # Remove HTML tags
                line = re.sub(r"<[^>]+>", "", line)

                if line:
                    text_lines.append(line)

            return "\n".join(text_lines)

        else:
            # For other formats, just remove common patterns
            text = re.sub(r"<[^>]+>", "", subtitle_text)  # Remove HTML tags
            text = re.sub(
                r"\d{2}:\d{2}:\d{2}[.,]\d{3} --> \d{2}:\d{2}:\d{2}[.,]\d{3}", "", text
            )  # Remove timing
            text = re.sub(
                r"^\d+$", "", text, flags=re.MULTILINE
            )  # Remove subtitle numbers
            text = re.sub(r"\n\s*\n", "\n", text)  # Remove extra blank lines
            return text.strip()

    except Exception as e:
        logger.error(f"Error parsing subtitle content: {e}")
        return subtitle_text  # Return original if parsing fails


async def download_subtitle_content(url: str) -> tuple[str, str]:
    """
    Download subtitle content from URL

    Args:
        url: Subtitle file URL

    Returns:
        Tuple of (content, format)
    """
    try:
        # Determine format from URL
        if ".vtt" in url:
            format_type = "vtt"
        elif ".srt" in url:
            format_type = "srt"
        else:
            format_type = "unknown"

        # Download subtitle content with proxy support if configured
        proxy_url = _get_proxy_config()
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

        response = requests.get(url, timeout=30, proxies=proxies)
        response.raise_for_status()

        return response.text, format_type

    except Exception as e:
        logger.error(f"Error downloading subtitle from {url}: {e}")
        raise Exception(f"Failed to download subtitle: {str(e)}")


async def extract_detailed_subtitles(
    url: str,
    subtitle_languages: Optional[List[str]] = None,
    include_automatic_captions: bool = True,
) -> Dict[str, Any]:
    """
    Extract and download subtitle content from a YouTube video

    Args:
        url: YouTube video URL
        subtitle_languages: Specific languages to extract (None for all)
        include_automatic_captions: Include auto-generated captions

    Returns:
        Dictionary containing subtitle text content
    """
    try:
        ydl_opts = {
            **_get_base_ydl_opts(),
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "writesubtitles": False,
            "writeautomaticsub": False,
        }

        def _extract_info():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _extract_info)

        # Process manual subtitles
        subtitles_content = {}
        if info.get("subtitles"):
            available_subtitles = info.get("subtitles", {})
            languages_to_extract = (
                subtitle_languages
                if subtitle_languages
                else list(available_subtitles.keys())
            )

            for lang in languages_to_extract:
                if lang in available_subtitles and available_subtitles[lang]:
                    # Get the best subtitle format (prefer VTT, then SRT)
                    subtitle_url = None
                    subtitle_format = None

                    for sub in available_subtitles[lang]:
                        if sub.get("ext") == "vtt":
                            subtitle_url = sub.get("url")
                            subtitle_format = "vtt"
                            break
                        elif sub.get("ext") == "srt":
                            subtitle_url = sub.get("url")
                            subtitle_format = "srt"

                    if not subtitle_url and available_subtitles[lang]:
                        # Fallback to first available format
                        subtitle_url = available_subtitles[lang][0].get("url")
                        subtitle_format = available_subtitles[lang][0].get(
                            "ext", "unknown"
                        )

                    if subtitle_url:
                        try:
                            content, detected_format = await download_subtitle_content(
                                subtitle_url
                            )
                            parsed_content = parse_subtitle_content(
                                content, detected_format
                            )

                            subtitles_content[lang] = {
                                "language": lang,
                                "language_name": _get_language_name(lang),
                                "format": detected_format,
                                "content": parsed_content,
                                "word_count": (
                                    len(parsed_content.split()) if parsed_content else 0
                                ),
                                "line_count": (
                                    len(parsed_content.split("\n"))
                                    if parsed_content
                                    else 0
                                ),
                            }
                        except Exception as e:
                            logger.error(f"Failed to download subtitle for {lang}: {e}")
                            subtitles_content[lang] = {
                                "language": lang,
                                "language_name": _get_language_name(lang),
                                "error": f"Failed to download: {str(e)}",
                            }

        # Process automatic captions
        automatic_captions_content = {}
        if include_automatic_captions and info.get("automatic_captions"):
            available_captions = info.get("automatic_captions", {})
            languages_to_extract = (
                subtitle_languages
                if subtitle_languages
                else list(available_captions.keys())
            )

            for lang in languages_to_extract:
                if lang in available_captions and available_captions[lang]:
                    # Get the best caption format
                    caption_url = None
                    caption_format = None

                    for cap in available_captions[lang]:
                        if cap.get("ext") == "vtt":
                            caption_url = cap.get("url")
                            caption_format = "vtt"
                            break
                        elif cap.get("ext") == "srt":
                            caption_url = cap.get("url")
                            caption_format = "srt"

                    if not caption_url and available_captions[lang]:
                        # Fallback to first available format
                        caption_url = available_captions[lang][0].get("url")
                        caption_format = available_captions[lang][0].get(
                            "ext", "unknown"
                        )

                    if caption_url:
                        try:
                            content, detected_format = await download_subtitle_content(
                                caption_url
                            )
                            parsed_content = parse_subtitle_content(
                                content, detected_format
                            )

                            automatic_captions_content[lang] = {
                                "language": lang,
                                "language_name": _get_language_name(lang),
                                "format": detected_format,
                                "content": parsed_content,
                                "word_count": (
                                    len(parsed_content.split()) if parsed_content else 0
                                ),
                                "line_count": (
                                    len(parsed_content.split("\n"))
                                    if parsed_content
                                    else 0
                                ),
                            }
                        except Exception as e:
                            logger.error(f"Failed to download caption for {lang}: {e}")
                            automatic_captions_content[lang] = {
                                "language": lang,
                                "language_name": _get_language_name(lang),
                                "error": f"Failed to download: {str(e)}",
                            }

        return {
            "video_title": info.get("title", "Unknown"),
            "video_id": info.get("id", ""),
            "uploader": info.get("uploader", "Unknown"),
            "duration": info.get("duration", 0),
            "subtitles": subtitles_content,
            "automatic_captions": automatic_captions_content,
            "extraction_summary": {
                "subtitle_languages_downloaded": len(subtitles_content),
                "automatic_caption_languages_downloaded": len(
                    automatic_captions_content
                ),
                "total_subtitle_content": sum(
                    sub.get("word_count", 0)
                    for sub in subtitles_content.values()
                    if "word_count" in sub
                ),
                "total_caption_content": sum(
                    cap.get("word_count", 0)
                    for cap in automatic_captions_content.values()
                    if "word_count" in cap
                ),
            },
        }

    except Exception as e:
        logger.error(f"Error extracting detailed subtitles: {e}")
        raise Exception(f"Failed to extract subtitles: {str(e)}")


def _get_language_name(lang_code: str) -> str:
    """
    Get human-readable language name from language code

    Args:
        lang_code: Language code (e.g., 'en', 'es', 'fr')

    Returns:
        Human-readable language name
    """
    language_names = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ru": "Russian",
        "ja": "Japanese",
        "ko": "Korean",
        "zh": "Chinese",
        "ar": "Arabic",
        "hi": "Hindi",
        "tr": "Turkish",
        "pl": "Polish",
        "nl": "Dutch",
        "sv": "Swedish",
        "da": "Danish",
        "no": "Norwegian",
        "fi": "Finnish",
        "cs": "Czech",
        "hu": "Hungarian",
        "ro": "Romanian",
        "bg": "Bulgarian",
        "hr": "Croatian",
        "sk": "Slovak",
        "sl": "Slovenian",
        "et": "Estonian",
        "lv": "Latvian",
        "lt": "Lithuanian",
        "el": "Greek",
        "he": "Hebrew",
        "th": "Thai",
        "vi": "Vietnamese",
        "id": "Indonesian",
        "ms": "Malay",
        "tl": "Filipino",
        "uk": "Ukrainian",
        "be": "Belarusian",
        "mk": "Macedonian",
        "sr": "Serbian",
        "bs": "Bosnian",
        "sq": "Albanian",
        "mt": "Maltese",
        "ga": "Irish",
        "cy": "Welsh",
        "is": "Icelandic",
        "fo": "Faroese",
        "eu": "Basque",
        "ca": "Catalan",
        "gl": "Galician",
        "af": "Afrikaans",
        "sw": "Swahili",
        "zu": "Zulu",
        "xh": "Xhosa",
        "am": "Amharic",
        "bn": "Bengali",
        "gu": "Gujarati",
        "kn": "Kannada",
        "ml": "Malayalam",
        "mr": "Marathi",
        "ne": "Nepali",
        "or": "Odia",
        "pa": "Punjabi",
        "si": "Sinhala",
        "ta": "Tamil",
        "te": "Telugu",
        "ur": "Urdu",
    }

    return language_names.get(lang_code, lang_code.upper())


async def extract_top_comments(url: str, max_comments: int = 10) -> Dict[str, Any]:
    """
    Extract top comments from a YouTube video

    Args:
        url: YouTube video URL
        max_comments: Maximum number of comments to extract (default: 10, max: 20)

    Returns:
        Dictionary containing video info and top comments
    """
    try:
        # Limit max_comments to 20
        max_comments = min(max_comments, 20)

        ydl_opts = {
            **_get_base_ydl_opts(),
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "writecomments": False,
            "getcomments": True,
            "max_comments": max_comments,
        }

        def _extract_info():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _extract_info)

        # Extract video basic info
        video_info = {
            "title": info.get("title", "Unknown"),
            "uploader": info.get("uploader", "Unknown"),
            "uploader_id": info.get("uploader_id", ""),
            "view_count": info.get("view_count", 0),
            "like_count": info.get("like_count", 0),
            "upload_date": info.get("upload_date", ""),
            "duration": info.get("duration", 0),
            "webpage_url": info.get("webpage_url", url),
        }

        # Extract comments
        comments = []
        raw_comments = info.get("comments", [])

        if raw_comments:
            # Sort comments by like count (descending) to get top comments
            sorted_comments = sorted(
                raw_comments, key=lambda x: x.get("like_count", 0), reverse=True
            )

            for i, comment in enumerate(sorted_comments[:max_comments], 1):
                comment_data = {
                    "rank": i,
                    "author": comment.get("author", "Unknown"),
                    "author_id": comment.get("author_id", ""),
                    "text": comment.get("text", ""),
                    "like_count": comment.get("like_count", 0),
                    "is_favorited": comment.get("is_favorited", False),
                    "author_is_uploader": comment.get("author_is_uploader", False),
                    "parent": comment.get(
                        "parent", "root"
                    ),  # "root" for top-level comments
                    "timestamp": comment.get("timestamp", 0),
                }

                # Clean up the comment text (remove extra whitespace)
                if comment_data["text"]:
                    comment_data["text"] = " ".join(comment_data["text"].split())

                comments.append(comment_data)

        return {
            "video_info": video_info,
            "comments": comments,
            "comments_extracted": len(comments),
            "max_comments_requested": max_comments,
            "total_comments_available": len(raw_comments),
        }

    except Exception as e:
        logger.error(f"Error extracting comments: {e}")
        raise Exception(f"Failed to extract comments: {str(e)}")
