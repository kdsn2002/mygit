import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, Toplevel
import git
import os
import time
import webbrowser
import json
import pyperclip
from datetime import datetime

class GitCreatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("KDSN Git Helper - 记忆集成版")
        self.root.geometry("600x650")
        
        # 1. 核心配置与样式
        self.config_file = "git_helper_config.json"
        self.config_data = self.load_config()
        self.colors = {
            "flash1": "#FFFF00", "flash2": "#800080",
            "current": "#2E7D32", "blue": "#2196F3", "gray": "gray",
            "repo_name": "#D32F2F" # 醒目的红色
        }

        # 2. 变量
        self.repo_path = tk.StringVar()
        self.remote_url = tk.StringVar()
        self.current_branch = "" 

        self.setup_ui()
        self.auto_load_last_project() # 启动时尝试自动恢复记忆

    def setup_ui(self):
        # --- 顶部状态栏 (拆分仓库名和分支状态) ---
        self.status_frame = tk.LabelFrame(self.root, text=" 实时 Git 现场 (点击复制分支) ", padx=10, pady=5, 
                                          fg=self.colors["blue"], font=('Arial', 9, 'bold'), cursor="hand2")
        self.status_frame.pack(fill="x", padx=15, pady=5)
        
        # 仓库名 (红字)
        self.lbl_repo_name = tk.Label(self.status_frame, text="等待选择仓库", fg=self.colors["repo_name"], font=("微软雅黑", 11, "bold"))
        self.lbl_repo_name.pack(side="left", padx=(0, 10))

        # 分支与状态 (黑字)
        self.lbl_status = tk.Label(self.status_frame, text="...", justify="left", font=("Consolas", 10))
        self.lbl_status.pack(side="left")
        
        # 绑定点击复制和闪烁
        self.status_frame.bind("<Button-1>", lambda e: self.copy_branch_and_flash())
        self.lbl_repo_name.bind("<Button-1>", lambda e: self.copy_branch_and_flash())
        self.lbl_status.bind("<Button-1>", lambda e: self.copy_branch_and_flash())

        # 设置按钮
        tk.Button(self.root, text="⚙️ 仓库配置", command=self.open_settings, font=('Arial', 8)).place(x=510, y=25)

        # --- 路径选择 ---
        path_frame = tk.Frame(self.root)
        path_frame.pack(fill="x", padx=20, pady=10)
        tk.Entry(path_frame, textvariable=self.repo_path, state='readonly').pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Button(path_frame, text="切换项目", command=self.select_dir).pack(side="right")

        # --- 核心流水线 ---
        flow_frame = tk.LabelFrame(self.root, text="🚀 核心流水线", padx=15, pady=15)
        flow_frame.pack(fill="x", padx=20, pady=10)

        self.btn_new_feat = tk.Button(flow_frame, text="1. 生成时间分支 (标准化命名)", bg="#e3f2fd", 
                                      command=self.prepare_new_feature, height=2)
        self.btn_new_feat.pack(fill="x", pady=5)
        
        tk.Button(flow_frame, text="2. 推送当前改动并跳转 PR", bg="#c8e6c9", 
                  command=self.push_feature_for_pr, height=2).pack(fill="x", pady=5)

        # --- 日志区域 ---
        self.log_area = scrolledtext.ScrolledText(self.root, height=15, font=('Consolas', 9))
        self.log_area.pack(fill="both", padx=20, pady=10, expand=True)

    # --- 启动恢复逻辑 ---
    def auto_load_last_project(self):
        """启动时自动加载配置文件中的最后一个项目"""
        if "last_opened" in self.config_data:
            last_path = self.config_data["last_opened"]
            if os.path.exists(last_path):
                self.repo_path.set(last_path)
                self.remote_url.set(self.config_data.get(last_path, ""))
                self.update_status()
                self.log(f"自动恢复上次项目: {os.path.basename(last_path)}")
                return
        
        # 如果没有last_opened标记，但有其他配置路径，随便挑一个存在的
        for path in self.config_data.keys():
            if path != "last_opened" and os.path.exists(path):
                self.repo_path.set(path)
                self.remote_url.set(self.config_data[path])
                self.update_status()
                self.log(f"自动加载项目: {os.path.basename(path)}")
                break

    # --- 交互反馈 ---
    def flash_effect(self, stage=0):
        sequence = [self.colors["flash1"], self.colors["flash2"], self.colors["flash1"], self.colors["flash2"]]
        if stage < len(sequence):
            self.status_frame.config(fg=sequence[stage])
            self.lbl_repo_name.config(fg=sequence[stage])
            self.lbl_status.config(fg=sequence[stage])
            self.root.after(120, lambda: self.flash_effect(stage + 1))
        else:
            self.status_frame.config(fg=self.colors["blue"])
            self.lbl_repo_name.config(fg=self.colors["repo_name"])
            self.lbl_status.config(fg="black")

    def copy_branch_and_flash(self):
        if self.current_branch and self.current_branch != "None":
            pyperclip.copy(self.current_branch)
            self.flash_effect()
            self.log(f"已复制分支名: {self.current_branch}")

    # --- 核心逻辑 ---
    def get_formatted_time(self):
        now = datetime.now()
        return f"{now.year}-{now.month}-{now.day}--{now.strftime('%H-%M-%S')}"

    def update_status(self):
        path = self.repo_path.get()
        if path and os.path.exists(os.path.join(path, '.git')):
            repo_name = os.path.basename(path)
            self.lbl_repo_name.config(text=f"[{repo_name}]") # 红字显示仓库名
            try:
                repo = git.Repo(path)
                self.current_branch = repo.active_branch.name
                
                status_raw = repo.git.status()
                is_clean = "nothing to commit, working tree clean" in status_raw
                clean_msg = "✅ 现场干净" if is_clean else "⚠️ 有改动需提交"
                
                self.lbl_status.config(text=f"🌿 {self.current_branch} | {clean_msg}")
            except:
                self.lbl_status.config(text="❌ 仓库读取异常")
        else:
            self.lbl_repo_name.config(text="未选择")
            self.lbl_status.config(text="未初始化 Git 仓库")

    def prepare_new_feature(self):
        path = self.repo_path.get()
        if not path: return
        try:
            repo = git.Repo(path)
            new_time = self.get_formatted_time()
            branch_name = f"dev-{new_time}"
            
            repo.create_head(branch_name).checkout()
            self.log(f"🌱 已创建标准化时间分支: {branch_name}")
            self.update_status()
            messagebox.showinfo("分支已就绪", f"当前分支: {branch_name}\n已自动更新现场监控。")
        except Exception as e:
            self.log(f"失败: {e}")

    # --- 存档与设置 ---
    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f: return json.load(f)
        return {}

    def save_config(self):
        # 记录最后打开的路径
        self.config_data["last_opened"] = self.repo_path.get()
        with open(self.config_file, 'w') as f: json.dump(self.config_data, f)

    def select_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.repo_path.set(path)
            self.remote_url.set(self.config_data.get(path, ""))
            self.update_status()
            self.save_config() # 切换项目时自动保存为最后打开
            self.log(f"项目切换: {os.path.basename(path)}")

    def open_settings(self):
        path = self.repo_path.get()
        if not path: return
        win = Toplevel(self.root)
        win.title("仓库配置")
        win.geometry("400x200")
        tk.Label(win, text="远程 GitHub URL:").pack(pady=5)
        ent = tk.Entry(win, textvariable=self.remote_url, width=45)
        ent.pack(pady=5)
        tk.Button(win, text="保存并初始化", command=lambda: self.save_and_init(win)).pack(pady=10)

    def save_and_init(self, win):
        path = self.repo_path.get()
        self.config_data[path] = self.remote_url.get()
        self.save_config()
        if not os.path.exists(os.path.join(path, '.git')):
            git.Repo.init(path)
        win.destroy()
        self.update_status()

    def log(self, message):
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)

    def push_feature_for_pr(self):
        path = self.repo_path.get()
        url = self.remote_url.get()
        if not path or not url: return
        try:
            repo = git.Repo(path)
            current = repo.active_branch.name
            if current in ['main', 'master']:
                messagebox.showwarning("严谨警告", "禁止直接推送主分支！")
                return
            repo.git.add(A=True)
            repo.index.commit(f"PR Update: {current}")
            origin = repo.remote('origin') if 'origin' in repo.remotes else repo.create_remote('origin', url)
            origin.set_url(url)
            self.log(f"正在推送 {current}...")
            origin.push(current, force=True)
            webbrowser.open(f"{url.replace('.git', '')}/compare/{current}")
        except Exception as e: self.log(f"失败: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = GitCreatorGUI(root)
    root.mainloop()