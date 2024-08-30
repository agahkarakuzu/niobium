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
import click
from datetime import datetime
import random

ANKI_LOCAL = "http://localhost:8765"

class niobium:
    def __init__(self, args):
        self.args = args

    def ocr4io(self):
        """
        Optical Charancter Recognition for Image Occlusion
        Image Occlusion entry
        """
        #print(self)
        if self.deck_exists(self.args["deck_name"]):
            print(f'[INFO] --> Found Anki deck named {self.args["deck_name"]}')
        else:
            print('==> User input needed <===========================================')
            if click.confirm(f'[!!!!] Deck {self.args["deck_name"]} not found. Create?', default=True):
                self.create_deck(self.args["deck_name"])
            else:
                raise Exception('Cannot create notes without a deck. Terminating ...')

        if self.args['image'] != None:
            # Single image
            results, H, W = self.ocr_single_image(self.args["image"], self.args["langs"], self.args["gpu"])
            if self.args["merge_rects"]:
                results = self.merge_boxes(results, (self.args["merge_lim_x"], self.args["merge_lim_y"]))
                results, extra = self.filter_results(results)
            else:
                results, extra = self.filter_results(results)
            occlusion = self.get_occlusion_coords(results, H, W)
            status = self.add_image_occlusion_deck(self.args["image"], occlusion, self.args["deck_name"], extra, None,self.args["add_header"])
            print(status[1])
            self.save_qc_image(results, self.args["image"], image_in=None)
        elif self.args['directory'] != None:
            # Batch process
            print(f"[INFO] --> Starting batch processing {self.args['directory']}")
            opdir = os.path.join(self.args['directory'], 'niobium-io')
            print(opdir)
            if not os.path.exists(opdir):
                os.makedirs(opdir)
            img_list = self.get_images_in_directory(self.args['directory'])
            print(f"[INFO] --> {len(img_list)} images are found")
            it = 1
            for img_path in img_list:
                print(f"[{it}/{len(img_list)}] ................................................")
                results, H, W = self.ocr_single_image(img_path, self.args["langs"], self.args["gpu"])
                if self.args["merge_rects"]:
                    results = self.merge_boxes2(results, (self.args["merge_lim_x"], self.args["merge_lim_y"]))
                    results = self.clean_boxes(results)
                    results, extra = self.filter_results(results)
                else:
                    results, extra = self.filter_results(results)
                occlusion = self.get_occlusion_coords(results, H, W)
                status = self.add_image_occlusion_deck(img_path, occlusion, self.args["deck_name"], extra, None,self.args["add_header"])
                print(status[1])
                self.save_qc_image(results, img_path, path=opdir, image_in=None)
                it += 1
        elif self.args['single_pdf'] != None:
            print(f"[INFO] --> Extracting images from the PDF")
            opdir = os.path.dirname(os.path.abspath(self.args['single_pdf']))
            opdir = os.path.join(opdir, 'niobium-io')
            if not os.path.exists(opdir):
                os.makedirs(opdir)
            print(f"[INFO] --> Preview images will be saved at {opdir}")
            all_images = self.extract_images_from_pdf(self.args['single_pdf'])
            print(f"[INFO] --> {len(all_images)} images were extracted from the PDF.")
            it = 1
            for im in all_images:
                print(f"[{it}/{len(all_images)}] ................................................")
                results, H, W = self.ocr_single_image(None, self.args["langs"], self.args["gpu"], im)
                if self.args["merge_rects"]:
                    results = self.merge_boxes(results, (self.args["merge_lim_x"], self.args["merge_lim_y"]))
                    results, extra = self.filter_results(results)
                else:
                    results, extra = self.filter_results(results)
                occlusion = self.get_occlusion_coords(results, H, W)
                status = self.add_image_occlusion_deck(None, occlusion, self.args["deck_name"], extra, im,self.args["add_header"])
                print(status[1])
                self.save_qc_image(results, None, path=opdir, image_in=im)
                it += 1

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
    def filter_results(results):
        with open('config.json') as f:
            config = json.load(f)
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
                        print(f'[INFO] --> Adding extra information for {text}')
                        break

            if cur_exact_flag or cur_reg_flag:
                print(f'[INFO] --> Discarding occlusion with text {text}')
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
    def save_qc_image(results, image_name, path=None, image_in=None):
        if image_name:
            if path is None:
                path = os.path.abspath(image_name)
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
        try:
            image = image.convert('RGB')
            image.save(os.path.join(path, hashed_name), quality=50)
        except Exception as e:
            print(f"[ERR] {e}")
            print(f'[WARN] Issue with resolving paths, saving preview image at {os.getcwd()}')
            image = image.convert('RGB')
            image.save(hashed_name, quality=50)

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
            print(f"[INFO] --> Running for {image_name}")
        else:
            image = image_in
            W, H = image.size
            image = niobium.byte_convert(image)
            print(f"[INFO] --> Running for PDF image")
        langs = langs.split(",")
        reader = Reader(langs, gpu=gpu > 0, verbose=False)
        results = reader.readtext(image)
        return (results, H, W)

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
                return (True, f"[ERR] --> Could not add note: {data['error']}")
            else:
                return (True, f"[SUCCESS] --> Note added: {data['result']}")
        else:
            data = json.loads(response.content)
            return (False, f"[ERR] --> Could not create note for {image_name}: {data}")

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
        print(f'[INFO]--> {len(results)} occlusion pairs.')
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
            print(f'[INFO] --> Images will be extracted from {file}')
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
        print(f'[INFO] --> Extracted images will be saved to {opdir}')
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
            print(f'[DONE] --> {count-1} images have been saved.')

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
                print(f"[INFO] --> Created deck {deck_name}: {data['result']}")
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
    def does_touch(rect1,rect2):
        if abs(rect1[0][1] - rect2[2][1]) <=2 or abs(rect2[0][1] - rect1[2][1]) <= 2:
            return False
        if abs(rect1[2][1] - rect2[0][1]) <=2 or abs(rect2[2][1] == rect1[0][1]) <=2:
            return False
        return True

    @staticmethod
    def clean_boxes(results):
        print(f'[INFO]--> {len(results)} occlusion pairs.')
        merged_results = []
        if len(results) == 0:
            return merged_results
        
        #results = random.shuffle(results)
        results = sorted(results, key=lambda x: x[0][1][1],reverse=True)

        #print(results)
        for i, (bbox1, text1, prob1) in enumerate(results):
            if i == 0:
                merged_results.append((bbox1, text1, prob1))
                continue

            merged = False
            for j, (bbox2, text2, prob2) in enumerate(merged_results):
                intersect = niobium.does_intersect(bbox1,bbox2)
                touch = niobium.does_touch(bbox1,bbox2)
                if intersect or touch:
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

        return merged_results
    
    @staticmethod
    def merge_boxes2(results, threshold=(20, 20)):
        print(f'[INFO]--> {len(results)} occlusion pairs.')
        merged_results = []
        if len(results) == 0:
            return merged_results

        results = sorted(results, key=lambda x: x[0][0][1])
        for i in range(len(results)):
            bbox1  = results[i][0]
            text1  = results[i][1]
            prob1  = results[i][2]
            if i <= len(results)-2:
                bbox2  = results[i+1][0]
                text2  = results[i+1][1]
                prob2  = results[i+1][2]
            else:
                merged_results.append((bbox1, text1, prob1))

            if (i == 0) or (i == len(results)-1):
                merged_results.append((bbox1, text1, prob1))
                continue

            merged = False

            kek = niobium.calc_sim(bbox1, bbox2)
            intersect = niobium.does_intersect(bbox1,bbox2)
            touch = niobium.does_touch(bbox1,bbox2)
            if ((kek[0] < threshold[0]) and (kek[1] < threshold[1]) or (intersect or touch)):
                merged_bbox = [
                    [int(min(bbox1[0][0], bbox2[0][0])), int(min(bbox1[0][1], bbox2[0][1]))],
                    [int(max(bbox1[1][0], bbox2[1][0])), int(min(bbox1[1][1], bbox2[1][1]))],
                    [int(max(bbox1[2][0], bbox2[2][0])), int(max(bbox1[2][1], bbox2[2][1]))],
                    [int(min(bbox1[3][0], bbox2[3][0])), int(max(bbox1[3][1], bbox2[3][1]))]
                ]
                merged_text = text1 + " " + text2
                merged_prob = max(prob1, prob2)
                #del merged_results[i-1]  # Remove the old bbox2
                merged_results.append((merged_bbox, merged_text, merged_prob))
                merged = True

            if not merged:
                merged_results.append((bbox1, text1, prob1))
        return merged_results
    
