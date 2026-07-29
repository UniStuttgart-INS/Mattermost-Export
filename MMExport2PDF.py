#!/usr/bin/env python3

"""MMExport2PDF

Using the Mattermost API, connects to an instance and exports
all channel for a user on a team.

Images and Files are downloaded as well.

This is a fork of https://github.com/alallier/Mattermost-Export.
"""

import argparse
import dataclasses
import datetime
import gzip
import os
import pathlib
import platform
import shutil
from pathlib import Path
from typing import Final

import emoji
import fpdf  # https://py-pdf.github.io/fpdf2/index.html
import requests
import simplejson as json
from fontTools.ttLib import TTCollection, TTFont

__author__ = "Alexander J. Lallier, Clemens Sonnleitner"
__version__ = "2.0.0"
__license__ = "MIT"

#########################
## MARK: Globals constants
##
DEFAULT_FONT: Final[str] = "DejaVu Sans"

#########################
## MARK: Globals Variables
##

imageExtenstions = ["gif", "png", "jpeg", "jpg"]

mattermostURL = ""
headers = {}
baseUserPath = ""

users = {}
channelCache = {}


channelDisplayName = ""
messageHeader = None
tableOfContents = {}


#########################
## MARK: Exception Definitions
##


class OptionsException(Exception):
    def __init__(self, message=None):
        super().__init__(message)


class UserInfoException(Exception):
    def __init__(self, message=None):
        super().__init__(message)


class UserIDException(Exception):
    def __init__(self, message=None):
        super().__init__(message)


class TeamIDException(Exception):
    def __init__(self, message=None):
        super().__init__(message)


class UserChannelsException(Exception):
    def __init__(self, message=None):
        super().__init__(message)


class ImageException(Exception):
    def __init__(self, message=None):
        super().__init__(message)


class FileException(Exception):
    def __init__(self, message=None):
        super().__init__(message)


class ChannelPostsException(Exception):
    def __init__(self, message=None):
        super().__init__(message)


class ChannelMembersException(Exception):
    def __init__(self, message=None):
        super().__init__(message)


#########################
## MARK: MMExport2PDF Options
##


