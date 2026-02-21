import argparse
import sys
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich import box
from rich_argparse import RichHelpFormatter
from anki_niobium.io import niobium

console = Console()

BANNER = r"""
[#5FBAE6]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣤⣦⣤ [/#5FBAE6]
[#5FBAE6]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⣿⣿⣿⣧[/#5FBAE6]
[#5FBAE6]⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⣿⠃⠀⠙⣿⣧[/#5FBAE6]
[#5FBAE6]⠀⠀⠀⠀⠀⠀⠀⠀⣰⣿⠃⠀⠀⠀⠘⣿⣆⡀[/#5FBAE6]
[#5FBAE6]⣠⣤⣴⣶⣶⣾⠿⠿⠿⠃⠀⠀⠀⠀⠀⠈⠻⠿⣿⣷⣶⣶⣦⣤⣄[/#5FBAE6]
[#5FBAE6]⢻⣿⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢉⣹⣿⡟[/#5FBAE6]
[#5FBAE6]⠀⠙⢿⣷⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⡿⠋[/#5FBAE6]
[#5FBAE6]⠀⠀⠀⠙⢿⣷⡀⠀⠀⠀[bold bright_cyan]Nb41[/bold bright_cyan]⠀⠀⠀⠀⢀⣾⡿⠋[/#5FBAE6]
[#5FBAE6]⠀⠀⠀⠀⠀⣿⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢼⣿[/#5FBAE6]  [bold bright_cyan] ╔╗╔[/bold bright_cyan] [bold bright_cyan]╦[/bold bright_cyan] [bold bright_cyan]╔═╗[/bold bright_cyan] [bold bright_cyan]╔╗ [/bold bright_cyan] [bold bright_cyan]╦[/bold bright_cyan] [bold bright_cyan]╦ ╦[/bold bright_cyan] [bold bright_cyan]╔╦╗[/bold bright_cyan] [bold sky_blue3]╔═╗╦[/bold sky_blue3]
[#5FBAE6]⠀⠀⠀⠀⠀⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿[/#5FBAE6]  [bold bright_cyan] ║║║[/bold bright_cyan] [bold bright_cyan]║[/bold bright_cyan] [bold bright_cyan]║ ║[/bold bright_cyan] [bold bright_cyan]╠╩╗[/bold bright_cyan] [bold bright_cyan]║[/bold bright_cyan] [bold bright_cyan]║ ║[/bold bright_cyan] [bold bright_cyan]║║║[/bold bright_cyan] [bold sky_blue3]╠═╣║[/bold sky_blue3]
[#5FBAE6]⠀⠀⠀⠀⢸⣿⠁⠀⠀⣄⣤⣴⣶⣦⣤⣀⠀⠀⠸⣿⡆[/#5FBAE6] [bold bright_cyan] ╝╚╝[/bold bright_cyan] [bold bright_cyan]╩[/bold bright_cyan] [bold bright_cyan]╚═╝[/bold bright_cyan] [bold bright_cyan]╚═╝[/bold bright_cyan] [bold bright_cyan]╩[/bold bright_cyan] [bold bright_cyan]╚═╝[/bold bright_cyan] [bold bright_cyan]╩ ╩[/bold bright_cyan] [bold sky_blue3]╩ ╩╩[/bold sky_blue3]
[#5FBAE6]⠀⠀⠀⠀⢸⣿⣤⣴⣾⠿⠛⠉⠀⠉⠛⠿⣷⣶⣤⣿⣷[/#5FBAE6] [white bold] Putting AI in Anki. For free.  [/white bold]
[#5FBAE6]⠀⠀⠀⠀⠘⠛⠛⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⠛⠃[/#5FBAE6] [dim light_steel_blue1 italic] Because making 200 flashcards[/dim light_steel_blue1 italic]
                      [dim light_steel_blue1 italic] by hand is not high-yield.[/dim light_steel_blue1 italic]
[dim green][/dim green]
"""


def show_banner():
    banner_text = Text.from_markup(BANNER.strip())
    panel = Align(Panel.fit(
        banner_text,
        subtitle="[white][bold bright_cyan]N[/bold bright_cyan]adia's [bold bright_cyan]I[/bold bright_cyan]mage [bold bright_cyan]O[/bold bright_cyan]cclusion [bold bright_cyan]B[/bold bright_cyan]ooster [bold bright_cyan]I[/bold bright_cyan]s [bold bright_cyan]U[/bold bright_cyan]n[bold bright_cyan]M[/bold bright_cyan]anned[/white]",
        border_style="sky_blue3",
        box=box.ROUNDED,
        padding=(0, 2),
    ),align="center")
    console.print(panel)
    console.print()

