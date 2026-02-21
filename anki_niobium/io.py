import requests
import base64
import numpy as np
from easyocr import Reader
from PIL import Image, ImageDraw
from hashlib import blake2b
import time
import os
import json
import yaml
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
import pymupdf4llm

from anki_niobium.cache import content_hash_file, content_hash_bytes, is_processed, mark_processed

ANKI_LOCAL = "http://localhost:8765"
console = Console()

CLOZE_MODEL = genanki.Model(
    1607392320,
    'Cloze',
    fields=[{'name': 'Text'}, {'name': 'Back Extra'}],
    templates=[{
        'name': 'Cloze',
        'qfmt': '{{cloze:Text}}',
        'afmt': '{{cloze:Text}}<br><hr id=answer>{{Back Extra}}',
    }],
    css='.card { font-size: 18px; text-align: center; }',
    model_type=genanki.Model.CLOZE,
)

BASIC_MODEL = genanki.Model(
    1607392321,
    'Basic',
    fields=[{'name': 'Front'}, {'name': 'Back'}],
    templates=[{
        'name': 'Card 1',
        'qfmt': '{{Front}}',
        'afmt': '{{FrontSide}}<hr id=answer>{{Back}}',
    }],
    css='.card { font-size: 18px; text-align: center; }',
)

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
        self.generate = self.args.get("generate", False)
        self.page = self.args.get("page")
        self.card_type = self.args.get("card_type")
        self.qc = self.config.get("qc", False)
        self.no_cache = self.args.get("no_cache", False)

        # max_cards: CLI flag overrides config
        llm_cfg = self.config.get("llm", {})
        self.max_cards = self.args.get("max_cards") if self.args.get("max_cards") is not None else llm_cfg.get("max_cards")

        # Work directory for smart mode artifacts
        if self.smart:
            work_dir_cfg = self.config.get("work_dir")
            if work_dir_cfg:
                base = os.path.expanduser(work_dir_cfg)
                artifacts_base = os.path.join(base, "artifacts")
                os.makedirs(artifacts_base, exist_ok=True)
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                self.work_dir = os.path.join(artifacts_base, f"nb41_smart_{ts}")
                os.makedirs(self.work_dir, exist_ok=True)
            else:
                self.work_dir = None
        else:
            self.work_dir = None

    def _derive_deck_name(self):
        """Derive a human-readable deck name from the input."""
        if self.args.get('single_pdf'):
            return Path(self.args['single_pdf']).stem
        elif self.args.get('image'):
            return Path(self.args['image']).stem
        elif self.args.get('directory'):
            return Path(self.args['directory']).name
        return 'Niobium Export'

    def _derive_output_stem(self):
        """Derive an apkg filename stem: no spaces, with page range and timestamp."""
        if self.args.get('single_pdf'):
            base = Path(self.args['single_pdf']).stem
        elif self.args.get('image'):
            base = Path(self.args['image']).stem
        elif self.args.get('directory'):
            base = Path(self.args['directory']).name
        else:
            base = 'niobium_export'
        base = base.replace(' ', '_')
        if self.page:
            base += f"_p{self.page}"
        base += f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return base

    def confirm_smart_instructions(self):
        """Display pipeline summary and LLM config, ask user to confirm before proceeding."""
        is_gen = self.generate or (self.smart and self.page and self.args.get('single_pdf'))
        llm_config = self.config.get("llm", {})
        instructions = llm_config.get("instructions")
        model = llm_config.get("model", "claude-sonnet-4-6")

        # --- Mode title ---
        mode = "Smart Generation" if is_gen else "Smart Filtering"

        # --- Input ---
        if self.args.get('single_pdf'):
            src = os.path.basename(self.args['single_pdf'])
            if self.page:
                src += f", page {self.page}"
        elif self.args.get('image'):
            src = os.path.basename(self.args['image'])
        elif self.args.get('directory'):
            src = self.args['directory']
        else:
            src = "input"

        # --- Output ---
        if self.args.get('deck_name'):
            output_desc = f"Anki deck → {self.args['deck_name']}"
        elif self.args.get('apkg_out'):
            output_desc = f".apkg → {self.args['apkg_out']}/"
        else:
            output_desc = "default output directory"

        # --- Pipeline steps ---
        if is_gen:
            steps = []
            if self.args.get('single_pdf'):
                steps.append("Render PDF page(s) as image or extract text (by image coverage)")
            steps.append(f"Send content to {model}")
            steps.append("Claude analyzes and generates flashcards from scratch")
            if self.card_type:
                steps.append(f"Output only {self.card_type} cards")
            else:
                steps.append("Output best-fit card types (cloze, basic, image occlusion)")
            card_note = "Claude decides" if not self.card_type else self.card_type
        else:
            steps = [
                "OCR detects text regions (EasyOCR)",
                "Bounding boxes merged by proximity",
                f"Claude ({model}) filters noise, corrects OCR, adds hints",
                "Output image occlusion cards",
            ]
            card_note = "image occlusion"

        # --- Build panel ---
        panel_parts = []
        panel_parts.append(f"[bold]Input:[/bold]  {src}")
        panel_parts.append(f"[bold]Output:[/bold] {output_desc}")
        panel_parts.append(f"[bold]Model:[/bold]  {model}")
        panel_parts.append("")
        panel_parts.append("[bold]Pipeline:[/bold]")
        for i, step in enumerate(steps, 1):
            panel_parts.append(f"  {i}. {step}")
        panel_parts.append("")
        panel_parts.append(f"[bold]Card types:[/bold] {card_note}")
        if self.max_cards:
            panel_parts.append(f"[bold]Max cards:[/bold]  {self.max_cards} per page/image")
        if instructions:
            panel_parts.append(f"[bold]Instructions:[/bold] {instructions}")
        else:
            panel_parts.append("[dim]No custom instructions (Claude uses defaults)[/dim]")
        if self.no_cache:
            panel_parts.append("[bold]Cache:[/bold] disabled for this run")
        if self.work_dir:
            panel_parts.append(f"[bold]Artifacts:[/bold] {self.work_dir}")

        from rich.panel import Panel
        console.print(Panel(
            "\n".join(panel_parts),
            title=f"[bold cyan]{mode}[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        ))
        if not Confirm.ask("Proceed?", default=True):
            console.print("[yellow]Aborted.[/yellow]")
            import shutil
            if self.work_dir:
                shutil.rmtree(self.work_dir, ignore_errors=True)
            raise SystemExit(0)

    @staticmethod
    def _show_cache_hit(label, cached_info):
        """Display a panel with previously saved output/artifact paths."""
        from rich.panel import Panel
        parts = [f"[dim]{label} was already processed[/dim]"]
        if cached_info.get("output_path"):
            parts.append(f"[bold]Output:[/bold] {cached_info['output_path']}")
        if cached_info.get("artifacts_path"):
            parts.append(f"[bold]Artifacts:[/bold] {cached_info['artifacts_path']}")
        console.print(Panel(
            "\n".join(parts),
            title="[dim]Cache hit[/dim]",
            border_style="dim",
            padding=(0, 2),
        ))

    def save_work_artifact(self, page_idx, page_img=None, page_text=None, card_data=None, display_name=None):
        """Save per-page artifacts to the smart work directory for inspection."""
        if not self.work_dir:
            return
        tag = display_name or str(page_idx + 1)
        prefix = f"page_{tag.zfill(3)}"
        if page_img is not None:
            img_path = os.path.join(self.work_dir, f"{prefix}_render.png")
            page_img.save(img_path)
        if page_text is not None:
            md_path = os.path.join(self.work_dir, f"{prefix}_text.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(page_text)
        if card_data is not None:
            json_path = os.path.join(self.work_dir, f"{prefix}_cards.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(card_data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load_config(config_path):
        with open(config_path) as f:
            if config_path.endswith(('.yaml', '.yml')):
                return yaml.safe_load(f)
            return json.load(f)

    @staticmethod
    def resolve_config(config_path=None):
        if config_path:
            p = Path(config_path)
            if not p.is_file():
                raise FileNotFoundError(f"Config file not found: {config_path}")
            console.print(f'[cyan]Using config: {p}[/cyan]')
            return str(p)

        # Check user config: YAML first, then legacy JSON
        config_dir = Path.home() / ".config" / "niobium"
        for name in ("config.yaml", "config.yml", "config.json"):
            user_config = config_dir / name
            if user_config.is_file():
                console.print(f'[cyan]Using config: {user_config}[/cyan]')
                return str(user_config)

        default_config = Path(__file__).parent / "default_config.yaml"
        console.print(f'[cyan]Using config: {default_config} (bundled default)[/cyan]')
        return str(default_config)

    @staticmethod
    def init_config():
        import shutil
        config_dir = Path.home() / ".config" / "niobium"
        # Check for any existing config (YAML or legacy JSON)
        for name in ("config.yaml", "config.yml", "config.json"):
            existing = config_dir / name
            if existing.is_file():
                console.print(f'[cyan]Config already exists: {existing}[/cyan]')
                console.print('[cyan]Edit this file to customize filtering rules.[/cyan]')
                return existing
        config_dir.mkdir(parents=True, exist_ok=True)
        dest = config_dir / "config.yaml"
        src = Path(__file__).parent / "default_config.yaml"
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
            doc = fitz.Document(self.args['single_pdf'])
            page_set = niobium.parse_page_range(self.page, doc.page_count, doc=doc) if self.page else None
            doc.close()
            all_images = self.extract_images_from_pdf(self.args['single_pdf'], pages=page_set)
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

    def deliver_generated_cards(self, card_data, page_image, page_index,
                                deck_name=None, deck=None, media_files=None,
                                tmp_media_dir=None):
        cards = card_data.get("cards", [])
        created = 0

        for card in cards:
            card_type = card["type"]
            hint = card.get("hint", "")

            if card_type == "image_occlusion":
                occlusion_str = ""
                for idx, occ in enumerate(card.get("occlusions", []), 1):
                    left = format(occ["left"], '.4f').lstrip('0')
                    top = format(occ["top"], '.4f').lstrip('0')
                    width = format(occ["width"], '.4f').lstrip('0')
                    height = format(occ["height"], '.4f').lstrip('0')
                    occlusion_str += f"{{{{c{idx}::image-occlusion:rect:left={left}:top={top}:width={width}:height={height}:oi=1}}}};"

                if deck_name:
                    status = self.add_image_occlusion_deck(
                        None, occlusion_str, deck_name, hint, page_image, False
                    )
                    console.print(status[1])
                elif deck:
                    hashed_name = niobium.get_image_hash() + '.png'
                    tmp_path = os.path.join(tmp_media_dir, hashed_name)
                    page_image.save(tmp_path, format='PNG')
                    media_files.append(tmp_path)
                    IO_MODEL = genanki.Model(
                        1607392319, 'Image Occlusion',
                        fields=[
                            {'name': 'Occlusion'}, {'name': 'Image'},
                            {'name': 'Header'}, {'name': 'Back Extra'}, {'name': 'Comments'},
                        ],
                        templates=[{
                            'name': 'Cloze',
                            'qfmt': '{{cloze:Occlusion}}<br>{{Image}}',
                            'afmt': '{{cloze:Occlusion}}<br>{{Image}}<br><hr id=answer>{{Back Extra}}',
                        }],
                        css='.card { text-align: center; }',
                        model_type=genanki.Model.CLOZE,
                    )
                    note = genanki.Note(
                        model=IO_MODEL,
                        fields=[occlusion_str, f'<img src="{hashed_name}">', '', hint, ''],
                        tags=['NIOBIUM'],
                    )
                    deck.add_note(note)
                created += 1

            elif card_type == "cloze":
                text = card.get("text", "")
                if not text:
                    continue
                if deck_name:
                    status = niobium.add_cloze_note(text, deck_name, hint)
                    console.print(status[1])
                elif deck:
                    note = genanki.Note(
                        model=CLOZE_MODEL,
                        fields=[text, hint],
                        tags=['NIOBIUM'],
                    )
                    deck.add_note(note)
                created += 1

            elif card_type == "basic":
                front = card.get("front", "")
                back = card.get("back", "")
                if not front:
                    continue
                if hint:
                    back = f"{back}<br><hr><i>{hint}</i>"
                if deck_name:
                    status = niobium.add_basic_note(front, back, deck_name)
                    console.print(status[1])
                elif deck:
                    note = genanki.Note(
                        model=BASIC_MODEL,
                        fields=[front, back],
                        tags=['NIOBIUM'],
                    )
                    deck.add_note(note)
                created += 1

        return created

    def _collect_generate_items(self):
        """Collect items for the generation pipeline.

        Returns list of (label, idx, display_name, img_or_None, text_or_None, content_hash, source) tuples.
        display_name is the user-visible page label (for artifact naming).
        Works for both PDF pages and image inputs.
        """
        items = []

        if self.args.get('single_pdf'):
            pdf_path = self.args['single_pdf']
            doc = fitz.Document(pdf_path)
            page_set = niobium.parse_page_range(self.page, doc.page_count, doc=doc)
            doc.close()

            rendered_pages = niobium.render_pdf_pages(pdf_path, pages=page_set)
            n_img = sum(1 for _, img, _, _ in rendered_pages if img is not None)
            n_txt = len(rendered_pages) - n_img
            console.print(f"[cyan]{len(rendered_pages)} page(s) analyzed ({n_img} with images, {n_txt} text-only).[/cyan]")

            for page_idx, page_img, page_text, page_label in rendered_pages:
                label = f"Page {page_label}"
                if page_img is not None:
                    c_hash = content_hash_bytes(niobium.byte_convert(page_img))
                else:
                    c_hash = content_hash_bytes(page_text.encode("utf-8"))
                source = f"pdf_page:{os.path.basename(pdf_path)}:p{page_label}"
                items.append((label, page_idx, page_label, page_img, page_text, c_hash, source))

        elif self.args.get('image'):
            img_path = self.args['image']
            img = Image.open(img_path)
            label = os.path.basename(img_path)
            c_hash = content_hash_file(img_path)
            items.append((label, 0, None, img, None, c_hash, img_path))

        elif self.args.get('directory'):
            img_list = self.get_images_in_directory(self.args['directory'])
            console.print(f"[cyan]{len(img_list)} images found.[/cyan]")
            for idx, img_path in enumerate(img_list):
                img = Image.open(img_path)
                label = os.path.basename(img_path)
                c_hash = content_hash_file(img_path)
                items.append((label, idx, None, img, None, c_hash, img_path))

        return items

    def smart_generate_to_deck(self):
        """Smart generation pipeline → push to Anki via AnkiConnect."""
        deck_name = self.args["deck_name"]
        if self.deck_exists(deck_name):
            console.print(f'[cyan]Found Anki deck named {deck_name}[/cyan]')
        else:
            if Confirm.ask(f'Deck [bold]{deck_name}[/bold] not found. Create?', default=True):
                self.create_deck(deck_name)
            else:
                raise Exception('Cannot create notes without a deck. Terminating ...')

        from anki_niobium.llm import smart_generate_cards
        items = self._collect_generate_items()

        total_cards = 0
        skipped = 0
        for label, idx, display_name, img, text, c_hash, source in items:
            console.print(f"[dim]\\[{label}][/dim]")
            self.save_work_artifact(idx, page_img=img, page_text=text, display_name=display_name)

            if not self.no_cache:
                cached_info = is_processed(c_hash)
                if cached_info:
                    niobium._show_cache_hit(label, cached_info)
                    skipped += 1
                    continue

            page_bytes = niobium.byte_convert(img) if img is not None else None
            card_data = smart_generate_cards(
                idx, page_bytes, {**self.config, "_no_cache": self.no_cache},
                max_cards=self.max_cards, card_type=self.card_type, page_text=text,
                page_label=display_name,
            )
            self.save_work_artifact(idx, card_data=card_data, display_name=display_name)
            n = self.deliver_generated_cards(card_data, img, idx, deck_name=deck_name)
            total_cards += n
            mark_processed(c_hash, source, output_path=f"deck:{deck_name}", artifacts_path=self.work_dir)

        if skipped:
            console.print(f"[dim]{skipped} item(s) skipped (already in cache)[/dim]")
        console.print(f"[bold green]{total_cards} cards created from {len(items)} item(s).[/bold green]")
        if self.work_dir:
            console.print(f"[cyan]Artifacts: {self.work_dir}[/cyan]")

    def smart_generate_export_apkg(self):
        """Smart generation pipeline → export .apkg file."""
        deck_name = self.args.get('deck_name') or self._derive_deck_name()
        deck = genanki.Deck(random.randrange(1 << 30, 1 << 31), deck_name)
        media_files = []

        out_dir = self.args['apkg_out']
        os.makedirs(out_dir, exist_ok=True)
        tmp_media_dir = os.path.join(out_dir, f"nb41_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(tmp_media_dir, exist_ok=True)

        from anki_niobium.llm import smart_generate_cards
        items = self._collect_generate_items()

        total_cards = 0
        skipped = 0
        for label, idx, display_name, img, text, c_hash, source in items:
            console.print(f"[dim]\\[{label}][/dim]")
            self.save_work_artifact(idx, page_img=img, page_text=text, display_name=display_name)

            if not self.no_cache:
                cached_info = is_processed(c_hash)
                if cached_info:
                    niobium._show_cache_hit(label, cached_info)
                    skipped += 1
                    continue

            page_bytes = niobium.byte_convert(img) if img is not None else None
            card_data = smart_generate_cards(
                idx, page_bytes, {**self.config, "_no_cache": self.no_cache},
                max_cards=self.max_cards, card_type=self.card_type, page_text=text,
                page_label=display_name,
            )
            self.save_work_artifact(idx, card_data=card_data, display_name=display_name)
            n = self.deliver_generated_cards(
                card_data, img, idx,
                deck=deck, media_files=media_files, tmp_media_dir=tmp_media_dir,
            )
            total_cards += n

        apkg_path = os.path.join(out_dir, f'{self._derive_output_stem()}.apkg')
        pkg = genanki.Package(deck)
        pkg.media_files = media_files
        pkg.write_to_file(apkg_path)
        import shutil
        shutil.rmtree(tmp_media_dir)

        # Record paths for all processed items
        for label, idx, display_name, img, text, c_hash, source in items:
            mark_processed(c_hash, source, output_path=apkg_path, artifacts_path=self.work_dir)

        if skipped:
            console.print(f"[dim]{skipped} item(s) skipped (already in cache)[/dim]")
        console.print(f'[bold green]Saved {apkg_path} ({len(deck.notes)} notes, {total_cards} cards)[/bold green]')
        if self.work_dir:
            console.print(f"[cyan]Artifacts: {self.work_dir}[/cyan]")

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

        deck_name = self.args.get('deck_name') or self._derive_deck_name()
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
            tmp_path = os.path.join(tmp_media_dir, hashed_name)
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
        tmp_media_dir = os.path.join(out_dir, f"nb41_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(tmp_media_dir, exist_ok=True)

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
            doc = fitz.Document(self.args['single_pdf'])
            page_set = niobium.parse_page_range(self.page, doc.page_count, doc=doc) if self.page else None
            doc.close()
            all_images = self.extract_images_from_pdf(self.args['single_pdf'], pages=page_set)
            console.print(f'[cyan]{len(all_images)} images extracted from PDF.[/cyan]')
            skipped = 0
            for i, im in enumerate(all_images, 1):
                console.print(f'[dim]\\[{i}/{len(all_images)}][/dim]')
                if process_image(None, image_in=im, is_batch=True):
                    skipped += 1
            if skipped:
                console.print(f"[dim]{skipped} image(s) skipped (already in cache)[/dim]")

        apkg_path = os.path.join(out_dir, f'{self._derive_output_stem()}.apkg')
        pkg = genanki.Package(deck)
        pkg.media_files = media_files
        pkg.write_to_file(apkg_path)
        import shutil
        shutil.rmtree(tmp_media_dir)
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
    def parse_page_range(page_str, total_pages, doc=None):
        """Parse a page string (e.g. '5' or '5-10') into a set of 0-based page indices.

        When a fitz.Document is provided, page labels are used for resolution so
        that the user-visible page number in their PDF viewer maps to the correct
        physical page — even when the PDF has front matter that shifts numbering.
        """
        if page_str is None:
            return None
        page_str = page_str.strip()

        def _resolve_label(label):
            """Resolve a single page label to a physical page index using the PDF's label dictionary."""
            if doc is not None:
                hits = doc.get_page_numbers(label, only_one=True)
                if hits:
                    return hits[0]
            # Fallback: treat as 1-based integer
            return int(label) - 1

        if '-' in page_str:
            parts = page_str.split('-', 1)
            start = _resolve_label(parts[0].strip())
            end = _resolve_label(parts[1].strip())
            if start < 0 or end >= total_pages or start > end:
                raise ValueError(f"Invalid page range '{page_str}' for document with {total_pages} pages")
            return set(range(start, end + 1))
        else:
            page_idx = _resolve_label(page_str)
            if page_idx < 0 or page_idx >= total_pages:
                raise ValueError(f"Page {page_str} out of range (document has {total_pages} pages)")
            return {page_idx}

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
    def add_cloze_note(text, deck_name, hint=""):
        note_data = {
            "action": "addNote",
            "version": 6,
            "params": {
                "note": {
                    "deckName": deck_name,
                    "modelName": "Cloze",
                    "fields": {
                        "Text": text,
                        "Back Extra": hint,
                    },
                    "options": {"allowDuplicate": False},
                    "tags": ['NIOBIUM'],
                }
            }
        }
        response = requests.post(ANKI_LOCAL, json=note_data)
        if response.status_code == 200:
            data = json.loads(response.content)
            if data['error']:
                return (True, f"[bold red]Could not add cloze note: {data['error']}[/bold red]")
            else:
                return (True, f"[green]Cloze note added: {data['result']}[/green]")
        else:
            data = json.loads(response.content)
            return (False, f"[bold red]Could not create cloze note: {data}[/bold red]")

    @staticmethod
    def add_basic_note(front, back, deck_name):
        note_data = {
            "action": "addNote",
            "version": 6,
            "params": {
                "note": {
                    "deckName": deck_name,
                    "modelName": "Basic",
                    "fields": {
                        "Front": front,
                        "Back": back,
                    },
                    "options": {"allowDuplicate": False},
                    "tags": ['NIOBIUM'],
                }
            }
        }
        response = requests.post(ANKI_LOCAL, json=note_data)
        if response.status_code == 200:
            data = json.loads(response.content)
            if data['error']:
                return (True, f"[bold red]Could not add basic note: {data['error']}[/bold red]")
            else:
                return (True, f"[green]Basic note added: {data['result']}[/green]")
        else:
            data = json.loads(response.content)
            return (False, f"[bold red]Could not create basic note: {data}[/bold red]")

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
    def _classify_page_images(page):
        """Classify embedded images on a PDF page by shape and size.

        Returns (meaningful, decorative) where each is a list of dicts with
        keys: xref, width, height, aspect, area_ratio, kind.

        Classification rules (all in PDF points):
          - icon:       both dimensions < 50pt
          - strip:      aspect ratio > 5:1 (banners, rules, decorative bars)
          - background: covers > 80% of page area (full-page scan)
          - figure:     everything else (diagrams, charts, photos)
        """
        page_area = page.rect.width * page.rect.height
        meaningful = []
        decorative = []
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            for rect in page.get_image_rects(xref):
                w, h = rect.width, rect.height
                if w < 1 or h < 1:
                    continue
                aspect = max(w, h) / min(w, h)
                area_ratio = (w * h) / page_area if page_area > 0 else 0
                entry = dict(xref=xref, width=w, height=h, aspect=round(aspect, 1),
                             area_ratio=round(area_ratio, 2))
                if w < 50 and h < 50:
                    entry["kind"] = "icon"
                    decorative.append(entry)
                elif aspect > 5:
                    entry["kind"] = "strip"
                    decorative.append(entry)
                elif area_ratio > 0.8:
                    entry["kind"] = "background"
                    decorative.append(entry)
                else:
                    entry["kind"] = "figure"
                    meaningful.append(entry)
        return meaningful, decorative

    @staticmethod
    def render_pdf_pages(file, pages=None, dpi=200):
        """Render PDF pages for smart card generation.

        For each page, extracts structured markdown and classifies embedded
        images by shape. Pages with meaningful figures (not icons, banners, or
        full-page scans) are also rendered as images so Claude can see diagrams.

        Returns list of (page_index, image_or_None, markdown_text, page_label).
        Markdown is always extracted. Image is rendered only for pages with
        meaningful visual content that text alone cannot capture.
        """
        doc = fitz.Document(file)
        page_indices = sorted(pages) if pages else range(len(doc))
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        rendered = []
        for i in tqdm(page_indices, desc="rendering pages"):
            page = doc.load_page(i)
            page_label = page.get_label() or str(i + 1)
            md = pymupdf4llm.to_markdown(doc, pages=[i])
            meaningful, decorative = niobium._classify_page_images(page)
            # Build a concise summary for the terminal
            parts = []
            for img in meaningful:
                parts.append(f"[green]{img['kind']}[/green] {img['width']:.0f}x{img['height']:.0f}pt")
            for img in decorative:
                parts.append(f"[dim]{img['kind']} {img['width']:.0f}x{img['height']:.0f}pt[/dim]")
            img_summary = ", ".join(parts) if parts else "no images"
            if meaningful:
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                rendered.append((i, img, md, page_label))
                console.print(f"  [cyan]Page {page_label}:[/cyan] {img_summary} → [bold]image + text[/bold]")
            else:
                rendered.append((i, None, md, page_label))
                console.print(f"  [cyan]Page {page_label}:[/cyan] {img_summary} → [bold]text[/bold]")
        return rendered

    @staticmethod
    def extract_images_from_pdf(file,path=None,pages=None):
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
        page_indices = sorted(pages) if pages else range(len(doc))
        console.print(f'[cyan]Extracted images will be saved to {opdir}[/cyan]')
        count = 1
        for i in tqdm(page_indices, desc="pages"):
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