def processOptions():
    """
    Process command line arguments and set the internal options appropriately.

            @param argv List of command line arguments.
            @return The object containing the processed options.
    """
    # process options

    options = None

    try:
        usage = "%(prog)s [options]"
        description = (
            "%(prog)s is used to export all a users channels and DMs from a team."
        )
        epilog = "This can take a long time to run."

        parser = argparse.ArgumentParser(
            usage=usage,
            description=description,
            epilog=epilog,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )

        usergroup = parser.add_argument_group(title="User Info")
        _ = usergroup.add_argument(
            "-a",
            "--auth",
            help="Auth Token",
            action="store",
            dest="auth",
            required=True,
        )
        _ = usergroup.add_argument(
            "-u",
            "--user",
            help="Username of user to be exported",
            action="store",
            dest="user",
            required=True,
        )
        _ = usergroup.add_argument(
            "-t",
            "--team",
            help="Team to export from",
            action="store",
            dest="team",
            required=True,
        )

        servergroup = parser.add_argument_group(title="Server Info")
        _ = servergroup.add_argument(
            "-s",
            "--server",
            help="Hostname or IP of the server",
            action="store",
            dest="server",
            default="mattermost.com",
        )

        categorygroup = parser.add_argument_group(title="Channel Categories")
        _ = categorygroup.add_argument(
            "-p",
            "--public",
            help="Exclude public channels",
            action="store_true",
            dest="public",
        )
        _ = categorygroup.add_argument(
            "-P",
            "--private",
            help="Exclude private channels",
            action="store_true",
            dest="private",
        )
        _ = categorygroup.add_argument(
            "-g",
            "--groups",
            help="Exclude group messages",
            action="store_true",
            dest="group",
        )
        _ = categorygroup.add_argument(
            "-d",
            "--DMs",
            help="Exclude direct messages",
            action="store_true",
            dest="dms",
        )

        filtergroup = parser.add_argument_group(title="Message Filters")
        _ = filtergroup.add_argument(
            "-I",
            "--include",
            help="Only include these channels in the export.",
            nargs="*",
            dest="include",
            default=[],
        )
        _ = filtergroup.add_argument(
            "-E",
            "--exclude",
            help="Exclude these channels from the export",
            nargs="*",
            dest="exclude",
            default=[],
        )

        exportgroup = parser.add_argument_group(title="Export Options")
        _ = exportgroup.add_argument(
            "-sf",
            "--single-file-per-chat",
            help="Output a single file per chat/channel",
            action="store_true",
            dest="single_file_per_chat",
        )
        _ = exportgroup.add_argument(
            "-i",
            "--images",
            help="Embed images in PDF",
            action="store_true",
            dest="images",
        )
        _ = exportgroup.add_argument(
            "--no-downscale-images",
            help="Do not downscale oversized images",
            action="store_true",
            dest="no_downscale_images",
        )
        _ = exportgroup.add_argument(
            "-f",
            "--files",
            help="Embed files in PDF",
            action="store_true",
            dest="files",
        )
        _ = exportgroup.add_argument(
            "--replace-unicode",
            help="Map all unicode to latin-1. With this flag set, also the build the font management gets easier and also the built in fonts can be used for export",
            action="store_true",
            dest="replace_unicode",
        )
        _ = exportgroup.add_argument(
            "--resolve-emoji-aliases",
            help="Resolve emoji aliases like :thumbs_up:, :+1:, etc.",
            action="store_true",
            dest="resolve_emoji_aliases",
        )
        _ = exportgroup.add_argument(
            "-j", "--json", help="Export JSON", action="store_true", dest="json"
        )
        _ = exportgroup.add_argument(
            "-o",
            "--output",
            help="Base output directory",
            action="store",
            dest="output",
            default="./users",
        )
        _ = exportgroup.add_argument(
            "-n",
            "--filename",
            help="Filename of the generated PDF",
            action="store",
            dest="filename",
            default=None,
        )
        _ = exportgroup.add_argument(
            "--font-family-text",
            help="The font family that should be used for the text",
            # action="store",
            type=check_font_is_core_font,
            dest="font_family_text",
            default=DEFAULT_FONT,
        )
        _ = exportgroup.add_argument(
            "--font-family-header-footer",
            help="The font family that should be used for the header and footer",
            # action="store",
            type=check_font_is_core_font,
            dest="font_family_header_footer",
            default=DEFAULT_FONT,
        )
        _ = exportgroup.add_argument(
            "--font-family-title",
            help="The font family that should be used for the titles",
            # action="store",
            type=check_font_is_core_font,
            dest="font_family_title",
            default=DEFAULT_FONT,
        )
        _ = exportgroup.add_argument(
            "--fallback-fonts",
            help="Names of extra fallback fonts installed on the system. Useful for e.g. emoji support and CJK characters",
            nargs="*",
            dest="fallback_fonts",
            default=[],
        )

        options = parser.parse_args()  # uses sys.argv[1:] by default

        if options.replace_unicode and options.resolve_emoji_aliases:
            parser.error(
                "--replace-unicode and --resolve-emoji-aliases cannot be used at the same time"
            )

    except Exception as e:  # pylint: disable=broad-except
        raise OptionsException(e) from e

    return options


#########################
## MARK: Main
##


