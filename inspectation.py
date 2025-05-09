import matplotlib
matplotlib.rc('font', family='Malgun Gothic')

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.stats import shapiro
import os

class InspectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("자주검사 통계 분석")
        self.root.state('zoomed')

        self.file_path = None
        self.df = None

        self.create_widgets()

    def create_widgets(self):
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill='x', padx=10, pady=8)

        self.upload_btn = ttk.Button(top_frame, text="엑셀 파일 업로드", command=self.load_excel)
        self.upload_btn.pack(side='left', padx=(0, 10))

        self.print_btn = ttk.Button(top_frame, text="프린트", command=self.print_page, state='disabled')
        self.print_btn.pack(side='left')

        note_frame = ttk.Frame(self.root)
        note_frame.pack(fill='x', padx=10, pady=4)

        note_label = tk.Label(note_frame, text="Note:", font=("Arial", 12))
        note_label.pack(side='left')
        self.note_entry = tk.Entry(note_frame, font=("Arial", 12), width=70, state='disabled')
        self.note_entry.pack(side='left', padx=(5, 0))

        self.fig = None
        self.canvas = None

    def load_excel(self):
        file_path = filedialog.askopenfilename(
            title="엑셀 파일 선택",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if not file_path:
            return

        try:
            df = pd.read_excel(file_path)
            if not {'값', '상한', '하한'}.issubset(df.columns):
                raise Exception("필수 컬럼(값, 상한, 하한)이 없습니다.")
            self.file_path = file_path
            self.df = df
            self.note_entry.config(state='normal')
            self.analyze_and_plot(note_for_fig=None)
            self.print_btn.config(state='normal')
        except Exception as e:
            messagebox.showerror("오류", f"파일을 불러올 수 없습니다:\n{e}")
            self.print_btn.config(state='disabled')
            self.note_entry.config(state='disabled')

    def analyze_and_plot(self, note_for_fig=None):
        values = self.df['값'].values
        USL = self.df['상한'].iloc[0]
        LSL = self.df['하한'].iloc[0]
        mean_val = np.mean(values)
        std_val = np.std(values, ddof=1)
        mid_target = (USL + LSL) / 2
        mean_diff = mean_val - mid_target

        # 정규성 테스트 (Shapiro-Wilk)
        shapiro_stat, shapiro_p = shapiro(values)
        if shapiro_p > 0.05:
            normality_result = f"정규분포를 따름 (p={shapiro_p:.3f})"
        else:
            normality_result = f"정규분포 아님 (p={shapiro_p:.3f})"

        Cp = (USL - LSL) / (6 * std_val)
        Cpu = (USL - mean_val) / (3 * std_val)
        Cpl = (mean_val - LSL) / (3 * std_val)
        Cpk = min(Cpu, Cpl)

        group_size = 5
        num_groups = len(values) // group_size
        groups = [values[i*group_size:(i+1)*group_size] for i in range(num_groups)]
        xbar = [np.mean(g) for g in groups]
        rbar = [np.ptp(g) for g in groups]

        if note_for_fig is None:
            note_text_display = "(인쇄시 Note가 반영됩니다)"
        else:
            note_text_display = note_for_fig if note_for_fig.strip() else "(설명 없음)"

        if self.fig:
            plt.close(self.fig)
        self.fig, axes = plt.subplots(3, 1, figsize=(8.27, 11.69))

        # (1) 히스토그램
        axes[0].hist(values, bins=10, edgecolor='black')
        axes[0].set_title('측정값 히스토그램')
        axes[0].axvline(USL, color='red', linestyle='--', label='상한')
        axes[0].axvline(LSL, color='blue', linestyle='--', label='하한')
        axes[0].axvline(mean_val, color='green', linestyle='-', label=f'중심값 {mean_val:.4f}')
        axes[0].set_xlabel('측정값')
        axes[0].set_ylabel('빈도')
        axes[0].legend()

        # (2) X-bar 관리도
        axes[1].plot(xbar, marker='o')
        axes[1].axhline(np.mean(xbar), color='green', linestyle='-', label=f'평균 {np.mean(xbar):.4f}')
        axes[1].set_title('X-bar 관리도')
        axes[1].set_xlabel('샘플 그룹')
        axes[1].set_ylabel('평균값')
        axes[1].legend()

        # (3) R 관리도
        axes[2].plot(rbar, marker='o', color='orange')
        axes[2].axhline(np.mean(rbar), color='green', linestyle='-', label=f'평균 {np.mean(rbar):.4f}')
        axes[2].set_title('R 관리도')
        axes[2].set_xlabel('샘플 그룹')
        axes[2].set_ylabel('범위(R)')
        axes[2].legend()

        # 통계 요약 텍스트
        file_line = f"파일: {os.path.basename(self.file_path)}"
        note_line = f"Note: {note_text_display}"
        stats_lines = (
            f"중심값(Mean): {mean_val:.4f}    목표중앙값: {mid_target:.4f}    차이: {mean_diff:.4f}\n"
            f"표준편차(Standard Deviation): {std_val:.4f}\n"
            f"Cp: {Cp:.3f}    Cpk: {Cpk:.3f}\n"
            f"USL(상한): {USL}    LSL(하한): {LSL}\n"
            f"총 샘플 수: {len(values)}\n"
            f"{normality_result}"
        )

        self.fig.subplots_adjust(top=0.78)
        self.fig.suptitle(f"{file_line}\n{note_line}\n{stats_lines}",
                          fontsize=13, fontweight='bold', x=0.02, y=0.98, ha='left', va='top')
        plt.tight_layout(rect=(0, 0, 1, 0.90))

        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

    def print_page(self):
        note_for_fig = self.note_entry.get()
        self.analyze_and_plot(note_for_fig=note_for_fig)

        pdf_path = os.path.splitext(self.file_path)[0] + '_inspection_report.pdf'
        try:
            self.fig.savefig(pdf_path, format='pdf', bbox_inches='tight')
            os.startfile(pdf_path)
            messagebox.showinfo("알림", f"PDF로 저장 완료\n파일: {pdf_path}")
        except Exception as e:
            messagebox.showerror("오류", f"PDF 저장 또는 열기 중 오류:\n{e}")

        self.analyze_and_plot(note_for_fig=None)

if __name__ == '__main__':
    root = tk.Tk()
    app = InspectionApp(root)
    root.mainloop()
