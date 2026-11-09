"""
YouTube Video Downloader (yt-dlp + Tkinter)

Setup:
    pip install -U yt-dlp
    Install FFmpeg and make sure it is on your PATH (needed for merging
    video+audio and for MP3 conversion).

Run:
    python yt_downloader.py

Only download content you own, that is licensed for download, or that you
otherwise have permission to save. Respect YouTube's Terms of Service.
"""

import threading
import tkinter as tk
from pathlib import Path
from shutil import which
from tkinter import filedialog, messagebox, ttk

import yt_dlp


class DownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Downloader")
        self.geometry("560x330")
        self.resizable(False, False)

        self.url_var = tk.StringVar()
        self.folder_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.mode_var = tk.StringVar(value="Video (MP4)")
        self.quality_var = tk.StringVar(value="Best")
        self.playlist_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready")

        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}
        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=8, pady=8)

        ttk.Label(frm, text="Video URL").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.url_var, width=52).grid(
            row=0, column=1, columnspan=2, sticky="ew", **pad
        )

        ttk.Label(frm, text="Save to").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.folder_var, width=38).grid(
            row=1, column=1, sticky="ew", **pad
        )
        ttk.Button(frm, text="Browse", command=self._browse).grid(
            row=1, column=2, sticky="e", **pad
        )

        ttk.Label(frm, text="Format").grid(row=2, column=0, sticky="w", **pad)
        ttk.Combobox(
            frm,
            textvariable=self.mode_var,
            values=["Video (MP4)", "Audio (MP3)"],
            state="readonly",
            width=16,
        ).grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(frm, text="Max quality").grid(row=3, column=0, sticky="w", **pad)
        ttk.Combobox(
            frm,
            textvariable=self.quality_var,
            values=["Best", "1080p", "720p", "480p", "360p"],
            state="readonly",
            width=16,
        ).grid(row=3, column=1, sticky="w", **pad)

        ttk.Checkbutton(
            frm, text="Download whole playlist", variable=self.playlist_var
        ).grid(row=4, column=1, sticky="w", **pad)

        self.progress = ttk.Progressbar(frm, maximum=100)
        self.progress.grid(row=5, column=0, columnspan=3, sticky="ew", **pad)

        ttk.Label(frm, textvariable=self.status_var).grid(
            row=6, column=0, columnspan=2, sticky="w", **pad
        )
        self.btn = ttk.Button(frm, text="Download", command=self._start)
        self.btn.grid(row=6, column=2, sticky="e", **pad)

        frm.columnconfigure(1, weight=1)

    def _browse(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)

    # ---------- Download logic ----------
    def _start(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please paste a video URL.")
            return

        out_dir = self.folder_var.get().strip()
        if not out_dir:
            messagebox.showwarning("Missing folder", "Please choose a save folder.")
            return

        mode = self.mode_var.get()
        if not which("ffmpeg"):
            messagebox.showerror(
                "FFmpeg required",
                "FFmpeg is required for video merging and MP3 conversion. "
                "Install FFmpeg and make sure it is on your PATH.",
            )
            return

        options = self._build_options(
            out_dir,
            mode,
            self.quality_var.get(),
            self.playlist_var.get(),
        )
        self.btn.config(state="disabled")
        self.progress["value"] = 0
        self.status_var.set("Starting...")
        threading.Thread(
            target=self._download,
            args=(url, out_dir, options),
            daemon=True,
        ).start()

    def _build_options(self, out_dir, mode, quality, download_playlist):
        opts = {
            "outtmpl": str(Path(out_dir) / "%(title)s.%(ext)s"),
            "noplaylist": not download_playlist,
            "progress_hooks": [self._hook],
            "quiet": True,
            "no_warnings": True,
        }

        if mode == "Audio (MP3)":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
        else:
            q = quality
            cap = "" if q == "Best" else f"[height<={q.rstrip('p')}]"
            opts["format"] = (
                f"bestvideo{cap}[ext=mp4]+bestaudio[ext=m4a]/"
                f"bestvideo{cap}+bestaudio/best{cap}"
            )
            opts["merge_output_format"] = "mp4"
        return opts

    def _download(self, url, out_dir, options):
        try:
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([url])
            self.after(0, self._done, "Download complete!", True)
        except Exception as exc:  # show any yt-dlp error to the user
            self.after(0, self._done, f"Error: {exc}", False)

    def _hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total:
                pct = d["downloaded_bytes"] / total * 100
                speed = d.get("_speed_str", "").strip()
                eta = d.get("_eta_str", "").strip()
                self.after(0, self._update, pct, f"{pct:.1f}%  {speed}  ETA {eta}")
        elif d["status"] == "finished":
            self.after(0, self._update, 100, "Processing...")

    def _update(self, pct, text):
        self.progress["value"] = pct
        self.status_var.set(text)

    def _done(self, message, ok):
        self.btn.config(state="normal")
        self.status_var.set(message[:70])
        if ok:
            messagebox.showinfo("Done", message)
        else:
            messagebox.showerror("Failed", message)


if __name__ == "__main__":
    DownloaderApp().mainloop()
