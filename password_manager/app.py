# app.py — Password Manager (Premium UI)
# Screens: Setup → Login → Main Vault

import tkinter as tk
from tkinter import ttk, messagebox
import threading

from crypto    import derive_key, generate_salt, encrypt, decrypt, verify_master_password
from database  import initialize_db, is_master_set, save_master, get_master, \
                      add_password, get_all_passwords, delete_password, search_passwords
from generator import generate_password, check_strength

# ── Clipboard ──────────────────────────────────────────────────────────────
def copy_to_clipboard(root, text):
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN TOKENS
# ─────────────────────────────────────────────────────────────────────────────
C = {
    'bg':       '#080d1a',   # Deep space black
    'bg2':      '#0d1526',   # Slightly lighter
    'sidebar':  '#10192e',   # Sidebar panel
    'card':     '#141f35',   # Card background
    'card2':    '#1a2845',   # Hover card
    'border':   '#1e3050',   # Subtle border
    'border2':  '#2a4070',   # Active border
    'primary':  '#6d28d9',   # Deep violet
    'p_mid':    '#7c3aed',   # Violet
    'p_lite':   '#a78bfa',   # Light violet
    'accent':   '#0891b2',   # Teal
    'a_lite':   '#22d3ee',   # Light teal
    'success':  '#059669',   # Green
    's_lite':   '#34d399',   # Light green
    'warn':     '#d97706',   # Amber
    'error':    '#dc2626',   # Red
    'e_lite':   '#f87171',   # Light red
    'text':     '#e2e8f0',   # Near white
    'text2':    '#cbd5e1',   # Slightly dimmed
    'muted':    '#64748b',   # Muted grey
    'muted2':   '#475569',   # Darker muted
}

# Service icon mapping
SERVICE_ICONS = {
    'google': '🔵', 'gmail': '📧', 'youtube': '▶️',
    'github': '🐙', 'gitlab': '🦊',
    'facebook': '👤', 'instagram': '📸', 'twitter': '🐦', 'x': '✖️',
    'netflix': '🎬', 'spotify': '🎵', 'amazon': '📦',
    'microsoft': '🪟', 'outlook': '📨', 'office': '🗂️',
    'apple': '🍎', 'icloud': '☁️',
    'discord': '💬', 'slack': '💼', 'zoom': '📹',
    'paypal': '💳', 'bank': '🏦',
    'steam': '🎮', 'epic': '🎮',
    'linkedin': '🔗',
}

def get_service_icon(service_name):
    s = service_name.lower()
    for key, icon in SERVICE_ICONS.items():
        if key in s:
            return icon
    return '🔐'

def get_service_color(service_name):
    """Return a color accent based on service type."""
    s = service_name.lower()
    if any(k in s for k in ['google','gmail','youtube']): return '#4285f4'
    if any(k in s for k in ['github','gitlab']):          return '#6e7681'
    if any(k in s for k in ['facebook','instagram']):     return '#e1306c'
    if any(k in s for k in ['netflix']):                  return '#e50914'
    if any(k in s for k in ['spotify']):                  return '#1db954'
    if any(k in s for k in ['twitter','x']):              return '#1da1f2'
    if any(k in s for k in ['amazon']):                   return '#ff9900'
    if any(k in s for k in ['discord']):                  return '#5865f2'
    if any(k in s for k in ['microsoft','outlook']):      return '#0078d4'
    if any(k in s for k in ['apple','icloud']):           return '#a2aaad'
    if any(k in s for k in ['paypal']):                   return '#003087'
    if any(k in s for k in ['steam','epic']):             return '#171a21'
    return C['p_mid']


# ─────────────────────────────────────────────────────────────────────────────
# TTK STYLE SETUP
# ─────────────────────────────────────────────────────────────────────────────
def apply_styles(root):
    style = ttk.Style(root)
    style.theme_use('clam')

    # Scrollbar
    style.configure('Dark.Vertical.TScrollbar',
                    background=C['border'], troughcolor=C['bg'],
                    bordercolor=C['bg'], arrowcolor=C['muted'],
                    relief='flat')
    style.map('Dark.Vertical.TScrollbar',
              background=[('active', C['border2'])])

    # Progress bar (strength meter)
    style.configure('Strength.Horizontal.TProgressbar',
                    background=C['s_lite'], troughcolor=C['card'],
                    bordercolor=C['card'], lightcolor=C['s_lite'],
                    darkcolor=C['s_lite'], thickness=6)


