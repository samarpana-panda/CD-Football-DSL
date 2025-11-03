import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, List
import json
import os

from compiler import FootballDSLCompiler
from football_dsl_lexer_parser import VALID_ROLES, VALID_ACTIONS, TokenType


TEMPLATES: Dict[str, str] = {
    "4-3-3": (
        "formation 4-3-3\n"
        "GK: Keeper\n"
        "LB: LeftBack\n"
        "CB1: CenterBack1\n"
        "CB2: CenterBack2\n"
        "RB: RightBack\n"
        "CM1: Mid1\n"
        "CM2: Mid2\n"
        "CM3: Mid3\n"
        "LW: LeftWing\n"
        "RW: RightWing\n"
        "ST: Striker\n\n"
        "play Example433 {\n"
        "  LeftWing -> Striker [cross]\n"
        "  Striker -> shoot\n"
        "}\n"
    ),
    "4-4-2": (
        "formation 4-4-2\n"
        "GK: Keeper\n"
        "LB: LeftBack\n"
        "CB1: CenterBack1\n"
        "CB2: CenterBack2\n"
        "RB: RightBack\n"
        "LM: LeftMid\n"
        "CM1: CenterMid1\n"
        "CM2: CenterMid2\n"
        "RM: RightMid\n"
        "CF1: Forward1\n"
        "CF2: Forward2\n\n"
        "play Example442 {\n"
        "  LeftMid -> Forward1 [through_pass]\n"
        "  Forward1 -> Forward2 [pass]\n"
        "  Forward2 -> shoot\n"
        "}\n"
    ),
    "4-2-3-1": (
        "formation 4-2-3-1\n"
        "GK: Keeper\n"
        "LB: LeftBack\n"
        "CB1: CenterBack1\n"
        "CB2: CenterBack2\n"
        "RB: RightBack\n"
        "CDM: Holder\n"
        "CM1: Mid1\n"
        "CM2: Mid2\n"
        "CAM: Playmaker\n"
        "LM: LeftMid\n"
        "RM: RightMid\n"
        "ST: Striker\n\n"
        "play Example4231 {\n"
        "  Playmaker -> Striker [through_pass]\n"
        "  Striker -> shoot\n"
        "}\n"
    ),
    "3-5-2": (
        "formation 3-5-2\n"
        "GK: Keeper\n"
        "CB1: CenterBack1\n"
        "CB2: CenterBack2\n"
        "CB3: CenterBack3\n"
        "LWB: LeftWingBack\n"
        "RWB: RightWingBack\n"
        "CDM: Holder\n"
        "CM1: Mid1\n"
        "CM2: Mid2\n"
        "CF1: Striker1\n"
        "CF2: Striker2\n\n"
        "play Example352 {\n"
        "  RightWingBack -> Striker1 [cross]\n"
        "  Striker1 -> shoot\n"
        "}\n"
    ),
}


class DSLGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Football DSL Workbench")
        self.geometry("1100x750")

        self.compiler = FootballDSLCompiler()

        self._build_menu()
        self._build_layout()
        self._bind_highlighting()

        # Start with a default template
        self._insert_text(TEMPLATES["4-3-3"]) 

    def _build_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", command=self._new)
        file_menu.add_command(label="Open .dsl...", command=self._open)
        file_menu.add_command(label="Save", command=self._save)
        file_menu.add_command(label="Save As...", command=self._save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        template_menu = tk.Menu(menubar, tearoff=0)
        for name in TEMPLATES.keys():
            template_menu.add_command(label=name, command=lambda n=name: self._load_template(n))
        menubar.add_cascade(label="Templates", menu=template_menu)

        self.config(menu=menubar)

    def _build_layout(self):
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(toolbar, text="Validate", command=self._validate).pack(side=tk.LEFT, padx=4, pady=4)
        ttk.Button(toolbar, text="Generate IR (JSON)", command=self._generate_ir).pack(side=tk.LEFT, padx=4, pady=4)
        ttk.Button(toolbar, text="Save IR JSON", command=self._save_ir).pack(side=tk.LEFT, padx=4, pady=4)
        ttk.Button(toolbar, text="Open Visualizer", command=self._open_visualizer).pack(side=tk.LEFT, padx=4, pady=4)

        # Editor and Outputs
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        # Editor
        editor_frame = ttk.Frame(main_pane)
        self.text = tk.Text(editor_frame, wrap=tk.NONE, undo=True, font=("Consolas", 11))
        self.text.pack(fill=tk.BOTH, expand=True)

        # Scrollbars
        yscroll = ttk.Scrollbar(editor_frame, command=self.text.yview)
        xscroll = ttk.Scrollbar(editor_frame, orient=tk.HORIZONTAL, command=self.text.xview)
        self.text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)

        main_pane.add(editor_frame, weight=3)

        # Output tabs
        output_frame = ttk.Frame(main_pane)
        self.tabs = ttk.Notebook(output_frame)
        self.token_view = tk.Text(self.tabs, wrap=tk.NONE, state=tk.DISABLED, font=("Consolas", 10))
        self.ast_view = tk.Text(self.tabs, wrap=tk.NONE, state=tk.DISABLED, font=("Consolas", 10))
        self.ast_tree_view = tk.Text(self.tabs, wrap=tk.NONE, state=tk.DISABLED, font=("Consolas", 10))
        self.symbol_view = tk.Text(self.tabs, wrap=tk.NONE, state=tk.DISABLED, font=("Consolas", 10))
        self.semantic_view = tk.Text(self.tabs, wrap=tk.NONE, state=tk.DISABLED, font=("Consolas", 10))
        self.log_view = tk.Text(self.tabs, wrap=tk.NONE, state=tk.DISABLED, font=("Consolas", 10))
        self.ir_view = tk.Text(self.tabs, wrap=tk.NONE, state=tk.DISABLED, font=("Consolas", 10))

        self.tabs.add(self.token_view, text="Tokens")
        self.tabs.add(self.ast_view, text="AST")
        self.tabs.add(self.symbol_view, text="Symbol Table")
        self.tabs.add(self.semantic_view, text="Semantic Results")
        self.tabs.add(self.ir_view, text="IR JSON")
        self.tabs.add(self.ast_tree_view, text="AST Tree")
        self.tabs.add(self.log_view, text="Log")
        self.tabs.pack(fill=tk.BOTH, expand=True)

        main_pane.add(output_frame, weight=2)

        # Highlighting tags
        self.text.tag_configure("kw", foreground="#005cc5")
        self.text.tag_configure("role", foreground="#22863a")
        self.text.tag_configure("action", foreground="#e36209")
        self.text.tag_configure("arrow", foreground="#6f42c1")
        self.text.tag_configure("error", background="#ffeef0")

    def _bind_highlighting(self):
        self.text.bind("<KeyRelease>", lambda e: self._highlight())

    def _insert_text(self, content: str):
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        self._highlight()

    def _new(self):
        self.current_path = None
        self._insert_text("")

    def _open(self):
        path = filedialog.askopenfilename(filetypes=[("DSL files", "*.dsl"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.current_path = path
            self._insert_text(content)
        except Exception as e:
            messagebox.showerror("Open Error", str(e))

    def _save(self):
        if not getattr(self, 'current_path', None):
            return self._save_as()
        try:
            with open(self.current_path, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", tk.END))
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def _save_as(self):
        path = filedialog.asksaveasfilename(defaultextension=".dsl", filetypes=[("DSL files", "*.dsl"), ("All files", "*.*")])
        if not path:
            return
        self.current_path = path
        self._save()

    def _load_template(self, name: str):
        self._insert_text(TEMPLATES[name])

    def _highlight(self):
        # Clear existing tags
        for tag in ("kw", "role", "action", "arrow", "error"):
            self.text.tag_remove(tag, "1.0", tk.END)
        content = self.text.get("1.0", tk.END)
        # Very basic token-like highlighting
        def highlight_word(word: str, tag: str):
            start = "1.0"
            while True:
                idx = self.text.search(r"\m" + word + r"\M", start, tk.END, regexp=True)
                if not idx:
                    break
                end = f"{idx}+{len(word)}c"
                self.text.tag_add(tag, idx, end)
                start = end
        highlight_word("formation", "kw")
        highlight_word("play", "kw")
        for role in sorted(VALID_ROLES, key=len, reverse=True):
            highlight_word(role, "role")
        for act in sorted(VALID_ACTIONS, key=len, reverse=True):
            highlight_word(act, "action")
        highlight_word("->", "arrow")

    def _validate(self):
        code = self.text.get("1.0", tk.END)
        result = self.compiler.compile(code)
        self._show_results(result)
        if result.get("semantic_errors"):
            self._status_error("Validation found issues.")
        elif not result.get("success"):
            self._status_error("Compilation failed.")
        else:
            self._status_ok("Validation passed.")

    def _generate_ir(self):
        code = self.text.get("1.0", tk.END)
        result = self.compiler.compile(code)
        self._show_results(result)
        if result.get("ir_json"):
            self._status_ok("IR generated.")
        else:
            self._status_error("IR not generated due to errors.")

    def _save_ir(self):
        code = self.text.get("1.0", tk.END)
        result = self.compiler.compile(code)
        self._show_results(result)
        if not result.get("ir_json"):
            messagebox.showerror("Save IR", "Cannot save IR: there are semantic or parsing errors.")
            return
        # Ask user where to save to avoid permission issues with CWD
        try:
            initialdir = os.getcwd()
            path = filedialog.asksaveasfilename(
                title="Save IR JSON",
                initialdir=initialdir,
                initialfile="playbook_ir.json",
                defaultextension=".json",
                filetypes=[("JSON", "*.json"), ("All files", "*.*")],
            )
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                f.write(result["ir_json"])
            # remember last saved path for launching visualizer
            self.last_saved_ir_path = path
            messagebox.showinfo("Save IR", f"Saved: {path}\nYou can open this in the visualizer.")
        except Exception as e:
            messagebox.showerror("Save IR", str(e))

    def _open_visualizer(self):
        # Launch visualizer using the same interpreter and the project directory
        try:
            import sys
            import subprocess
            project_dir = os.path.dirname(os.path.abspath(__file__))
            visualizer_path = os.path.join(project_dir, "visualizer.py")
            args = [sys.executable, visualizer_path]
            # if we have a recently saved IR path, pass it explicitly
            ir_path = getattr(self, 'last_saved_ir_path', None)
            if ir_path and os.path.isfile(ir_path):
                args.append(ir_path)
            subprocess.Popen(args, cwd=project_dir)
        except Exception as e:
            messagebox.showerror("Visualizer", str(e))

    def _set_text(self, widget: tk.Text, text: str):
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state=tk.DISABLED)

    def _show_results(self, result: Dict):
        # Tokens
        if result.get("tokens"):
            token_lines = []
            for t in result["tokens"]:
                if t["type"] == 'EOF':
                    continue
                token_lines.append(f"{t['type']:>12}  {t['value']}  (L{t['line']},C{t['column']})")
            self._set_text(self.token_view, "\n".join(token_lines))
        else:
            self._set_text(self.token_view, "")

        # AST
        ast_dict = result.get("ast_dict")
        self._set_text(self.ast_view, json.dumps(ast_dict, indent=2) if ast_dict else "")
        # AST Tree (ASCII)
        ast_tree = result.get("ast_tree")
        self._set_text(self.ast_tree_view, ast_tree or "")

        # Symbol table: flat lexeme->token class table in lexer order (include punctuation)
        tokens = result.get("tokens") or []
        rows = [(t["value"], t["type"]) for t in tokens if t.get("type") != 'EOF']
        # Calculate column widths
        lex_w = max(7, len("Lexeme"), *(len(str(v)) for v, _ in rows))
        cls_w = max(11, len("Token Class"), *(len(str(c)) for _, c in rows))
        sep_lex = "-" * lex_w
        sep_cls = "-" * cls_w
        lines = [
            "LEXEME TOKEN CLASSIFICATION TABLE",
            "=================================",
            f"{'Lexeme'.ljust(lex_w)}   {'Token Class'.ljust(cls_w)}",
            f"{sep_lex}   {sep_cls}",
        ]
        for v, c in rows:
            lines.append(f"{str(v).ljust(lex_w)}   {str(c).ljust(cls_w)}")
        self._set_text(self.symbol_view, "\n".join(lines))

        # Semantic results
        sem_errs = result.get("semantic_errors") or []
        if sem_errs:
            self._set_text(self.semantic_view, "\n\n".join(sem_errs))
        else:
            self._set_text(self.semantic_view, "No semantic errors.")

        # IR JSON
        self._set_text(self.ir_view, result.get("ir_json") or "")


        # Log
        self._set_text(self.log_view, "\n".join(result.get("log") or []))

    def _status_ok(self, msg: str):
        self.title(f"Football DSL Workbench — {msg}")

    def _status_error(self, msg: str):
        self.title(f"Football DSL Workbench — {msg}")


def main():
    app = DSLGUI()
    app.mainloop()


if __name__ == "__main__":
    main()


