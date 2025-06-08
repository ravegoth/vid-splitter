import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import re
import threading
import configparser
import sys
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

# ---------------- config persistence ----------------
cfg_path = os.path.join(os.path.dirname(sys.argv[0]), "config.ini")
cfg = configparser.ConfigParser()
if os.path.exists(cfg_path):
    cfg.read(cfg_path)
last_video = cfg.get("paths", "last_video", fallback="")
last_out = cfg.get("paths", "last_out",   fallback=os.getcwd())


def save_paths(video_path, out_dir):
    cfg["paths"] = {"last_video": video_path, "last_out": out_dir}
    with open(cfg_path, "w") as f:
        cfg.write(f)

# ---------------- helpers ----------------


def center(win):
    win.update_idletasks()
    w, h = win.winfo_width(), win.winfo_height()
    x = (win.winfo_screenwidth() // 2) - (w // 2)
    y = (win.winfo_screenheight() // 2) - (h // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")


def safe_name(name: str) -> str:
    return re.sub(r"[^\w\-\.]", "_", name)

# ---------------- core split threaded ----------------


def split_video_threaded(filename: str, num_parts: int, output_dir: str):
    try:
        for w in all_widgets:
            w.config(state=tk.DISABLED)

        clip = VideoFileClip(filename)
        total = int(clip.duration)
        if total == 0:
            raise ValueError("video duration is zero")

        part_len = total // num_parts
        if part_len == 0:
            messagebox.showwarning(
                "warning",
                f"video too short ({total}s) for {num_parts} parts – "
                "some parts will be <1 s"
            )

        start = 0
        for i in range(num_parts):
            end = total if i == num_parts - 1 else start + part_len
            out_name = f"{safe_name(os.path.splitext(os.path.basename(filename))[0])}_part_{i+1}.mp4"
            out_path = os.path.join(output_dir, out_name)
            ffmpeg_extract_subclip(filename, start, end, targetname=out_path)
            start = end
            progress["value"] = i + 1
            progress_txt.set(
                f"{i+1} / {num_parts}   –   {int((i+1)/num_parts*100)} %")
            root.update_idletasks()

        clip.close()
        save_paths(filename, output_dir)
        messagebox.showinfo("done", f"split complete in\n{output_dir}")
    except Exception as e:
        messagebox.showerror("error", str(e))
    finally:
        progress["value"] = 0
        progress_txt.set("0 %")
        for w in all_widgets:
            w.config(state=tk.NORMAL)

# ---------------- gui callbacks ----------------


def start_split():
    fn = video_path.get()
    out = out_dir.get()
    parts = parts_entry.get()

    if not fn:
        messagebox.showerror("input error", "select a video file")
        return
    if not parts.isdigit() or int(parts) < 1:
        messagebox.showerror("input error", "parts must be a positive integer")
        return
    if not out:
        messagebox.showerror("input error", "select an output folder")
        return

    t = threading.Thread(
        target=split_video_threaded,
        args=(fn, int(parts), out),
        daemon=True
    )
    t.start()


def browse_video():
    path = filedialog.askopenfilename(
        title="choose mp4",
        filetypes=[("mp4 files", "*.mp4"), ("all files", "*.*")]
    )
    if path:
        video_path.set(path)


def browse_out():
    path = filedialog.askdirectory(title="choose output folder")
    if path:
        out_dir.set(path)


# ---------------- build gui ----------------
root = tk.Tk()
root.title("video splitter")
root.configure(bg="#fff")
root.resizable(False, False)

# style tweaks
style = ttk.Style(root)
style.theme_use("clam")
style.configure(".", background="#fff", foreground="#000", font=("inter", 10))
style.configure("TButton", padding=6, background="#fff", foreground="#000")
style.map("TButton",
        background=[("active", "#444")],
        foreground=[("disabled", "#777")])
style.configure("TEntry", fieldbackground="#fff", bordercolor="#555")
style.configure("TProgressbar", troughcolor="#fff", bordercolor="#555",
                background="#0078d4", thickness=18)

pad = {'padx': 8, 'pady': 4}

# --- video file row
video_path = tk.StringVar(value=last_video)
tk.Label(root, text="video file:", bg="#fff").grid(
    row=0, column=0, sticky="w", **pad)
ttk.Entry(root, textvariable=video_path, width=48).grid(row=0, column=1, **pad)
ttk.Button(root, text="browse", command=browse_video).grid(
    row=0, column=2, **pad)

# --- output dir row
out_dir = tk.StringVar(value=last_out)
tk.Label(root, text="output folder:", bg="#fff").grid(
    row=1, column=0, sticky="w", **pad)
ttk.Entry(root, textvariable=out_dir, width=48).grid(row=1, column=1, **pad)
ttk.Button(root, text="browse", command=browse_out).grid(
    row=1, column=2, **pad)

# --- parts row
tk.Label(root, text="number of parts:", bg="#fff").grid(
    row=2, column=0, sticky="w", **pad)
parts_entry = ttk.Entry(root, width=10)
parts_entry.grid(row=2, column=1, sticky="w", **pad)
parts_entry.insert(0, "2")

# --- split button
ttk.Button(root, text="split", command=start_split).grid(
    row=3, column=1, pady=12)

# --- progress bar + label
progress_txt = tk.StringVar(value="0 %")
progress = ttk.Progressbar(root, length=430, mode="determinate")
progress.grid(row=4, column=0, columnspan=3, padx=10, pady=(0, 4))
tk.Label(root, textvariable=progress_txt, bg="#fff").grid(
    row=5, column=0, columnspan=3)

# collect widgets to enable/disable easily
all_widgets = (root.grid_slaves(row=0, column=2)[0],
            root.grid_slaves(row=0, column=1)[0],
            root.grid_slaves(row=0, column=2)[0],
            root.grid_slaves(row=1, column=2)[0],
            root.grid_slaves(row=3, column=1)[0])

center(root)
root.mainloop()
