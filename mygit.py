import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, Toplevel, simpledialog
from tkinter import ttk
import git
import os
import time
import json
import pyperclip
import webbrowser
import sqlite3
import shutil
import stat
from datetime import datetime

class GitCreatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("KDSN Git Helper - 终极纯净版 (自适应拉伸 + 弹窗交互)")
        self.root.geometry("620x800") 
        self.root.minsize(550, 600) # 防止缩得太小导致控件重叠
        
        self.config_file = "git_helper_config.json"
        self.config_data = self.load_config()
        self.colors = {
            "flash1": "#FFFF00", "flash2": "#800080",
            "current": "#2E7D32", "blue": "#2196F3", "gray": "gray",
            "repo_name": "#D32F2F",
            "alert": "#E65100"
        }

        self.repo_path = tk.StringVar()
        self.remote_url = tk.StringVar()
        self.last_branch = "无"
        self.curr_branch = "无"

        self.init_database()
        self.setup_ui()
        self.load_recent_logs()
        self.auto_load_last_project()
        
        # 启动极低开销的实时监控引擎
        self.auto_check_status()

    def init_database(self):
        self.db_conn = sqlite3.connect("git_helper_data.db", check_same_thread=False)
        self.cursor = self.db_conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS logs
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                time TEXT,
                                message TEXT)''')
        self.db_conn.commit()

    def setup_ui(self):
        # --- 1. 顶部大红字与导航 (填满 X 轴) ---
        header_frame = tk.Frame(self.root)
        header_frame.pack(fill="x", padx=15, pady=(15, 5))

        tk.Button(header_frame, text="⚙️ 仓库配置", command=self.open_settings, font=('Arial', 10, 'bold'), bg="#f0f0f0").pack(side="left")
        # 将历史分支按钮收纳至顶部
        tk.Button(header_frame, text="🗂️ 历史分支", command=self.open_history_window, font=('Arial', 10, 'bold'), bg="#e8f5e9").pack(side="left", padx=(10, 0))
        
        self.lbl_main_repo = tk.Label(header_frame, text="[未选择仓库]", fg="red", font=("微软雅黑", 16, "bold"))
        self.lbl_main_repo.pack(side="left", expand=True)

        # --- 2. 路径切换与下拉框 ---
        path_frame = tk.Frame(self.root)
        path_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        self.combo_path = ttk.Combobox(path_frame, textvariable=self.repo_path, state='readonly', font=('Arial', 10))
        self.combo_path.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.combo_path.bind("<<ComboboxSelected>>", self.on_combo_select)
        
        tk.Button(path_frame, text="📁 浏览新目录", command=self.select_dir, font=('Arial', 9)).pack(side="right")

        # ====== 3. 双状态面板 (上下流线布局，自适应宽度) ======
        # [上次状态]
        self.frame_last = tk.LabelFrame(self.root, text=" 上次状态 ", fg=self.colors["gray"], font=('微软雅黑', 10))
        self.frame_last.pack(fill="x", padx=15, pady=5)
        
        last_info_frame = tk.Frame(self.frame_last, cursor="hand2")
        last_info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        
        self.lbl_last_msg = tk.Label(last_info_frame, text="📝 记录: 无", fg="gray", font=("微软雅黑", 10, "bold"))
        self.lbl_last_msg.pack(anchor="w")
        self.lbl_last_branch = tk.Label(last_info_frame, text="🌿 分支: 无", font=("Consolas", 10), fg="gray")
        self.lbl_last_branch.pack(anchor="w")
        self.lbl_last_status = tk.Label(last_info_frame, text="...", fg="gray", font=("微软雅黑", 9))
        self.lbl_last_status.pack(anchor="w")

        last_btn_frame = tk.Frame(self.frame_last)
        last_btn_frame.pack(side="right", padx=10, pady=5)
        self.btn_last_web = tk.Button(last_btn_frame, text="🌐 查看", command=lambda: self.open_branch_web("last"), state="disabled")
        self.btn_last_web.pack(fill="x", pady=2)
        self.btn_last_copy = tk.Button(last_btn_frame, text="🔗 链接", command=lambda: self.copy_branch_url("last"), state="disabled")
        self.btn_last_copy.pack(fill="x", pady=2)

        # [当前实时状态]
        self.frame_curr = tk.LabelFrame(self.root, text=" 当前实时状态 ", fg=self.colors["blue"], font=('微软雅黑', 10, 'bold'))
        self.frame_curr.pack(fill="x", padx=15, pady=5)
        
        curr_info_frame = tk.Frame(self.frame_curr, cursor="hand2")
        curr_info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        
        # 移除原有的文本框，直接用 Label 表征当前是在什么分支工作
        self.lbl_curr_branch = tk.Label(curr_info_frame, text="🌿 分支: 无", font=("Consolas", 12, "bold"), fg="black")
        self.lbl_curr_branch.pack(anchor="w")
        self.lbl_curr_status = tk.Label(curr_info_frame, text="请检测状态...", font=("微软雅黑", 10))
        self.lbl_curr_status.pack(anchor="w")

        curr_btn_frame = tk.Frame(self.frame_curr)
        curr_btn_frame.pack(side="right", padx=10, pady=5)
        self.btn_curr_web = tk.Button(curr_btn_frame, text="🌐 查看", command=lambda: self.open_branch_web("curr"), state="disabled")
        self.btn_curr_web.pack(fill="x", pady=2)
        self.btn_curr_copy = tk.Button(curr_btn_frame, text="🔗 链接", command=lambda: self.copy_branch_url("curr"), font=('Arial', 9, 'bold'), state="disabled")
        self.btn_curr_copy.pack(fill="x", pady=2)

        for target in [last_info_frame, self.lbl_last_msg, self.lbl_last_branch, self.lbl_last_status]:
            target.bind("<Button-1>", lambda e: self.copy_branch_and_flash("last"))
        for target in [curr_info_frame, self.lbl_curr_branch, self.lbl_curr_status]:
            target.bind("<Button-1>", lambda e: self.copy_branch_and_flash("curr"))

        # --- 4. 核心流水线区 ---
        flow_frame = tk.LabelFrame(self.root, text="🚀 核心流水线", padx=15, pady=10)
        flow_frame.pack(fill="x", padx=15, pady=5)
        
        self.btn_pipeline = tk.Button(flow_frame, text="📦 一键打包上云\n(点击后输入更新内容 ➔ 建分支 ➔ 提交 ➔ 推送)", 
                                      bg="#e3f2fd", font=('微软雅黑', 11, 'bold'), command=self.run_one_click_pipeline, height=2)
        self.btn_pipeline.pack(fill="x")
        
        self.lbl_gui_alert = tk.Label(flow_frame, text="", font=("微软雅黑", 10, "bold"))
        self.lbl_gui_alert.pack(fill="x")

        # --- 5. 日志控制条与内容区 (拉伸的核心支撑) ---
        log_ctrl_frame = tk.Frame(self.root)
        log_ctrl_frame.pack(fill="x", padx=15, pady=(5, 0))
        
        tk.Label(log_ctrl_frame, text="📄 操作日志", font=('微软雅黑', 9, 'bold'), fg="gray").pack(side="left")
        tk.Button(log_ctrl_frame, text="🧹 清空", command=self.clear_logs, font=('微软雅黑', 8), cursor="hand2", bg="#f5f5f5").pack(side="right", padx=(5, 0))
        tk.Button(log_ctrl_frame, text="📋 复制全部", command=self.copy_all_logs, font=('微软雅黑', 8), cursor="hand2", bg="#e8f5e9").pack(side="right")

        # expand=True 让日志区域在窗口被纵向拉伸时能自动吸纳所有多余空间
        self.log_area = scrolledtext.ScrolledText(self.root, height=12, font=('Consolas', 9))
        self.log_area.pack(fill="both", expand=True, padx=15, pady=(2, 10))

    def show_gui_alert(self, message, color):
        self.lbl_gui_alert.config(text=message, fg=color)
        self.root.after(4000, lambda: self.lbl_gui_alert.config(text=""))

    def load_recent_logs(self):
        try:
            self.log_area.delete('1.0', tk.END)
            self.cursor.execute("SELECT time, message FROM logs ORDER BY id DESC LIMIT 15")
            rows = self.cursor.fetchall()
            if rows:
                for row in rows:
                    self.log_area.insert(tk.END, f"[{row[0]}] {row[1]}\n")
                self.log_area.insert(tk.END, "--- 以上为数据库历史记录 ---\n")
        except Exception as e:
            pass

    def log(self, message):
        full_time = time.strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{full_time}] {message}\n"
        
        self.log_area.insert('1.0', log_line)
        self.log_area.see('1.0') 
        
        try:
            self.cursor.execute("INSERT INTO logs (time, message) VALUES (?, ?)", (full_time, message))
            self.db_conn.commit()
        except: pass

    def clear_logs(self):
        self.log_area.delete('1.0', tk.END)
        try:
            self.cursor.execute("DELETE FROM logs")
            self.db_conn.commit()
        except: pass
        try:
            with open("git_helper_history.log", "w", encoding="utf-8") as f:
                pass 
        except: pass
        self.log("🧹 历史日志已瞬间清空。")

    def copy_all_logs(self):
        content = self.log_area.get('1.0', tk.END).strip()
        if content:
            pyperclip.copy(content)
            self.show_gui_alert("📋 日志已全部复制到剪贴板！", self.colors["current"])
        else:
            self.show_gui_alert("⚠️ 日志为空", self.colors["alert"])

    def update_combo_values(self):
        paths = [p for p in self.config_data.keys() if p != "last_opened" and os.path.exists(p)]
        self.combo_path['values'] = paths

    def auto_load_last_project(self):
        self.update_combo_values()
        if "last_opened" in self.config_data:
            last_path = self.config_data["last_opened"]
            if os.path.exists(last_path):
                self.repo_path.set(last_path)
                self.remote_url.set(self.config_data.get(last_path, ""))
                self.update_status()
                self.log(f"🔄 自动恢复上次项目: {os.path.basename(last_path)}")
                return
        for path in self.config_data.keys():
            if path != "last_opened" and os.path.exists(path):
                self.repo_path.set(path)
                self.remote_url.set(self.config_data[path])
                self.update_status()
                self.log(f"🔄 自动恢复项目: {os.path.basename(path)}")
                break

    def enforce_gitignore(self, repo, path):
        ignores = [
            '# Git Helper 自身文件',
            'git_helper_history.log', 'git_helper_config.json', 'git_helper_data.db',
            '# Python 打包与编译垃圾',
            '__pycache__/', '*.pyc', 'build/', 'dist/', '*.exe', '*.spec',
            '# 自动化测试与浏览器缓存 (webqu 专属)',
            'browser_data/', 'browser_data_safe/',
            '# 虚拟环境与前端依赖',
            'venv/', '.venv/', 'node_modules/'
        ]
        
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
            for junk in ['__pycache__', 'build', 'dist', 'browser_data', 'browser_data_safe', '*.pyc', '*.exe', 'git_helper_history.log', 'git_helper_config.json', 'git_helper_data.db']:
                try:
                    repo.git.rm('-r', '--cached', junk, ignore_unmatch=True)
                except:
                    pass 
        except: pass

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

    def copy_branch_url(self, mode):
        url = self.remote_url.get().replace('.git', '')
        branch = self.last_branch if mode == "last" else self.curr_branch
        if url and branch and branch != "无":
            full_url = f"{url}/tree/{branch}"
            pyperclip.copy(full_url)
            self.log(f"🔗 已复制网页链接，可直接发送给 AI！")
            self.show_gui_alert(f"✅ {mode} 状态网页链接已复制！", self.colors["current"])

    def open_branch_web(self, mode):
        url = self.remote_url.get().replace('.git', '')
        branch = self.last_branch if mode == "last" else self.curr_branch
        if url and branch and branch != "无":
            webbrowser.open(f"{url}/tree/{branch}")
            self.log("🌐 已在浏览器中打开分支")

    def get_formatted_time(self):
        now = datetime.now()
        return f"{now.year}-{now.month}-{now.day}--{now.strftime('%H-%M-%S')}"

    # --- 极低资源消耗的动态监控 ---
    def auto_check_status(self):
        path = self.repo_path.get()
        if path and os.path.exists(os.path.join(path, '.git')):
            try:
                repo = git.Repo(path)
                status_raw = repo.git.status('--porcelain')
                is_clean = len(status_raw) == 0
                clean_msg = "✅ 现场干净，无需重复打包" if is_clean else "⚠️ 有新改动，请点击打包并输入更新记录"
                
                if self.lbl_curr_status.cget("text") != clean_msg:
                    self.lbl_curr_status.config(text=clean_msg)
                    has_url = bool(self.remote_url.get())
                    self.btn_curr_copy.config(state="normal" if is_clean and has_url else "disabled")
            except: pass
        
        self.root.after(2000, self.auto_check_status)

    # --- 【重点功能重构】：弹出独立的“历史分支”窗口 ---
    def open_history_window(self):
        path = self.repo_path.get()
        if not path or not os.path.exists(os.path.join(path, '.git')):
            messagebox.showwarning("提示", "当前目录不是有效的 Git 仓库，无法查看历史分支。")
            return

        win = Toplevel(self.root)
        win.title("🗂️ 历史分支与载入")
        win.geometry("650x450")
        win.minsize(500, 300)
        
        frame_branches = tk.Frame(win)
        frame_branches.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("select", "branch", "message")
        tree = ttk.Treeview(frame_branches, columns=columns, show="headings", selectmode="browse")
        
        tree.heading("select", text="单选")
        tree.column("select", width=50, anchor="center", stretch=False)
        
        tree.heading("branch", text="时间分支名")
        tree.column("branch", width=160, anchor="w", stretch=False)
        
        tree.heading("message", text="纯净更新内容")
        tree.column("message", width=360, anchor="w", stretch=True)
        
        def on_tree_click(event):
            item = tree.identify_row(event.y)
            if item:
                # 重置所有为未选
                for child in tree.get_children():
                    vals = list(tree.item(child, "values"))
                    if vals[0] == "🔘":
                        vals[0] = "⚪"
                        tree.item(child, values=vals)
                # 勾选当前
                vals = list(tree.item(item, "values"))
                vals[0] = "🔘"
                tree.item(item, values=vals)
                
        tree.bind("<ButtonRelease-1>", on_tree_click)
        
        scrollbar = ttk.Scrollbar(frame_branches, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        tree.pack(side="top", fill="both", expand=True)

        try:
            repo = git.Repo(path)
            branches = sorted(repo.branches, key=lambda b: b.commit.committed_datetime, reverse=True)
            for b in branches:
                msg = b.commit.message.strip().split('\n')[0]
                if msg.startswith("Auto Wrap: "):
                    msg = msg.replace("Auto Wrap: ", "")
                # 【强迫症清理】：剔除可能带上的 ": 分支名" 尾巴，保证列表只看纯净文字
                if f": {b.name}" in msg:
                    msg = msg.replace(f": {b.name}", "")
                
                # 当前工作区的分支前加个小标记
                if b.name == repo.active_branch.name:
                    msg = f"[当前停留] {msg}"
                    
                tree.insert("", "end", values=("⚪", b.name, msg))
        except Exception as e:
            pass

        btn_load = tk.Button(win, text="⬇️ 载入勾选的历史分支 (回到过去)", font=('微软雅黑', 10, 'bold'), bg="#e8f5e9", height=2,
                             command=lambda: self.load_selected_branch_from_tree(tree, win))
        btn_load.pack(fill="x", padx=10, pady=(0, 10))

    def load_selected_branch_from_tree(self, tree, win):
        target_branch = None
        for child in tree.get_children():
            if tree.item(child, "values")[0] == "🔘":
                target_branch = tree.item(child, "values")[1]
                break
                
        if not target_branch:
            messagebox.showwarning("提示", "请先在列表中点击勾选一个分支", parent=win)
            return
            
        path = self.repo_path.get()
        try:
            repo = git.Repo(path)
            if repo.is_dirty(untracked_files=True):
                if not messagebox.askyesno("⚠️ 改动冲突警告", "当前有未提交的代码改动！\n\n强行载入历史分支会导致当前未打包的代码被覆盖丢失。\n是否坚持载入？", parent=win):
                    return
                repo.git.reset('--hard') 
            
            repo.git.checkout(target_branch)
            self.log(f"🔄 成功穿越载入历史分支: {target_branch}")
            self.update_status()
            self.show_gui_alert(f"✅ 已成功载入分支: {target_branch}", self.colors["current"])
            win.destroy()
        except Exception as e:
            self.log(f"❌ 载入分支失败: {e}")
            self.show_gui_alert("❌ 载入失败，请检查日志", "red")

    def update_status(self):
        path = self.repo_path.get()
        if path and os.path.exists(os.path.join(path, '.git')):
            repo_name = os.path.basename(path)
            self.lbl_main_repo.config(text=f"[{repo_name}]")
            try:
                repo = git.Repo(path)
                self.enforce_gitignore(repo, path)
                
                self.curr_branch = repo.active_branch.name
                self.lbl_curr_branch.config(text=f"🌿 分支: {self.curr_branch}")
                
                has_url = bool(self.remote_url.get())
                self.btn_curr_web.config(state="normal" if has_url else "disabled")
            except:
                self.lbl_curr_branch.config(text="🌿 分支: 获取失败")
        else:
            repo_name = os.path.basename(path) if path else "未选择"
            self.lbl_main_repo.config(text=f"[{repo_name}]")
            self.lbl_curr_branch.config(text="🌿 分支: 无")
            self.lbl_curr_status.config(text="未初始化 Git 仓库 (请点击左上角配置 URL)")
            self.btn_curr_web.config(state="disabled")
            self.btn_curr_copy.config(state="disabled")

    def run_one_click_pipeline(self):
        path = self.repo_path.get()
        url = self.remote_url.get()
        if not path or not url: 
            self.show_gui_alert("❌ 请先配置本地仓库和远程 URL！", "red")
            return
            
        try:
            if not os.path.exists(os.path.join(path, '.git')):
                git.Repo.init(path)
                self.log(f"🌱 发现空白状态，流水线已自动为你执行 git init")
                self.update_status() 

            repo = git.Repo(path)
            status_raw = repo.git.status()
            is_clean = "nothing to commit, working tree clean" in status_raw
            
            if is_clean:
                if not messagebox.askyesno("异常同步提示", "当前代码没有检测到任何新改动。\n\n如果您刚刚删除了云端仓库并重新创建，或者由于其他原因云端数据丢失，请点击【是】强行新建时间分支并同步。\n\n否则请点击【否】取消操作。"):
                    self.show_gui_alert("🛡️ 已取消打包推送。", self.colors["alert"])
                    return
                else:
                    self.log("⚠️ 触发强制同步模式...")

            # --- 【重点重构】：通过优雅的弹窗接收更新内容 ---
            custom_msg = simpledialog.askstring("输入更新内容", "准备打包上云！\n请输入本次更新的核心记录描述：\n（留空将默认使用 '自动打包上云'）", parent=self.root)
            
            if custom_msg is None:
                # 用户点击了弹窗的“取消”或关闭了弹窗
                self.show_gui_alert("🛡️ 已取消打包推送 (未确认更新内容)。", self.colors["alert"])
                return
                
            custom_msg = custom_msg.strip()
            if not custom_msg:
                custom_msg = "自动打包上云"

            self.show_gui_alert("⏳ 正在创建时间分支并推送至云端...", "blue")
            self.root.update()

            self.last_branch = self.curr_branch
            self.lbl_last_msg.config(text=f"📝 记录: {custom_msg}")
            self.lbl_last_branch.config(text=self.lbl_curr_branch.cget("text"))
            self.lbl_last_status.config(text="✅ 历史状态归档")
            self.btn_last_web.config(state="normal")
            self.btn_last_copy.config(state="normal")

            branch_name = self.get_formatted_time()
            try:
                repo.git.checkout('-b', branch_name)
            except Exception:
                repo.git.checkout('-B', branch_name)

            repo.git.add(A=True)
            # 提交格式：更新内容 : 分支名
            repo.index.commit(f"{custom_msg}: {branch_name}")

            self.log(f"📡 正在尝试连线推送到: {url}")
            
            origin = repo.remote('origin') if 'origin' in repo.remotes else repo.create_remote('origin', url)
            origin.set_url(url)
            origin.push(branch_name, force=True, set_upstream=True)

            self.update_status()
            self.copy_branch_url("curr")
            
            self.show_gui_alert("✅ 时间分支打包上云成功！", self.colors["current"])
            self.log("✅ 代码流水线执行完毕，新时间分支已上云。")

        except Exception as e:
            self.log(f"❌ 流水线失败: {e}")
            self.show_gui_alert("❌ 推送失败，详情请看日志", "red")

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f: return json.load(f)
        return {}

    def save_config(self):
        self.config_data["last_opened"] = self.repo_path.get()
        with open(self.config_file, 'w') as f: json.dump(self.config_data, f)
        self.update_combo_values() 

    def on_combo_select(self, event):
        path = self.repo_path.get()
        if path and os.path.exists(path):
            self.remote_url.set(self.config_data.get(path, ""))
            self.last_branch = "无"
            self.lbl_last_msg.config(text="📝 记录: 无")
            self.lbl_last_branch.config(text="🌿 分支: 无")
            self.lbl_last_status.config(text="...")
            self.btn_last_web.config(state="disabled")
            self.btn_last_copy.config(state="disabled")
            
            self.update_status()
            self.save_config() 
            self.log(f"📂 下拉切换项目至: {os.path.basename(path)}")

    def select_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.repo_path.set(path)
            self.remote_url.set(self.config_data.get(path, ""))
            self.last_branch = "无"
            self.lbl_last_msg.config(text="📝 记录: 无")
            self.lbl_last_branch.config(text="🌿 分支: 无")
            self.lbl_last_status.config(text="...")
            self.btn_last_web.config(state="disabled")
            self.btn_last_copy.config(state="disabled")
            
            self.update_status()
            self.save_config() 
            self.log(f"📁 浏览切换项目至: {os.path.basename(path)}")

    def remove_readonly(self, func, path, _):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def delete_git_folder(self, win):
        path = self.repo_path.get()
        git_dir = os.path.join(path, '.git')
        
        if not os.path.exists(git_dir):
            messagebox.showinfo("提示", "当前目录干净清爽，不存在 .git 记忆，无需删除。")
            return
            
        if messagebox.askyesno("🔥 终极警告", "确定要彻底删除本地的 .git 记忆吗？\n\n这会清空所有本地 Git 提交历史，但【绝对不会】删除你的任何代码文件！\n\n物理超度后，下次打包将作为全新的项目推送到云端！"):
            try:
                shutil.rmtree(git_dir, onerror=self.remove_readonly)
                self.log(f"🔥 已成功摧毁本地影子库记忆: {os.path.basename(path)}")
                self.update_status() 
                win.destroy() 
                messagebox.showinfo("超度成功", "本地影子库已被彻底物理粉碎！\n\n系统已进入无感复活模式，请直接点击【📦 一键打包上云】，一切将自动从零开始！")
            except Exception as e:
                messagebox.showerror("删除失败", f"删除 .git 文件夹时出错:\n{e}")

    def open_settings(self):
        path = self.repo_path.get()
        if not path: return
        win = Toplevel(self.root)
        win.title("仓库配置与高级管理")
        win.geometry("500x180")
        
        tk.Label(win, text="远程 GitHub URL:").pack(pady=(20, 5))
        ent = tk.Entry(win, textvariable=self.remote_url, width=50)
        ent.pack(pady=5)
        
        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=20, fill="x", padx=20)
        tk.Button(btn_frame, text="💾 保存 URL 配置", command=lambda: self.save_and_init(win), bg="#e3f2fd", font=("微软雅黑", 9, "bold"), height=2).pack(side="left", expand=True, fill="x", padx=(0, 5))
        tk.Button(btn_frame, text="🔥 删除 .git 记忆", command=lambda: self.delete_git_folder(win), bg="#ffebee", fg="red", font=("微软雅黑", 9, "bold"), height=2).pack(side="right", expand=True, fill="x", padx=(5, 0))

    def save_and_init(self, win):
        path = self.repo_path.get()
        self.config_data[path] = self.remote_url.get()
        self.save_config()
        if not os.path.exists(os.path.join(path, '.git')):
            git.Repo.init(path)
            self.log(f"🌱 自动为 {os.path.basename(path)} 初始化了全新的 Git 仓库")
        win.destroy()
        self.update_status()

if __name__ == "__main__":
    root = tk.Tk()
    app = GitCreatorGUI(root)
    root.mainloop()