def main():
    # find_system_fonts()

    try:
        global baseUserPath
        global mattermostURL
        global headers

        options = processOptions()

        if options.public and options.private and options.group and options.dms:
            raise OptionsException("At least one channel category must be exported")

        # Setup
        mattermostURL = f"https://{options.server}/api/v4/"
        headers["Authorization"] = f"Bearer {options.auth}"

        userInfo = getUserFromName(options.user)
        teamInfo = getTeam(options.team)

        baseUserPath = os.path.join(options.output, options.user)
        baseUserFilePath = os.path.join(baseUserPath, "files/")

        os.makedirs(baseUserPath, mode=0o755, exist_ok=True)

        # Start Working
        allChannelsForUser = getChannelsForAUser(userInfo["id"], teamInfo["id"])
        allChannelsForUser.reverse()

        hitPublicChannel = False
        hitPrivateChannel = False
        hitDMChannel = False
        hitGroupMessages = False

        # Initialize PDF
        pdf = PDF(
            font_family_text=options.font_family_text,
            font_family_header_footer=options.font_family_header_footer,
            font_family_title=options.font_family_title,
            replace_unicode=options.replace_unicode,
            fallback_fonts=options.fallback_fonts,
        )
        if not options.no_downscale_images:
            pdf.oversized_images = "DOWNSCALE"
        pdf.add_page()
        pdf.set_auto_page_break(True, 15.0)

        publicChannels = []
        privateChannels = []
        groupChannels = []
        directMessageChannels = []

        channelGroupingsList = []

        for channel in allChannelsForUser:
            if channel["display_name"] not in options.exclude:
                if (not options.include) or (
                    channel["display_name"] in options.include
                ):
                    if (not options.public) and channel["type"] == "O":
                        publicChannels.append(channel)

                    if (not options.private) and channel["type"] == "P":
                        privateChannels.append(channel)

                    if (not options.dms) and channel["type"] == "D":
                        directMessageChannels.append(channel)

                    if (not options.group) and channel["type"] == "G":
                        groupChannels.append(channel)

        # Pre-process names in direct messages so we can sort by the other user"s name
        for channel in directMessageChannels:
            channel["full_name"] = directMessageOtherUserName(channel, userInfo["id"])

        # Sort alphabetical

        publicChannels = sorted(publicChannels, key=lambda i: i["name"])
        privateChannels = sorted(privateChannels, key=lambda i: i["name"])
        groupChannels = sorted(groupChannels, key=lambda i: i["name"])
        directMessageChannels = sorted(
            directMessageChannels, key=lambda i: i["full_name"]
        )

        channelGroupingsList = (
            publicChannels + privateChannels + groupChannels + directMessageChannels
        )

        if not channelGroupingsList:
            raise ChannelPostsException("No posts matched the export criteria")

        for channel in channelGroupingsList:
            messagesArray = []
            pinnedMessages = []

            # Setup Channel Name and Headers for printing
            setupChannelNameAndHeader(channel, userInfo["id"])

            if channel["type"] == "O" and hitPublicChannel == False:
                pdf.set_fill_color(255, 165, 0)
                pdf.start_section("PUBLIC CHANNELS")
                hitPublicChannel = True

            if channel["type"] == "P" and hitPrivateChannel == False:
                pdf.set_fill_color(255, 165, 0)
                pdf.start_section("PRIVATE CHANNELS")
                hitPrivateChannel = True

            if channel["type"] == "D" and hitDMChannel == False:
                pdf.set_fill_color(255, 165, 0)
                pdf.start_section("DIRECT MESSAGE CHANNELS")
                hitDMChannel = True

            if channel["type"] == "G" and hitGroupMessages == False:
                pdf.set_fill_color(255, 165, 0)
                pdf.start_section("GROUP MESSAGE CHANNELS")
                hitGroupMessages = True

            print(channelDisplayName)
            # File_object.write("## " + channelDisplayName + "\n\n")
            pdf.set_fill_color(255, 0, 0)
            pdf.start_section(f"Channel: {channelDisplayName}", level=1)
            # pdf.set_link(tableOfContents[channel["display_name"]])
            # pdf.multi_cell(0, 5, messageHeader, 0, "L", True)
            # pdf.ln()

            channelId = channel["id"]

            morePages = True
            channelPostsCounter = 0
            allPosts = []
            allPostsFull = []
            # Get all pages and append messages to one array.
            # We reverse this array before processing so order is from older to newest when printing

            while morePages:
                allPostsForChannel = getPostsForChannel(channelId, channelPostsCounter)

                postFiles = []

                if not allPostsForChannel["posts"]:
                    morePages = False

                channelPostsCounter += 1

                for key in allPostsForChannel["order"]:
                    allPosts.append(allPostsForChannel["posts"][key])

                allPostsFull.append(allPostsForChannel)

            # CACHE CHANNEL HERE
            channelCache[channelId] = {
                "channelName": channelDisplayName,
                "posts": allPostsFull,
            }

            # Reverse so it prints oldest to newest
            allPosts.reverse()

            # BEGIN POST PROCESSING
            # Loop over posts for channel
            for post in allPosts:
                pictures = []
                files = []

                message = post["message"]
                if isinstance(message, str):
                    postUserId = post["user_id"]

                    theUser = getUser(postUserId)

                    # Files
                    if "metadata" in post and "files" in post["metadata"]:
                        postFiles = post["metadata"]["files"]

                        if len(postFiles) > 0:
                            for file in postFiles:
                                # file["extension"] == "gif"
                                if file["extension"].lower() in imageExtenstions:
                                    pictures.append(file)
                                else:
                                    files.append(file)

                    postWithUserName = {
                        "name": theUser["first_name"] + " " + theUser["last_name"],
                        "message": message,
                        "time": str(
                            datetime.datetime.fromtimestamp(
                                post["create_at"] / 1000
                            ).strftime("%m/%d/%Y, %I:%M:%S %p")
                        ),
                        "pictures": pictures,
                        "files": files,
                        "post": post,
                    }

                    if post["is_pinned"] == True:
                        pinnedMessages.append(postWithUserName)

                    messagesArray.append(postWithUserName)

            print(f"Total Messages: {len(messagesArray) + 1}")

            if len(pinnedMessages) > 0:
                pdf.start_section("Pinned Messages", level=2)

            # Loop through Pinned messages first, to put them all at the front
            for message in pinnedMessages:
                userName = message["name"]
                singleMessage = message["message"]
                time = message["time"]

                # pdf.set_fill_color(220, 220, 220)
                pdf.set_fill_color(255, 165, 0)
                pdf.set_draw_color(255, 165, 0)
                _ = pdf.cell(
                    0,
                    5,
                    f"{
                        handleUnicode(
                            userName,
                            resolve_emoji_aliases=options.resolve_emoji_aliases,
                            replace_unicode=options.replace_unicode,
                        )
                    } {time} Pinned",
                    0,
                    align="L",
                    fill=True,
                )
                pdf.set_fill_color(255, 255, 255)
                pdf.ln()
                _ = pdf.multi_cell(
                    0,
                    5,
                    handleUnicode(
                        singleMessage,
                        resolve_emoji_aliases=options.resolve_emoji_aliases,
                        replace_unicode=options.replace_unicode,
                    ),
                    1,
                    align="L",
                    fill=True,
                    markdown=True,
                )
                # pdf.write_html(marko.convert(singleMessage))
                pdf.ln()

            pdf.set_draw_color(0, 0, 0)
            pdf.set_fill_color(220, 220, 220)
            pdf.start_section("Regular Messages", level=2)

            pdf.set_fill_color(255, 255, 255)
            for message in messagesArray:
                userName = message["name"]
                singleMessage = message["message"]
                time = message["time"]
                post = message["post"]

                if post["is_pinned"] == True:
                    pdf.set_fill_color(255, 165, 0)
                    pdf.set_draw_color(255, 165, 0)
                    _ = pdf.cell(
                        0,
                        5,
                        f"{
                            handleUnicode(
                                userName,
                                resolve_emoji_aliases=options.resolve_emoji_aliases,
                                replace_unicode=options.replace_unicode,
                            )
                        } {time} Pinned",
                        0,
                        align="L",
                        fill=True,
                    )
                    pdf.set_fill_color(255, 255, 255)

                    pdf.ln()
                    _ = pdf.multi_cell(
                        0,
                        5,
                        handleUnicode(
                            singleMessage,
                            resolve_emoji_aliases=options.resolve_emoji_aliases,
                            replace_unicode=options.replace_unicode,
                        ),
                        1,
                        align="L",
                        fill=True,
                        markdown=True,
                    )
                    pdf.ln()
                    pdf.set_draw_color(0, 0, 0)
                else:
                    pdf.set_fill_color(220, 220, 220)
                    _ = pdf.cell(
                        0,
                        5,
                        f"{
                            handleUnicode(
                                userName,
                                resolve_emoji_aliases=options.resolve_emoji_aliases,
                                replace_unicode=options.replace_unicode,
                            )
                        } {time}",
                        0,
                        align="L",
                        fill=True,
                    )
                    pdf.set_fill_color(255, 255, 255)
                    pdf.ln()
                    _ = pdf.multi_cell(
                        0,
                        5,
                        handleUnicode(
                            singleMessage,
                            resolve_emoji_aliases=options.resolve_emoji_aliases,
                            replace_unicode=options.replace_unicode,
                        ),
                        0,
                        align="L",
                        fill=True,
                        markdown=True,
                    )
                    pdf.ln()

                if options.images:
                    try:
                        userPicturesFilePath = os.path.join(baseUserFilePath, "pics/")
                        os.makedirs(userPicturesFilePath, 0o755, True)

                        for picture in message["pictures"]:
                            try:
                                # APPEND FILE ID TO PATH TO MAKE UNIQUE AND CACHE THIS
                                imagePath = os.path.join(
                                    userPicturesFilePath,
                                    f"{picture['id']}",
                                )
                                myImage = Path(imagePath)

                                if not myImage.exists():
                                    imageObj = getFile(picture["id"])

                                    with open(imagePath, "wb") as f:
                                        imageObj.raw.decode_content = True
                                        shutil.copyfileobj(imageObj.raw, f)

                                _ = pdf.image(
                                    imagePath,
                                    w=(pdf.epw * 0.75),
                                    alt_text=f"{picture['name']}",
                                )

                            except ImageException as ie:
                                print(f"Embed Image error: {ie}")
                                # traceback.print_exc()
                            except Exception as e:
                                print("Embed Image error: Couldn't add picture to PDF")
                                print(e)
                                # traceback.print_exc()

                    except ImageException as ie:
                        print(ie)

                if options.files:
                    try:
                        userAttachmentsFilePath = os.path.join(
                            baseUserFilePath, "files/"
                        )
                        os.makedirs(userAttachmentsFilePath, 0o755, True)

                        for aFile in message["files"]:
                            try:
                                filePath = os.path.join(
                                    userAttachmentsFilePath,
                                    f"{aFile['id']}_{aFile['name']}",
                                )
                                myFile = Path(filePath)

                                if not myFile.exists():
                                    fileObj = getFile(aFile["id"])

                                    with open(filePath, "wb") as f:
                                        fileObj.raw.decode_content = True
                                        shutil.copyfileobj(fileObj.raw, f)

                                if myFile.is_file():
                                    _ = pdf.embed_file(
                                        myFile, desc=aFile["name"], compress=True
                                    )
                                    _ = pdf.cell(
                                        30,
                                        5,
                                        "Attached file: ",
                                        0,
                                        align="L",
                                        fill=True,
                                    )
                                    pdf.set_text_color(0, 0, 255)
                                    _ = pdf.cell(
                                        0,
                                        5,
                                        f"{aFile['id']}_{aFile['name']}",
                                        0,
                                        align="L",
                                        fill=True,
                                    )

                            except FileException as fe:
                                print(f"Embed File error: {fe}")
                                # traceback.print_exc()
                            except Exception as e:
                                print("Embed File error: Couldn't add file to PDF")
                                print(e)
                                # traceback.print_exc()
                            finally:
                                pdf.set_text_color(0, 0, 0)
                                pdf.ln()

                    except ImageException as ie:
                        print(ie)
            print("\n")

        if options.filename:
            pdfOutput = os.path.join(baseUserPath, f"{options.filename}.pdf")
        else:
            pdfOutput = os.path.join(baseUserPath, f"{options.user}.pdf")

        print(pdfOutput)
        print()
        pdf.add_page()
        pdf.output(pdfOutput)

        if options.json:
            makeJsonFile(options.user)

    except Exception as e:
        print(e)
        # traceback.print_exc()


