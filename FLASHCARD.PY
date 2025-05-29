import tkinter as tk
from tkinter import ttk, messagebox
import pyodbc
from gtts import gTTS
from playsound import playsound
import os

# DB 연결 정보
server = 'ms1901.gabiadb.com'
database = 'yujincast'
username = 'pinkyj81'
password = 'zoskek38!!'

conn_str = f"""
DRIVER={{ODBC Driver 17 for SQL Server}};
SERVER={server};
DATABASE={database};
UID={username};
PWD={password};
"""

# DB 연결 함수
def get_sources():
    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT Source FROM dbo.Flashcards WHERE Source IS NOT NULL")
            return [row.Source for row in cursor.fetchall()]
    except Exception as e:
        messagebox.showerror("DB 오류", str(e))
        return []

def load_flashcards(source):
    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT EnglishWord, KoreanMeaning FROM dbo.Flashcards WHERE Source = ?", source)
            return cursor.fetchall()
    except Exception as e:
        messagebox.showerror("DB 오류", str(e))
        return []

# 카드 보여주기
def show_card():
    global showing_word
    if 0 <= current_index < len(flashcards):
        word_label.config(text=flashcards[current_index][0])
        meaning_label.config(text="")
        showing_word = True
        progress_label.config(text=f"{current_index + 1} / {len(flashcards)}")
    else:
        word_label.config(text="끝났어요!")
        meaning_label.config(text="")
        progress_label.config(text=f"{len(flashcards)} / {len(flashcards)}")
        next_button.config(state=tk.DISABLED)
        show_button.config(state=tk.DISABLED)
        pronounce_button.config(state=tk.DISABLED)

def show_answer():
    global showing_word
    if showing_word:
        meaning_label.config(text=flashcards[current_index][1])
        showing_word = False

def next_card():
    global current_index
    current_index += 1
    show_card()

def pronounce_word():
    if 0 <= current_index < len(flashcards):
        word = flashcards[current_index][0]
        try:
            tts = gTTS(word, lang='en')
            filename = "temp_audio.mp3"
            tts.save(filename)
            playsound(filename)
            os.remove(filename)
        except Exception as e:
            messagebox.showerror("발음 오류", str(e))

def on_source_selected(event=None):
    global flashcards, current_index
    selected = source_combo.get()
    flashcards = load_flashcards(selected)
    current_index = 0
    if flashcards:
        next_button.config(state=tk.NORMAL)
        show_button.config(state=tk.NORMAL)
        pronounce_button.config(state=tk.NORMAL)
        show_card()
    else:
        word_label.config(text="데이터 없음")
        meaning_label.config(text="")
        progress_label.config(text="0 / 0")
        next_button.config(state=tk.DISABLED)
        show_button.config(state=tk.DISABLED)
        pronounce_button.config(state=tk.DISABLED)

# GUI 시작
root = tk.Tk()
root.title("영어 플래시카드 학습기")

frame = tk.Frame(root, padx=20, pady=20)
frame.pack()

# Source 콤보박스
source_label = tk.Label(frame, text="Source 선택:")
source_label.pack()

source_combo = ttk.Combobox(frame, values=get_sources(), state="readonly")
source_combo.pack(pady=5)
source_combo.bind("<<ComboboxSelected>>", on_source_selected)

# 카드 표시
word_label = tk.Label(frame, text="단어가 여기에 표시됩니다", font=("Arial", 24))
word_label.pack(pady=10)

meaning_label = tk.Label(frame, text="", font=("Arial", 18), fg="gray")
meaning_label.pack(pady=5)

# 진행 상황 표시
progress_label = tk.Label(frame, text="0 / 0", font=("Arial", 14), fg="blue")
progress_label.pack(pady=5)

# 버튼들
btn_frame = tk.Frame(frame)
btn_frame.pack(pady=10)

show_button = tk.Button(btn_frame, text="정답 보기", command=show_answer, state=tk.DISABLED)
show_button.grid(row=0, column=0, padx=5)

next_button = tk.Button(btn_frame, text="다음 카드", command=next_card, state=tk.DISABLED)
next_button.grid(row=0, column=1, padx=5)

pronounce_button = tk.Button(btn_frame, text="발음 듣기", command=pronounce_word, state=tk.DISABLED)
pronounce_button.grid(row=0, column=2, padx=5)

# 상태 변수
flashcards = []
current_index = 0
showing_word = True

root.mainloop()
