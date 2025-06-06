import asyncio

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio

# Import helper functions for YouTube functionality
from .helper import extract_video_info, extract_detailed_subtitles, extract_top_comments

# Initialize the MCP server
server = Server("youtube_dlp_server")


@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """
    List available resources.
    Currently no resources are exposed by this server.
    """
    return []


@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    """
    Read a specific resource by its URI.
    Currently no resources are supported.
    """
    raise ValueError(f"Unsupported resource URI: {uri}")


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """
    List available prompts.
    Currently no prompts are exposed by this server.
    """
    return []


@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    """
    Generate a prompt by name.
    Currently no prompts are supported.
    """
    raise ValueError(f"Unknown prompt: {name}")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available YouTube DLP tools.
    """
    return [
        types.Tool(
            name="get-video-info",
            description="Extract detailed information from a YouTube video URL without downloading",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "YouTube video URL to extract information from",
                    }
                },
                "required": ["url"],
            },
        ),
        types.Tool(
            name="get-video-subtitles",
            description="Extract subtitles and captions from a YouTube video",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "YouTube video URL to extract subtitles from",
                    },
                    "languages": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of language codes to extract (e.g., ['en', 'es']). If not provided, all available languages will be extracted.",
                    },
                    "include_auto_captions": {
                        "type": "boolean",
                        "description": "Whether to include auto-generated captions (default: true)",
                        "default": True,
                    },
                },
                "required": ["url"],
            },
        ),
        types.Tool(
            name="get-top-comments",
            description="Extract top comments from a YouTube video (sorted by likes)",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "YouTube video URL to extract comments from",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of top comments to extract (default: 10, maximum: 20)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["url"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle YouTube DLP tool execution requests.
    """
    if name == "get-video-info":
        return await _handle_get_video_info(arguments)
    elif name == "get-video-subtitles":
        return await _handle_get_video_subtitles(arguments)
    elif name == "get-top-comments":
        return await _handle_get_top_comments(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def _handle_get_video_info(arguments: dict | None) -> list[types.TextContent]:
    """
    Handle get-video-info tool execution.

    Args:
        arguments: Tool arguments containing the video URL

    Returns:
        List containing formatted video information
    """
    if not arguments or not arguments.get("url"):
        raise ValueError("URL is required for video info extraction")

    try:
        video_info = await extract_video_info(arguments["url"])

        # Format the response nicely
        info_text = f"""📹 **Video Information**

**Title:** {video_info.get('title', 'Unknown')}
**Uploader:** {video_info.get('uploader', 'Unknown')}
**Duration:** {video_info.get('duration', 0)} seconds
**View Count:** {video_info.get('view_count', 0):,}
**Like Count:** {video_info.get('like_count', 0):,}
**Upload Date:** {video_info.get('upload_date', 'Unknown')}

**Description:**
{video_info.get('description', 'No description available')[:500]}{'...' if len(video_info.get('description', '')) > 500 else ''}

**Available Subtitle Languages:** {', '.join(video_info.get('available_subtitle_languages', []))}
**Available Caption Languages:** {', '.join(video_info.get('available_caption_languages', []))}

**Categories:** {', '.join(video_info.get('categories', []))}
**Tags:** {', '.join(video_info.get('tags', [])[:10])}{'...' if len(video_info.get('tags', [])) > 10 else ''}

**Available Formats:** {len(video_info.get('formats', []))} formats available
"""

        return [
            types.TextContent(
                type="text",
                text=info_text,
            )
        ]

    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"❌ Error extracting video info: {str(e)}",
            )
        ]