# Pixel degil ratio uzerinden git, goruntunun boyutuna gore bu degisebilir. 
# Liste icerisinde en genis text ve en dar text arasindaki faki bulup diklemesine birlestime icin xlim olarak onu 
# Yukarida yazdigimin benzerini de y icin yap.

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
                return (True, f"[ERR] --> Could not add note: {data['error']}")
            else:
                return (True, f"[SUCCESS] --> Note added: {data['result']}")
        else:
            data = json.loads(response.content)
            return (False, f"[ERR] --> Could not create note for {image_name}: {data}")

    @staticmethod
    def pdf_to_basic(directory,deck_name):
        if niobium.deck_exists(deck_name):
            print(f'[INFO] --> Found Anki deck named {deck_name}')
        else:
            print('==> User input needed <===========================================')
        if click.confirm(f'[!!!!] Deck {deck_name} not found. Create?', default=True):
            niobium.create_deck(deck_name)
        else:
            raise Exception('Cannot create notes without a deck. Terminating ...')
        img_list = niobium.get_images_in_directory(directory)
        print(f"[INFO] --> {len(img_list)} images are found")
        it = 1
        for img_path in sorted(img_list):
            print(f"[{it}/{len(img_list)}] ................................................")
            niobium.add_basic_deck(img_path, deck_name)
            it += 1