#########################
## MARK: Helper Functions
##


def check_font_is_core_font(font: str) -> str:
    """Checks if a font is one of the fpdf2 core fonts.

    Helper function for the argparse type parameter.
    """
    if font.lower() in fpdf.fonts.CORE_FONTS:
        return font

    print(
        f"The selected font '{font}' is not one of the PDF standard core fonts. Make sure it is installed on your system."
    )
    return font


@dataclasses.dataclass
class FontInfo:
    family: str
    path: pathlib.Path
    style: str


@dataclasses.dataclass
class FontCollectionInfo:
    index: int
    family: str
    path: pathlib.Path
    style: str


def find_system_fonts() -> dict[str, list[FontInfo | FontCollectionInfo]]:
    """Find the system wide installed fonts.

    Should work on Linux, Windows and MacOS.
    """

    def _get_font_info(path: pathlib.Path) -> FontInfo:
        font = TTFont(path)

        family = None
        style = None

        for record in font["name"].names:
            if record.nameID == 1:  # Font family
                family = record.toUnicode()
            elif record.nameID == 2:  # Font style
                style = record.toUnicode()

        assert family is not None
        assert style is not None

        return FontInfo(family=family, path=path, style=style)

    def _get_font_collection_info(path: pathlib.Path) -> list[FontCollectionInfo]:
        font_coll = TTCollection(path)

        font_coll_info = []
        for i, font in enumerate(font_coll.fonts):
            family = None
            subfamily = None
            for record in font["name"].names:
                if record.nameID == 1:
                    family = record.toUnicode()
                elif record.nameID == 2:
                    subfamily = record.toUnicode()

            assert family is not None
            assert subfamily is not None

            font_coll_info.append(
                FontCollectionInfo(family=family, path=path, style=subfamily, index=i)
            )

        return font_coll_info

    system = platform.system()

    if system == "Windows":
        font_roots = [pathlib.Path(r"C:\Windows\Fonts")]
    elif system == "Darwin":
        font_roots = [
            pathlib.Path("/System/Library/Fonts"),
            pathlib.Path("/Library/Fonts"),
            pathlib.Path.home() / "Library/Fonts",
        ]
    else:
        font_roots = [
            pathlib.Path("/usr/share/fonts"),
            pathlib.Path("/usr/local/share/fonts"),
            pathlib.Path.home() / ".local/share/fonts",
        ]

    fonts_paths = []
    font_collection_paths = []
    for font_root in font_roots:
        if font_root.exists():
            fonts_paths.extend(font_root.rglob("*.ttf"))
            fonts_paths.extend(font_root.rglob("*.otf"))
            font_collection_paths.extend(font_root.rglob("*.ttc"))

    fonts = {}
    for font_path in fonts_paths:
        font_info = _get_font_info(font_path)
        if font_info.family in fonts:
            fonts[font_info.family].append(font_info)
        else:
            fonts[font_info.family] = [font_info]
    for font_collection_path in font_collection_paths:
        font_collection_info = _get_font_collection_info(font_collection_path)
        for font_info in font_collection_info:
            if font_info.family in fonts:
                fonts[font_info.family].append(font_info)
            else:
                fonts[font_info.family] = [font_info]

    return fonts


