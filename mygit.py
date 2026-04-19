import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, Toplevel
import git
import os
import time
import json
import pyperclip
import webbrowser
from datetime import datetime

class GitCreatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("KDSN Git Helper - 严谨防呆版 (防自我背刺)")
        self.root.geometry("620x760")
        
        # 1. 核心配置与样式
        self.config_file = "git_helper_config.json"
        self.config_data = self.load_config()
        self.colors = {
            "flash1": "#FFFF00", "flash2": "#800080",
            "current": "#2E7D32", "blue": "#2196F3", "gray": "gray",
            "repo_name": "#D32F2F" 
        }

        # 2. 变量
        self.repo_path = tk.StringVar()
        self.remote_url = tk.StringVar()
        self.last_branch = "无"
        self.curr_branch = "无"

        self.setup_ui()
        self.auto_load_last_project()

    def setup_ui(self):
        # --- 顶部功能区 ---
        tk.Button(self.root, text="⚙️ 仓库配置 (需配置远程 URL 才能生链接)", command=self.open_settings, font=('Arial', 9)).pack(fill="x", padx=15, pady=(10, 5))

        # ====== 双状态面板 (内嵌独立操作按钮) ======
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

        # 绑定点击复制分支名和闪烁
        for target in [last_info_frame, self.lbl_last_repo, self.lbl_last_branch, self.lbl_last_status]:
            target.bind("<Button-1>", lambda e: self.copy_branch_and_flash("last"))
        for target in [curr_info_frame, self.lbl_curr_repo, self.lbl_curr_branch, self.lbl_curr_status]:
            target.bind("<Button-1>", lambda e: self.copy_branch_and_flash("curr"))

        # --- 路径选择 ---
        path_frame = tk.Frame(self.root)
        path_frame.pack(fill="x", padx=15, pady=10)
        tk.Entry(path_frame, textvariable=self.repo_path, state='readonly').pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Button(path_frame, text="切换项目目录", command=self.select_dir).pack(side="right")

        # --- 核心流水线 (强力防重复提交) ---
        flow_frame = tk.LabelFrame(self.root, text="🚀 核心流水线 (自动防浪费保护)", padx=15, pady=15)
        flow_frame.pack(fill="x", padx=15, pady=5)

        self.btn_pipeline = tk.Button(flow_frame, text="📦 一键打包上云\n(无改动自动拦截 | 有改动自动建时间分支推云端)", 
                                      bg="#e3f2fd", font=('微软雅黑', 10, 'bold'), command=self.run_one_click_pipeline, height=2)
        self.btn_pipeline.pack(fill="x", pady=5)

        # --- 日志区域 ---
        self.log_area = scrolledtext.ScrolledText(self.root, height=10, font=('Consolas', 9))
        self.log_area.pack(fill="both", padx=15, pady=10, expand=True)

    # --- 启动恢复逻辑 ---
    def auto_load_last_project(self):
        if "last_opened" in self.config_data:
            last_path = self.config_data["last_opened"]
            if os.path.exists(last_path):
                self.repo_path.set(last_path)
                self.remote_url.set(self.config_data.get(last_path, ""))
                self.update_status()
                self.log(f"自动恢复项目: {os.path.basename(last_path)}")
                return
        for path in self.config_data.keys():
            if path != "last_opened" and os.path.exists(path):
                self.repo_path.set(path)
                self.remote_url.set(self.config_data[path])
                self.update_status()
                break

    # --- 【新增代码：生成隐身衣】 ---
    def enforce_gitignore(self, repo, path):
        """强制将工具自身文件加入忽略名单，防止被当成代码修改"""
        ignores = ['git_helper_history.log', 'git_helper_config.json']
        gitignore_path = os.path.join(path, '.gitignore')
        
        # 1. 确保名字写入了 .gitignore
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
        
        # 2. 从 Git 缓存中强行解除之前的错误追踪
        try:
            repo.git.rm('--cached', 'git_helper_history.log', 'git_helper_config.json', ignore_unmatch=True)
        except:
            pass

    # --- 交互反馈 ---
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
            self.log(f"已复制分支名: {branch}")

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

    # --- 独立 URL 获取与网页打开 ---
    def copy_branch_url(self, mode):
        url = self.remote_url.get().replace('.git', '')
        branch = self.last_branch if mode == "last" else self.curr_branch
        if url and branch and branch != "无":
            full_url = f"{url}/tree/{branch}"
            pyperclip.copy(full_url)
            self.log(f"🔗 已复制 {mode} 状态网页链接！")
            messagebox.showinfo("链接已复制", f"已复制 {mode} 状态的直达链接：\n{full_url}")

    def open_branch_web(self, mode):
        url = self.remote_url.get().replace('.git', '')
        branch = self.last_branch if mode == "last" else self.curr_branch
        if url and branch and branch != "无":
            webbrowser.open(f"{url}/tree/{branch}")

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
                
                # 【防呆机制核心】：检测前先把工具自己的文件藏起来
                self.enforce_gitignore(repo, path)
                
                self.curr_branch = repo.active_branch.name
                self.lbl_curr_branch.config(text=f"🌿 分支: {self.curr_branch}")
                
                status_raw = repo.git.status()
                is_clean = "nothing to commit, working tree clean" in status_raw
                clean_msg = "✅ 现场干净，无需重复打包" if is_clean else "⚠️ 有新改动，请点击打包上云"
                self.lbl_curr_status.config(text=clean_msg)
                
                # 按钮点亮逻辑
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

    # --- 流水线拦截 ---
    def run_one_click_pipeline(self):
        path = self.repo_path.get()
        url = self.remote_url.get()
        if not path or not url: 
            messagebox.showwarning("警告", "请先选择项目目录并在上方配置远程 URL。")
            return
            
        try:
            repo = git.Repo(path)
            status_raw = repo.git.status()
            is_clean = "nothing to commit, working tree clean" in status_raw
            
            # 【核心保护】：如果现场干净，强行拦截！
            if is_clean:
                messagebox.showinfo("拦截保护", "检测到您的代码【没有任何新修改】。\n为了节约资源，系统拒绝执行重复的打包推送操作。\n\n请先去改动代码，再来点击。")
                self.log("🛡️ 已拦截无意义的重复打包。")
                return

            # 1. 状态移交
            self.last_branch = self.curr_branch
            self.lbl_last_repo.config(text=self.lbl_curr_repo.cget("text"))
            self.lbl_last_branch.config(text=self.lbl_curr_branch.cget("text"))
            self.lbl_last_status.config(text="✅ 历史状态归档")
            self.btn_last_web.config(state="normal")
            self.btn_last_copy.config(state="normal")

            # 2. 创建时间分支
            branch_name = self.get_formatted_time()
            repo.create_head(branch_name).checkout()
            self.log(f"🌱 创建纯时间分支: {branch_name}")

            # 3. 提交改动
            repo.git.add(A=True)
            repo.index.commit(f"Auto Wrap: {branch_name}")
            self.log(f"📦 已打包本地新改动。")

            # 4. 推送云端
            origin = repo.remote('origin') if 'origin' in repo.remotes else repo.create_remote('origin', url)
            origin.set_url(url)
            self.log(f"🚀 正在推送到 GitHub...")
            origin.push(branch_name, force=True)
            self.log("✅ 代码已安全上云！")

            # 5. 刷新界面
            self.update_status()
            # 自动复制新链接
            self.copy_branch_url("curr")

        except Exception as e:
            self.log(f"❌ 流水线失败: {e}")

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
        tk.Button(win, text="保存 URL 配置", command=lambda: self.save_and_init(win)).pack(pady=10)

    def save_and_init(self, win):
        path = self.repo_path.get()
        self.config_data[path] = self.remote_url.get()
        self.save_config()
        if not os.path.exists(os.path.join(path, '.git')):
            git.Repo.init(path)
        win.destroy()
        self.update_status()

    # --- 日志持久化写入 ---
    def log(self, message):
        short_time = time.strftime('%H:%M:%S')
        long_time = time.strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{short_time}] {message}\n"
        
        self.log_area.insert(tk.END, log_line)
        self.log_area.see(tk.END)
        try:
            with open("git_helper_history.log", "a", encoding="utf-8") as f:
                f.write(f"[{long_time}] {message}\n")
        except: pass

if __name__ == "__main__":
    root = tk.Tk()
    app = GitCreatorGUI(root)
    root.mainloop()