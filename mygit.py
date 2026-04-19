import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, Toplevel
import git
import os
import time
import json
import pyperclip
import webbrowser
import sqlite3
from datetime import datetime

class GitCreatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("KDSN Git Helper - 终极无感版 (带本地数据库)")
        self.root.geometry("620x780")
        
        # 1. 核心配置与样式
        self.config_file = "git_helper_config.json"
        self.config_data = self.load_config()
        self.colors = {
            "flash1": "#FFFF00", "flash2": "#800080",
            "current": "#2E7D32", "blue": "#2196F3", "gray": "gray",
            "repo_name": "#D32F2F",
            "alert": "#E65100" # 警告橘色
        }

        # 2. 变量
        self.repo_path = tk.StringVar()
        self.remote_url = tk.StringVar()
        self.last_branch = "无"
        self.curr_branch = "无"

        # 3. 初始化本地数据库
        self.init_database()

        self.setup_ui()
        self.load_recent_logs() # 启动时读取历史日志
        self.auto_load_last_project()

    def init_database(self):
        """初始化 SQLite 数据库"""
        self.db_conn = sqlite3.connect("git_helper_data.db", check_same_thread=False)
        self.cursor = self.db_conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS logs
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                time TEXT,
                                message TEXT)''')
        self.db_conn.commit()

    def setup_ui(self):
        # --- 顶部功能区 ---
        tk.Button(self.root, text="⚙️ 仓库配置 (需配置远程 URL 才能生链接)", command=self.open_settings, font=('Arial', 9)).pack(fill="x", padx=15, pady=(10, 5))

        # ====== 双状态面板 ======
        # --- 上次状态 ---
        self.frame_last = tk.LabelFrame(self.root, text=" 上次状态 ", fg=self.colors["gray"], font=('微软雅黑', 9))
        self.frame_last.pack(fill="x", padx=15, pady=5)
        
        last_info_frame = tk.Frame(self.frame_last, cursor="hand2")
        last_info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        
        self.lbl_last_repo = tk.Label(last_info_frame, text="📁 仓库: 无", fg="gray", font=("微软雅黑", 9))
        self.lbl_last_repo.pack(anchor="w")
        self.lbl_last_branch = tk.Label(last_info_frame, text="🌿 分支: 无", font=("Consolas", 10), fg="gray")
        self.lbl_last_branch.pack(anchor="w")
        self.lbl_last_status = tk.Label(last_info_frame, text="...", fg="gray", font=("微软雅黑", 9))
        self.lbl_last_status.pack(anchor="w")

        last_btn_frame = tk.Frame(self.frame_last)
        last_btn_frame.pack(side="right", padx=10, pady=5)
        self.btn_last_web = tk.Button(last_btn_frame, text="🌐 查看", command=lambda: self.open_branch_web("last"), state="disabled")
        self.btn_last_web.pack(fill="x", pady=2)
        self.btn_last_copy = tk.Button(last_btn_frame, text="🔗 复制链接", command=lambda: self.copy_branch_url("last"), state="disabled")
        self.btn_last_copy.pack(fill="x", pady=2)

        # --- 当前实时状态 ---
        self.frame_curr = tk.LabelFrame(self.root, text=" 当前实时状态 ", fg=self.colors["blue"], font=('微软雅黑', 10, 'bold'))
        self.frame_curr.pack(fill="x", padx=15, pady=5)
        
        curr_info_frame = tk.Frame(self.frame_curr, cursor="hand2")
        curr_info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        
        self.lbl_curr_repo = tk.Label(curr_info_frame, text="📁 仓库: [等待选择]", fg=self.colors["repo_name"], font=("微软雅黑", 10, "bold"))
        self.lbl_curr_repo.pack(anchor="w")
        self.lbl_curr_branch = tk.Label(curr_info_frame, text="🌿 分支: 无", font=("Consolas", 12, "bold"), fg="black")
        self.lbl_curr_branch.pack(anchor="w")
        self.lbl_curr_status = tk.Label(curr_info_frame, text="请检测状态...", font=("微软雅黑", 10))
        self.lbl_curr_status.pack(anchor="w")

        curr_btn_frame = tk.Frame(self.frame_curr)
        curr_btn_frame.pack(side="right", padx=10, pady=5)
        self.btn_curr_web = tk.Button(curr_btn_frame, text="🌐 查看", command=lambda: self.open_branch_web("curr"), state="disabled")
        self.btn_curr_web.pack(fill="x", pady=2)
        self.btn_curr_copy = tk.Button(curr_btn_frame, text="🔗 复制链接", command=lambda: self.copy_branch_url("curr"), font=('Arial', 9, 'bold'), state="disabled")
        self.btn_curr_copy.pack(fill="x", pady=2)

        # 绑定点击事件 (无弹窗)
        for target in [last_info_frame, self.lbl_last_repo, self.lbl_last_branch, self.lbl_last_status]:
            target.bind("<Button-1>", lambda e: self.copy_branch_and_flash("last"))
        for target in [curr_info_frame, self.lbl_curr_repo, self.lbl_curr_branch, self.lbl_curr_status]:
            target.bind("<Button-1>", lambda e: self.copy_branch_and_flash("curr"))

        # --- 路径选择 ---
        path_frame = tk.Frame(self.root)
        path_frame.pack(fill="x", padx=15, pady=5)
        tk.Entry(path_frame, textvariable=self.repo_path, state='readonly').pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Button(path_frame, text="切换项目目录", command=self.select_dir).pack(side="right")

        # --- 核心流水线 (GUI 内嵌提示，拒绝弹窗) ---
        flow_frame = tk.LabelFrame(self.root, text="🚀 核心流水线", padx=15, pady=10)
        flow_frame.pack(fill="x", padx=15, pady=5)

        self.btn_pipeline = tk.Button(flow_frame, text="📦 一键打包上云\n(无弹窗 | 自动拦截 | 自动推云端)", 
                                      bg="#e3f2fd", font=('微软雅黑', 10, 'bold'), command=self.run_one_click_pipeline, height=2)
        self.btn_pipeline.pack(fill="x", pady=2)
        
        # 【新增】：专门用来显示成功或拦截信息的 GUI 文字屏 (替代弹窗)
        self.lbl_gui_alert = tk.Label(flow_frame, text="", font=("微软雅黑", 10, "bold"))
        self.lbl_gui_alert.pack(fill="x")

        # --- 日志区域 ---
        self.log_area = scrolledtext.ScrolledText(self.root, height=12, font=('Consolas', 9))
        self.log_area.pack(fill="both", padx=15, pady=10, expand=True)

    # --- GUI 提示屏功能 ---
    def show_gui_alert(self, message, color):
        """在界面上显示提示信息，3秒后自动消失"""
        self.lbl_gui_alert.config(text=message, fg=color)
        self.root.after(4000, lambda: self.lbl_gui_alert.config(text=""))

    # --- 数据库日志读写 ---
    def load_recent_logs(self):
        try:
            self.cursor.execute("SELECT time, message FROM logs ORDER BY id DESC LIMIT 15")
            rows = self.cursor.fetchall()
            if rows:
                self.log_area.insert(tk.END, "--- 数据库历史记录载入 ---\n")
                for row in reversed(rows):
                    short_t = row[0].split(" ")[1] if " " in row[0] else row[0]
                    self.log_area.insert(tk.END, f"[{short_t}] {row[1]}\n")
                self.log_area.insert(tk.END, "------------------------\n\n")
                self.log_area.see(tk.END)
        except Exception as e:
            print("读取数据库失败", e)

    def log(self, message):
        short_time = time.strftime('%H:%M:%S')
        long_time = time.strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{short_time}] {message}\n"
        
        self.log_area.insert(tk.END, log_line)
        self.log_area.see(tk.END)
        try:
            # 存入真正的 SQLite 数据库
            self.cursor.execute("INSERT INTO logs (time, message) VALUES (?, ?)", (long_time, message))
            self.db_conn.commit()
        except: pass

    # --- 启动恢复 ---
    def auto_load_last_project(self):
        if "last_opened" in self.config_data:
            last_path = self.config_data["last_opened"]
            if os.path.exists(last_path):
                self.repo_path.set(last_path)
                self.remote_url.set(self.config_data.get(last_path, ""))
                self.update_status()
                return
        for path in self.config_data.keys():
            if path != "last_opened" and os.path.exists(path):
                self.repo_path.set(path)
                self.remote_url.set(self.config_data[path])
                self.update_status()
                break

    # --- 保护机制：将数据库也加入隐身衣 ---
    def enforce_gitignore(self, repo, path):
        ignores = ['git_helper_history.log', 'git_helper_config.json', 'git_helper_data.db']
        gitignore_path = os.path.join(path, '.gitignore')
        
        content = ""
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        with open(gitignore_path, 'a', encoding='utf-8') as f:
            for item in ignores:
                if item not in content:
                    if content and not content.endswith('\n'):
                        f.write("\n")
                    f.write(f"{item}\n")
                    content += f"{item}\n"
        
        try:
            repo.git.rm('--cached', 'git_helper_history.log', 'git_helper_config.json', 'git_helper_data.db', ignore_unmatch=True)
        except: pass

    # --- 无弹窗交互反馈 ---
    def copy_branch_and_flash(self, mode):
        if mode == "last":
            branch = self.last_branch
            target_frame = self.frame_last
            target_lbl = self.lbl_last_branch
        else:
            branch = self.curr_branch
            target_frame = self.frame_curr
            target_lbl = self.lbl_curr_branch

        if branch and branch != "无" and "获取失败" not in branch:
            pyperclip.copy(branch)
            self.flash_effect(target_frame, target_lbl, mode, 0)
            self.log(f"📋 已复制分支名: {branch}")

    def flash_effect(self, frame, lbl, mode, stage):
        sequence = [self.colors["flash1"], self.colors["flash2"], self.colors["flash1"], self.colors["flash2"]]
        orig_fg = self.colors["blue"] if mode == "curr" else self.colors["gray"]
        orig_lbl_fg = "black" if mode == "curr" else self.colors["gray"]
        
        if stage < len(sequence):
            frame.config(fg=sequence[stage])
            lbl.config(fg=sequence[stage])
            self.root.after(120, lambda: self.flash_effect(frame, lbl, mode, stage + 1))
        else:
            frame.config(fg=orig_fg)
            lbl.config(fg=orig_lbl_fg)

    # --- 独立 URL 复制 (去弹窗版) ---
    def copy_branch_url(self, mode):
        url = self.remote_url.get().replace('.git', '')
        branch = self.last_branch if mode == "last" else self.curr_branch
        if url and branch and branch != "无":
            full_url = f"{url}/tree/{branch}"
            pyperclip.copy(full_url)
            self.log(f"🔗 已复制网页链接，可直接发送给 AI！")
            # 使用 GUI 屏幕提示，不弹窗
            self.show_gui_alert(f"✅ {mode} 状态网页链接已复制到剪贴板！", self.colors["current"])

    def open_branch_web(self, mode):
        url = self.remote_url.get().replace('.git', '')
        branch = self.last_branch if mode == "last" else self.curr_branch
        if url and branch and branch != "无":
            webbrowser.open(f"{url}/tree/{branch}")
            self.log("🌐 已在浏览器中打开分支")

    # --- 核心逻辑 ---
    def get_formatted_time(self):
        now = datetime.now()
        return f"{now.year}-{now.month}-{now.day}--{now.strftime('%H-%M-%S')}"

    def update_status(self):
        path = self.repo_path.get()
        if path and os.path.exists(os.path.join(path, '.git')):
            repo_name = os.path.basename(path)
            self.lbl_curr_repo.config(text=f"📁 仓库: [{repo_name}]")
            try:
                repo = git.Repo(path)
                self.enforce_gitignore(repo, path)
                
                self.curr_branch = repo.active_branch.name
                self.lbl_curr_branch.config(text=f"🌿 分支: {self.curr_branch}")
                
                status_raw = repo.git.status()
                is_clean = "nothing to commit, working tree clean" in status_raw
                clean_msg = "✅ 现场干净，无需重复打包" if is_clean else "⚠️ 有新改动，请点击打包上云"
                self.lbl_curr_status.config(text=clean_msg)
                
                has_url = bool(self.remote_url.get())
                self.btn_curr_web.config(state="normal" if has_url else "disabled")
                self.btn_curr_copy.config(state="normal" if is_clean and has_url else "disabled")
                
            except:
                self.lbl_curr_branch.config(text="🌿 分支: 获取失败")
                self.lbl_curr_status.config(text="❌ 仓库读取异常")
        else:
            self.lbl_curr_repo.config(text="📁 仓库: 未选择")
            self.lbl_curr_branch.config(text="🌿 分支: 无")
            self.lbl_curr_status.config(text="未初始化 Git 仓库")

    # --- 终极无弹窗版流水线 ---
    def run_one_click_pipeline(self):
        path = self.repo_path.get()
        url = self.remote_url.get()
        if not path or not url: 
            self.show_gui_alert("❌ 请先配置本地仓库和远程 URL！", "red")
            return
            
        try:
            repo = git.Repo(path)
            status_raw = repo.git.status()
            is_clean = "nothing to commit, working tree clean" in status_raw
            
            # 【核心保护：彻底无弹窗的拦截】
            if is_clean:
                self.show_gui_alert("🛡️ 拦截：代码无改动，拒绝浪费资源的重复打包！", self.colors["alert"])
                self.log("🛡️ 已拦截无意义的重复打包。")
                return

            self.show_gui_alert("⏳ 正在打包并推送至云端...", "blue")
            self.root.update() # 强制刷新 UI 让提示立刻显示

            # 1. 状态移交
            self.last_branch = self.curr_branch
            self.lbl_last_repo.config(text=self.lbl_curr_repo.cget("text"))
            self.lbl_last_branch.config(text=self.lbl_curr_branch.cget("text"))
            self.lbl_last_status.config(text="✅ 历史状态归档")
            self.btn_last_web.config(state="normal")
            self.btn_last_copy.config(state="normal")

            # 2. 创建分支 & 提交
            branch_name = self.get_formatted_time()
            repo.create_head(branch_name).checkout()
            repo.git.add(A=True)
            repo.index.commit(f"Auto Wrap: {branch_name}")

            # 3. 推送云端
            origin = repo.remote('origin') if 'origin' in repo.remotes else repo.create_remote('origin', url)
            origin.set_url(url)
            origin.push(branch_name, force=True)

            # 4. 界面刷新与成功提示
            self.update_status()
            self.copy_branch_url("curr") # 自动复制
            
            # GUI 原生成功提示
            self.show_gui_alert("✅ 打包上云成功！当前链接已自动复制！", self.colors["current"])
            self.log("✅ 代码流水线执行完毕，安全上云。")

        except Exception as e:
            self.log(f"❌ 流水线失败: {e}")
            self.show_gui_alert("❌ 推送失败，详情请看日志", "red")

    # --- 存档与设置 ---
    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f: return json.load(f)
        return {}

    def save_config(self):
        self.config_data["last_opened"] = self.repo_path.get()
        with open(self.config_file, 'w') as f: json.dump(self.config_data, f)

    def select_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.repo_path.set(path)
            self.remote_url.set(self.config_data.get(path, ""))
            self.update_status()
            self.save_config() 

    def open_settings(self):
        path = self.repo_path.get()
        if not path: return
        win = Toplevel(self.root)
        win.title("仓库配置")
        win.geometry("400x200")
        tk.Label(win, text="远程 GitHub URL:").pack(pady=5)
        ent = tk.Entry(win, textvariable=self.remote_url, width=45)
        ent.pack(pady=5)
        tk.Button(win, text="保存 URL 配置", command=lambda: self.save_and_init(win)).pack(pady=10)

    def save_and_init(self, win):
        path = self.repo_path.get()
        self.config_data[path] = self.remote_url.get()
        self.save_config()
        if not os.path.exists(os.path.join(path, '.git')):
            git.Repo.init(path)
        win.destroy()
        self.update_status()

if __name__ == "__main__":
    root = tk.Tk()
    app = GitCreatorGUI(root)
    root.mainloop()