def map_font_style_names(style: str) -> str:
    """Maps the style names from the ones in TTF files to the required ones for FPDF2.

    Returns
    -------
        _description_
    """
    style_lower = style.lower()
    fpdf_str = ""
    if "bold" in style_lower:
        fpdf_str += "B"
    if "italic" in style_lower or "oblique" in style_lower:
        fpdf_str += "I"
    return fpdf_str


def getUser(userID):
    """
    getUser

    Returns the user info for the given ID.

        @param userID The user ID to look up

    :raises:
        UserInfoException
    """
    if userID not in users:
        getUserResponse = requests.get(
            f"{mattermostURL}/users/{userID}", headers=headers
        )

        if getUserResponse.status_code != 200:
            raise UserInfoException(f"Failed to get user info for: {userID}")

        users[userID] = getUserResponse.json()

    return users[userID]


def getUserFromName(username):
    """
    getUserFromName

    Retrieves the user info for the username.

        @param username the username to look up.

    :raises:
        UserIDException
    """
    getUserIDResponse = requests.get(
        f"{mattermostURL}/users/username/{username}", headers=headers
    )

    if getUserIDResponse.status_code != 200:
        raise UserIDException(f"Failed to get user ID for: {username}")

    return getUserIDResponse.json()


def getTeam(team):
    """
    getTeamID

    Returns the ID for the team.

        @param team the team name to look up.

    :raises:
        TeamIDException
    """

    getTeamIDResponse = requests.get(
        f"{mattermostURL}/teams/name/{team}", headers=headers
    )

    if getTeamIDResponse.status_code != 200:
        raise TeamIDException(f"Failed to get team ID for: {team}")

    return getTeamIDResponse.json()


