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
        self.root.title("KDSN Git Helper - 终极流水线版")
        self.root.geometry("620x720")
        
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
        self.last_branch = "无"
        self.curr_branch = "无"

        self.setup_ui()
        self.auto_load_last_project()

    def setup_ui(self):
        # --- 顶部大容器 (分左右两列) ---
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=15, pady=5)
        
        left_frame = tk.Frame(top_frame)
        left_frame.pack(side="left", fill="both", expand=True)
        
        right_frame = tk.Frame(top_frame)
        right_frame.pack(side="right", fill="y", padx=(10, 0), pady=5)

        # ====== 左侧：双状态面板 ======
        # --- 上次状态 ---
        self.frame_last = tk.LabelFrame(left_frame, text=" 上次状态 (点击复制分支) ", fg=self.colors["gray"], font=('微软雅黑', 9), cursor="hand2")
        self.frame_last.pack(fill="x", pady=2)
        
        self.lbl_last_repo = tk.Label(self.frame_last, text="📁 仓库: 无", fg="gray", font=("微软雅黑", 9))
        self.lbl_last_repo.pack(anchor="w")
        self.lbl_last_branch = tk.Label(self.frame_last, text="🌿 分支: 无", font=("Consolas", 10), fg="gray")
        self.lbl_last_branch.pack(anchor="w")
        self.lbl_last_status = tk.Label(self.frame_last, text="...", fg="gray", font=("微软雅黑", 9))
        self.lbl_last_status.pack(anchor="w")

        # --- 当前实时状态 ---
        self.frame_curr = tk.LabelFrame(left_frame, text=" 当前实时状态 (点击复制分支) ", fg=self.colors["blue"], font=('微软雅黑', 10, 'bold'), cursor="hand2")
        self.frame_curr.pack(fill="x", pady=2)
        
        self.lbl_curr_repo = tk.Label(self.frame_curr, text="📁 仓库: [等待选择]", fg=self.colors["repo_name"], font=("微软雅黑", 10, "bold"))
        self.lbl_curr_repo.pack(anchor="w")
        self.lbl_curr_branch = tk.Label(self.frame_curr, text="🌿 分支: 无", font=("Consolas", 12, "bold"), fg="black")
        self.lbl_curr_branch.pack(anchor="w")
        self.lbl_curr_status = tk.Label(self.frame_curr, text="请检测状态...", font=("微软雅黑", 10))
        self.lbl_curr_status.pack(anchor="w")

        # 绑定点击复制和闪烁
        for target in [self.frame_last, self.lbl_last_repo, self.lbl_last_branch, self.lbl_last_status]:
            target.bind("<Button-1>", lambda e: self.copy_branch_and_flash("last"))
        for target in [self.frame_curr, self.lbl_curr_repo, self.lbl_curr_branch, self.lbl_curr_status]:
            target.bind("<Button-1>", lambda e: self.copy_branch_and_flash("curr"))

        # ====== 右侧：功能按钮组 ======
        tk.Button(right_frame, text="⚙️ 仓库配置", command=self.open_settings, font=('Arial', 8)).pack(fill="x", pady=3)
        tk.Button(right_frame, text="🌐 查看分支", command=self.open_branch_web, font=('Arial', 8)).pack(fill="x", pady=3)
        
        # 【新增】：智能复制网址按钮（默认为灰）
        self.btn_copy_url = tk.Button(right_frame, text="🔗 复制网页链接", command=self.copy_branch_url, font=('Arial', 8, 'bold'), state="disabled")
        self.btn_copy_url.pack(fill="x", pady=3)

        # --- 路径选择 ---
        path_frame = tk.Frame(self.root)
        path_frame.pack(fill="x", padx=20, pady=5)
        tk.Entry(path_frame, textvariable=self.repo_path, state='readonly').pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Button(path_frame, text="切换项目", command=self.select_dir).pack(side="right")

        # --- 核心流水线 (合并为一个大按钮) ---
        flow_frame = tk.LabelFrame(self.root, text="🚀 核心流水线", padx=15, pady=15)
        flow_frame.pack(fill="x", padx=20, pady=10)

        self.btn_pipeline = tk.Button(flow_frame, text="📦 一键打包上云\n(建时间分支 ➔ 提交改动 ➔ 推送)", 
                                      bg="#e3f2fd", font=('微软雅黑', 11, 'bold'), command=self.run_one_click_pipeline, height=2)
        self.btn_pipeline.pack(fill="x", pady=5)

        # --- 日志区域 ---
        self.log_area = scrolledtext.ScrolledText(self.root, height=10, font=('Consolas', 9))
        self.log_area.pack(fill="both", padx=20, pady=5, expand=True)

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

    # --- 交互反馈 (区分上次和本次闪烁) ---
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

    # --- 智能获取网页直达链接 ---
    def copy_branch_url(self):
        url = self.remote_url.get().replace('.git', '')
        if url and self.curr_branch and self.curr_branch != "无":
            full_url = f"{url}/tree/{self.curr_branch}"
            pyperclip.copy(full_url)
            self.log(f"🔗 已提取并复制源码网页链接！")
            messagebox.showinfo("链接已就绪", "网页直达链接已在剪贴板，快去发给 Gemini 吧！")

    def open_branch_web(self):
        url = self.remote_url.get().replace('.git', '')
        if url and self.curr_branch and self.curr_branch != "无":
            webbrowser.open(f"{url}/tree/{self.curr_branch}")

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
                self.curr_branch = repo.active_branch.name
                self.lbl_curr_branch.config(text=f"🌿 分支: {self.curr_branch}")
                
                status_raw = repo.git.status()
                is_clean = "nothing to commit, working tree clean" in status_raw
                clean_msg = "✅ 现场干净，可以去 PR 了" if is_clean else "⚠️ 有改动，请先打包上云"
                self.lbl_curr_status.config(text=clean_msg)
                
                # 【关键点】：如果是干净的（意味着已提交/刚推送过），就点亮第三条按钮！否则变灰。
                self.btn_copy_url.config(state="normal" if is_clean else "disabled")
                
            except:
                self.lbl_curr_branch.config(text="🌿 分支: 获取失败")
                self.lbl_curr_status.config(text="❌ 仓库读取异常")
                self.btn_copy_url.config(state="disabled")
        else:
            self.lbl_curr_repo.config(text="📁 仓库: 未选择")
            self.lbl_curr_branch.config(text="🌿 分支: 无")
            self.lbl_curr_status.config(text="未初始化 Git 仓库")
            self.btn_copy_url.config(state="disabled")

    # --- 【重点】合并后的一键流水线 ---
    def run_one_click_pipeline(self):
        path = self.repo_path.get()
        url = self.remote_url.get()
        if not path or not url: 
            messagebox.showwarning("警告", "请确保路径已选择且 URL 已配置。")
            return
            
        try:
            repo = git.Repo(path)
            status_raw = repo.git.status()
            is_clean = "nothing to commit" in status_raw
            
            # 1. 现场保护：如果没有改动，询问是否还要强行建分支
            if is_clean:
                if not messagebox.askyesno("提示", "当前没有检测到代码改动（现场是干净的）。\n确定还要新建一个时间分支并推送吗？"):
                    return

            # 2. 状态移交 (将当前UI内容移交给上次状态)
            self.last_branch = self.curr_branch
            self.lbl_last_repo.config(text=self.lbl_curr_repo.cget("text"))
            self.lbl_last_branch.config(text=self.lbl_curr_branch.cget("text"))
            self.lbl_last_status.config(text=self.lbl_curr_status.cget("text"))

            # 3. 创建时间分支
            branch_name = self.get_formatted_time()
            repo.create_head(branch_name).checkout()
            self.log(f"🌱 已创建纯时间分支: {branch_name}")

            # 4. 提交改动
            if not is_clean:
                repo.git.add(A=True)
                repo.index.commit(f"Auto Wrap: {branch_name}")
                self.log(f"📦 已打包本地改动。")

            # 5. 推送云端
            origin = repo.remote('origin') if 'origin' in repo.remotes else repo.create_remote('origin', url)
            origin.set_url(url)
            self.log(f"🚀 正在推送到 GitHub...")
            origin.push(branch_name, force=True)
            self.log("✅ 代码已安全上云！")

            # 6. 刷新界面 (此时现场一定干净，复制按钮会自动变亮)
            self.update_status()

        except Exception as e:
            self.log(f"❌ 流水线失败: {e}")

    # --- 存档与基础设置 ---
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
        tk.Button(win, text="保存并初始化", command=lambda: self.save_and_init(win)).pack(pady=10)

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