import argparse
import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich import box
from rich_argparse import RichHelpFormatter
from anki_niobium.io import niobium
from anki_niobium.theme import S, set_theme

console = Console()


def _load_theme_early():
    """Load just the theme setting from config before full init."""
    from pathlib import Path
    import yaml
    for cfg in [
        Path.home() / ".config" / "niobium" / "config.yaml",
        Path.home() / ".config" / "niobium" / "config.yml",
        Path(__file__).parent / "default_config.yaml",
    ]:
        if cfg.is_file():
            try:
                with open(cfg) as f:
                    data = yaml.safe_load(f)
                if data and data.get("theme"):
                    set_theme(data["theme"])
            except Exception:
                pass
            break

_load_theme_early()


_BANNER_TEMPLATE = r"""
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
[#5FBAE6]⠀⠀⠀⠀⢸⣿⣤⣴⣾⠿⠛⠉⠀⠉⠛⠿⣷⣶⣤⣿⣷[/#5FBAE6] [{tagline}] Putting AI in Anki. For free.  [/{tagline}]
[#5FBAE6]⠀⠀⠀⠀⠘⠛⠛⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⠛⠃[/#5FBAE6] [{subtitle}] Because making 200 flashcards[/{subtitle}]
                      [{subtitle}] by hand is not high-yield.[/{subtitle}]
[{S.muted}][/{S.muted}]
"""


def show_banner():
    banner = _BANNER_TEMPLATE.format(
        tagline=S.banner_tagline,
        subtitle=S.banner_subtitle,
        S=S,
    )
    banner_text = Text.from_markup(banner.strip())
    panel = Align(Panel.fit(
        banner_text,
        subtitle="[bold bright_cyan]N[/bold bright_cyan]adia's [bold bright_cyan]I[/bold bright_cyan]mage [bold bright_cyan]O[/bold bright_cyan]cclusion [bold bright_cyan]B[/bold bright_cyan]ooster [bold bright_cyan]I[/bold bright_cyan]s [bold bright_cyan]U[/bold bright_cyan]n[bold bright_cyan]M[/bold bright_cyan]anned",
        border_style="sky_blue3",
        box=box.ROUNDED,
        padding=(0, 2),
    ), align="center")
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
        console.print(f"[{S.success}]Cache cleared ({s['processed']} processed entries, {s['claude_cache']} Claude responses)[/{S.success}]")
        console.print(f"[{S.muted}]{CACHE_DB}[/{S.muted}]")
        return

    ap = argparse.ArgumentParser(formatter_class=RichHelpFormatter)

    # Config management
    config_group = ap.add_argument_group("config management")
    config_group.add_argument("--init-config", action="store_true", default=False,
        help="create a config file at ~/.config/niobium/config.yaml")
    config_group.add_argument("--edit-config", action="store_true", default=False,
        help="open the config directory in Finder")
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

    # Output — mutually exclusive; optional when work_dir is configured
    group2 = ap.add_mutually_exclusive_group(required=False)
    group2.add_argument("-deck", "--deck-name", type=str, default=None,
        help="anki deck where the notes will be pushed to (requires anki-connect)")
    group2.add_argument("-pout", "--pdf-img-out", type=str, default=None,
        help="output dir where pdf extracted images will be saved (required IF --single-pdf is passed)")
    group2.add_argument("-apkg", "--apkg-out", type=str, default=None, nargs='?', const='__default__',
        help="output dir for .apkg file (defaults to work_dir/outputs if no path given)")

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
        help="path to config file (default: ~/.config/niobium/config.yaml, then bundled default)")
    ap.add_argument("--smart", action="store_true", default=False,
        help="use Claude AI for smart filtering or card generation (requires ANTHROPIC_API_KEY)")
    ap.add_argument("--generate", "-gen", action="store_true", default=False,
        help="generation-first mode: Claude sees the full image and generates cards from scratch (requires --smart)")
    ap.add_argument("--page", type=str, default=None,
        help="page or page range for PDF input, e.g. '5' or '5-10' (requires -pin)")
    ap.add_argument("--max-cards", type=int, default=None,
        help="max number of cards to generate per page/image (requires --smart with --page or --generate)")
    ap.add_argument("--card-type", type=str, default=None, choices=["cloze", "basic", "image_occlusion"],
        help="force a specific card type (requires --smart with --page or --generate)")
    ap.add_argument("--no-cache", action="store_true", default=False,
        help="skip the cache for this run (does not clear existing cache)")
    args = vars(ap.parse_args())

    if args.get('page') and not args.get('single_pdf'):
        ap.error("--page requires -pin/--single-pdf")
    if args.get('generate') and not args.get('smart'):
        ap.error("--generate requires --smart")
    # Default to all pages when --generate + -pin but no --page
    if args.get('generate') and args.get('single_pdf') and not args.get('page'):
        import fitz
        doc = fitz.Document(args['single_pdf'])
        total = doc.page_count
        doc.close()
        args['page'] = f"1-{total}"

    # Resolve default output directory from work_dir when needed
    needs_default = (
        (not args.get('deck_name') and not args.get('pdf_img_out') and not args.get('apkg_out'))
        or args.get('apkg_out') == '__default__'
    )
    if needs_default:
        cfg_path = niobium.resolve_config(args.get("config"))
        cfg = niobium.load_config(cfg_path)
        work_dir_cfg = cfg.get("work_dir")
        if work_dir_cfg:
            default_out = os.path.join(os.path.expanduser(work_dir_cfg), "outputs")
            os.makedirs(default_out, exist_ok=True)
            args['apkg_out'] = default_out
            console.print(f"[{S.accent}]Output: {default_out}[/{S.accent}]")
        else:
            ap.error("No output specified. Use -deck, -apkg PATH, or -pout PATH (or set work_dir in config).")
        # Pass resolved config path to avoid resolving twice
        args['config'] = cfg_path

    nb = niobium(args)

    if nb.smart:
        nb.confirm_smart_instructions()

    # Determine if we're in generation-first mode
    # --generate flag for images, or --smart --page for PDFs (implicit generate)
    is_generate = nb.generate or (nb.smart and nb.page and args.get('single_pdf'))

    if args['pdf_img_out']:
        if args['single_pdf'] == None:
            raise Exception('--single-pdf must be passed for --pdf-img-out')
        import fitz
        doc = fitz.Document(args['single_pdf'])
        page_set = niobium.parse_page_range(nb.page, doc.page_count, doc=doc) if nb.page else None
        doc.close()
        nb.extract_images_from_pdf(args['single_pdf'],args['pdf_img_out'],pages=page_set)
    elif args['apkg_out']:
        if is_generate:
            nb.smart_generate_export_apkg()
        else:
            nb.export_apkg()
    elif args['basic_type']:
        nb.pdf_to_basic(args['directory'],args['deck_name'])
    else:
        if is_generate:
            nb.smart_generate_to_deck()
        else:
            nb.ocr4io()

if __name__ == "__main__":
    main()