def getFile(fileID):
    """
    getFile

    Retrieves an attachement file from the server.

        @param fileID the attachment ID/

    :raises:
        FileException
    """

    getFileResponse = requests.get(
        f"{mattermostURL}/files/{fileID}", headers=headers, stream=True
    )

    if getFileResponse.status_code != 200:
        raise FileException(
            f"Failed to get file[{fileID}], status code: {getFileResponse.status_code}"
        )

    return getFileResponse


def getChannelsForAUser(userID, teamID):
    """
    getChannelsForAUser

    Get all Channels for a User

        @param userID
        @param teamID

    :raises:
        UserChannelsException
    """
    allChannelsForUserResponse = requests.get(
        f"{mattermostURL}/users/{userID}/teams/{teamID}/channels?include_deleted=false&last_delete_at=0",
        headers=headers,
    )

    if allChannelsForUserResponse.status_code != 200:
        raise UserChannelsException("Failed to get channels for user")

    return allChannelsForUserResponse.json()


def getPostsForChannel(channelID, channelPostsCounter):
    """
    getPostsForChannel

    Get all Posts for a Channels

        @param channelID
        @param channelPostsCounter

    :raises:
        ChannelPostsException
    """
    getPostsForChannelResponse = requests.get(
        f"{mattermostURL}channels/{channelID}/posts?page={channelPostsCounter}",
        headers=headers,
    )

    if getPostsForChannelResponse.status_code != 200:
        raise ChannelPostsException("Failed to get posts for channels")

    return getPostsForChannelResponse.json()


