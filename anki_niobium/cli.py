import argparse
import sys
from rich.console import Console
from anki_niobium.io import niobium

console = Console()

def main():
    if '--init-config' in sys.argv:
        niobium.init_config()
        return

    if '--edit-config' in sys.argv:
        niobium.edit_config()
        return

    ap = argparse.ArgumentParser()
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

    ap.add_argument("-ioid", "--io-model-id", type=bool, default=None,
        help="ID of the built-in Image Occlusion model in anki (optional, to be used with --apkg-out)")
    ap.add_argument("-m", "--merge-rects", type=bool, default=None,
        help="whether or not to merge detected rectangles in close proximity (default from config)")
    ap.add_argument("-mx", "--merge-lim-x", type=int, default=None,
        help="merges boxes horizontally if the distance is smaller than the specified # pixels (default from config)")
    ap.add_argument("-my", "--merge-lim-y", type=int, default=None,
        help="merges boxes vertically if the distance is smaller than the specified # pixels (default from config)")
    ap.add_argument("-l", "--langs", type=str, default=None,
        help="comma separated list of languages to OCR (default from config)")
    ap.add_argument("-g", "--gpu", type=int, default=None,
        help="whether or not GPU should be used (default from config)")
    ap.add_argument("-hdr", "--add-header", type=bool, default=False,
        help="whether or not to add filename as header.")
    ap.add_argument("-basic", "--basic-type", type=bool, default=False,
        help="whether or not add basic cards")
    ap.add_argument("-c", "--config", type=str, default=None,
        help="path to config.json (default: ~/.config/niobium/config.json, then bundled default)")
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
