"""Man hinh Tro ly AI.

Cau tra loi duoc lay o luong (thread) rieng: che do Claude API co the mat
vai giay, goi thang tren luong giao dien se lam ca cua so dong bang.
Luong phu KHONG duoc dong vao widget Tk — ket qua bo vao Queue, luong
chinh doc ra bang after() dinh ky.
"""
import queue
import threading
import tkinter as tk
from tkinter import ttk

from app.services import ai_service
from app.views import theme
from app.views.base_frame import BaseFrame, make_title

SUGGESTIONS = [
    "Doanh thu hôm nay?",
    "Sản phẩm nào sắp hết hàng?",
    "Top bán chạy tháng này?",
    "Khách nào mua nhiều nhất?",
    "Cách hủy hóa đơn?",
]


class ChatView(BaseFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._busy = False
        self._queue: queue.Queue[str] = queue.Queue()
        self._history: list[dict] = []   # chi dung cho che do Claude
        self._welcomed = False

        if ai_service.has_api():
            subtitle = f"Đang dùng Claude API ({ai_service.CLAUDE_MODEL})"
        else:
            subtitle = ("Chế độ offline — trả lời theo từ khóa trên dữ liệu thật. "
                        "Thêm ANTHROPIC_API_KEY vào .env để dùng Claude.")
        make_title(self, "Trợ lý AI", subtitle)

        self._build_suggestions()
        self._build_chat_area()
        self._build_input()
        self._poll()

    # ---------- giao dien ----------

    def _build_suggestions(self):
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="Gợi ý:", style="Muted.TLabel").pack(
            side="left", padx=(0, 6))
        for text in SUGGESTIONS:
            ttk.Button(row, text=text, style="Chip.TButton",
                       command=lambda t=text: self._send_text(t)).pack(
                side="left", padx=(0, 4))

    def _build_chat_area(self):
        area = ttk.Frame(self)
        area.pack(fill="both", expand=True)

        self.text = tk.Text(
            area, wrap="word", state="disabled", relief="flat",
            background=theme.SURFACE, foreground=theme.TEXT,
            font=theme.FONT_BASE, padx=14, pady=12,
            insertbackground=theme.TEXT,
            highlightthickness=1, highlightbackground=theme.BORDER,
            highlightcolor=theme.BORDER,
        )
        scroll = ttk.Scrollbar(area, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.text.tag_configure("who_user", foreground=theme.PRIMARY,
                                font=theme.FONT_BOLD, spacing1=10)
        self.text.tag_configure("who_bot", foreground=theme.SUCCESS,
                                font=theme.FONT_BOLD, spacing1=10)
        self.text.tag_configure("msg", lmargin1=14, lmargin2=14, spacing3=4)
        self.text.tag_configure("typing", lmargin1=14, foreground=theme.MUTED)

    def _build_input(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(10, 0))

        self.entry = ttk.Entry(bar, font=(theme.FAMILY, 11))
        self.entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.entry.bind("<Return>", lambda e: self.send())

        self.send_button = ttk.Button(bar, text="Gửi", style="Accent.TButton",
                                      command=self.send)
        self.send_button.pack(side="left", padx=(8, 0))

    # ---------- hien thi tin nhan ----------

    def _append(self, who: str, message: str):
        self.text.configure(state="normal")
        if who == "user":
            self.text.insert("end", "Bạn\n", "who_user")
        else:
            self.text.insert("end", "Trợ lý\n", "who_bot")
        self.text.insert("end", message.rstrip() + "\n", "msg")
        self.text.configure(state="disabled")
        self.text.see("end")

    def _show_typing(self):
        self.text.configure(state="normal")
        self.typing_index = self.text.index("end-1c")
        self.text.insert("end", "Đang soạn câu trả lời…\n", "typing")
        self.text.configure(state="disabled")
        self.text.see("end")

    def _hide_typing(self):
        self.text.configure(state="normal")
        self.text.delete(self.typing_index, "end")
        self.text.insert("end", "\n")
        self.text.configure(state="disabled")

    # ---------- gui / nhan ----------

    def on_show(self):
        self.entry.focus_set()
        if not self._welcomed:
            self._welcomed = True
            name = self.app.user.get("display_name", "bạn") if getattr(
                self.app, "user", None) else "bạn"
            self._append("bot",
                         f"Chào {name}! Mình có thể trả lời về doanh thu, tồn kho, "
                         "sản phẩm bán chạy, khách hàng và cách dùng phần mềm. "
                         "Bấm một gợi ý phía trên hoặc gõ câu hỏi rồi Enter.")

    def _send_text(self, text: str):
        if self._busy:
            return
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        self.send()

    def send(self):
        question = self.entry.get().strip()
        if not question or self._busy:
            return
        self.entry.delete(0, "end")
        self._append("user", question)
        self._busy = True
        self.send_button.state(["disabled"])
        self._show_typing()

        thread = threading.Thread(
            target=self._worker, args=(question, list(self._history)),
            daemon=True)
        thread.start()
        self._pending_question = question

    def _worker(self, question: str, history: list[dict]):
        try:
            answer = ai_service.ask(question, history)
        except Exception as exc:
            answer = f"Xin lỗi, có lỗi xảy ra: {exc}"
        self._queue.put(answer)

    def _poll(self):
        try:
            answer = self._queue.get_nowait()
        except queue.Empty:
            pass
        else:
            self._hide_typing()
            self._append("bot", answer)
            self._history.append(
                {"role": "user", "content": self._pending_question})
            self._history.append({"role": "assistant", "content": answer})
            self._history = self._history[-12:]   # giu 6 luot gan nhat
            self._busy = False
            self.send_button.state(["!disabled"])
        self.after(150, self._poll)
