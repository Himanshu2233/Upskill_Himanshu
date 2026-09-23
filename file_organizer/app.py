# app.py — Desktop UI for File Organizer using Tkinter
#
# Tkinter is Python's BUILT-IN GUI library.
# No pip install needed!
#
# Key concepts:
#   - tk.Tk()        → the main window
#   - widgets        → buttons, labels, text boxes (like HTML elements)
#   - .pack()/.grid()→ layout (like CSS flexbox/grid)
#   - command=       → what to do when a button is clicked (like onclick)
#   - StringVar()    → a special variable that auto-updates the UI when changed

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading                # lets us run organize() without freezing the UI
import os
from organizer import organize_directory   # import our core logic!


# ─────────────────────────────────────────
# COLOR PALETTE
# ─────────────────────────────────────────
COLORS = {
    'bg':         '#0f172a',   # Dark navy background
    'card':       '#1e293b',   # Slightly lighter card
    'border':     '#334155',   # Subtle borders
    'primary':    '#7c3aed',   # Purple accent
    'primary_lt': '#a78bfa',   # Light purple
    'accent':     '#06b6d4',   # Cyan
    'success':    '#10b981',   # Green
    'warning':    '#f59e0b',   # Amber
    'error':      '#ef4444',   # Red
    'text':       '#f1f5f9',   # Near-white text
    'text_muted': '#94a3b8',   # Muted grey text
}

FONT_TITLE  = ('Segoe UI', 22, 'bold')
FONT_LABEL  = ('Segoe UI', 10)
FONT_BOLD   = ('Segoe UI', 10, 'bold')
FONT_MONO   = ('Consolas', 9)
FONT_SMALL  = ('Segoe UI', 8)


