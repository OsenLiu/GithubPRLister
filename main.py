import requests
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import csv
import threading
import os  # Import os module for file operations

PR_PER_PAGE_OPTIONS = [20, 50, 100]
CONFIG_FILE = "pr_lister_config.txt"  # Configuration file name

class PRListApp:
    def __init__(self, root):
        self.root = root
        root.title("GitHub Pull Request Lister")

        self.all_prs_data = []
        self.current_page = 1
        self.prs_per_page = PR_PER_PAGE_OPTIONS[0]
        self.total_pages = 1
        self.is_loading = False
        self.animation_id = None

        # --- UI Elements ---
        # Repository Information Frame
        repo_frame = ttk.LabelFrame(root, text="Repository Information", padding=10)
        repo_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ttk.Label(repo_frame, text="Owner:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.repo_owner_entry = ttk.Entry(repo_frame, width=30)
        self.repo_owner_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(repo_frame, text="Name:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.repo_name_entry = ttk.Entry(repo_frame, width=30)
        self.repo_name_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(repo_frame, text="GitHub Token (Optional):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.github_token_entry = ttk.Entry(repo_frame, width=30, show="*")
        self.github_token_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Filter Frame
        filter_frame = ttk.LabelFrame(root, text="Filter Options", padding=10)
        filter_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        ttk.Label(filter_frame, text="Creator Username:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.filter_creator_entry = ttk.Entry(filter_frame, width=30)
        self.filter_creator_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(filter_frame, text="Unclosed Days (>=):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.filter_days_entry = ttk.Entry(filter_frame, width=10)
        self.filter_days_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.fetch_button = ttk.Button(root, text="Get Pull Requests", command=self.start_fetch_process)
        self.fetch_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        # Loading Indicator
        self.loading_label = ttk.Label(root, text="", font=("Arial", 10))
        self.loading_label.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.loading_label.grid_remove()

        # PR List Treeview Frame
        pr_tree_frame = ttk.LabelFrame(root, text="Pull Requests", padding=10)
        pr_tree_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        self.pr_tree = ttk.Treeview(pr_tree_frame, columns=("Title", "Creator", "Created At", "Closed At", "Duration (Days)"), show="headings")
        self.pr_tree.heading("Title", text="Title")
        self.pr_tree.heading("Creator", text="Creator")
        self.pr_tree.heading("Created At", text="Created At")
        self.pr_tree.heading("Closed At", text="Closed At")
        self.pr_tree.heading("Duration (Days)", text="Duration (Days)")
        self.pr_tree.column("Title", width=300)
        self.pr_tree.column("Creator", width=100)
        self.pr_tree.column("Created At", width=150)
        self.pr_tree.column("Closed At", width=150)
        self.pr_tree.column("Duration (Days)", width=100)
        self.pr_tree.pack(fill="both", expand=True)

        # Pagination Frame
        pagination_frame = ttk.Frame(root, padding=10)
        pagination_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")

        ttk.Label(pagination_frame, text="items of one page:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.prs_per_page_combo = ttk.Combobox(pagination_frame, values=PR_PER_PAGE_OPTIONS, state="readonly")
        self.prs_per_page_combo.set(PR_PER_PAGE_OPTIONS[0])
        self.prs_per_page_combo.bind("<<ComboboxSelected>>", self.change_prs_per_page)
        self.prs_per_page_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.prev_page_button = ttk.Button(pagination_frame, text="Previous", command=self.prev_page, state=tk.DISABLED)
        self.prev_page_button.grid(row=0, column=2, padx=5, pady=5)

        self.page_label = ttk.Label(pagination_frame, text="Page: 1/1")
        self.page_label.grid(row=0, column=3, padx=5, pady=5)

        self.next_page_button = ttk.Button(pagination_frame, text="Next", command=self.next_page, state=tk.DISABLED)
        self.next_page_button.grid(row=0, column=4, padx=5, pady=5)

        # Export CSV Button
        self.export_csv_button = ttk.Button(root, text="export CSV", command=self.export_to_csv, state=tk.DISABLED)
        self.export_csv_button.grid(row=5, column=0, padx=10, pady=10, sticky="ew")

        root.columnconfigure(0, weight=1)
        repo_frame.columnconfigure(1, weight=1)
        filter_frame.columnconfigure(1, weight=1)
        pr_tree_frame.columnconfigure(0, weight=1)
        pagination_frame.columnconfigure(4, weight=1)

        # Load configuration at startup
        self.load_config()

        # Save configuration when window is closed
        root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    self.repo_owner_entry.insert(0, config.get("repo_owner", ""))
                    self.repo_name_entry.insert(0, config.get("repo_name", ""))
                    self.github_token_entry.insert(0, config.get("github_token", ""))
            except (FileNotFoundError, json.JSONDecodeError):
                pass # Ignore if config file is not found or corrupted, use default values

    def save_config(self):
        config = {
            "repo_owner": self.repo_owner_entry.get(),
            "repo_name": self.repo_name_entry.get(),
            "github_token": self.github_token_entry.get()
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")

    def on_closing(self):
        self.save_config() # Save config before closing
        self.root.destroy()

    def get_github_prs(self, repo_owner, repo_name, github_token=None):
        headers = {}
        if github_token:
            headers['Authorization'] = f'token {github_token}'

        url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/pulls?state=all&per_page=100'
        all_prs = []
        page_num = 1
        while True:
            paged_url = f"{url}&page={page_num}"
            try:
                response = requests.get(paged_url, headers=headers)
                response.raise_for_status()
                prs = response.json()
                if not prs:
                    break
                all_prs.extend(prs)
                page_num += 1
            except requests.exceptions.RequestException as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to fetch pull requests: {e}"))
                return None
        return all_prs

    def calculate_duration(self, start_date_str, end_date_str):
        start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            duration = (end_date - start_date).days
            return duration
        else:
            return None

    def start_fetch_process(self):
        if not self.is_loading:
            repo_owner = self.repo_owner_entry.get()
            repo_name = self.repo_name_entry.get()

            if not repo_owner or not repo_name:
                messagebox.showerror("Error", "Please enter Repository Owner and Repository Name.")
                return

            self.start_loading_animation()
            self.fetch_button.config(state=tk.DISABLED)
            self.export_csv_button.config(state=tk.DISABLED)

            thread = threading.Thread(target=self.fetch_and_display_prs_thread)
            thread.start()

    def fetch_and_display_prs_thread(self):
        repo_owner = self.repo_owner_entry.get()
        repo_name = self.repo_name_entry.get()
        github_token = self.github_token_entry.get()
        filter_creator = self.filter_creator_entry.get().lower()
        filter_days_str = self.filter_days_entry.get()

        try:
            filter_days = int(filter_days_str) if filter_days_str else 0
        except ValueError:
            self.root.after(0, lambda: messagebox.showerror("Error", "Invalid value for 'Filter by Unclosed Days'. Please enter a number."))
            self.stop_loading_animation()
            self.root.after(0, lambda: self.fetch_button.config(state=tk.NORMAL))
            return

        prs_data = self.get_github_prs(repo_owner, repo_name, github_token)

        if prs_data is None:
            self.all_prs_data = []
        else:
            pr_list = []
            for pr in prs_data:
                creator = pr['user']['login']
                created_at = pr['created_at']
                closed_at = pr['closed_at']
                duration = self.calculate_duration(created_at, closed_at)

                pr_info = {
                    "Title": pr['title'],
                    "Creator": creator,
                    "Created At": created_at,
                    "Closed At": closed_at if closed_at else "Open",
                    "Duration (Days)": duration if duration is not None else "Open"
                }
                pr_list.append(pr_info)

            filtered_prs = pr_list
            if filter_creator:
                filtered_prs = [pr for pr in filtered_prs if filter_creator in pr["Creator"].lower()]
            if filter_days > 0:
                filtered_prs = [pr for pr in filtered_prs if pr["Duration (Days)"] == "Open" or (pr["Duration (Days)"] != "Open" and pr["Duration (Days)"] >= filter_days)]

            self.all_prs_data = filtered_prs
            self.current_page = 1

        self.root.after(0, self.update_ui_after_fetch)

    def update_ui_after_fetch(self):
        self.update_pr_display()
        if self.all_prs_data:
            self.export_csv_button.config(state=tk.NORMAL)
        else:
            self.export_csv_button.config(state=tk.DISABLED)
        self.stop_loading_animation()
        self.fetch_button.config(state=tk.NORMAL)

    def update_pr_display(self):
        for item in self.pr_tree.get_children():
            self.pr_tree.delete(item)

        start_index = (self.current_page - 1) * self.prs_per_page
        end_index = start_index + self.prs_per_page
        prs_to_display = self.all_prs_data[start_index:end_index]

        if not self.all_prs_data:
            self.total_pages = 1
        else:
            self.total_pages = (len(self.all_prs_data) + self.prs_per_page - 1) // self.prs_per_page

        self.page_label.config(text=f"Page: {self.current_page}/{self.total_pages}")

        self.prev_page_button.config(state=tk.DISABLED if self.current_page <= 1 else tk.NORMAL)
        self.next_page_button.config(state=tk.DISABLED if self.current_page >= self.total_pages else tk.NORMAL)

        if prs_to_display:
            for pr in prs_to_display:
                self.pr_tree.insert("", tk.END, values=(
                    pr["Title"],
                    pr["Creator"],
                    pr["Created At"],
                    pr["Closed At"],
                    pr["Duration (Days)"]
                ))
        elif self.all_prs_data and self.repo_owner_entry.get() and self.repo_name_entry.get():
            messagebox.showinfo("Info", "No pull requests found matching the filter criteria.")
        elif not self.all_prs_data and self.repo_owner_entry.get() and self.repo_name_entry.get():
            messagebox.showinfo("Info", "No pull requests found in this repository.")

    def change_prs_per_page(self, event):
        self.prs_per_page = int(self.prs_per_page_combo.get())
        self.current_page = 1
        self.update_pr_display()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_pr_display()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_pr_display()

    def export_to_csv(self):
        if not self.all_prs_data:
            messagebox.showinfo("Info", "No PR data to export.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    fieldnames = ["Title", "Creator", "Created At", "Closed At", "Duration (Days)"]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for pr in self.all_prs_data:
                        writer.writerow(pr)
                messagebox.showinfo("Info", f"PR data exported to: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export CSV: {e}")

    def start_loading_animation(self):
        self.is_loading = True
        self.loading_label.grid()
        self.animate_loading()

    def stop_loading_animation(self):
        self.is_loading = False
        self.loading_label.grid_remove()
        if self.animation_id:
            self.root.after_cancel(self.animation_id)
            self.animation_id = None

    def animate_loading(self):
        if not self.is_loading:
            return

        spinner = "|/-\\"
        current_spinner = spinner[0]
        if self.loading_label.cget("text") in spinner:
             current_index = spinner.find(self.loading_label.cget("text"))
             next_index = (current_index + 1) % len(spinner)
             current_spinner = spinner[next_index]

        self.loading_label.config(text=current_spinner)
        self.animation_id = self.root.after(100, self.animate_loading)


if __name__ == "__main__":
    root = tk.Tk()
    app = PRListApp(root)
    root.mainloop()