def main():
    show_banner()

    # Pre-parse for standalone config commands before full argument validation
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--init-config", action="store_true", default=False)
    pre.add_argument("--edit-config", action="store_true", default=False)
    pre.add_argument("--clear-cache", action="store_true", default=False)
    early, _ = pre.parse_known_args()

    if early.init_config:
        niobium.init_config()
        return
    if early.edit_config:
        niobium.edit_config()
        return
    if early.clear_cache:
        from anki_niobium.cache import clear_all, stats, CACHE_DB
        s = stats()
        clear_all()
        console.print(f"[green]Cache cleabright_cyan ({s['processed']} processed entries, {s['claude_cache']} Claude responses)[/green]")
        console.print(f"[dim]{CACHE_DB}[/dim]")
        return

    ap = argparse.ArgumentParser(formatter_class=RichHelpFormatter)

    # Config management
    config_group = ap.add_argument_group("config management")
    config_group.add_argument("--init-config", action="store_true", default=False,
        help="create a config file at ~/.config/niobium/config.json")
    config_group.add_argument("--edit-config", action="store_true", default=False,
        help="open the config file in $EDITOR")
    config_group.add_argument("--clear-cache", action="store_true", default=False,
        help="clear the processing cache and exit")

    # This group requires an input
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("-i", "--image", type=str,
        help="abs path to a single image")
    group.add_argument("-dir", "--directory", type=str,
        help="directory containing multiple images")
    group.add_argument("-pin", "--single-pdf", type=str, default=None,
        help="abs path to a single PDF")

    # This group requires a type of output
    group2 = ap.add_mutually_exclusive_group(required=True)
    group2.add_argument("-deck", "--deck-name", type=str, default='Default',
        help="anki deck where the notes will be pushed to (requires anki-connect) (default Default)")
    group2.add_argument("-pout", "--pdf-img-out", type=str, default=None,
        help="output dir where pdf extracted images will be saved (required IF --single-pdf is passed)")
    group2.add_argument("-apkg", "--apkg-out", type=str, default=None,
        help="output dir where apkg file will be saved")

    # Config-managed args — still accepted via CLI but hidden from help
    ap.add_argument("-ioid", "--io-model-id", type=bool, default=None, help=argparse.SUPPRESS)
    ap.add_argument("-m", "--merge-rects", type=bool, default=None, help=argparse.SUPPRESS)
    ap.add_argument("-mx", "--merge-lim-x", type=int, default=None, help=argparse.SUPPRESS)
    ap.add_argument("-my", "--merge-lim-y", type=int, default=None, help=argparse.SUPPRESS)
    ap.add_argument("-l", "--langs", type=str, default=None, help=argparse.SUPPRESS)
    ap.add_argument("-g", "--gpu", type=int, default=None, help=argparse.SUPPRESS)

    ap.add_argument("-hdr", "--add-header", type=bool, default=False,
        help="whether or not to add filename as header.")
    ap.add_argument("-basic", "--basic-type", type=bool, default=False,
        help="whether or not add basic cards")
    ap.add_argument("-c", "--config", type=str, default=None,
        help="path to config.json (default: ~/.config/niobium/config.json, then bundled default)")
    ap.add_argument("--smart", action="store_true", default=False,
        help="use Claude Vision to intelligently filter OCR results (requires ANTHROPIC_API_KEY)")
    ap.add_argument("--no-cache", action="store_true", default=False, help=argparse.SUPPRESS)
    args = vars(ap.parse_args())
    nb = niobium(args)

    if args['pdf_img_out']:
        """
        Enable users to use niobium just to extract images from a PDF.
        """
        if args['single_pdf'] == None:
            raise Exception('--single-pdf must be passed for --pdf-img-out')
        console.print('[cyan]PDF image export mode.[/cyan]')
        nb.extract_images_from_pdf(args['single_pdf'],args['pdf_img_out'])
    elif args['apkg_out']:
        console.print('[cyan]APKG export mode.[/cyan]')
        nb.export_apkg()
    elif args['basic_type']:
        nb.pdf_to_basic(args['directory'],args['deck_name'])
    else:
        """
        Perform optical character recognition for image occlusion (ocr4io).
        """
        nb.ocr4io()

if __name__ == "__main__":
    main()
