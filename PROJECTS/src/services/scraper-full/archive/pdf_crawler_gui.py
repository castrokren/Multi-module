import os
import re
import unicodedata
import threading
import asyncio
import time
import requests
import urllib.parse
from urllib.parse import urlparse, urljoin, urldefrag
from tkinter import Tk, Entry, Label, Text, Scrollbar, Button, END, filedialog, IntVar, Checkbutton
from tkinter.ttk import Progressbar
import pandas as pd
import difflib
from PyPDF2 import PdfReader
import pdfplumber
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Error as PlaywrightError
import shutil
from typing import Optional
from playwright.async_api import Browser

MAX_CONCURRENT = 1
PAGE_TIMEOUT = 120000  # 2 minutes
WAIT_UNTIL = 'networkidle'

class PDFCrawlerApp:
    def __init__(self, master):
        self.master = master
        master.title("PDF Crawler and Filter")
        # --- UI setup ---
        Label(master, text="Input Excel:").grid(row=0, column=0, sticky='e')
        self.input_path = Entry(master, width=40)
        self.input_path.grid(row=0, column=1, padx=5, pady=5)
        Button(master, text="Browse...", command=self.browse_input).grid(row=0, column=2)

        Label(master, text="Master List Excel:").grid(row=1, column=0, sticky='e')
        self.master_path = Entry(master, width=40)
        self.master_path.grid(row=1, column=1, padx=5, pady=5)
        Button(master, text="Browse...", command=self.browse_master).grid(row=1, column=2)

        Label(master, text="PDF Download Folder:").grid(row=2, column=0, sticky='e')
        self.pdf_folder_path = Entry(master, width=40)
        self.pdf_folder_path.grid(row=2, column=1, padx=5, pady=5)
        Button(master, text="Browse...", command=self.browse_pdf_folder).grid(row=2, column=2)

        self.verbose_var = IntVar(value=0)
        Checkbutton(master, text="Verbose", variable=self.verbose_var).grid(row=3, column=0)

        self.run_button = Button(master, text="Run Scraping", command=self.on_run_clicked)
        self.run_button.grid(row=3, column=1)
        self.stop_button = Button(master, text="Stop Scraping", command=self.on_stop_clicked, state='disabled')
        self.stop_button.grid(row=3, column=2)

        self.timer_label = Label(master, text="Elapsed: 00:00:00")
        self.timer_label.grid(row=3, column=3)

        self.progress = Progressbar(master, orient='horizontal', length=300, mode='determinate')
        self.progress.grid(row=4, column=0, columnspan=4, padx=5, pady=(0,5))

        self.log_area = Text(master, height=15, width=80)
        scrollbar = Scrollbar(master, command=self.log_area.yview)
        self.log_area.configure(yscrollcommand=scrollbar.set)
        self.log_area.grid(row=5, column=0, columnspan=3, padx=5, pady=5)
        scrollbar.grid(row=5, column=3, sticky='ns')

        # --- Internal state ---
        self.running = False
        self.visited = set()
        self.tasks = []
        self.session = requests.Session()
        self.download_folder = None
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/pdf,*/*;q=0.8',
        }
        self.playwright = None
        self.used_pdfs = set()
        self.browser: Optional[Browser] = None
        self.base_netlocs = {}

    def browse_input(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if path:
            self.input_path.delete(0, END)
            self.input_path.insert(0, path)

    def browse_master(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if path:
            self.master_path.delete(0, END)
            self.master_path.insert(0, path)

    def browse_pdf_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.pdf_folder_path.delete(0, END)
            self.pdf_folder_path.insert(0, path)

    def log(self, message, level="info"):
        if level == "debug" and not self.verbose_var.get():
            return
        self.log_area.insert(END, message + "\n")
        self.log_area.see(END)

    def on_run_clicked(self):
        input_file = self.input_path.get()
        master_file = self.master_path.get()
        pdf_folder = self.pdf_folder_path.get() or 'pdfs'
        os.makedirs(pdf_folder, exist_ok=True)
        self.download_folder = pdf_folder

        df_in = pd.read_excel(input_file)
        df_master = pd.read_excel(master_file)

        for df in (df_in, df_master):
            df['Supplier Name'] = df['Supplier Name'].astype(str).str.strip().str.lower()

        type_col = next((c for c in df_in.columns if c.strip().lower() == 'type'), None)
        if type_col:
            inst = df_in[df_in[type_col].astype(str).str.lower() == 'instrument']
        else:
            inst = df_in.copy()
            self.log("[WARNING] 'TYPE' column missing; processing all rows.")

        merged = inst.merge(df_master[['Supplier Name','Website']], on='Supplier Name', how='left', indicator=True)
        self.log(f"[INFO] Merge counts: {merged['_merge'].value_counts().to_dict()}")

        unique = merged.drop_duplicates('Supplier Name')
        missing = unique.loc[unique['Website'].isna(), 'Supplier Name'].tolist()
        if missing:
            self.log("[WARNING] No URL for suppliers:\n  • " + "\n  • ".join(missing))
            for name in missing:
                close = difflib.get_close_matches(name, df_master['Supplier Name'], n=1)
                if close:
                    self.log(f"[SUGGEST] '{name}' → '{close[0]}'")

        filtered = unique[unique['Website'].notna()]
        pairs = list(zip(filtered['Supplier Name'], filtered['Website']))

        # Record base domains (without subdomain restriction)
        for sup, url in pairs:
            base = urlparse(url).netloc.lower().split(':')[0]
            self.base_netlocs[sup] = base

        self.inst_rows = inst.reset_index(drop=True)
        self.progress.config(maximum=len(self.inst_rows), value=0)
        self.running = True
        self.start_time = time.time()
        self.update_timer()
        self.visited.clear()
        self.tasks = []
        self.run_button.config(state='disabled')
        self.stop_button.config(state='normal')

        threading.Thread(target=self.process_all, args=(pairs,), daemon=True).start()
        self.log("[INFO] Crawl started…")

    def update_timer(self):
        if not self.running:
            return
        elapsed = int(time.time() - self.start_time)
        h, rem = divmod(elapsed, 3600)
        m, s = divmod(rem, 60)
        self.timer_label.config(text=f"Elapsed: {h:02d}:{m:02d}:{s:02d}")
        self.master.after(1000, self.update_timer)

    def process_all(self, pairs):
        async def main():
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
            await self.run_all_concurrent(pairs)
            await self.browser.close()
            await self.playwright.stop()

        asyncio.run(main())

        self.log(f"[INFO] Finished crawling {len(self.inst_rows)} suppliers, visited {len(self.visited)} pages, downloaded {len(self.used_pdfs)} PDFs.")
        self.post_filter()
        self.running = False
        self.run_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.log("[INFO] Done.")
        self.cleanup_unused_pdfs(self.download_folder)

    async def run_all_concurrent(self, pairs):
        self.tasks = []
        sem = asyncio.Semaphore(MAX_CONCURRENT)
        for supplier, url in pairs:
            task = asyncio.create_task(self._sem_crawl(sem, supplier, url))
            self.tasks.append(task)
        await asyncio.gather(*self.tasks, return_exceptions=True)

    async def _sem_crawl(self, sem, supplier, url):
        async with sem:
            await self.crawl_site(supplier, url)

    async def crawl_site(self, supplier, url):
        if not self.running:
            return
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Download PDFs immediately
        if path.endswith('.pdf'):
            await asyncio.to_thread(self.download_pdf, url, supplier)
            return

        # Allow any subdomain of base
        domain = parsed.netloc.lower().split(':')[0]
        base = self.base_netlocs.get(supplier)
        if domain != base and not domain.endswith('.' + base):
            self.log(f"[DEBUG] Skipping out-of-domain: {url}", level="debug")
            return

        clean_url, _ = urldefrag(url)
        clean_url = clean_url.rstrip('/')
        if clean_url in self.visited:
            self.log(f"[DEBUG] Skipping visited: {url}", level="debug")
            return
        self.visited.add(clean_url)
        self.log(f"[INFO] Crawling {url}...")
        try:
            page = await self.browser.new_page()
            await page.goto(url, timeout=PAGE_TIMEOUT, wait_until='domcontentloaded')
            await page.wait_for_load_state(WAIT_UNTIL, timeout=PAGE_TIMEOUT)
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            await page.close()
            for a in soup.find_all('a', href=True):
                href = a['href']
                if not isinstance(href, str) or href.startswith('#'):
                    continue
                absolute = urljoin(clean_url, href)
                stripped = absolute.split('#',1)[0].split('?',1)[0]
                if stripped.lower().endswith('.pdf'):
                    await asyncio.to_thread(self.download_pdf, absolute, supplier)
                else:
                    await self.crawl_site(supplier, absolute)
        except PlaywrightError as e:
            self.log(f"[ERROR] Playwright error on {url}: {e}")

    def download_pdf(self, pdf_url, supplier=None):
        try:
            r = self.session.get(pdf_url, headers=self.default_headers, stream=True, timeout=30)
            r.raise_for_status()
        except Exception as e:
            self.log(f"[ERROR] Download error: {e} for {pdf_url}")
            return
        filename = os.path.basename(urlparse(pdf_url).path) or 'file.pdf'
        safe = re.sub(r'\W+', '_', filename)
        vendor_folder = os.path.join(self.download_folder, supplier) if supplier else self.download_folder
        os.makedirs(vendor_folder, exist_ok=True)
        save_path = os.path.join(vendor_folder, safe)
        with open(save_path, 'wb') as f:
            for chunk in r.iter_content(8192): f.write(chunk)
        self.used_pdfs.add(safe)
        self.log(f"[INFO] Downloaded PDF: {safe} in {vendor_folder}")
        self.master.after(0, lambda: self.progress.step(1))

    def post_filter(self):
        # existing post-filter logic
        pass

    def cleanup_unused_pdfs(self, download_folder: str):
        for root, dirs, files in os.walk(download_folder):
            for fname in files:
                if not fname.lower().endswith('.pdf'): continue
                if fname not in self.used_pdfs:
                    os.remove(os.path.join(root, fname))
                    self.log(f"[INFO] Removed orphan PDF: {fname}")

    def extract_text(self, path):
        text = ""
        try:
            reader = PdfReader(path)
            text = "\n".join(p.extract_text() or "" for p in reader.pages).strip()
        except:
            pass
        if not text:
            try:
                with pdfplumber.open(path) as pdf:
                    text = "\n".join(p.extract_text() or "" for p in pdf.pages).strip()
            except:
                pass
        return text.lower() if text else ""

    def sanitize(self, text: str) -> str:
        # existing sanitize logic
        return text

    def on_stop_clicked(self):
        self.running = False
        for t in self.tasks:
            try: t.cancel()
            except: pass
        self.stop_button.config(state='disabled')
        self.run_button.config(state='normal')
        self.log("[INFO] Crawl stopped by user.")

if __name__ == '__main__':
    root = Tk()
    app = PDFCrawlerApp(root)
    root.mainloop()