# ─────────────────────────────────────────────────────────────────────────────
# REUSABLE WIDGET HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def styled_btn(parent, text, cmd, bg=None, fg=C['text'],
               pad_x=16, pad_y=9, font_size=9, **kw):
    bg = bg or C['p_mid']
    b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                  font=('Segoe UI', font_size, 'bold'), relief='flat',
                  cursor='hand2', padx=pad_x, pady=pad_y,
                  activebackground=_lighten(bg), activeforeground=fg, bd=0, **kw)
    b.bind('<Enter>', lambda e: b.config(bg=_lighten(bg)))
    b.bind('<Leave>', lambda e: b.config(bg=bg))
    return b

def styled_entry(parent, show=None, width=32, textvariable=None, font_size=10):
    f = tk.Frame(parent, bg=C['border2'], padx=1, pady=1)
    e = tk.Entry(f, font=('Consolas', font_size), bg=C['card2'],
                 fg=C['text'], insertbackground=C['a_lite'],
                 relief='flat', show=show, width=width,
                 textvariable=textvariable,
                 disabledbackground=C['card'])
    e.pack(padx=1, pady=1, fill='x', ipady=6)
    # Glow on focus
    e.bind('<FocusIn>',  lambda ev: f.config(bg=C['p_lite']))
    e.bind('<FocusOut>', lambda ev: f.config(bg=C['border2']))
    f.entry = e   # expose entry widget via frame
    return f

def lbl(parent, text, font=None, fg=None, bg=None, **kw):
    return tk.Label(parent, text=text,
                    font=font or ('Segoe UI', 10),
                    fg=fg or C['text'],
                    bg=bg or C['bg'], **kw)

def separator(parent, color=None, pady=8):
    f = tk.Frame(parent, bg=color or C['border'], height=1)
    f.pack(fill='x', pady=pady)
    return f