async def _handle_get_video_subtitles(
    arguments: dict | None,
) -> list[types.TextContent]:
    """
    Handle get-video-subtitles tool execution.

    Args:
        arguments: Tool arguments containing URL and subtitle options

    Returns:
        List containing formatted subtitle information
    """
    if not arguments or not arguments.get("url"):
        raise ValueError("URL is required for subtitle extraction")

    try:
        url = arguments["url"]
        languages = arguments.get("languages")
        include_auto_captions = arguments.get("include_auto_captions", True)

        subtitle_data = await extract_detailed_subtitles(
            url=url,
            subtitle_languages=languages,
            include_automatic_captions=include_auto_captions,
        )

        # Format the response
        response_parts = []
        response_parts.append(
            f"📝 **Subtitles for:** {subtitle_data.get('video_title', 'Unknown')}"
        )
        response_parts.append(
            f"**Video ID:** {subtitle_data.get('video_id', 'Unknown')}"
        )
        response_parts.append(
            f"**Uploader:** {subtitle_data.get('uploader', 'Unknown')}"
        )
        response_parts.append(
            f"**Duration:** {subtitle_data.get('duration', 0)} seconds"
        )
        response_parts.append("")

        # Manual subtitles
        subtitles = subtitle_data.get("subtitles", {})
        if subtitles:
            response_parts.append("**Manual Subtitles:**")
            for lang, sub_info in subtitles.items():
                if "error" in sub_info:
                    response_parts.append(
                        f"- {sub_info.get('language_name', lang)} ({lang}): ❌ {sub_info['error']}"
                    )
                else:
                    word_count = sub_info.get("word_count", 0)
                    line_count = sub_info.get("line_count", 0)
                    response_parts.append(
                        f"- {sub_info.get('language_name', lang)} ({lang}): {word_count} words, {line_count} lines"
                    )

                    # Include a preview of the content (first 300 characters)
                    content = sub_info.get("content", "")
                    if content:
                        preview = content[:300] + ("..." if len(content) > 300 else "")
                        response_parts.append(f"  Preview: {preview}")
            response_parts.append("")

        # Automatic captions
        auto_captions = subtitle_data.get("automatic_captions", {})
        if auto_captions:
            response_parts.append("**Automatic Captions:**")
            for lang, cap_info in auto_captions.items():
                if "error" in cap_info:
                    response_parts.append(
                        f"- {cap_info.get('language_name', lang)} ({lang}): ❌ {cap_info['error']}"
                    )
                else:
                    word_count = cap_info.get("word_count", 0)
                    line_count = cap_info.get("line_count", 0)
                    response_parts.append(
                        f"- {cap_info.get('language_name', lang)} ({lang}): {word_count} words, {line_count} lines"
                    )

                    # Include a preview of the content (first 300 characters)
                    content = cap_info.get("content", "")
                    if content:
                        preview = content[:300] + ("..." if len(content) > 300 else "")
                        response_parts.append(f"  Preview: {preview}")
            response_parts.append("")

        # Summary
        summary = subtitle_data.get("extraction_summary", {})
        response_parts.append("**Summary:**")
        response_parts.append(
            f"- Manual subtitle languages: {summary.get('subtitle_languages_downloaded', 0)}"
        )
        response_parts.append(
            f"- Auto-caption languages: {summary.get('automatic_caption_languages_downloaded', 0)}"
        )
        response_parts.append(
            f"- Total subtitle words: {summary.get('total_subtitle_content', 0):,}"
        )
        response_parts.append(
            f"- Total caption words: {summary.get('total_caption_content', 0):,}"
        )

        return [
            types.TextContent(
                type="text",
                text="\n".join(response_parts),
            )
        ]

    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"❌ Error extracting subtitles: {str(e)}",
            )
        ]


async def _handle_get_top_comments(arguments: dict | None) -> list[types.TextContent]:
    """
    Handle get-top-comments tool execution.

    Args:
        arguments: Tool arguments containing URL and comment count

    Returns:
        List containing formatted top comments
    """
    if not arguments or not arguments.get("url"):
        raise ValueError("URL is required for comment extraction")

    try:
        url = arguments["url"]
        count = arguments.get("count", 10)

        # Ensure count is within valid range
        count = max(1, min(count, 20))

        comment_data = await extract_top_comments(url, count)

        # Format the response
        response_parts = []
        video_info = comment_data.get("video_info", {})

        response_parts.append(
            f"💬 **Top Comments for:** {video_info.get('title', 'Unknown')}"
        )
        response_parts.append(f"**Uploader:** {video_info.get('uploader', 'Unknown')}")
        response_parts.append(f"**Views:** {video_info.get('view_count', 0):,}")
        response_parts.append(f"**Likes:** {video_info.get('like_count', 0):,}")
        response_parts.append("")
        response_parts.append(
            f"**Top {comment_data.get('comments_extracted', 0)} Comments** (sorted by likes):"
        )
        response_parts.append("")

        comments = comment_data.get("comments", [])
        if comments:
            for comment in comments:
                # Format each comment
                author = comment.get("author", "Unknown")
                text = comment.get("text", "")
                likes = comment.get("like_count", 0)
                rank = comment.get("rank", 0)
                is_uploader = comment.get("author_is_uploader", False)
                is_favorited = comment.get("is_favorited", False)

                # Add badges for special comments
                badges = []
                if is_uploader:
                    badges.append("👤 CREATOR")
                if is_favorited:
                    badges.append("❤️ FAVORITED")

                badge_text = f" {' '.join(badges)}" if badges else ""

                response_parts.append(f"**#{rank}** - **{author}**{badge_text}")
                response_parts.append(f"👍 {likes:,} likes")
                response_parts.append(f"📝 {text}")
                response_parts.append("")
        else:
            response_parts.append(
                "No comments found or comments are disabled for this video."
            )

        # Add summary
        response_parts.append("---")
        response_parts.append("**Summary:**")
        response_parts.append(
            f"- Comments extracted: {comment_data.get('comments_extracted', 0)}"
        )
        response_parts.append(
            f"- Total comments available: {comment_data.get('total_comments_available', 0)}"
        )
        response_parts.append(
            f"- Requested count: {comment_data.get('max_comments_requested', 0)}"
        )

        return [
            types.TextContent(
                type="text",
                text="\n".join(response_parts),
            )
        ]

    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"❌ Error extracting comments: {str(e)}",
            )
        ]


async def main():
    """
    Main entry point for the YouTube DLP MCP server.
    """
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="youtube_dlp_server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