def setupChannelNameAndHeader(channel, userID):
    global messageHeader
    global channelDisplayName

    channelDisplayName = channel["display_name"]
    # Direct messsages
    # if len(channel["display_name"]) == 0:
    if channel["type"] == "D":
        nameSplit = channel["name"].split("__")
        firstPerson = getUser(nameSplit[0])
        firstPersonFirstName = firstPerson["first_name"]
        firstPersonLastName = firstPerson["last_name"]
        firstPersonUserId = nameSplit[0]

        secondPerson = getUser(nameSplit[1])
        secondPersonFirstName = secondPerson["first_name"]
        secondPersonLastName = secondPerson["last_name"]
        secondPersonUserId = nameSplit[1]

        if firstPersonUserId == userID:
            otherPersonFirstName = secondPersonFirstName
            otherPersonLastName = secondPersonLastName
        else:
            otherPersonFirstName = firstPersonFirstName
            otherPersonLastName = firstPersonLastName

        messageHeader = "DM with " + otherPersonFirstName + " " + otherPersonLastName
        channelDisplayName = messageHeader
    else:
        # If MM Group message
        if channel["type"] == "G":
            # Get Channel Members:
            names = getChannelMembersFn(channel)

            messageHeader = "Group Message between: " + names
            channelDisplayName = messageHeader
        # Public/Private Channels
        else:
            messageHeader = channelDisplayName


def directMessageOtherUserName(channel, userID):
    nameSplit = channel["name"].split("__")
    firstPerson = getUser(nameSplit[0])
    firstPersonFirstName = firstPerson["first_name"]
    firstPersonLastName = firstPerson["last_name"]
    firstPersonUserId = nameSplit[0]

    secondPerson = getUser(nameSplit[1])
    secondPersonFirstName = secondPerson["first_name"]
    secondPersonLastName = secondPerson["last_name"]
    secondPersonUserId = nameSplit[1]

    if firstPersonUserId == userID:
        return secondPersonFirstName + secondPersonLastName
    else:
        return firstPersonFirstName + firstPersonLastName


def getChannelMembersFn(channel):
    channelMembersCounter = 0
    morePages = True
    names = ""
    while morePages:
        getChannelMembers = (
            f"/channels/{channel['id']}/members?page={channelMembersCounter}"
        )
        getChannelMembersResponse = requests.get(
            mattermostURL + getChannelMembers, headers=headers
        )

        if getChannelMembersResponse.status_code != 200:
            raise ChannelPostsException("ERROR: Getting all posts for channel")

        channelMembers = getChannelMembersResponse.json()

        channelMembersCounter += 1

        channelMembersLoopCounter = 0
        for member in channelMembers:
            user = getUser(member["user_id"])

            if channelMembersLoopCounter == len(channelMembers) - 1:
                names += "and " + user["first_name"] + " " + user["last_name"]
            else:
                names += user["first_name"] + " " + user["last_name"] + ", "

            channelMembersLoopCounter += 1

        if len(channelMembers) == 0:
            morePages = False
            break
    return names


