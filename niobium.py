import argparse
from niobium.io import niobium

def main():
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
    ap.add_argument("-m", "--merge-rects", type=bool, default=True,
        help="whether or not to merge detected rectangles in close proximity (default True)")
    ap.add_argument("-mx", "--merge-lim-x", type=int, default=10,
        help="merges boxes horizontally if the distance is smaller than the specified # pixels (default 10)")
    ap.add_argument("-my", "--merge-lim-y", type=int, default=10,
        help="merges boxes vertically if the distance is smaller than the specified # pixels (default 10)")
    ap.add_argument("-l", "--langs", type=str, default="en",
        help="comma separated list of languages to OCR (default en)")
    ap.add_argument("-g", "--gpu", type=int, default=-1,
        help="whether or not GPU should be used (default -1, no GPU)")
    ap.add_argument("-hdr", "--add-header", type=bool, default=False,
        help="whether or not to add filename as header.")
    ap.add_argument("-basic", "--basic-type", type=bool, default=False,
        help="whether or not add basic cards")
    args = vars(ap.parse_args())
    nb = niobium(args)

    if args['pdf_img_out']:
        """
        Enable users to use niobium just to extract images from a PDF.
        """
        if args['single_pdf'] == None:
            raise Exception('--single-pdf must be passed for --pdf-img-out')
        print('[INFO] --> PDF image export mode.')
        nb.extract_images_from_pdf(args['single_pdf'],args['pdf_img_out'])
    elif args['basic_type']:
        nb.pdf_to_basic(args['directory'],args['deck_name'])
    else:
        """
        Perform optical character recognition for image occlusion (ocr4io).
        """
        nb.ocr4io()

if __name__ == "__main__":
    main()