# ─────────────────────────────────────────
# MAIN APPLICATION CLASS
# ─────────────────────────────────────────
class FileOrganizerApp:
    """
    This is our main app class.
    It holds the window and all widgets (UI elements).
    
    We use a class so we can easily share data between methods
    (e.g., self.selected_path is accessible everywhere in the class).
    """

    def __init__(self, root):
        self.root = root
        self.root.title('📁 File Organizer')
        self.root.geometry('780x620')
        self.root.minsize(680, 520)
        self.root.configure(bg=COLORS['bg'])
        self.root.resizable(True, True)

        # StringVar = a Tkinter-aware string. When it changes, UI auto-updates.
        self.selected_path = tk.StringVar(value='No folder selected')
        self.status_text   = tk.StringVar(value='Ready. Select a folder to begin.')
        self.dry_run_var   = tk.BooleanVar(value=True)   # Checkbox state

        self._build_ui()

    # ── BUILD THE FULL UI ──────────────────────────────────────────────────
    def _build_ui(self):
        """Assembles all the UI pieces."""

        # ── Header ──
        header = tk.Frame(self.root, bg=COLORS['bg'], pady=20)
        header.pack(fill='x', padx=30)

        tk.Label(header, text='📁', font=('Segoe UI', 32),
                 bg=COLORS['bg'], fg=COLORS['primary']).pack(side='left')

        title_frame = tk.Frame(header, bg=COLORS['bg'])
        title_frame.pack(side='left', padx=12)
        tk.Label(title_frame, text='File Organizer', font=FONT_TITLE,
                 bg=COLORS['bg'], fg=COLORS['text']).pack(anchor='w')
        tk.Label(title_frame, text='Organize your messy folders in one click',
                 font=FONT_SMALL, bg=COLORS['bg'], fg=COLORS['text_muted']).pack(anchor='w')

        # ── Folder Selector Card ──
        self._card(label='📂  Select Folder', builder=self._build_folder_section)

        # ── Options Card ──
        self._card(label='⚙️  Options', builder=self._build_options_section)

        # ── Action Buttons ──
        btn_frame = tk.Frame(self.root, bg=COLORS['bg'])
        btn_frame.pack(fill='x', padx=30, pady=(0, 8))

        self._btn(btn_frame, '🔍  Preview  (Dry Run)', self._run_dry,
                  COLORS['accent'], side='left')
        self._btn(btn_frame, '⚡  Organize Now!', self._run_organize,
                  COLORS['primary'], side='left', padleft=10)

        # ── Log / Output Area ──
        self._card(label='📋  Output Log', builder=self._build_log_section, expand=True)

        # ── Status Bar ──
        status_bar = tk.Frame(self.root, bg=COLORS['border'], height=1)
        status_bar.pack(fill='x')
        tk.Label(self.root, textvariable=self.status_text, font=FONT_SMALL,
                 bg=COLORS['bg'], fg=COLORS['text_muted'], anchor='w',
                 pady=6).pack(fill='x', padx=30)

    # ── CARD HELPER — creates a styled panel ──────────────────────────────
    def _card(self, label, builder, expand=False):
        """Creates a labeled card (panel) with a builder function filling it."""
        outer = tk.Frame(self.root, bg=COLORS['bg'])
        outer.pack(fill='both' if expand else 'x', padx=30, pady=(0, 10),
                   expand=expand)

        # Card title
        tk.Label(outer, text=label, font=FONT_BOLD,
                 bg=COLORS['bg'], fg=COLORS['text_muted']).pack(anchor='w', pady=(0, 4))

        # The card body
        card = tk.Frame(outer, bg=COLORS['card'],
                        highlightbackground=COLORS['border'],
                        highlightthickness=1)
        card.pack(fill='both', expand=expand)

        builder(card)   # call the section builder to fill the card

    # ── BUTTON HELPER ─────────────────────────────────────────────────────
    def _btn(self, parent, text, command, color, side='left', padleft=0):
        btn = tk.Button(parent, text=text, command=command,
                        bg=color, fg='white', font=FONT_BOLD,
                        relief='flat', cursor='hand2',
                        padx=18, pady=10, bd=0)
        btn.pack(side=side, padx=(padleft, 0))
        # Hover effect
        btn.bind('<Enter>', lambda e: btn.config(bg=self._lighten(color)))
        btn.bind('<Leave>', lambda e: btn.config(bg=color))
        return btn

    def _lighten(self, hex_color):
        """Makes a hex color slightly brighter for hover effect."""
        r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        r, g, b = min(255, r+30), min(255, g+30), min(255, b+30)
        return f'#{r:02x}{g:02x}{b:02x}'

    # ── SECTION BUILDERS ──────────────────────────────────────────────────

    def _build_folder_section(self, card):
        """Builds the folder path row."""
        row = tk.Frame(card, bg=COLORS['card'])
        row.pack(fill='x', padx=16, pady=12)

        # Path display label
        path_label = tk.Label(row, textvariable=self.selected_path,
                              font=FONT_MONO, bg=COLORS['bg'],
                              fg=COLORS['accent'], anchor='w',
                              relief='flat', padx=10, pady=8,
                              width=55, wraplength=480)
        path_label.pack(side='left', fill='x', expand=True)

        # Browse button
        browse_btn = tk.Button(row, text='Browse...', command=self._browse,
                               bg=COLORS['primary'], fg='white',
                               font=FONT_BOLD, relief='flat',
                               cursor='hand2', padx=14, pady=8)
        browse_btn.pack(side='right', padx=(10, 0))

    def _build_options_section(self, card):
        """Builds the options checkboxes."""
        row = tk.Frame(card, bg=COLORS['card'])
        row.pack(fill='x', padx=16, pady=10)

        # Dry-run checkbox
        dry_cb = tk.Checkbutton(row, text='Preview mode (show moves without doing them)',
                                variable=self.dry_run_var,
                                bg=COLORS['card'], fg=COLORS['text'],
                                selectcolor=COLORS['bg'],
                                font=FONT_LABEL, activebackground=COLORS['card'],
                                activeforeground=COLORS['text'])
        dry_cb.pack(side='left')

    def _build_log_section(self, card):
        """Builds the scrollable log output area."""
        self.log = scrolledtext.ScrolledText(
            card, font=FONT_MONO,
            bg=COLORS['bg'], fg=COLORS['text'],
            insertbackground=COLORS['text'],
            relief='flat', padx=12, pady=10,
            state='disabled',    # Read-only by default
            wrap='word'
        )
        self.log.pack(fill='both', expand=True, padx=2, pady=2)

        # Tag styles for colored text in the log
        self.log.tag_config('header',  foreground=COLORS['primary_lt'], font=('Consolas', 9, 'bold'))
        self.log.tag_config('success', foreground=COLORS['success'])
        self.log.tag_config('skip',    foreground=COLORS['text_muted'])
        self.log.tag_config('error',   foreground=COLORS['error'])
        self.log.tag_config('info',    foreground=COLORS['accent'])
        self.log.tag_config('warn',    foreground=COLORS['warning'])

    # ── EVENT HANDLERS ────────────────────────────────────────────────────

    def _browse(self):
        """Opens a folder picker dialog."""
        # filedialog.askdirectory() opens the native OS folder browser!
        folder = filedialog.askdirectory(title='Select a folder to organize')
        if folder:
            self.selected_path.set(folder)
            self.status_text.set(f'Folder selected: {folder}')

    def _log_write(self, text, tag=None):
        """Appends a line to the log box."""
        self.log.config(state='normal')
        if tag:
            self.log.insert('end', text + '\n', tag)
        else:
            self.log.insert('end', text + '\n')
        self.log.see('end')           # Auto-scroll to bottom
        self.log.config(state='disabled')

    def _log_clear(self):
        self.log.config(state='normal')
        self.log.delete('1.0', 'end')
        self.log.config(state='disabled')

    def _run_dry(self):
        """Forces a dry run preview."""
        self.dry_run_var.set(True)
        self._start_organize()

    def _run_organize(self):
        """Confirms then runs the actual organize."""
        path = self.selected_path.get()
        if path == 'No folder selected':
            messagebox.showwarning('No Folder', 'Please select a folder first!')
            return
        confirm = messagebox.askyesno(
            'Confirm',
            f'This will move files in:\n\n{path}\n\nAre you sure?'
        )
        if confirm:
            self.dry_run_var.set(False)
            self._start_organize()

    def _start_organize(self):
        """
        Runs the organize task in a BACKGROUND THREAD.
        
        Why? Because organize_directory() could take a few seconds for large folders.
        If we ran it directly, the window would FREEZE until it's done (bad UX!).
        threading.Thread lets it run in the background while the UI stays responsive.
        """
        path = self.selected_path.get()
        if path == 'No folder selected':
            messagebox.showwarning('No Folder', 'Please select a folder first!')
            return

        self._log_clear()
        self.status_text.set('Working...')

        # Run in background thread so UI doesn't freeze
        thread = threading.Thread(target=self._do_organize, args=(path,), daemon=True)
        thread.start()

    def _do_organize(self, path):
        """The actual work — called from the background thread."""
        dry_run = self.dry_run_var.get()
        mode = '🔍 PREVIEW MODE' if dry_run else '⚡ ORGANIZING'

        self._log_write(f'{"─"*55}', 'header')
        self._log_write(f'  {mode}', 'header')
        self._log_write(f'  Folder: {path}', 'info')
        self._log_write(f'{"─"*55}', 'header')

        result = organize_directory(path, dry_run=dry_run)

        if 'error' in result:
            self._log_write(f'\n❌ Error: {result["error"]}', 'error')
            self.status_text.set('Error — see log.')
            return

        # Show moved files grouped by category
        if result['moved']:
            categories = {}
            for item in result['moved']:
                categories.setdefault(item['category'], []).append(item['file'])

            for category, files in sorted(categories.items()):
                self._log_write(f'\n📁 {category}  ({len(files)} files)', 'info')
                for f in files:
                    arrow = '  →  ' if not dry_run else '  ≫  '
                    self._log_write(f'    {arrow}{f}', 'success')
        else:
            self._log_write('\n✅ Nothing to move — folder is already organized!', 'success')

        # Show skipped items
        if result['skipped']:
            self._log_write(f'\n⏭️  Skipped ({len(result["skipped"])} items):', 'skip')
            for s in result['skipped']:
                self._log_write(f'     {s}', 'skip')

        # Show errors
        for e in result['errors']:
            self._log_write(f'\n❌ Error moving {e["file"]}: {e["error"]}', 'error')

        # Summary
        self._log_write(f'\n{"─"*55}', 'header')
        action_word = 'Would move' if dry_run else 'Moved'
        self._log_write(f'  ✅ {action_word} {len(result["moved"])} files', 'success' if result['moved'] else 'warn')
        if dry_run:
            self._log_write('  ℹ️  This was a PREVIEW. Uncheck "Preview mode" to actually move files.', 'warn')
        self._log_write(f'{"─"*55}', 'header')

        self.status_text.set(
            f'{"Preview" if dry_run else "Done!"} — '
            f'{len(result["moved"])} files {"would be" if dry_run else ""} organized.'
        )


# ─────────────────────────────────────────
# LAUNCH THE APP
# ─────────────────────────────────────────
if __name__ == '__main__':
    root = tk.Tk()
    app  = FileOrganizerApp(root)
    root.mainloop()   # Starts the event loop — keeps window open and responsive