def _lighten(h):
    try:
        r,g,b = int(h[1:3],16), int(h[3:5],16), int(h[5:7],16)
        return f'#{min(255,r+35):02x}{min(255,g+35):02x}{min(255,b+35):02x}'
    except:
        return h


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
class PasswordManagerApp:

    def __init__(self, root):
        self.root = root
        self.root.title('🔐 SecureVault — Password Manager')
        self.root.geometry('960x660')
        self.root.minsize(800, 560)
        self.root.configure(bg=C['bg'])
        self.key = None

        apply_styles(root)
        initialize_db()

        if is_master_set():
            self._show_login()
        else:
            self._show_setup()

    def _clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    # ═══════════════════════════════════════════════════════════════════════
    # SCREEN 1 — SETUP
    # ═══════════════════════════════════════════════════════════════════════
    def _show_setup(self):
        self._clear()
        self.root.title('🔐 SecureVault — Create Master Password')

        outer = tk.Frame(self.root, bg=C['bg'])
        outer.place(relx=0.5, rely=0.5, anchor='center')

        # Icon + Title
        lbl(outer, '🔐', font=('Segoe UI', 56)).pack()
        lbl(outer, 'SecureVault', font=('Segoe UI', 26, 'bold'),
            fg=C['p_lite']).pack(pady=(0, 2))
        lbl(outer, 'Create your master password to get started',
            fg=C['muted'], font=('Segoe UI', 10)).pack(pady=(0, 24))

        # Card
        card = tk.Frame(outer, bg=C['card'], highlightbackground=C['border2'],
                        highlightthickness=1)
        card.pack(padx=0, ipadx=30, ipady=28)

        lbl(card, 'Master Password', fg=C['muted'],
            font=('Segoe UI', 9, 'bold'), bg=C['card']).pack(anchor='w', padx=28, pady=(0,4))
        self._setup_pw_frame = styled_entry(card, show='●', width=38)
        self._setup_pw_frame.pack(padx=28, fill='x')
        self._setup_pw_entry = self._setup_pw_frame.entry
        self._setup_pw_entry.focus()

        # Strength bar area
        self._setup_strength_frame = tk.Frame(card, bg=C['card'])
        self._setup_strength_frame.pack(fill='x', padx=28, pady=(6,0))
        self._setup_strength_lbl = lbl(self._setup_strength_frame, '',
                                        fg=C['muted'], bg=C['card'],
                                        font=('Segoe UI', 8))
        self._setup_strength_lbl.pack(side='left')
        self._setup_strength_bar = ttk.Progressbar(
            self._setup_strength_frame, style='Strength.Horizontal.TProgressbar',
            orient='horizontal', length=160, maximum=100, mode='determinate')
        self._setup_strength_bar.pack(side='right')
        self._setup_pw_entry.bind('<KeyRelease>', self._on_setup_pw_change)

        lbl(card, 'Confirm Password', fg=C['muted'],
            font=('Segoe UI', 9, 'bold'), bg=C['card']).pack(anchor='w', padx=28, pady=(18,4))
        self._setup_pw2_frame = styled_entry(card, show='●', width=38)
        self._setup_pw2_frame.pack(padx=28, fill='x')
        self._setup_pw2_entry = self._setup_pw2_frame.entry
        self._setup_pw2_entry.bind('<Return>', lambda e: self._do_setup())

        self._setup_err = lbl(card, '', fg=C['e_lite'], bg=C['card'],
                               font=('Segoe UI', 9))
        self._setup_err.pack(pady=(8,0))

        styled_btn(card, '🔑   Create Vault', self._do_setup,
                   bg=C['p_mid'], pad_x=40, pad_y=12,
                   font_size=11).pack(pady=(16,4))

        lbl(outer, '⚠️  There is NO recovery if you forget your master password.',
            fg=C['warn'], font=('Segoe UI', 8)).pack(pady=(12,0))

    def _on_setup_pw_change(self, _=None):
        pw = self._setup_pw_entry.get()
        if pw:
            s = check_strength(pw)
            style = ttk.Style()
            style.configure('Strength.Horizontal.TProgressbar', background=s['color'])
            self._setup_strength_bar['value'] = s['score']
            self._setup_strength_lbl.config(text=f'  {s["label"]}', fg=s['color'])
        else:
            self._setup_strength_bar['value'] = 0
            self._setup_strength_lbl.config(text='')

    def _do_setup(self):
        pw  = self._setup_pw_entry.get()
        pw2 = self._setup_pw2_entry.get()
        self._setup_err.config(text='')

        if not pw:
            self._setup_err.config(text='⚠  Password cannot be empty.'); return
        if len(pw) < 8:
            self._setup_err.config(text='⚠  Use at least 8 characters.'); return
        if pw != pw2:
            self._setup_err.config(text='⚠  Passwords do not match.'); return

        salt = generate_salt()
        key  = derive_key(pw, salt)
        vtoken = encrypt('VALID_MASTER_KEY', key)
        save_master(salt, vtoken)
        self.key = key
        self._show_main()

    # ═══════════════════════════════════════════════════════════════════════
    # SCREEN 2 — LOGIN
    # ═══════════════════════════════════════════════════════════════════════
    def _show_login(self):
        self._clear()
        self.root.title('🔐 SecureVault — Login')
        self._login_attempts = 0

        outer = tk.Frame(self.root, bg=C['bg'])
        outer.place(relx=0.5, rely=0.5, anchor='center')

        lbl(outer, '🔐', font=('Segoe UI', 56)).pack()
        lbl(outer, 'SecureVault', font=('Segoe UI', 26, 'bold'),
            fg=C['p_lite']).pack(pady=(0,2))
        lbl(outer, 'Enter your master password to unlock',
            fg=C['muted'], font=('Segoe UI', 10)).pack(pady=(0,24))

        card = tk.Frame(outer, bg=C['card'], highlightbackground=C['border2'],
                        highlightthickness=1)
        card.pack(ipadx=30, ipady=28)

        lbl(card, 'Master Password', fg=C['muted'],
            font=('Segoe UI', 9, 'bold'), bg=C['card']).pack(anchor='w', padx=28, pady=(0,4))
        self._login_pw_frame = styled_entry(card, show='●', width=38)
        self._login_pw_frame.pack(padx=28, fill='x')
        self._login_pw_entry = self._login_pw_frame.entry
        self._login_pw_entry.focus()
        self._login_pw_entry.bind('<Return>', lambda e: self._do_login())

        self._login_err = lbl(card, '', fg=C['e_lite'], bg=C['card'],
                               font=('Segoe UI', 9))
        self._login_err.pack(pady=(8,0))

        styled_btn(card, '🔓   Unlock Vault', self._do_login,
                   bg=C['p_mid'], pad_x=40, pad_y=12,
                   font_size=11).pack(pady=(16,4))

    def _do_login(self):
        pw = self._login_pw_entry.get()
        self._login_err.config(text='')
        if not pw:
            self._login_err.config(text='⚠  Please enter your master password.'); return

        salt, vtoken = get_master()
        key = derive_key(pw, salt)

        if verify_master_password(vtoken, key):
            self.key = key
            self._show_main()
        else:
            self._login_attempts += 1
            self._login_pw_entry.delete(0, 'end')
            self._login_err.config(
                text=f'❌  Incorrect password. (Attempt {self._login_attempts})')

    # ═══════════════════════════════════════════════════════════════════════
    # SCREEN 3 — MAIN VAULT
    # ═══════════════════════════════════════════════════════════════════════
    def _show_main(self):
        self._clear()
        self.root.title('🔐 SecureVault — Vault Unlocked')

        # ── Two-column layout: sidebar + content ──────────────────────────
        self._main_frame = tk.Frame(self.root, bg=C['bg'])
        self._main_frame.pack(fill='both', expand=True)

        self._build_sidebar()
        self._build_content()

    # ── SIDEBAR ──────────────────────────────────────────────────────────
    def _build_sidebar(self):
        sb = tk.Frame(self._main_frame, bg=C['sidebar'], width=220)
        sb.pack(side='left', fill='y')
        sb.pack_propagate(False)

        # Logo
        logo = tk.Frame(sb, bg=C['sidebar'])
        logo.pack(fill='x', pady=(24,20), padx=20)
        lbl(logo, '🔐', font=('Segoe UI', 28), bg=C['sidebar']).pack(side='left')
        title_f = tk.Frame(logo, bg=C['sidebar'])
        title_f.pack(side='left', padx=8)
        lbl(title_f, 'SecureVault', font=('Segoe UI', 13, 'bold'),
            fg=C['p_lite'], bg=C['sidebar']).pack(anchor='w')
        lbl(title_f, 'Password Manager', font=('Segoe UI', 8),
            fg=C['muted'], bg=C['sidebar']).pack(anchor='w')

        separator(sb, color=C['border'], pady=0)

        # Nav items
        nav_items = [
            ('🔑  All Passwords', self._refresh_list),
            ('➕  Add Password',  self._show_add_dialog),
            ('🔄  Generator',     self._show_generator_dialog),
        ]
        for text, cmd in nav_items:
            b = tk.Button(sb, text=text, command=cmd,
                          bg=C['sidebar'], fg=C['text2'],
                          font=('Segoe UI', 10), relief='flat',
                          cursor='hand2', anchor='w',
                          padx=20, pady=11, bd=0,
                          activebackground=C['card'],
                          activeforeground=C['text'])
            b.pack(fill='x')
            b.bind('<Enter>', lambda e, b=b: b.config(bg=C['card']))
            b.bind('<Leave>', lambda e, b=b: b.config(bg=C['sidebar']))

        # Stats at the bottom
        separator(sb, color=C['border'], pady=0)
        self._stat_lbl = lbl(sb, '', fg=C['muted'],
                              font=('Segoe UI', 8), bg=C['sidebar'])
        self._stat_lbl.pack(pady=12, padx=20, anchor='w')

        # Lock button at very bottom
        tk.Frame(sb, bg=C['sidebar']).pack(fill='both', expand=True)
        separator(sb, color=C['border'], pady=0)
        styled_btn(sb, '🔒  Lock Vault', self._show_login,
                   bg=C['sidebar'], fg=C['muted'],
                   pad_x=20, pad_y=12).pack(fill='x')

    # ── CONTENT AREA ──────────────────────────────────────────────────────
    def _build_content(self):
        content = tk.Frame(self._main_frame, bg=C['bg'])
        content.pack(side='left', fill='both', expand=True)

        # ── Top bar ──
        topbar = tk.Frame(content, bg=C['bg2'],
                          highlightbackground=C['border'], highlightthickness=1)
        topbar.pack(fill='x')

        lbl(topbar, 'All Passwords', font=('Segoe UI', 14, 'bold'),
            bg=C['bg2']).pack(side='left', padx=20, pady=14)

        styled_btn(topbar, '＋  Add Password', self._show_add_dialog,
                   bg=C['success'], pad_y=10).pack(side='right', padx=16, pady=10)

        # ── Search bar ──
        search_row = tk.Frame(content, bg=C['bg'])
        search_row.pack(fill='x', padx=20, pady=(14,6))

        search_icon = lbl(search_row, '🔍', font=('Segoe UI', 13), bg=C['bg'])
        search_icon.pack(side='left', padx=(0,8))

        self._search_var = tk.StringVar()
        self._search_var.trace('w', lambda *a: self._refresh_list())
        sf = styled_entry(search_row, width=42, textvariable=self._search_var)
        sf.pack(side='left', fill='x', expand=True)
        sf.entry.config(font=('Segoe UI', 10))

        lbl(search_row, 'Search service or username',
            fg=C['muted'], font=('Segoe UI', 9), bg=C['bg']).pack(side='left', padx=12)

        # ── Password list (scrollable) ──
        list_outer = tk.Frame(content, bg=C['bg'])
        list_outer.pack(fill='both', expand=True, padx=20, pady=(6,16))

        self._canvas = tk.Canvas(list_outer, bg=C['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_outer, orient='vertical',
                                  command=self._canvas.yview,
                                  style='Dark.Vertical.TScrollbar')
        self._scroll_frame = tk.Frame(self._canvas, bg=C['bg'])

        self._scroll_frame.bind('<Configure>', lambda e: self._canvas.configure(
            scrollregion=self._canvas.bbox('all')))
        self._canvas.create_window((0, 0), window=self._scroll_frame, anchor='nw')
        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self._canvas.bind_all('<MouseWheel>',
            lambda e: self._canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))

        self._refresh_list()

    def _refresh_list(self):
        for w in self._scroll_frame.winfo_children():
            w.destroy()

        q = self._search_var.get() if hasattr(self, '_search_var') else ''
        entries = search_passwords(q) if q else get_all_passwords()

        count = len(entries)
        if hasattr(self, '_stat_lbl'):
            self._stat_lbl.config(
                text=f'🔑  {count} password{"s" if count != 1 else ""}')

        if not entries:
            empty = tk.Frame(self._scroll_frame, bg=C['bg'])
            empty.pack(pady=80)
            lbl(empty, '🔒', font=('Segoe UI', 40), bg=C['bg']).pack()
            lbl(empty, 'No passwords yet', font=('Segoe UI', 14, 'bold'),
                fg=C['muted'], bg=C['bg']).pack(pady=(8,4))
            lbl(empty, 'Click "＋ Add Password" to save your first one.',
                fg=C['muted2'], font=('Segoe UI', 10), bg=C['bg']).pack()
            return

        for entry in entries:
            self._make_card(entry)

    def _make_card(self, entry):
        icon  = get_service_icon(entry['service'])
        color = get_service_color(entry['service'])

        # Outer card
        card = tk.Frame(self._scroll_frame, bg=C['card'],
                        highlightbackground=C['border'], highlightthickness=1)
        card.pack(fill='x', pady=4, padx=2)

        # Colored left accent strip
        accent_strip = tk.Frame(card, bg=color, width=4)
        accent_strip.pack(side='left', fill='y')

        # Icon badge
        icon_frame = tk.Frame(card, bg=color, width=46, height=46)
        icon_frame.pack(side='left', padx=(12,0), pady=12)
        icon_frame.pack_propagate(False)
        tk.Label(icon_frame, text=icon, font=('Segoe UI', 18),
                 bg=color, fg='white').place(relx=0.5, rely=0.5, anchor='center')

        # Info
        info = tk.Frame(card, bg=C['card'])
        info.pack(side='left', padx=14, pady=12, fill='x', expand=True)
        tk.Label(info, text=entry['service'],
                 font=('Segoe UI', 11, 'bold'),
                 fg=C['text'], bg=C['card']).pack(anchor='w')
        tk.Label(info, text=entry['username'],
                 font=('Segoe UI', 9),
                 fg=C['muted'], bg=C['card']).pack(anchor='w')
        if entry.get('notes'):
            tk.Label(info, text=entry['notes'][:60],
                     font=('Segoe UI', 8, 'italic'),
                     fg=C['muted2'], bg=C['card']).pack(anchor='w')

        # Password dots preview
        tk.Label(card, text='●●●●●●●●',
                 font=('Segoe UI', 9), fg=C['muted2'],
                 bg=C['card']).pack(side='left', padx=8)

        # Action buttons
        btn_frame = tk.Frame(card, bg=C['card'])
        btn_frame.pack(side='right', padx=12, pady=10)

        styled_btn(btn_frame, '📋', lambda e=entry: self._copy_password(e),
                   bg=C['accent'], pad_x=10, pad_y=8,
                   font_size=12).pack(side='left', padx=3)
        styled_btn(btn_frame, '👁', lambda e=entry: self._show_password(e),
                   bg=C['border'], fg=C['text'], pad_x=10, pad_y=8,
                   font_size=12).pack(side='left', padx=3)
        styled_btn(btn_frame, '🗑', lambda e=entry: self._delete_entry(e),
                   bg=C['error'], pad_x=10, pad_y=8,
                   font_size=12).pack(side='left', padx=3)

        # Hover effect on entire card
        def on_enter(e, c=card):
            c.config(bg=C['card2'], highlightbackground=C['border2'])
            for child in c.winfo_children():
                try: child.config(bg=C['card2'])
                except: pass
        def on_leave(e, c=card):
            c.config(bg=C['card'], highlightbackground=C['border'])
            for child in c.winfo_children():
                try: child.config(bg=C['card'])
                except: pass
        card.bind('<Enter>', on_enter)
        card.bind('<Leave>', on_leave)

    # ── ACTIONS ─────────────────────────────────────────────────────────
    def _copy_password(self, entry):
        dec = decrypt(bytes(entry['encrypted_password']), self.key)
        if dec:
            copy_to_clipboard(self.root, dec)
            self._flash_status(f'✅ Copied password for {entry["service"]}!', C['s_lite'])
        else:
            messagebox.showerror('Error', 'Decryption failed.')

    def _flash_status(self, msg, color):
        """Temporary status message in the title bar."""
        self.root.title(f'🔐 SecureVault — {msg}')
        self.root.after(3000, lambda: self.root.title('🔐 SecureVault — Vault Unlocked'))

    def _show_password(self, entry):
        dec = decrypt(bytes(entry['encrypted_password']), self.key)
        if not dec:
            messagebox.showerror('Error', 'Decryption failed.'); return

        win = tk.Toplevel(self.root)
        win.title(f'Password — {entry["service"]}')
        win.configure(bg=C['bg'])
        win.geometry('420x260')
        win.resizable(False, False)
        win.grab_set()

        icon = get_service_icon(entry['service'])
        color = get_service_color(entry['service'])

        header = tk.Frame(win, bg=color)
        header.pack(fill='x')
        tk.Label(header, text=f'{icon}  {entry["service"]}',
                 font=('Segoe UI', 14, 'bold'),
                 bg=color, fg='white', pady=14).pack()

        body = tk.Frame(win, bg=C['bg'])
        body.pack(fill='both', expand=True, padx=24, pady=16)

        lbl(body, f'👤  {entry["username"]}',
            fg=C['muted'], font=('Segoe UI', 10), bg=C['bg']).pack(anchor='w', pady=(0,12))

        pw_box = tk.Frame(body, bg=C['card2'],
                          highlightbackground=C['border2'], highlightthickness=1)
        pw_box.pack(fill='x')
        tk.Label(pw_box, text=dec, font=('Consolas', 13),
                 bg=C['card2'], fg=C['a_lite'],
                 pady=14, padx=16).pack(side='left')

        styled_btn(pw_box, '📋', lambda: [copy_to_clipboard(self.root, dec), win.destroy()],
                   bg=C['accent'], pad_x=12, pad_y=10).pack(side='right', padx=10)

        styled_btn(body, 'Close', win.destroy,
                   bg=C['border'], fg=C['text'],
                   pad_x=30, pad_y=9).pack(pady=(16,0))

    def _delete_entry(self, entry):
        if messagebox.askyesno('Delete',
                               f'Delete password for "{entry["service"]}"?\n\nThis cannot be undone.'):
            delete_password(entry['id'])
            self._refresh_list()

    # ── ADD PASSWORD DIALOG ─────────────────────────────────────────────
    def _show_add_dialog(self):
        win = tk.Toplevel(self.root)
        win.title('Add New Password')
        win.configure(bg=C['bg'])
        win.geometry('500x600')
        win.resizable(False, False)
        win.grab_set()

        # Header
        header = tk.Frame(win, bg=C['p_mid'])
        header.pack(fill='x')
        tk.Label(header, text='➕  Add New Password',
                 font=('Segoe UI', 14, 'bold'),
                 bg=C['p_mid'], fg='white', pady=16).pack()

        body = tk.Frame(win, bg=C['bg'])
        body.pack(fill='both', expand=True, padx=28, pady=20)

        entries = {}
        fields = [
            ('Service / Website', 'service', None),
            ('Username / Email',  'username', None),
            ('Password',          'password', '●'),
            ('Notes (optional)',  'notes',    None),
        ]
        for label, key, show in fields:
            lbl(body, label, fg=C['muted'],
                font=('Segoe UI', 9, 'bold'), bg=C['bg']).pack(anchor='w', pady=(10,3))
            ef = styled_entry(body, show=show, width=44)
            ef.pack(fill='x')
            entries[key] = ef.entry

        # Strength meter
        strength_row = tk.Frame(body, bg=C['bg'])
        strength_row.pack(fill='x', pady=(6,0))
        strength_lbl = lbl(strength_row, '', fg=C['muted'],
                           font=('Segoe UI', 8), bg=C['bg'])
        strength_lbl.pack(side='left')
        strength_bar = ttk.Progressbar(strength_row,
                                        style='Strength.Horizontal.TProgressbar',
                                        orient='horizontal', length=180,
                                        maximum=100, mode='determinate')
        strength_bar.pack(side='right')

        def on_pw_change(_=None):
            pw = entries['password'].get()
            if pw:
                s = check_strength(pw)
                ttk.Style().configure('Strength.Horizontal.TProgressbar',
                                      background=s['color'])
                strength_bar['value'] = s['score']
                strength_lbl.config(text=f'Strength: {s["label"]}', fg=s['color'])
            else:
                strength_bar['value'] = 0
                strength_lbl.config(text='')

        entries['password'].bind('<KeyRelease>', on_pw_change)

        def auto_gen():
            pw = generate_password(length=20)
            entries['password'].delete(0, 'end')
            entries['password'].insert(0, pw)
            on_pw_change()

        styled_btn(body, '⚡  Generate Strong Password', auto_gen,
                   bg=C['accent'], pad_x=20, pad_y=9).pack(pady=(10,0), anchor='w')

        separator(body, color=C['border'], pady=14)

        def save():
            service  = entries['service'].get().strip()
            username = entries['username'].get().strip()
            password = entries['password'].get()
            notes    = entries['notes'].get().strip()
            if not service or not username or not password:
                messagebox.showwarning('Missing Fields',
                                       'Service, username and password are required.')
                return
            enc = encrypt(password, self.key)
            add_password(service, username, enc, notes)
            win.destroy()
            self._refresh_list()
            self._flash_status(f'✅ Saved password for {service}!', C['s_lite'])

        styled_btn(body, '💾  Save Password', save,
                   bg=C['success'], pad_x=40, pad_y=12,
                   font_size=11).pack()

    # ── STANDALONE GENERATOR DIALOG ────────────────────────────────────
    def _show_generator_dialog(self):
        win = tk.Toplevel(self.root)
        win.title('Password Generator')
        win.configure(bg=C['bg'])
        win.geometry('440x400')
        win.resizable(False, False)
        win.grab_set()

        header = tk.Frame(win, bg=C['accent'])
        header.pack(fill='x')
        tk.Label(header, text='⚡  Password Generator',
                 font=('Segoe UI', 14, 'bold'),
                 bg=C['accent'], fg='white', pady=14).pack()

        body = tk.Frame(win, bg=C['bg'])
        body.pack(fill='both', expand=True, padx=28, pady=20)

        # Options
        opts = {
            'upper':   tk.BooleanVar(value=True),
            'digits':  tk.BooleanVar(value=True),
            'symbols': tk.BooleanVar(value=True),
        }
        length_var = tk.IntVar(value=18)

        lbl(body, 'Length', fg=C['muted'], font=('Segoe UI', 9, 'bold'),
            bg=C['bg']).pack(anchor='w')
        len_row = tk.Frame(body, bg=C['bg'])
        len_row.pack(fill='x', pady=(4,12))
        len_lbl = lbl(len_row, '18', fg=C['p_lite'],
                      font=('Segoe UI', 14, 'bold'), bg=C['bg'])
        len_lbl.pack(side='right')
        def on_len(v):
            length_var.set(int(float(v)))
            len_lbl.config(text=str(int(float(v))))

        tk.Scale(len_row, from_=8, to=40, orient='horizontal',
                 variable=length_var, command=on_len,
                 bg=C['bg'], fg=C['text'], troughcolor=C['card2'],
                 highlightthickness=0, sliderrelief='flat',
                 activebackground=C['p_lite']).pack(fill='x', expand=True, side='left')

        for text, key in [('Uppercase (A-Z)', 'upper'),
                           ('Numbers (0-9)',   'digits'),
                           ('Symbols (!@#$)',  'symbols')]:
            tk.Checkbutton(body, text=text, variable=opts[key],
                           bg=C['bg'], fg=C['text2'],
                           selectcolor=C['card'], font=('Segoe UI', 10),
                           activebackground=C['bg'],
                           activeforeground=C['text']).pack(anchor='w', pady=2)

        # Output
        separator(body, color=C['border'], pady=10)
        pw_var = tk.StringVar()
        pw_box = tk.Frame(body, bg=C['card2'],
                          highlightbackground=C['border2'], highlightthickness=1)
        pw_box.pack(fill='x')
        pw_display = tk.Entry(pw_box, textvariable=pw_var,
                              font=('Consolas', 11), bg=C['card2'],
                              fg=C['a_lite'], relief='flat',
                              state='readonly', readonlybackground=C['card2'])
        pw_display.pack(side='left', fill='x', expand=True, ipady=10, padx=12)

        def gen():
            pw = generate_password(
                length=length_var.get(),
                use_upper=opts['upper'].get(),
                use_digits=opts['digits'].get(),
                use_symbols=opts['symbols'].get()
            )
            pw_var.set(pw)

        def copy_gen():
            copy_to_clipboard(self.root, pw_var.get())

        btn_row = tk.Frame(body, bg=C['bg'])
        btn_row.pack(fill='x', pady=(10,0))
        styled_btn(btn_row, '🔄  Generate', gen, bg=C['p_mid']).pack(side='left')
        styled_btn(btn_row, '📋  Copy', copy_gen,
                   bg=C['accent']).pack(side='left', padx=10)

        gen()   # Generate one immediately on open


# ─────────────────────────────────────────────────────────────────────────────
# LAUNCH
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    root = tk.Tk()
    app  = PasswordManagerApp(root)
    root.mainloop()