def handleUnicode(
    text: str, *, resolve_emoji_aliases: bool = False, replace_unicode: bool = False
) -> str:
    """Handles unicode strings.

    Parameters
    ----------
    text
        The original text
    resolve_emoji_aliases
        Whether emoji aliases like `:+1:`, `:thumps_up:`, … should be resolved.
    replace_unicode
        Whether unicode should be replaced by latin-1 encoding.

    Returns
    -------
        _description_
    """
    if resolve_emoji_aliases and replace_unicode:
        raise ValueError(
            "resolve_emoji_aliases and replace_unicode cannot be used at the same time."
        )

    if replace_unicode:
        return text.encode("latin-1", "replace").decode("latin-1")

    if resolve_emoji_aliases:
        return emoji.emojize(text, language="alias")

    return text


class PDF(fpdf.FPDF):
    def __init__(
        self,
        font_family_text: str,
        font_family_header_footer: str,
        font_family_title: str,
        fallback_fonts: list[str],
        *,
        replace_unicode: bool,
    ):
        super().__init__()

        self._font_families = {
            "text": font_family_text,
            "header_footer": font_family_header_footer,
            "title": font_family_title,
        }

        system_fonts = find_system_fonts()

        # If set font is not a core font load it from system fonts
        for ff in list(self._font_families.values()) + fallback_fonts:
            if not ff.lower() in fpdf.fonts.CORE_FONTS:
                if not ff in system_fonts:
                    raise OptionsException(
                        f"Font '{ff}' is neither a core font nor has been found in the system wide installed fonts"
                    )
                for fs in system_fonts[ff]:
                    match fs:
                        case FontInfo():
                            self.add_font(
                                family=fs.family,
                                style=map_font_style_names(fs.style),
                                fname=fs.path,
                            )
                        case FontCollectionInfo():
                            self.add_font(
                                family=fs.family,
                                style=map_font_style_names(fs.style),
                                fname=fs.path,
                                collection_font_number=fs.index,
                            )

        self.set_font(self._font_families["text"], "", 10)

        self.set_section_title_styles(
            level0=fpdf.TextStyle(
                font_family=self._font_families["title"],
                font_style="B",
                font_size_pt=24,
                color=(0, 0, 0),
                underline=True,
                t_margin=5,
                l_margin=0,
                b_margin=5,
            ),
            level1=fpdf.TextStyle(
                font_family=self._font_families["title"],
                font_style="B",
                font_size_pt=20,
                color=(0, 0, 0),
                underline=True,
                t_margin=5,
                l_margin=0,
                b_margin=5,
            ),
            level2=fpdf.TextStyle(
                font_family=self._font_families["title"],
                font_style="B",
                font_size_pt=15,
                color=(255, 165, 0),
                underline=True,
                t_margin=5,
                l_margin=0,
                b_margin=5,
            ),
        )
        self.set_fallback_fonts(fallback_fonts, exact_match=False)

    def header(self):
        self.set_font(self._font_families["header_footer"], style="I", size=8)

        if channelDisplayName:
            _ = self.multi_cell(w=0, text=f"Channel: {channelDisplayName}", align="R")

        # Line break
        self.ln(10)

    def footer(self):
        # Go to 1.5 cm from bottom
        self.set_y(-15)
        self.set_font(self._font_families["header_footer"], style="I", size=8)
        # Print centered page number
        _ = self.cell(0, 10, f"Page {self.page_no()}", 0, align="C")


def makeJsonFile(username):
    """
    makeJsonFile

    Export the messages as JSON

        @param username

    """
    ## PRINT STATEMENT FOR JSON FILE NEEDED
    jsonPath = os.path.join(baseUserPath, f"{username}.gz")
    print("Writing JSON to file")
    print(jsonPath)
    with gzip.open(jsonPath, "wt", encoding="ascii") as zipfile:
        json.dump(channelCache, zipfile)


if __name__ == "__main__":
    main()
