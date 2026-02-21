import requests
import base64
import numpy as np
from easyocr import Reader
from PIL import Image, ImageDraw
from hashlib import blake2b
import time
import os
import json
import re
import fitz
from tqdm import tqdm
from io import BytesIO
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm
from datetime import datetime
import random
import genanki

from anki_niobium.cache import content_hash_file, content_hash_bytes, is_processed, mark_processed

ANKI_LOCAL = "http://localhost:8765"
console = Console()

class niobium:
    def __init__(self, args):
        self.args = args
        self.config_path = niobium.resolve_config(self.args.get("config"))
        self.config = niobium.load_config(self.config_path)

        merge_cfg = self.config.get("merge", {})
        self.merge_enabled = self.args.get("merge_rects") if self.args.get("merge_rects") is not None else merge_cfg.get("enabled", True)
        self.merge_lim_x = self.args.get("merge_lim_x") if self.args.get("merge_lim_x") is not None else merge_cfg.get("limit_x", 10)
        self.merge_lim_y = self.args.get("merge_lim_y") if self.args.get("merge_lim_y") is not None else merge_cfg.get("limit_y", 10)

        self.langs = self.args.get("langs") if self.args.get("langs") is not None else self.config.get("langs", "en")
        self.gpu = self.args.get("gpu") if self.args.get("gpu") is not None else self.config.get("gpu", -1)
        self.smart = self.args.get("smart", False)
        self.qc = self.config.get("qc", False)
        self.no_cache = self.args.get("no_cache", False)

    @staticmethod
    def load_config(config_path):
        with open(config_path) as f:
            return json.load(f)

    @staticmethod
    def resolve_config(config_path=None):
        if config_path:
            p = Path(config_path)
            if not p.is_file():
                raise FileNotFoundError(f"Config file not found: {config_path}")
            console.print(f'[cyan]Using config: {p}[/cyan]')
            return str(p)

        user_config = Path.home() / ".config" / "niobium" / "config.json"
        if user_config.is_file():
            console.print(f'[cyan]Using config: {user_config}[/cyan]')
            return str(user_config)

        default_config = Path(__file__).parent / "default_config.json"
        console.print(f'[cyan]Using config: {default_config} (bundled default)[/cyan]')
        return str(default_config)

    @staticmethod
    def init_config():
        import shutil
        dest = Path.home() / ".config" / "niobium" / "config.json"
        if dest.is_file():
            console.print(f'[cyan]Config already exists: {dest}[/cyan]')
            console.print('[cyan]Edit this file to customize filtering rules.[/cyan]')
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        src = Path(__file__).parent / "default_config.json"
        shutil.copy2(src, dest)
        console.print(f'[bold green]Config created: {dest}[/bold green]')
        console.print('[cyan]Edit this file to customize filtering rules.[/cyan]')
        return dest

    @staticmethod
    def edit_config():
        import subprocess
        dest = niobium.init_config()
        subprocess.call(["open", str(dest.parent)])

    def ocr4io(self):
        """
        Optical Charancter Recognition for Image Occlusion
        Image Occlusion entry
        """
        #print(self)
        if self.deck_exists(self.args["deck_name"]):
            console.print(f'[cyan]Found Anki deck named {self.args["deck_name"]}[/cyan]')
        else:
            if Confirm.ask(f'Deck [bold]{self.args["deck_name"]}[/bold] not found. Create?', default=True):
                self.create_deck(self.args["deck_name"])
            else:
                raise Exception('Cannot create notes without a deck. Terminating ...')

        if self.args['image'] != None:
            # Single image
            results, H, W, image_bytes = self.ocr_single_image(self.args["image"], self.langs, self.gpu)
            if self.merge_enabled:
                results = self.merge_boxes(results, (self.merge_lim_x, self.merge_lim_y))
            if self.smart:
                from anki_niobium.llm import smart_filter_results
                results, extra = smart_filter_results(results, image_bytes, {**self.config, "_no_cache": self.no_cache})
            else:
                results, extra = self.filter_results(results, self.config)
            occlusion = self.get_occlusion_coords(results, H, W)
            status = self.add_image_occlusion_deck(self.args["image"], occlusion, self.args["deck_name"], extra, None,self.args["add_header"])
            console.print(status[1])
            c_hash = content_hash_file(self.args["image"])
            mark_processed(c_hash, self.args["image"])
            if self.qc:
                opdir = os.path.join(os.path.dirname(os.path.abspath(self.args["image"])), 'niobium-io')
                if not os.path.exists(opdir):
                    os.makedirs(opdir)
                self.save_qc_image(results, self.args["image"], path=opdir, image_in=None)
        elif self.args['directory'] != None:
            # Batch process
            console.print(f"[cyan]Starting batch processing {self.args['directory']}[/cyan]")
            opdir = os.path.join(self.args['directory'], 'niobium-io')
            console.print(f"[dim]{opdir}[/dim]")
            if not os.path.exists(opdir):
                os.makedirs(opdir)
            img_list = self.get_images_in_directory(self.args['directory'])
            console.print(f"[cyan]{len(img_list)} images found[/cyan]")
            it = 1
            skipped = 0
            for img_path in img_list:
                console.print(f"[dim]\\[{it}/{len(img_list)}][/dim]")
                c_hash = content_hash_file(img_path)
                if not self.no_cache and is_processed(c_hash):
                    console.print(f"[dim]Skipping {os.path.basename(img_path)} (already processed)[/dim]")
                    skipped += 1
                    it += 1
                    continue
                results, H, W, image_bytes = self.ocr_single_image(img_path, self.langs, self.gpu)
                if self.merge_enabled:
                    results = self.merge_boxes(results, (self.merge_lim_x, self.merge_lim_y))
                if self.smart:
                    from anki_niobium.llm import smart_filter_results
                    results, extra = smart_filter_results(results, image_bytes, {**self.config, "_no_cache": self.no_cache})
                else:
                    results, extra = self.filter_results(results, self.config)
                occlusion = self.get_occlusion_coords(results, H, W)
                status = self.add_image_occlusion_deck(img_path, occlusion, self.args["deck_name"], extra, None,self.args["add_header"])
                console.print(status[1])
                mark_processed(c_hash, img_path)
                if self.qc:
                    self.save_qc_image(results, img_path, path=opdir, image_in=None)
                it += 1
            if skipped:
                console.print(f"[dim]{skipped} image(s) skipped (already in cache)[/dim]")
        elif self.args['single_pdf'] != None:
            console.print("[cyan]Extracting images from the PDF[/cyan]")
            opdir = os.path.dirname(os.path.abspath(self.args['single_pdf']))
            opdir = os.path.join(opdir, 'niobium-io')
            if not os.path.exists(opdir):
                os.makedirs(opdir)
            console.print(f"[cyan]Preview images will be saved at {opdir}[/cyan]")
            all_images = self.extract_images_from_pdf(self.args['single_pdf'])
            console.print(f"[cyan]{len(all_images)} images were extracted from the PDF.[/cyan]")
            it = 1
            skipped = 0
            for im in all_images:
                console.print(f"[dim]\\[{it}/{len(all_images)}][/dim]")
                im_bytes = niobium.byte_convert(im)
                c_hash = content_hash_bytes(im_bytes)
                if not self.no_cache and is_processed(c_hash):
                    console.print(f"[dim]Skipping PDF image {it} (already processed)[/dim]")
                    skipped += 1
                    it += 1
                    continue
                results, H, W, image_bytes = self.ocr_single_image(None, self.langs, self.gpu, im)
                if self.merge_enabled:
                    results = self.merge_boxes(results, (self.merge_lim_x, self.merge_lim_y))
                if self.smart:
                    from anki_niobium.llm import smart_filter_results
                    results, extra = smart_filter_results(results, image_bytes, {**self.config, "_no_cache": self.no_cache})
                else:
                    results, extra = self.filter_results(results, self.config)
                occlusion = self.get_occlusion_coords(results, H, W)
                status = self.add_image_occlusion_deck(None, occlusion, self.args["deck_name"], extra, im,self.args["add_header"])
                console.print(status[1])
                mark_processed(c_hash, f"pdf:{os.path.basename(self.args['single_pdf'])}")
                if self.qc:
                    self.save_qc_image(results, None, path=opdir, image_in=im)
                it += 1
            if skipped:
                console.print(f"[dim]{skipped} image(s) skipped (already in cache)[/dim]")

    def export_apkg(self):
        """
        Export image occlusion notes as an .apkg file using genanki.
        Does not require AnkiConnect or a running Anki instance.
        """
        IO_MODEL = genanki.Model(
            1607392319,
            'Image Occlusion',
            fields=[
                {'name': 'Occlusion'},
                {'name': 'Image'},
                {'name': 'Header'},
                {'name': 'Back Extra'},
                {'name': 'Comments'},
            ],
            templates=[{
                'name': 'Cloze',
                'qfmt': '{{cloze:Occlusion}}<br>{{Image}}',
                'afmt': '{{cloze:Occlusion}}<br>{{Image}}<br><hr id=answer>{{Back Extra}}',
            }],
            css='.card { text-align: center; }',
            model_type=genanki.Model.CLOZE,
        )

        deck_name = self.args.get('deck_name') or 'Niobium Export'
        deck = genanki.Deck(random.randrange(1 << 30, 1 << 31), deck_name)
        media_files = []

        def process_image(image_name, image_in=None, is_batch=False):
            # Cache check: skip in batch context
            if image_name:
                c_hash = content_hash_file(image_name)
            else:
                c_hash = content_hash_bytes(niobium.byte_convert(image_in))
            if is_batch and not self.no_cache and is_processed(c_hash):
                console.print(f'[dim]Skipping (already processed)[/dim]')
                return True  # skipped

            results, H, W, image_bytes = self.ocr_single_image(image_name, self.langs, self.gpu, image_in)
            if self.merge_enabled:
                results = self.merge_boxes(results, (self.merge_lim_x, self.merge_lim_y))
            if self.smart:
                from anki_niobium.llm import smart_filter_results
                results, extra = smart_filter_results(results, image_bytes, {**self.config, "_no_cache": self.no_cache})
            else:
                results, extra = self.filter_results(results, self.config)
            if not results:
                console.print('[yellow]No occlusions found, skipping.[/yellow]')
                return False
            occlusion = self.get_occlusion_coords(results, H, W)

            # Prepare image file for media
            hashed_name = niobium.get_image_hash(image_name) + '.png'
            if image_name:
                img = Image.open(image_name)
            else:
                img = image_in
            tmp_path = os.path.join(out_dir, hashed_name)
            img.save(tmp_path, format='PNG')
            media_files.append(tmp_path)

            header = ''
            if self.args.get('add_header') and image_name:
                header = os.path.basename(image_name).split('.')[0]

            note = genanki.Note(
                model=IO_MODEL,
                fields=[occlusion, f'<img src="{hashed_name}">', header, extra, ''],
                tags=['NIOBIUM'],
            )
            deck.add_note(note)
            console.print(f'[green]Note created with {len(results)} occlusions.[/green]')
            mark_processed(c_hash, image_name or f"pdf:{os.path.basename(self.args.get('single_pdf', 'unknown'))}")
            return False

        out_dir = self.args['apkg_out']
        os.makedirs(out_dir, exist_ok=True)

        if self.args.get('image'):
            process_image(self.args['image'])
        elif self.args.get('directory'):
            img_list = self.get_images_in_directory(self.args['directory'])
            console.print(f'[cyan]{len(img_list)} images found.[/cyan]')
            skipped = 0
            for i, img_path in enumerate(img_list, 1):
                console.print(f'[dim]\\[{i}/{len(img_list)}][/dim]')
                if process_image(img_path, is_batch=True):
                    skipped += 1
            if skipped:
                console.print(f"[dim]{skipped} image(s) skipped (already in cache)[/dim]")
        elif self.args.get('single_pdf'):
            all_images = self.extract_images_from_pdf(self.args['single_pdf'])
            console.print(f'[cyan]{len(all_images)} images extracted from PDF.[/cyan]')
            skipped = 0
            for i, im in enumerate(all_images, 1):
                console.print(f'[dim]\\[{i}/{len(all_images)}][/dim]')
                if process_image(None, image_in=im, is_batch=True):
                    skipped += 1
            if skipped:
                console.print(f"[dim]{skipped} image(s) skipped (already in cache)[/dim]")

        apkg_path = os.path.join(out_dir, f'{deck_name}.apkg')
        pkg = genanki.Package(deck)
        pkg.media_files = media_files
        pkg.write_to_file(apkg_path)
        console.print(f'[bold green]Saved {apkg_path} ({len(deck.notes)} notes)[/bold green]')

    @staticmethod
    def reverse_word_order(string):
        # Split the string into words
        words = string.split()
        
        # Reverse the order of the words
        reversed_words = words[::-1]
        
        # Join the reversed words back into a string
        reversed_string = ' '.join(reversed_words)
        
        return reversed_string

    @staticmethod
    def filter_results(results, config):
        filtered_results = []
        extra = ''
        for (bbox, text, prob) in results:
            cur_reg_flag = False
            if config['exclude']['regex']:
                for rgx in config['exclude']['regex']:
                    matches = re.search(rgx, text)
                    if matches:
                        cur_reg_flag = True
                        break
            cur_exact_flag = False
            if config['exclude']['exact']:
                for cur_no in config['exclude']['exact']:
                    if (cur_no.lower() == text.lower()) or (cur_no.lower() == niobium.reverse_word_order(text.lower())):
                        cur_exact_flag = True
                        break
            if config['extra']:
                for cur_extra in config['extra']:
                    if (list(cur_extra.keys())[0].lower() == text.lower()):
                        extra += f'{list(cur_extra.values())[0]}<br>'
                        console.print(f'[cyan]Adding extra information for {text}[/cyan]')
                        break

            if cur_exact_flag or cur_reg_flag:
                console.print(f'[dim]Discarding occlusion with text {text}[/dim]')
            else:
                filtered_results.append((bbox, text, prob))

        return(filtered_results, extra)

    @staticmethod
    def get_image_hash(image_name=None):
        h = blake2b(digest_size=20)
        if image_name:
            h.update((str(time.time()) + image_name).encode("utf-8"))
        else:
            h.update((str(time.time())).encode("utf-8"))
        return h.hexdigest()

    @staticmethod
    def save_qc_image(results, image_name, path, image_in=None):
        if image_name:
            image = Image.open(image_name)
        else:
            image = image_in
        draw = ImageDraw.Draw(image)
        for (bbox, text, prob) in results:
            (tl, tr, br, bl) = bbox
            tl = (int(tl[0]), int(tl[1]))
            tr = (int(tr[0]), int(tr[1]))
            br = (int(br[0]), int(br[1]))
            bl = (int(bl[0]), int(bl[1]))
            draw.rectangle([tl, br], outline="red", width=2)
        hashed_name = niobium.get_image_hash(image_name) + '.jpeg'
        image = image.convert('RGB')
        image.save(os.path.join(path, hashed_name), quality=50)

    @staticmethod
    def get_occlusion_coords(results, H, W):
        lst = ''
        for idx, (box, text, prob) in enumerate(results, start=1):
            tmp = niobium.format_geom(box)
            data_left = format(tmp[1] / W, '.4f').lstrip('0')
            data_top = format(tmp[0] / H, '.4f').lstrip('0')
            data_width = format((tmp[3] / W - tmp[1] / W), '.4f').lstrip('0')
            data_height = format((tmp[2] / H - tmp[0] / H), '.4f').lstrip('0')
            lst += f"{{{{c{idx}::image-occlusion:rect:left={data_left}:top={data_top}:width={data_width}:height={data_height}:oi=1}}}};"
        return lst

    @staticmethod
    def ocr_single_image(image_name, langs, gpu, image_in=None):
        if image_name:
            image = Image.open(image_name)
            W, H = image.size
            image = niobium.byte_convert(image)
            console.print(f"[cyan]Running OCR for {image_name}[/cyan]")
        else:
            image = image_in
            W, H = image.size
            image = niobium.byte_convert(image)
            console.print("[cyan]Running OCR for PDF image[/cyan]")
        langs = langs.split(",")
        reader = Reader(langs, gpu=gpu > 0, verbose=False)
        results = reader.readtext(image)
        return (results, H, W, image)

    @staticmethod
    def add_image_occlusion_deck(image_name, occlusion, deck_name, extra, image_in,header=False):
        if image_name:
            with open(image_name, "rb") as f:
                image_data = f.read()
                image_base64 = base64.b64encode(image_data).decode("utf-8")
        else:
            image_in = niobium.byte_convert(image_in)
            image_base64 = base64.b64encode(image_in).decode("utf-8")
        hashed_name = "_" + niobium.get_image_hash(image_name) + '.jpeg'
        if header:
            fields =  {
                        "Occlusion": occlusion,
                        "Back Extra": extra,
                        "Header": os.path.basename(image_name).split('.')[0]
                      }
        else:
            fields =  {
                        "Occlusion": occlusion,
                        "Back Extra": extra
                      }

        note_data = {
            "action": "addNote",
            "version": 6,
            "params": {
                "note": {
                    "deckName": deck_name,
                    "modelName": "Image Occlusion",
                    "fields": fields,
                    "options": {
                        "allowDuplicate": False
                    },
                    "tags": ['NIOBIUM'],
                    "picture": [{
                        "filename": hashed_name,
                        "data": image_base64,
                        "fields": [
                            "Image"
                        ]
                    }]
                }
            }
        }
        response = requests.post(ANKI_LOCAL, json=note_data)
        if response.status_code == 200:
            data = json.loads(response.content)
            if data['error']:
                return (True, f"[bold red]Could not add note: {data['error']}[/bold red]")
            else:
                return (True, f"[green]Note added: {data['result']}[/green]")
        else:
            data = json.loads(response.content)
            return (False, f"[bold red]Could not create note for {image_name}: {data}[/bold red]")

    @staticmethod
    def cleanup_text(text):
        return "".join([c if ord(c) < 128 else "" for c in text]).strip()

    @staticmethod
    def format_geom(rect):
        tmp = np.array(rect)
        return [min(tmp[:, 1]), min(tmp[:, 0]), max(tmp[:, 1]), max(tmp[:, 0])]

    @staticmethod
    def calc_sim(box1, box2):
        box1 = niobium.format_geom(box1)
        box2 = niobium.format_geom(box2)
        box1_ymin, box1_xmin, box1_ymax, box1_xmax = box1
        box2_ymin, box2_xmin, box2_ymax, box2_xmax = box2
        x_dist = min(abs(box1_xmin - box2_xmin), abs(box1_xmin - box2_xmax), abs(box1_xmax - box2_xmin), abs(
            box1_xmax - box2_xmax))
        y_dist = min(abs(box1_ymin - box2_ymin), abs(box1_ymin - box2_ymax), abs(box1_ymax - box2_ymin), abs(
            box1_ymax - box2_ymax))
        return (int(x_dist), int(y_dist))

    @staticmethod
    def merge_boxes(results, threshold=(20, 20)):
        console.print(f'[cyan]{len(results)} occlusion pairs.[/cyan]')
        merged_results = []
        if len(results) == 0:
            return merged_results

        results = sorted(results, key=lambda x: x[0][0][1])

        for i, (bbox1, text1, prob1) in enumerate(results):
            if i == 0:
                merged_results.append((bbox1, text1, prob1))
                continue

            merged = False
            for j, (bbox2, text2, prob2) in enumerate(merged_results):
                kek = niobium.calc_sim(bbox1, bbox2)
                intersect = niobium.does_intersect(bbox1,bbox2)
                touch = niobium.does_touch(bbox1,bbox2)
                # print(text1 + " and " + text2)
                # print(f'TOUCH {touch}')
                # print(f'INTERSECT {intersect}')
                if ((kek[0] < threshold[0]) and (kek[1] < threshold[1]) or (intersect or touch)):
                    merged_bbox = [
                        [int(min(bbox1[0][0], bbox2[0][0])), int(min(bbox1[0][1], bbox2[0][1]))],
                        [int(max(bbox1[1][0], bbox2[1][0])), int(min(bbox1[1][1], bbox2[1][1]))],
                        [int(max(bbox1[2][0], bbox2[2][0])), int(max(bbox1[2][1], bbox2[2][1]))],
                        [int(min(bbox1[3][0], bbox2[3][0])), int(max(bbox1[3][1], bbox2[3][1]))]
                    ]
                    merged_text = text1 + " " + text2
                    merged_prob = max(prob1, prob2)
                    del merged_results[j]  # Remove the old bbox2
                    merged_results.append((merged_bbox, merged_text, merged_prob))
                    merged = True
                    break

            if not merged:
                merged_results.append((bbox1, text1, prob1))

        # final_results = []
        # for bbox1, text1, prob1 in merged_results:
        #     overlapping = False
        #     for bbox2, _, _ in merged_results:
        #         if bbox1 != bbox2:
        #             if bbox1[0][0] < bbox2[1][0] and bbox1[1][0] > bbox2[0][0] and bbox1[0][1] < bbox2[2][1] and bbox1[2][
        #                  1] > bbox2[0][1]:
        #                 if prob1 <= prob2:
        #                     overlapping = True
        #                     break
        #     if not overlapping:
        #         final_results.append((bbox1, text1, prob1))
        return merged_results

    @staticmethod
    def get_images_in_directory(directory):
        all_files = os.listdir(directory)
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        image_files = [os.path.join(directory, file) for file in all_files if
                       os.path.splitext(file)[1].lower() in image_extensions]
        return image_files

    @staticmethod
    def extract_images_from_pdf(file,path=None):
        if path:
            ct = datetime.now()
            console.print(f'[cyan]Images will be extracted from {file}[/cyan]')
            opdir = os.path.join(path,'niobium-pdf2img',os.path.basename(file).split('.')[0] + ct.strftime("_%H-%M-%S"))
            if not os.path.exists(opdir):
                os.makedirs(opdir)
        else:
            opdir = os.path.dirname(os.path.abspath(file))
            opdir = os.path.join(opdir, 'niobium-io')
            if not os.path.exists(opdir):
                os.makedirs(opdir)
        
        all_images = []
        doc = fitz.Document(file)
        console.print(f'[cyan]Extracted images will be saved to {opdir}[/cyan]')
        count = 1
        for i in tqdm(range(len(doc)), desc="pages"):
            for img in tqdm(doc.get_page_images(i), desc="page_images"):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                if path:
                    pix.save(os.path.join(opdir,f"{count:02d}.jpg"),jpg_quality=50)
                    count += 1
                else:
                    if pix.n < 5:
                        mode = "RGB"
                    else:
                        mode = "CMYK"
                    img_pil = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
                    all_images.append(img_pil)

        if path == None:
            return all_images
        else:
            console.print(f'[bold green]{count-1} images have been saved.[/bold green]')

    @staticmethod
    def create_deck(deck_name):
        prm = {
            "action": "createDeck",
            "version": 6,
            "params": {
                "deck": deck_name
            }}
        response = requests.post(ANKI_LOCAL, json=prm)
        if response.status_code == 200:
            data = json.loads(response.content)
            if data['error']:
                raise Exception(f'Cannot create deck: {data["error"]}')
            else:
                console.print(f"[green]Created deck {deck_name}: {data['result']}[/green]")
        else:
            raise Exception('Cannot connect to Anki')

    @staticmethod
    def deck_exists(deck_name):
        prm = {
            "action": "deckNames",
            "version": 6}
        response = requests.get(ANKI_LOCAL, json=prm)
        if response.status_code == 200:
            data = json.loads(response.content)
            if data['error']:
                raise Exception(f'Cannot find decks: {data["error"]}')
            else:
                data = data['result']
        else:
            raise Exception('Cannot connect to Anki.')

        if deck_name in data:
            return True
        else:
            return False

    @staticmethod
    def byte_convert(image_in):
        with BytesIO() as output:
            image_in.save(output, format="PNG")
            return output.getvalue()

    @staticmethod
    def does_intersect(rect1,rect2):
        if rect1[1][0] < rect2[0][0] or rect2[1][0] < rect1[0][0]:
                return False

        if rect1[2][1] < rect2[0][1] or rect2[2][1] < rect1[0][1]:
            return False

        return True

    @staticmethod
    def does_touch(rect1, rect2, tolerance=2):
        # rect format: [TL, TR, BR, BL] where each is [x, y]
        r1_xmin, r1_ymin = rect1[0][0], rect1[0][1]
        r1_xmax, r1_ymax = rect1[2][0], rect1[2][1]
        r2_xmin, r2_ymin = rect2[0][0], rect2[0][1]
        r2_xmax, r2_ymax = rect2[2][0], rect2[2][1]

        h_overlap = r1_xmin <= r2_xmax and r2_xmin <= r1_xmax
        v_overlap = r1_ymin <= r2_ymax and r2_ymin <= r1_ymax

        if h_overlap and (abs(r1_ymax - r2_ymin) <= tolerance or abs(r2_ymax - r1_ymin) <= tolerance):
            return True
        if v_overlap and (abs(r1_xmax - r2_xmin) <= tolerance or abs(r2_xmax - r1_xmin) <= tolerance):
            return True
        return False

    @staticmethod
    def add_basic_deck(image_name, deck_name):
        if image_name:
            with open(image_name, "rb") as f:
                image_data = f.read()
                image_base64 = base64.b64encode(image_data).decode("utf-8")
        # else:
        #     image_in = niobium.byte_convert(image_in)
        #     image_base64 = base64.b64encode(image_in).decode("utf-8")
        #hashed_name = "_" + niobium.get_image_hash(image_name) + '.jpeg'
        fields =  {
                    "Back": ""
                    }

        note_data = {
            "action": "addNote",
            "version": 6,
            "params": {
                "note": {
                    "deckName": deck_name,
                    "modelName": "Basic",
                    "fields": fields,
                    "options": {
                        "allowDuplicate": False
                    },
                    "tags": ['NIOBIUM'],
                    "picture": [{
                        "filename": os.path.basename(image_name).split('.')[0] + "_" + str(time.time()),
                        "data": image_base64,
                        "fields": [
                            "Front"
                        ]
                    }]
                }
            }
        }
        response = requests.post(ANKI_LOCAL, json=note_data)
        if response.status_code == 200:
            data = json.loads(response.content)
            if data['error']:
                return (True, f"[bold red]Could not add note: {data['error']}[/bold red]")
            else:
                return (True, f"[green]Note added: {data['result']}[/green]")
        else:
            data = json.loads(response.content)
            return (False, f"[bold red]Could not create note for {image_name}: {data}[/bold red]")

    @staticmethod
    def pdf_to_basic(directory,deck_name):
        if niobium.deck_exists(deck_name):
            console.print(f'[cyan]Found Anki deck named {deck_name}[/cyan]')
        else:
            if Confirm.ask(f'Deck [bold]{deck_name}[/bold] not found. Create?', default=True):
                niobium.create_deck(deck_name)
            else:
                raise Exception('Cannot create notes without a deck. Terminating ...')
        img_list = niobium.get_images_in_directory(directory)
        console.print(f"[cyan]{len(img_list)} images found[/cyan]")
        it = 1
        for img_path in sorted(img_list):
            console.print(f"[dim]\\[{it}/{len(img_list)}][/dim]")
            niobium.add_basic_deck(img_path, deck_name)
            it += 1
